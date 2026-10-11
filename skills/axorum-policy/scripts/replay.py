#!/usr/bin/env python3
"""Replay saved sandbox runs under a revised policy, and say which outcomes it changes.

Usage:
    replay.py --policy POLICY.axp RUN.yaml [RUN.yaml ...]
    replay.py --policy POLICY.axp --url URL [--save RUN.yaml]

Each run is a scenario ``axorum-sandbox save-run`` wrote: what agents did, the
outcome each step got, and the policy it was recorded under. Replaying it with
``--policy`` puts the draft in force for the whole run and holds each
submission to its recorded decision: the answer, the deciding rule by name,
the refusing mandate, and the duties it opened, met and breached. A step the
draft decides differently is named, with what changed, and so is a duty the
run ends with otherwise than the recording did. A run that records no
submission tries nothing, and is named as such.

A replay without ``--policy`` only plays the recording back under the policy
the run carries, so this script always passes the draft. A run saved by an
older sandbox names its policy file instead of carrying it, and cannot be
replayed under a draft: save it again.

With ``--url`` instead of run files, the run so far of the sandbox at URL is
saved first (to ``--save``, else a file beside the policy) and replayed. That
only reads the sandbox: it is never started, stopped or changed.

Exit 0 when every step keeps its recorded decision, 1 when one changes, 2 when
nothing was replayed: the policy does not compile (check it with ``check.py``
first), a run cannot be loaded or saved, or a run names its policy file.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from _common import fail, sandbox_binary

DEFAULT_URL = "http://127.0.0.1:7340"
URL_VAR = "AXORUM_SANDBOX_URL"


def submissions(scenario: str) -> int:
    """Count the submissions a saved run's script records. Pure.

    ``save-run`` writes the script as the top-level ``script:`` list, one
    ``- submit:`` item per submission; a run with none has no ``script:``.
    """
    count = 0
    inside = False
    for line in scenario.splitlines():
        if line.startswith("script:"):
            inside = True
        elif line[:1].isalpha():
            inside = False
        elif inside and line.startswith("- submit:"):
            count += 1
    return count


def main(argv: Sequence[str] | None = None) -> int:
    """Replay the runs the command line names."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    parser.add_argument("runs", nargs="*", type=Path, help="saved runs (scenario YAML)")
    parser.add_argument("--policy", type=Path, required=True, help="the revised policy")
    parser.add_argument("--url", help=f"save and replay this sandbox's run (${URL_VAR})")
    parser.add_argument("--save", type=Path, help="where to save the run read from --url")
    args = parser.parse_args(argv)

    binary = sandbox_binary()
    if binary is None:
        return fail("no axorum-sandbox binary: pip install axorum-sandbox")
    runs: list[Path] = list(args.runs)
    if args.url or not runs:
        url = args.url or os.environ.get(URL_VAR, DEFAULT_URL)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        saved = args.save or args.policy.parent / f"run-{stamp}.yaml"
        done = subprocess.run(
            [binary, "save-run", "--url", url, "--output", str(saved)],
            capture_output=True,
            text=True,
            check=False,
        )
        if done.returncode != 0:
            return fail(f"could not save the run of the sandbox at {url}: {done.stderr.strip()}")
        print(f"saved the run of {url} to {saved}", file=sys.stderr)
        runs.append(saved)
    for run in runs:
        try:
            recorded = submissions(run.read_text(encoding="utf-8"))
        except OSError:
            continue
        if recorded == 0:
            print(f"{run} records no submission: replaying it tries nothing", file=sys.stderr)
    replay = [binary, "run", *(str(run) for run in runs), "--policy", str(args.policy)]
    return subprocess.run(replay, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
