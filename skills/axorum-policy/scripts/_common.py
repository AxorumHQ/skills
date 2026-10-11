"""What the policy skill's scripts share: finding the binaries they run."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

SANDBOX_VAR = "AXORUM_SANDBOX_BIN"
"""The variable naming an ``axorum-sandbox`` binary, as the ``axorum_sandbox`` package reads it."""

UPGRADE = "pip install -U axorum-sandbox"


def sandbox_binary() -> str | None:
    """Name the ``axorum-sandbox`` binary to run, or ``None`` when there is none.

    The one ``AXORUM_SANDBOX_BIN`` names, else the one the ``axorum-sandbox``
    package installed beside this Python, else one on ``PATH``: the order
    ``axorum_sandbox.binary()`` uses.
    """
    named = os.environ.get(SANDBOX_VAR)
    if named:
        return named
    name = "axorum-sandbox.exe" if os.name == "nt" else "axorum-sandbox"
    packaged = Path(sysconfig.get_path("scripts")) / name
    if packaged.is_file():
        return str(packaged)
    return shutil.which(name)


def sandbox_has(binary: str, *command: str) -> bool:
    """Whether this ``axorum-sandbox`` runs and has the subcommand ``command``.

    A nested one is named word by word: ``sandbox_has(binary, "publish", "policy")``.
    """
    try:
        probe = subprocess.run(
            [binary, *command, "--help"], capture_output=True, text=True, check=False
        )
    except OSError:
        return False
    return probe.returncode == 0


def sandbox_offers(binary: str, flag: str, *command: str) -> bool:
    """Whether this ``axorum-sandbox``'s subcommand ``command`` takes ``flag`` (``--replace``).

    Read from the subcommand's ``--help``, which names every flag it takes; an
    older binary answers it without the flag, or with an error.
    """
    try:
        probe = subprocess.run(
            [binary, *command, "--help"], capture_output=True, text=True, check=False
        )
    except OSError:
        return False
    return probe.returncode == 0 and flag in probe.stdout.split()


PROBE_WORLD = """\
version: axorum.sandbox-world.v1
world: probe
policy: {source: "policy {}"}
currencies: [{currency: USD, exponent: 2}]
parties:
- agent: agent://example.com/agent/clerk_01h455vb4pex5vsknk084sn02q
  party: party_28zwgzaew1a2r92s1y9swtj3nj
events:
- at: 1h
  policy: {source: "policy {"}
"""
"""A world that holds together, with one scheduled policy change that does not compile."""

PROBE_REFUSAL = "the world cannot run event 1's policy change"
"""What a checker that judges a world's scheduled changes says of ``PROBE_WORLD``."""


def judges_scheduled_changes(binary: str) -> bool:
    """Whether this ``axorum-sandbox check --world`` judges the policy changes a world schedules.

    An older ``check`` reads the world but never compiles a change on its
    timeline, so it passes a world whose change cannot run, and its version
    does not tell it apart. So this asks the binary: it checks a policy that
    compiles against ``PROBE_WORLD``, whose one scheduled change does not, and
    answers yes only when the checker fails the check for that change.
    """
    with tempfile.TemporaryDirectory() as scratch:
        world = Path(scratch) / "probe.yaml"
        world.write_text(PROBE_WORLD, encoding="utf-8")
        try:
            done = subprocess.run(
                [binary, "check", "-", "--world", str(world), "--quiet"],
                input="policy {}\n",
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
    return refused_the_change(done.returncode, done.stderr)


def refused_the_change(returncode: int, stderr: str) -> bool:
    """Whether a check of ``PROBE_WORLD`` failed for its scheduled change: exit 3, naming it."""
    return returncode == 3 and PROBE_REFUSAL in stderr


def axorum_binary() -> str | None:
    """Name the ``axorum`` CLI on ``PATH``, or ``None`` when there is none."""
    return shutil.which("axorum.exe" if os.name == "nt" else "axorum")


def fail(message: str, code: int = 2) -> int:
    """Say why the script cannot go on, on stderr, and answer its exit code."""
    print(message, file=sys.stderr)
    return code
