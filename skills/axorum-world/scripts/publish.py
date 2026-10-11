#!/usr/bin/env python3
"""Publish a world, and the policy it names, to the console's library.

Usage:
    publish.py WORLD.yaml [--dry-run] [--replace]

Runs ``axorum-sandbox publish world WORLD --json [--dry-run] [--replace]`` with the
console secret of the sandbox the world was pulled from
(``AXORUM_SANDBOX_SINK`` and ``AXORUM_SANDBOX_TOKEN``). The sandbox checks the
world first, counting a warning as an error, so a world that would be refused
is never sent. It then writes the policy file the world names, then the
world, its name included, as the world attached to that sandbox; the secret
may write nothing else.

- The policy: a policy file named like the world's current policy updates it,
  or leaves it unchanged; so does one named like a policy this sandbox
  created that nobody has edited since. A name new to the library creates a
  policy. A name held by any other library policy is refused, one this
  sandbox created that a person has since edited included: rename the policy
  file and the world's ``policy: {file: ...}`` line to publish a copy under a
  new name, or ask an owner of that policy to attach it to the world in the
  console.
- The world: it is updated, or renamed when its ``world:`` line changed. A
  name another world in the organization holds is refused: rename the world
  in its ``world:`` line, not the policy file.

``--dry-run`` checks and says what would be written, writing nothing.

A publish writes only over what ``axorum-sandbox pull`` fetched into the
world's directory (``.axorum-pulled.json``): a world or policy saved in the
console since the pull, or one the directory holds no pull of, is refused
before anything is written. ``--replace`` overwrites the console's version of
each with the files instead; pass it only when the user has said to overwrite
the console's version. A save made in the console while the publish runs is
still refused. With ``--dry-run`` the sandbox names each record it would
replace and the size of each text.

What the sandbox wrote is read from its JSON report, never from its prose:
each change the console confirmed is printed on stdout, and what the sandbox
says passes through on stderr. A publish changes only the console library's
copy: when a change landed, the sandbox says that a running ``serve`` keeps
the world it started with until it is restarted, and that ``serve`` with no
world file starts on the published copy.

Exit 0 when published (with ``--dry-run``, when it would be). Exit 3 when the
check or the console refused it, saying why; when the console refused the
world after the policy was written, it says which policy was written. Exit 2
when it could not do its job: no ``axorum-sandbox`` that can publish a world,
a variable missing, the console out of reach, or a write the console did not
confirm. A write not confirmed may have landed, and so may anything when the
sandbox's report cannot be read: running the same publish again finishes the
job, and says ``unchanged`` for what had landed. Nothing else is ever reported
as published.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from _common import UPGRADE, fail, sandbox_binary, sandbox_has, sandbox_offers

CANNOT_PUBLISH = (
    "nothing was published: this axorum-sandbox cannot publish a world. Upgrade it "
    "(`{upgrade}`) and run this again. Until then, the world can be saved in the console "
    "by hand and attached to the sandbox, and `axorum-sandbox pull` fetches it back."
)

CANNOT_REPLACE = (
    "nothing was published: this axorum-sandbox's publish takes no --replace. Upgrade it "
    "(`{upgrade}`) and run this again."
)

MAY_HAVE_LANDED = (
    "it may have landed. Once the cause above is fixed, run the same publish again: it "
    "finishes the job, and says `unchanged` for what had landed."
)

LANDED = {"updated", "renamed", "created"}
"""The changes that write: ``unchanged`` writes nothing, and a world whose policy is
inline publishes no policy, its report's ``policy`` being ``null``."""


def outcome(returncode: int) -> int:
    """Answer the script's exit code for the sandbox's.

    0 and 3 pass through; anything else, a crash included, means the job was
    not done, so it is 2 and never a success.
    """
    return returncode if returncode in (0, 3) else 2


