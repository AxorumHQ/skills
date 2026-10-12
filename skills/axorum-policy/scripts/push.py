#!/usr/bin/env python3
"""Put a policy in force in a sandbox that is already running.

Usage:
    push.py POLICY.axp [--url URL] [--dry-run]

First checks the policy against the world the sandbox at URL is running (its
run so far, as ``axorum-sandbox save-run`` writes it, not the world file on
disk), every warning counting as an error. A policy that does not compile,
that the check refuses though it compiles (``DSL3010``: it takes more of a
run's snapshot than a policy may), or that draws a lint is the policy's to
fix; one that draws only world-fit warnings (``DSL3xxx``) does not fit that
world. Then says which running totals the
change keeps and which start again at zero: the engine keeps a total whose
declaration is unchanged, so the declarations of the policy in force and of
this one are compared in the canonical layout the engine stores. Then, unless
``--dry-run``, puts it in force with ``axorum-sandbox policy``: from the
sandbox clock's current time, for every agent of that run. What that command
did is read from its exit code and its stdout (the id of the policy in force);
what it said on stderr is quoted, never read. When it could not finish (exit
2), the sandbox may still have taken the policy: an answer lost after the
change applied, or one this ``axorum-sandbox`` cannot read. The sandbox's
snapshot then says which policy is in force. A policy refused, by the check or
by the sandbox, changes nothing, and the refusal says why. The URL is
``--url``, else ``AXORUM_SANDBOX_URL``, else http://127.0.0.1:7340. This
script never starts, stops or restarts a sandbox.

Exit 0 when the policy is in force, changed or already (with ``--dry-run``:
when it would be taken), 3 when the check refused it (it does not compile, is
too large for a run's snapshot, draws a lint, or does not fit the running
world) or the sandbox refused it, 2
when the run at URL could not be saved (no sandbox answered there, say), the
policy is not in force after the sandbox could not be asked, whether it is in
force could not be told, or no installed ``axorum-sandbox`` can check, read the
running world, or push a policy.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path

from _common import UPGRADE, fail, sandbox_binary, sandbox_has

DEFAULT_URL = "http://127.0.0.1:7340"
URL_VAR = "AXORUM_SANDBOX_URL"
AGGREGATE = re.compile(r"^aggregate ([a-z0-9_]+) ")
WORLD_FIT = "DSL3"
ERROR_CODE = re.compile(r"^\s*error\[(DSL\d{4})\]", re.MULTILINE)
COMPILE_CODES = ("DSL0", "DSL1")

NOT_COMPILED = (
    "this policy does not compile, so nothing was pushed: fix it as the error above says, "
    "check it with check.py, and push again."
)
CHECK_REFUSED = (
    "the check refused this policy ({codes}), so nothing was pushed: it compiles, but fix it "
    "as the error above says, check it with check.py, and push again."
)
NOT_CLEAN = (
    "this policy draws {codes}, so nothing was pushed: fix it as each warning above says, "
    "check it with check.py, and push again."
)
MISFIT = (
    "the sandbox at {url} runs a world this policy does not fit{codes}, so nothing was "
    "pushed. Where a warning's help says how, fix the policy to fit that world. A policy "
    "change cannot add an agent, a budget, an account or a currency to a running world: "
    "those need the user to restart their sandbox with the new world, which starts a new run."
)
REFUSED = (
    "the sandbox refused this policy, so the policy in force did not change: fix it as the "
    "reason above says, check it with check.py, and push again."
)
UNREADABLE = (
    "{binary} cannot read the run the sandbox at {url} serves: it refuses even the policy "
    "that run has in force, so it is older than the sandbox. Nothing was pushed: upgrade it "
    "({upgrade}) and push again."
)
IN_FORCE = (
    "in force: `axorum-sandbox policy` did not finish, for the reason above, but the sandbox "
    "at {url} has this policy ({draft}) in force now. If the reason is an answer it could not "
    "read, upgrade it ({upgrade})."
)
UNCHANGED = (
    "not in force: nothing changed, the sandbox at {url} still has {before} in force. "
    "`axorum-sandbox policy` did not finish, for the reason above. If theirs is older than "
    "this axorum-sandbox, it cannot take a policy while it runs: restarting it with a newer "
    "one starts a new run, which is the user's call."
)
UNTOLD = (
    "could not tell whether this policy is in force: check the sandbox. `axorum-sandbox "
    "policy` did not finish, for the reason above, and the sandbox at {url} then {why}. Its "
    "snapshot (GET {url}/_sandbox/snapshot) names the policy in force under reports.policy: "
    "this one is {draft}. If no sandbox answers there, ask the user to start theirs, or pass "
    "--url with its address."
)


def declarations(layout: str) -> dict[str, str]:
    """Each running total a canonical layout declares, by name, with its declaration. Pure.

    The canonical layout writes each declaration one way, so two of these
    lines are equal exactly when the declarations are.
    """
    found: dict[str, str] = {}
    for line in layout.splitlines():
        match = AGGREGATE.match(line.strip())
        if match:
            found[match.group(1)] = line.strip()
    return found


def refusal(codes: Sequence[str], url: str) -> str:
    """Say why a policy whose check drew ``codes`` was not pushed, and who fixes it. Pure.

    Only world-fit codes (``DSL3xxx``) say the running world is the trouble;
    a lint is the policy's to fix.
    """
    named = ", ".join(sorted(set(codes)))
    if codes and all(code.startswith(WORLD_FIT) for code in codes):
        return MISFIT.format(url=url, codes=f" ({named})")
    return NOT_CLEAN.format(codes=named)


def not_passed(stderr: str) -> str:
    """Say why a policy whose check failed on its own, saying ``stderr``, was not pushed. Pure.

    The check refuses some policies that compile, such as one that takes more
    of a run's snapshot than a policy may (``DSL3010``). The codes of the
    errors it printed tell those apart from a policy that does not compile
    (``DSL0xxx``, ``DSL1xxx``).
    """
    refused = sorted(
        {code for code in ERROR_CODE.findall(stderr) if not code.startswith(COMPILE_CODES)}
    )
    return CHECK_REFUSED.format(codes=", ".join(refused)) if refused else NOT_COMPILED


def totals(running: dict[str, str], draft: dict[str, str]) -> list[str]:
    """Say what the change does to each running total, kept or started again at zero.

    A total whose declaration reads the same in both policies keeps its
    figure; a changed or new one starts at zero from the change; a dropped
    one is gone.
    """
    kept = [name for name in draft if running.get(name) == draft[name]]
    changed = [name for name in draft if name in running and running[name] != draft[name]]
    new = [name for name in draft if name not in running]
    dropped = [name for name in running if name not in draft]
    lines = []
    for label, names in (
        ("keep their figures", kept),
        ("start again at zero, their declaration changed", changed),
        ("are new and start at zero", new),
        ("are dropped", dropped),
    ):
        if names:
            lines.append(f"  {label}: {', '.join(sorted(names))}")
    return lines or ["  none: neither policy keeps a running total"]


def unfinished(draft: str, before: str, after: str | None) -> str:
    """Say what an unfinished push left in force, from the sandbox's snapshots. Pure.

    ``draft`` is the pushed policy's id, ``before`` the id in force before
    the push, and ``after`` the id in force after it (``None`` when the
    sandbox did not say). Answers ``"in force"``, ``"unchanged"`` (the policy
    in force before still is), or ``"untold"``.
    """
    if after is None:
        return "untold"
    if after == draft:
        return "in force"
    if after == before:
        return "unchanged"
    return "untold"


def in_force(url: str) -> tuple[str, str]:
    """Read the id and source of the policy the sandbox at ``url`` has in force.

    Both are "" when none is. Raises ``OSError`` (``urllib.error.URLError``
    among them) when the sandbox does not answer, and ``ValueError`` or
    ``KeyError`` when its answer is not its snapshot.
    """
    request = urllib.request.Request(url.rstrip("/") + "/_sandbox/snapshot")
    with urllib.request.urlopen(request, timeout=30) as answer:
        snapshot = json.loads(answer.read())
    document = snapshot["reports"].get("policy") or {}
    return str(document.get("policy", "")), str(document.get("source", ""))


def run(binary: str, *args: str, given: str | None = None) -> subprocess.CompletedProcess[str]:
    """Run one ``axorum-sandbox`` command, ``given`` on its stdin, and keep what it printed."""
    return subprocess.run([binary, *args], input=given, capture_output=True, text=True, check=False)


def compiled(binary: str, source: str) -> tuple[str, str]:
    """Answer the id and the canonical layout the engine stores for the policy ``source``.

    Both are "" for no source. Raises ``ValueError`` when the source does not
    compile.
    """
    if not source:
        return "", ""
    checked = run(binary, "check", "-", "--print", given=source)
    if checked.returncode != 0:
        raise ValueError(last_line(checked.stderr))
    verdict = json.loads(checked.stdout)
    return str(verdict["policy"]), str(verdict["canonical"])


def last_line(stderr: str) -> str:
    """Answer the last thing a command said on stderr, without its program-name prefix."""
    lines = [line for line in stderr.splitlines() if line.strip()]
    said = lines[-1] if lines else "it said nothing"
    return said.removeprefix("axorum-sandbox: ")


def preflight(binary: str, policy: Path, url: str) -> int | None:
    """Check ``policy`` against the world the sandbox at ``url`` runs.

    Answers ``None`` when it passes, else the exit code after saying why the
    policy cannot go in force, decided from exit codes alone: the warnings'
    codes, from the check's verdict, say whether the policy or the world is
    the trouble. A policy that compiles alone but not against the run is
    told apart from a run this checker cannot read by checking the policy in
    force against the same run: that one always fits its own run.
    """
    with tempfile.TemporaryDirectory() as scratch:
        world = Path(scratch) / "running-world.yaml"
        saved = run(binary, "save-run", "--url", url, "--output", str(world))
        if saved.returncode != 0:
            return fail(
                f"could not save the run of the sandbox at {url} "
                f"({last_line(saved.stderr)}), so nothing was pushed. If no sandbox answers "
                "there, ask the user to start theirs with `axorum-sandbox serve <world.yaml>`, "
                "or pass --url with its address."
            )
        checked = run(binary, "check", str(policy), "--world", str(world), "-q")
        print(checked.stderr, end="", file=sys.stderr)
        if checked.returncode == 0:
            warnings = json.loads(checked.stdout).get("warnings", [])
            codes = [str(warning["code"]) for warning in warnings]
            return fail(refusal(codes, url), 3) if codes else None
        alone = run(binary, "check", str(policy), "-q")
        if alone.returncode != 0:
            return fail(not_passed(alone.stderr), 3)
        try:
            _, source = in_force(url)
        except (OSError, ValueError, KeyError) as unread:
            return fail(
                f"the sandbox at {url} could not say which policy it has in force ({unread}), "
                "so nothing was pushed."
            )
        own = run(binary, "check", "-", "--world", str(world), "-q", given=source)
    if own.returncode != 0:
        return fail(UNREADABLE.format(binary=binary, url=url, upgrade=UPGRADE))
    return fail(MISFIT.format(url=url, codes=""), 3)


def push(binary: str, policy: Path, url: str, draft: str, before: str) -> int:
    """Put the policy in force with ``axorum-sandbox policy``, and say what happened.

    Decides from the command's exit code: 0 in force (its stdout, the id of
    the policy in force, is passed on), 3 refused. Any other code means it
    did not finish, maybe after the sandbox took the policy, so the
    sandbox's snapshot decides: ``draft`` (this policy's id) in force, or
    ``before`` (the id in force before) still in force, or neither said.
    Its stderr, what changed and when or why not, is quoted as it is.
    """
    pushed = run(binary, "policy", str(policy), "--url", url)
    print(pushed.stderr, end="", file=sys.stderr)
    if pushed.returncode == 0:
        print(pushed.stdout, end="")
        return 0
    if pushed.returncode == 3:
        return fail(REFUSED, 3)
    try:
        after: str | None = in_force(url)[0]
        why = ""
    except (OSError, ValueError, KeyError) as unread:
        after, why = None, f"did not answer for its snapshot ({unread})"
    state = unfinished(draft, before, after)
    if state == "in force":
        print(IN_FORCE.format(url=url, draft=draft, upgrade=UPGRADE), file=sys.stderr)
        print(draft)
        return 0
    if state == "unchanged":
        return fail(UNCHANGED.format(url=url, before=before))
    why = why or f"named {after} in force, neither this policy nor the one before ({before})"
    return fail(UNTOLD.format(url=url, why=why, draft=draft))


def main(argv: Sequence[str] | None = None) -> int:
    """Check the policy the command line names against the running world, and push it."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    parser.add_argument("policy", type=Path, help="the policy file")
    parser.add_argument(
        "--url",
        default=os.environ.get(URL_VAR, DEFAULT_URL),
        help=f"the running sandbox (default: ${URL_VAR}, else {DEFAULT_URL})",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="check and report, but put nothing in force"
    )
    args = parser.parse_args(argv)

    if not args.policy.is_file():
        return fail(f"cannot read {args.policy}: no such file")
    binary = sandbox_binary()
    needs = ["save-run", "check"] if args.dry_run else ["save-run", "check", "policy"]
    if binary is None or not all(sandbox_has(binary, command) for command in needs):
        return fail(
            f"no axorum-sandbox that can {'check' if args.dry_run else 'check and push'} a "
            f"policy: install or upgrade it ({UPGRADE})"
        )

    refused = preflight(binary, args.policy, args.url)
    if refused is not None:
        return refused
    try:
        draft, layout = compiled(binary, args.policy.read_text(encoding="utf-8"))
        before, source = in_force(args.url)
        running = declarations(compiled(binary, source)[1])
    except (OSError, ValueError, KeyError) as unread:
        return fail(f"the sandbox at {args.url} could not say what totals it keeps ({unread})")
    print("Running totals, if this policy goes in force:", file=sys.stderr)
    for line in totals(running, declarations(layout)):
        print(line, file=sys.stderr)
    if args.dry_run:
        print("dry run: nothing was pushed", file=sys.stderr)
        return 0
    return push(binary, args.policy, args.url, draft, before)


if __name__ == "__main__":
    sys.exit(main())
