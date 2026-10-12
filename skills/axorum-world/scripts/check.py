#!/usr/bin/env python3
"""Check a world and the policy it runs, as the sandbox checks them before it loads anything.

Usage:
    check.py WORLD.yaml [--policy POLICY.axp] [--json]
    check.py --policy POLICY.axp [--json]

Runs ``axorum-sandbox check POLICY --world WORLD --deny-warnings``. The world
is read strictly and checked for every problem the format's reference lists
under "What the world check refuses"; then the policy is compiled and judged
against the world: the currencies it declares, and the mandates and parties
the policy names, opened and bound under the ids their names derive, with
the roles and capabilities the policy expects, and every party a rule's
``specific(...)`` names (DSL3001 to DSL3009), and what the policy takes of
a run's snapshot (DSL3010). Each policy change the world's
timeline schedules, inline or in a file beside the world, is compiled and
judged against the world too; its lint warnings are not reported or counted.

The policy checked is ``--policy``, else the file the world names (beside the
world), else the policy the world holds inline. Its errors, warnings, the
engine's plain-English rendering and the id table for parties and mandates go
to stderr, as the engine prints them. ``--json`` also prints the checker's JSON
verdict on stdout.

With no world, the policy alone is checked, and the parties and mandates it
names are listed with the ids to bind and open them under: what a world needs
before it exists.

Exit 0 when the world holds together, its policy compiles with no error and
no warning against it, and the world can run every policy change it
schedules; 3 when not; 2 when no ``axorum-sandbox`` with ``check`` is
installed, a world is named and the installed one does not judge the policy
changes a world schedules (one from before that check passes them unread), a
file to check cannot be found, or the checker ended any other way, a crash
included. Nothing else is ever reported as clean.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from _common import (
    UPGRADE,
    fail,
    judges_scheduled_changes,
    sandbox_binary,
    sandbox_has,
    world_policy,
)

UNJUDGED = (
    "this axorum-sandbox does not judge the policy changes a world schedules, so its "
    "pass would not mean the world can run them: {upgrade}"
)


def policy_input(world: Path, policy: Path | None) -> tuple[str, str | None] | str:
    """Name the policy argument to check and the text to pipe in, or say why there is none.

    A policy file is passed by path; a policy the world holds inline is passed
    as ``-`` with its text on stdin.
    """
    if policy is not None:
        return named_policy(policy)
    try:
        text = world.read_text(encoding="utf-8")
    except OSError as bad:
        return f"cannot read {world}: {bad}"
    found = world_policy(text)
    if found is None:
        return (
            f"cannot tell which policy {world} runs: write `policy: {{file: policy.axp}}`, "
            "or name the policy with --policy"
        )
    kind, value = found
    if kind == "file":
        return named_policy(world.parent / value)
    return "-", value


def named_policy(policy: Path) -> tuple[str, None] | str:
    """Pass a policy file by path, or say it is not there."""
    if not policy.is_file():
        return f"cannot find the policy {policy}: write it first (the axorum-policy skill)"
    return str(policy), None


def outcome(returncode: int) -> int:
    """Answer the script's exit code for the checker's.

    0 and 3 are the checker's verdicts and pass through; anything else means
    the check was not done, so it is 2 and never clean.
    """
    return returncode if returncode in (0, 3) else 2


def id_table(verdict: dict[str, Any]) -> str:
    """List the parties and mandates a policy names, with the ids a world must use for them."""
    lines = ["Parties, by the id a world binds each agent under (a principal is never bound):"]
    lines += [
        f"  {party['name']:<20} {party['kind']:<10} {party['party']}"
        for party in verdict.get("parties", [])
    ]
    mandates = verdict.get("mandates", [])
    if mandates:
        lines.append("Mandates the policy reads by name, by the id a world opens each under:")
        lines += [f"  {mandate['name']:<20} {mandate['mandate']}" for mandate in mandates]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Check the world the command line names, or the policy alone."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    parser.add_argument("world", type=Path, nargs="?", help="the world file")
    parser.add_argument("--policy", type=Path, help="a policy to check in place of the world's")
    parser.add_argument("--json", action="store_true", help="also print the JSON verdict on stdout")
    args = parser.parse_args(argv)

    if args.world is None and args.policy is None:
        return fail("name a world, or a policy with --policy to list the ids a world needs")
    if args.world is not None and not args.world.is_file():
        return fail(f"cannot find the world {args.world}")
    sandbox = sandbox_binary()
    if sandbox is None or not sandbox_has(sandbox, "check"):
        return fail(f"no axorum-sandbox with `check`: {UPGRADE}")
    if args.world is not None and not judges_scheduled_changes(sandbox):
        return fail(UNJUDGED.format(upgrade=UPGRADE))
    found = (
        named_policy(args.policy) if args.world is None else policy_input(args.world, args.policy)
    )
    if isinstance(found, str):
        return fail(found)
    policy, piped = found
    world = ["--world", str(args.world)] if args.world is not None else []
    run = [sandbox, "check", policy, *world, "--deny-warnings"]
    try:
        done = subprocess.run(run, input=piped, stdout=subprocess.PIPE, text=True, check=False)
    except OSError as bad:
        return fail(f"the checker {sandbox} did not run: {bad}")
    if args.json:
        sys.stdout.write(done.stdout)
    code = outcome(done.returncode)
    if args.world is None and code == 0:
        with contextlib.suppress(ValueError, KeyError, TypeError):
            print(id_table(json.loads(done.stdout)), file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
