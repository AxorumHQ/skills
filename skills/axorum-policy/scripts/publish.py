#!/usr/bin/env python3
"""Publish a policy to the console's library, through the user's console-connected sandbox.

Usage:
    publish.py POLICY.axp [--dry-run] [--replace]

Runs ``axorum-sandbox publish policy --json``. It reaches the console the way a
sandbox reports its runs there: ``AXORUM_SANDBOX_SINK`` names the console and
``AXORUM_SANDBOX_TOKEN`` holds the sandbox's secret, which is never printed.
The command checks the policy alone, then against the world attached to that
sandbox in the console, every warning counting as an error, and replaces the
library's text of the policy that world names. The file's whole name, ``.axp``
included, must be that policy's name in the library, as the policy file a
pulled world names already is: publish that file, never a copy made to
publish. With ``--dry-run`` it checks and says whether the text would be
updated or is unchanged, and publishes nothing. Nothing here touches a running
sandbox.

A publish writes only over the text ``axorum-sandbox pull`` fetched into the
file's directory (``.axorum-pulled.json``): a policy saved in the console
since the pull, or one the directory holds no pull of, is refused and nothing
is written. ``--replace`` overwrites the console's version with the file
instead; pass it only when the user has said to overwrite the console's
version. A save made in the console while the publish runs is still refused.
With ``--dry-run`` the command names the policy it would replace and the size
of each text.

What was written is read from the command's JSON account, never from its
prose: whether any write left it (``sent``), whether the console failed to
confirm one (``unconfirmed``), and the change it confirmed (``policy``).

Exit 0 when the policy is published or unchanged (with ``--dry-run``: when it
would be), 3 when the check or the console refused it, with the reason and its
fix, and 2 when it could not try or did not finish: a variable is not set, the
console refused the secret, no installed ``axorum-sandbox`` can publish a
policy, or the console stopped answering after the text was sent, which may
have left it in the library: publishing the same file again finishes it, and
says ``unchanged`` if it had landed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from _common import UPGRADE, fail, sandbox_binary, sandbox_has, sandbox_offers

SINK_VAR = "AXORUM_SANDBOX_SINK"
TOKEN_VAR = "AXORUM_SANDBOX_TOKEN"

NOT_TRIED = (
    f"nothing was published: it could not try. When the reason names {SINK_VAR} or "
    f"{TOKEN_VAR}, ask the user to set it in their own shell, as the console's sandbox page "
    "shows, and to run this again. Never ask them to paste the token into the conversation."
)
NOT_FINISHED = (
    "the publish did not finish: the reason is above. If it stopped at the write, the "
    "library may already have the new text: once the cause is fixed, publish the same "
    "file again, which ends `updated`, or `unchanged` when the text had landed."
)
NOT_TAKEN = "nothing was published: the reason is above."
TOOK = "the console took {what} before the publish stopped: the reason is above."


def account(stdout: str) -> Mapping[str, Any] | None:
    """Answer the command's JSON account: the last line of ``stdout`` that is an object.

    Answers ``None`` when there is none, as from a command that stopped before
    it could say. Pure.
    """
    for line in reversed(stdout.splitlines()):
        try:
            document = json.loads(line)
        except ValueError:
            continue
        if isinstance(document, dict):
            return document
    return None


def change_line(document: Mapping[str, Any]) -> str:
    """Write the line a person reads for a published (or, dry, publishable) policy. Pure."""
    policy = document.get("policy") or {}
    change = str(policy.get("change", "unchanged"))
    if document.get("dry_run") and change != "unchanged":
        change = f"would be {change}"
    ident = f" ({policy['id']})" if policy.get("id") else ""
    return f"policy {policy.get('name', '?')}{ident}: {change}"


def taken(document: Mapping[str, Any]) -> str | None:
    """Name the write the console confirmed, if the account shows one. Pure."""
    policy = document.get("policy") or {}
    change = policy.get("change")
    if change in (None, "unchanged"):
        return None
    return f"the policy {policy.get('name', '?')} ({change})"


def what_happened(code: int, document: Mapping[str, Any] | None, dry_run: bool) -> str:
    """Say what a publish that exited ``code`` left behind, from its JSON account. Pure.

    A dry run writes nothing. Otherwise only the account says whether a write
    left the command (``sent``), whether the console failed to confirm one
    (``unconfirmed``), and what it confirmed (``policy``'s ``change``); an
    account that does not say, or none, claims nothing.
    """
    sent = document.get("sent") if document is not None else None
    if dry_run or sent is False:
        return NOT_TAKEN if code == 3 else NOT_TRIED
    if sent is not True or document is None:
        return NOT_FINISHED
    if "unconfirmed" not in document or document["unconfirmed"]:
        return NOT_FINISHED
    confirmed = taken(document)
    return TOOK.format(what=confirmed) if confirmed else NOT_TAKEN


def publish(binary: str, policy: Path, dry_run: bool, replace: bool) -> int:
    """Run ``axorum-sandbox publish policy --json`` and say what happened."""
    command = [binary, "publish", "policy", str(policy), "--json"]
    if dry_run:
        command.append("--dry-run")
    if replace:
        command.append("--replace")
    published = subprocess.run(command, capture_output=True, text=True, check=False)
    print(published.stderr, end="", file=sys.stderr)
    document = account(published.stdout)
    if published.returncode == 0:
        print(change_line(document) if document is not None else published.stdout.strip())
        return 0
    code = 3 if published.returncode == 3 else 2
    return fail(what_happened(code, document, dry_run), code)


def main(argv: Sequence[str] | None = None) -> int:
    """Publish the policy the command line names to the console's library."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    parser.add_argument(
        "policy", type=Path, help="the policy file the world names, its whole name the library's"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="check and report, but publish nothing"
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="overwrite the console's version with this file, whatever was pulled; "
        "only when the user has said to",
    )
    args = parser.parse_args(argv)

    if not args.policy.is_file():
        return fail(f"cannot read {args.policy}: no such file")
    binary = sandbox_binary()
    if binary is None or not sandbox_has(binary, "publish", "policy"):
        return fail(
            f"no axorum-sandbox that can publish a policy to the console: install or "
            f"upgrade it ({UPGRADE})"
        )
    if args.replace and not sandbox_offers(binary, "--replace", "publish", "policy"):
        return fail(
            f"nothing was published: this axorum-sandbox's publish takes no --replace: "
            f"upgrade it ({UPGRADE})"
        )
    return publish(binary, args.policy, args.dry_run, args.replace)


if __name__ == "__main__":
    sys.exit(main())
