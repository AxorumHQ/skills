#!/usr/bin/env python3
"""Load a world into the engine, play its timeline, and say what the engine recorded.

Usage:
    run.py WORLD.yaml [--policy POLICY.axp] [--until SPAN] [--json]

Serves the world on a free port of 127.0.0.1, as ``axorum-sandbox serve``
does, so everything loading refuses (a policy that does not compile, a child
mandate above its parent, a fiscal calendar out of order) is refused here.
Then moves the clock by ``--until`` from where it stands once the run has
started (default: to one day past the world's last event, or to the clock's
last second, ``365250d``, if that comes first), so every event applies at its
own time, and prints:

- what the world opened as the run started, counted by the engine's record;
- each event at its time, the ones applied as the run started first (those at
  ``0s``, and any a ``0s`` advance reaches) and the rest as the clock reached
  them, with the engine's refusal when it refused the change (a refused change
  changes nothing);
- the engine's own account at the end: the period report, every mandate with
  its ceiling and who it is bound to, and every usage balance.

No agent acts, so no money moves: the run shows the world, not the policy's
verdicts. The sandbox is stopped whatever happened, and no other is touched.
``--policy`` runs another policy in place of the world's own from the start,
as ``serve --policy`` does: a ``policy`` change on the timeline still puts
its policy in force when the clock reaches it.

Exit 0 when the world loads and no event was refused, 3 when the world does
not load or an event was refused, 2 when no ``axorum-sandbox`` that can report
a run's events could run or the command line cannot be read.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from _common import UPGRADE, fail, sandbox_binary

try:
    from axorum_sandbox import Sandbox, SandboxError
except ImportError:  # pragma: no cover - the message is the point
    sys.exit(fail(f"run.py needs the axorum-sandbox package: {UPGRADE}"))

UNITS = {"w": 604_800, "d": 86_400, "h": 3_600, "m": 60, "s": 1}
"""Each unit a span is written in, in seconds, largest first."""

SPAN = re.compile(r"^(?:(\d+)w)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$")
"""A span as the world format writes it: ``90s``, ``2d``, ``1d12h30m``."""

DAY = 86_400

LAST = 365_250 * DAY
"""The last second the sandbox clock reaches: a thousand years of 365.25 days."""


def seconds(span: str) -> int | None:
    """Read a span as seconds, or ``None`` when it is not one."""
    if span.isdigit():
        return int(span)
    found = SPAN.match(span)
    if not span or found is None:
        return None
    return sum(
        int(count) * size
        for count, size in zip(found.groups(), UNITS.values(), strict=True)
        if count
    )


def span(total: int) -> str:
    """Write seconds as the world format writes a span back: largest units, no weeks."""
    if total == 0:
        return "0s"
    terms = []
    for unit, size in UNITS.items():
        if unit == "w":
            continue
        count, total = divmod(total, size)
        if count:
            terms.append(f"{count}{unit}")
    return "".join(terms)


def event_offsets(saved: str) -> list[int]:
    """Read each event's ``at``, in seconds, from the run as the sandbox writes it back.

    ``axorum-sandbox`` writes back the world it parsed in one shape: a top-level
    ``events:`` list in block style, each event's first line ``- at: <span>`` at
    the start of the line, its other keys indented under it, and the next
    top-level key at the start of a line again. So this reads what the sandbox
    loaded, not how the world file spells it: a quoted key, a comment or flow
    style is gone by then, and the sandbox refuses an anchor. Raises
    ``ValueError`` on an event line of any other shape.
    """
    offsets = []
    inside = False
    for line in saved.splitlines():
        if not line or line[0] == " ":
            continue
        if not line.startswith("- "):
            inside = line.rstrip() == "events:"
            continue
        if not inside:
            continue
        written = line.removeprefix("- at: ")
        offset = None if written == line else seconds(written.strip().strip("'\""))
        if offset is None:
            raise ValueError(f"an event that does not start with its time: {line!r}")
        offsets.append(offset)
    return offsets


def move(until: int | None, offsets: list[int], now: int) -> int | str:
    """How far to move the clock from ``now``, where it stands once the run started. Pure.

    ``until`` is how far the command line asked; when it did not, the clock
    moves to a day past the last event, or past ``now`` when every event is
    behind it, and no further than ``LAST``. Answers the refusal instead when
    the move would pass ``LAST``.
    """
    if until is None:
        return min(max([now, *offsets]) + DAY, LAST) - now
    if now + until > LAST:
        started = f", as the run starts at {span(now)}" if now else ""
        return (
            f"--until runs past the clock's last second: ask for {span(LAST - now)} or less"
            f"{started}"
        )
    return until


def opened(records: list[dict[str, Any]]) -> dict[str, int]:
    """Count the journal's records at the run's first tick by kind, in the order first seen."""
    kinds: Counter[str] = Counter()
    for record in records:
        for kind, body in record.items():
            if isinstance(body, dict) and body.get("tick") == 0:
                kinds[kind] += 1
    return dict(kinds)


def refusal(event: dict[str, Any]) -> str | None:
    """Give the engine's words for a refused event, or ``None`` when the change applied.

    A refusal is the agent plane's error: an HTTP status and a body whose
    ``error`` is the code and ``message`` the reason.
    """
    refused = event.get("refused")
    if refused is None:
        return None
    body = refused.get("body") if isinstance(refused, dict) else None
    if not isinstance(body, dict) or "message" not in body:
        return json.dumps(refused)
    return f"{body['message']} ({body.get('error', 'refused')})"


def account(
    started: list[dict[str, Any]], moved: dict[str, Any], snapshot: dict[str, Any]
) -> dict[str, Any]:
    """Gather what the run did, as the JSON verdict carries it.

    ``started`` is what the sandbox listed before the clock moved: the events
    applied as the run started, which no move reports. ``moved``
    answers the move: the advance asked for first, then each event it reached.
    """
    events = [
        {"at": span(int(event["at"])), "kind": event["kind"], "refused": refusal(event)}
        for event in [*started, *moved["events"][1:]]
    ]
    reports = snapshot["reports"]
    return {
        "ok": all(event["refused"] is None for event in events),
        "world": snapshot["world"]["name"],
        "clock": moved["clock"],
        "offset": moved["offset"],
        "opened": opened(snapshot["journal"]["records"]),
        "events": events,
        "reports": {
            "period": "".join(report["text"] for report in reports.get("periods", [])),
            "mandates": [report["text"] for report in reports.get("mandates", [])],
            "usages": [report["text"] for report in reports.get("usage_balances", [])],
        },
    }


def prose(verdict: dict[str, Any]) -> str:
    """Write the run in plain lines, for a person."""
    lines = [
        f"{verdict['world']}: loaded; the clock moved to {verdict['offset']} ({verdict['clock']})",
        "",
        "Opened as the run started:",
    ]
    lines += [f"  {kind} x{count}" for kind, count in verdict["opened"].items()]
    lines += ["", "Events, each at its time (the ones applied as the run started first):"]
    if not verdict["events"]:
        lines.append("  none")
    for event in verdict["events"]:
        said = f"REFUSED, nothing changed: {event['refused']}" if event["refused"] else "applied"
        lines.append(f"  {event['at']:<8} {event['kind']:<12} {said}")
    lines += ["", "The engine's account at the end:", verdict["reports"]["period"].rstrip()]
    lines += [text.rstrip() for text in verdict["reports"]["mandates"]]
    lines += [text.rstrip() for text in verdict["reports"]["usages"]]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the world the command line names."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    parser.add_argument("world", type=Path, help="the world file")
    parser.add_argument("--policy", type=Path, help="a policy to run in place of the world's")
    parser.add_argument(
        "--until", help="how far to move the clock once the run has started: a span such as 40d"
    )
    parser.add_argument("--json", action="store_true", help="answer JSON on stdout")
    args = parser.parse_args(argv)

    if not args.world.is_file():
        return fail(f"cannot read {args.world}: no such file")
    until = seconds(args.until) if args.until else None
    if args.until and not until:
        return fail(f"--until takes a span of at least 1s, such as 40d or 12h, not {args.until}")
    if until is not None and until > LAST:
        return fail(f"--until runs past the clock's last second: ask for {span(LAST)} or less")
    if sandbox_binary() is None:
        return fail(f"no axorum-sandbox binary: {UPGRADE}")

    if not hasattr(Sandbox, "events"):
        return fail(f"this axorum-sandbox package cannot list a run's events: {UPGRADE}")

    try:
        with Sandbox(args.world, policy=args.policy) as sandbox:
            started = sandbox.events()
            offsets = event_offsets(sandbox.save_run())
            now = seconds(str(sandbox.snapshot()["clock"]))
            if now is None:
                return fail("the sandbox answered a clock this script cannot read: " + UPGRADE)
            moving = move(until, offsets, now)
            if isinstance(moving, str):
                return fail(moving)
            moved = sandbox.advance(span(moving))
            snapshot = sandbox.snapshot()
    except SandboxError as bad:
        if bad.status == 404:
            return fail(f"this axorum-sandbox cannot list a run's events: {UPGRADE}")
        return fail(f"{args.world} did not load: {bad}", 3)
    except ValueError as unread:
        return fail(
            f"the sandbox wrote the world back in a shape this script cannot read: {unread}"
        )

    verdict = account(started, moved, snapshot)
    print(json.dumps(verdict, indent=2) if args.json else prose(verdict))
    return 0 if verdict["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