def read_report(stdout: str) -> dict[str, Any] | None:
    """Read the sandbox's JSON report, its last line on stdout, or ``None`` when there is none."""
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        return None
    try:
        report = json.loads(lines[-1])
    except ValueError:
        return None
    return report if isinstance(report, dict) else None


def confirmed(report: dict[str, Any]) -> list[tuple[str, str, str]]:
    """List what the console confirmed, as (what, name, change), the world's last.

    A write the console did not confirm has no ``change`` and is left out.
    """
    found = []
    for what in ("policy", "world"):
        entry = report.get(what)
        if isinstance(entry, dict) and isinstance(entry.get("change"), str):
            change = entry["change"]
            if what == "world" and change == "renamed" and entry.get("from"):
                change = f"renamed from {entry['from']}"
            found.append((what, str(entry.get("name")), change))
    return found


def lines(report: dict[str, Any]) -> list[str]:
    """Say each confirmed change in a line, ``would be`` on a dry run."""
    would = "would be " if report.get("dry_run") else ""
    return [
        f"{what} {name}: {change if change == 'unchanged' else would + change}"
        for what, name, change in confirmed(report)
    ]


def verdict(returncode: int, report: dict[str, Any] | None) -> tuple[int, list[str], list[str]]:
    """Answer the exit code, the lines for stdout and the lines for stderr. Pure.

    Reads only the sandbox's exit code and its JSON report: whether a write was
    ``sent``, what the console confirmed, and the write it left ``unconfirmed``.
    When the report cannot be read, what was written cannot be told: a refusal
    leaves it to the sandbox's reason, and anything else may have landed.
    """
    code = outcome(returncode)
    if report is None:
        if code == 3:
            return 3, [], ["refused: the reason above says what was written, if anything."]
        return (
            2,
            [],
            [
                f"the sandbox's report could not be read, so what it wrote is unknown: "
                f"{MAY_HAVE_LANDED}"
            ],
        )
    if code == 0:
        return 0, lines(report), []
    written = [
        f"the {what} {name} was {change}"
        for what, name, change in confirmed(report)
        if change.split()[0] in LANDED
    ]
    if not report.get("sent") or (code == 3 and not written):
        reason = "the reason is above" if code == 3 else "it could not try"
        return code, [], [f"nothing was published: {reason}."]
    said = f"{' and '.join(written)}, but " if written else ""
    if code == 3:
        return 3, [], [f"{said}the console refused the rest, and nothing else was written."]
    unconfirmed = report.get("unconfirmed")
    what = f"the {unconfirmed} write" if isinstance(unconfirmed, str) else "a write"
    return 2, [], [f"{said}the console did not confirm {what}: {MAY_HAVE_LANDED}"]


def main(argv: Sequence[str] | None = None) -> int:
    """Publish the world the command line names."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    parser.add_argument("world", type=Path, help="the world file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="check and say what would be written, writing nothing",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="overwrite the console's version with these files, whatever was pulled; "
        "only when the user has said to",
    )
    args = parser.parse_args(argv)

    if not args.world.is_file():
        return fail(f"cannot find the world {args.world}")
    sandbox = sandbox_binary()
    if sandbox is None or not sandbox_has(sandbox, "publish", "world"):
        return fail(CANNOT_PUBLISH.format(upgrade=UPGRADE))
    if args.replace and not sandbox_offers(sandbox, "--replace", "publish", "world"):
        return fail(CANNOT_REPLACE.format(upgrade=UPGRADE))
    run = [sandbox, "publish", "world", str(args.world), "--json"]
    if args.dry_run:
        run.append("--dry-run")
    if args.replace:
        run.append("--replace")
    try:
        done = subprocess.run(run, stdout=subprocess.PIPE, text=True, check=False)
    except OSError as bad:
        return fail(f"nothing was published: {sandbox} did not run: {bad}")
    code, out, err = verdict(done.returncode, read_report(done.stdout))
    for line in out:
        print(line)
    for line in err:
        print(line, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
