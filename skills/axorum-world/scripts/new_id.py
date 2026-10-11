#!/usr/bin/env python3
"""Mint fresh ids for a world: accounts, mandates, deferrals, usage balances.

Usage:
    new_id.py PREFIX [PREFIX ...] [--count N]

Prints one id per line for each PREFIX (``acc``, ``mand``, ``defr``,
``usage``), ``--count`` of each, in the form the world format reads: the
prefix, ``_``, and 26 characters of lowercase Crockford base32 encoding a
random UUID. A mandate or party the policy names is never minted: it must use
the id its name derives, which ``check.py`` prints.

Exit 0, or 2 for a prefix the world format does not mint.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Sequence

from _common import fail

ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"
"""Crockford's base32, lowercase: no ``i``, ``l``, ``o`` or ``u``."""

PREFIXES = ("acc", "mand", "defr", "usage")
"""The ids a world opens under ids of its own choosing."""


def encode(value: int) -> str:
    """Write a 128-bit value as 26 base32 characters, the first of them 0 to 7."""
    return "".join(ALPHABET[(value >> (5 * (25 - index))) & 31] for index in range(26))


def mint(prefix: str) -> str:
    """Mint a fresh id under ``prefix``."""
    return f"{prefix}_{encode(uuid.uuid4().int)}"


def main(argv: Sequence[str] | None = None) -> int:
    """Print the ids the command line asks for."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    parser.add_argument("prefixes", nargs="+", metavar="PREFIX", help=", ".join(PREFIXES))
    parser.add_argument("--count", type=int, default=1, help="how many of each (default 1)")
    args = parser.parse_args(argv)

    unknown = [prefix for prefix in args.prefixes if prefix not in PREFIXES]
    if unknown:
        return fail(
            f"no such prefix: {', '.join(unknown)}. A world mints {', '.join(PREFIXES)}; "
            "a party's id comes from the policy (check.py prints it)"
        )
    if args.count < 1:
        return fail("--count is at least 1")
    for prefix in args.prefixes:
        for _ in range(args.count):
            print(mint(prefix))
    return 0


if __name__ == "__main__":
    sys.exit(main())
