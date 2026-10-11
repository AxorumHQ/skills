#!/usr/bin/env python3
"""Check a policy offline, and against the world it will run in, as the engine checks it.

Usage:
    check.py POLICY.axp [--world WORLD.yaml] [--print] [--json]

Runs ``axorum-sandbox check --deny-warnings``, which compiles the policy with
the engine's own parser, validator and linter. With ``--world`` it also checks
the policy against that world: currencies the world declares, mandates and
parties the policy names, under the ids their names derive; and each policy
change the world's timeline schedules, compiled against the world and never
linted. Without ``axorum-sandbox``, it runs ``axorum policy check
--deny-warnings``, which checks the policy alone, and exits 2 if a world was
named.

Errors, lints, the engine's plain-English rendering and, with a world, the id
the world must use for each mandate and party go to stderr, as the engine
prints them. ``--json`` also prints the checker's JSON document on stdout.
Exit 0 when the policy compiles with no error and no lint (and, with a world,
the world can run it and every policy change it schedules), 3 when it does
not, 2 when no checker could run, or a world was named and no installed
checker reads one or judges the policy changes it schedules (an
``axorum-sandbox`` from before that check passes them unread).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence

from _common import (
    UPGRADE,
    axorum_binary,
    fail,
    judges_scheduled_changes,
    sandbox_binary,
    sandbox_has,
)

UNJUDGED = (
    "this axorum-sandbox does not judge the policy changes a world schedules, so its "
    "pass would not mean the world can run them: {upgrade}"
)


def command(policy: str, world: str | None, show: bool) -> tuple[list[str], bool] | None:
    """Name the check to run and whether it reads the world, or ``None`` with no checker."""
    printing = ["--print"] if show else []
    sandbox = sandbox_binary()
    if sandbox is not None and sandbox_has(sandbox, "check"):
        worlded = ["--world", world] if world else []
        return [sandbox, "check", policy, *worlded, "--deny-warnings", *printing], True
    axorum = axorum_binary()
    if axorum is not None:
        return [axorum, "policy", "check", policy, "--deny-warnings", *printing], False
    return None


def main(argv: Sequence[str] | None = None) -> int:
    """Check the policy the command line names."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    parser.add_argument("policy", help="the policy file, or - for stdin")
    parser.add_argument("--world", help="the world file the policy will run in")
    parser.add_argument("--print", action="store_true", help="also print the canonical layout")
    parser.add_argument("--json", action="store_true", help="also print the JSON verdict on stdout")
    args = parser.parse_args(argv)

    found = command(args.policy, args.world, args.print)
    if found is None:
        return fail(
            "no checker: install axorum-sandbox (pip install axorum-sandbox) or the axorum CLI"
        )
    run, reads_world = found
    if args.world and reads_world and not judges_scheduled_changes(run[0]):
        return fail(UNJUDGED.format(upgrade=UPGRADE))
    stdout = None if args.json else subprocess.DEVNULL
    try:
        code = subprocess.run(run, stdout=stdout, check=False).returncode
    except OSError as bad:
        return fail(f"the checker {run[0]} did not run: {bad}")
    if code == 0 and args.world and not reads_world:
        return fail(
            f"the policy checks clean on its own, but {args.world} was not checked: only "
            f"axorum-sandbox with `check` reads a world ({UPGRADE})"
        )
    return code


if __name__ == "__main__":
    sys.exit(main())
