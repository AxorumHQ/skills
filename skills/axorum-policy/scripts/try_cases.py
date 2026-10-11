#!/usr/bin/env python3
"""Try a policy on concrete cases in a throwaway sandbox, and say which behaved as expected.

Usage:
    try_cases.py CASES.json [--policy POLICY.axp] [--json]

CASES.json names the world and the policy (both relative to it), the agents by
their policy names, and the cases in order: intents an agent submits, and
moves of the clock. ``references/testing.md`` in the skill describes the
format. ``--policy`` tries another draft against the same cases.

Every run serves the world on a free port of 127.0.0.1, submits each intent as
its agent with a fresh token, compares what happened with what the case
expected, and stops the sandbox, whatever happened. No other sandbox is
touched.

Exit 0 when every case behaved as expected and every brief item the policy's
header lists has a case, 1 when one did not, 2 when the cases could not be run:
a package or the binary is missing, the policy's header lists no brief items
(the message shows the header to write), a case is written wrong, or the
sandbox will not serve the world.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from _common import fail, sandbox_binary

try:
    from axorum import (
        ActionTerm,
        AgentOutcome,
        Amount,
        ApiError,
        AxorumClient,
        AxorumError,
        Entry,
        IntentDraft,
        Refusal,
        Value,
        ValueKind,
        default_chart_account,
    )

    from axorum_sandbox import Sandbox, SandboxError
except ImportError as missing:  # pragma: no cover - the message is the point
    print(
        f"try_cases.py needs the axorum-sandbox and axorum-client packages ({missing.name} is "
        "missing): pip install axorum-sandbox axorum-client",
        file=sys.stderr,
    )
    sys.exit(2)

if "mandate" not in {known.name for known in fields(Refusal)}:
    print(
        "try_cases.py needs an axorum-client that names the mandate behind a refusal, and this "
        "one does not: pip install -U axorum-client",
        file=sys.stderr,
    )
    sys.exit(2)

AMOUNT = re.compile(r"^(-?\d+(?:\.\d+)?) ([A-Z]{3,8})$")
"""An amount as a person writes it: ``120.00 USD``."""

MONEYISH = re.compile(r"^[$€£]|^-?\d[\d,]*(?:\.\d+)? ?[A-Z]{3,8}$|^-?\d{1,3}(?:,\d{3})+(?:\.\d+)?$")
"""A value written as money but not as an amount: ``$6,000``, ``6,000.00 USD``, ``6,000``."""

BRIEF_ITEM = re.compile(r"^//\s+(B\d+)\b")
"""A brief item in a policy's header comment: ``//   B3  No single payment ...``."""

NO_BRIEF = """{policy} lists no brief items, so nothing says which controls the cases must cover.
Write the brief into the comment above `policy {{`, one line per control: its number, the
control in the user's words, and the rules that carry it out. For example:

  // Brief, and the rules that carry it out:
  //   B1  The AP agent may pay vendors.                      permit_payment
  //   B2  No single payment over $5,000.00.                  single_payment_cap

Then give each case the `brief` item it tries, and run this again."""
"""What to do about a policy whose header lists no brief items, with the header's syntax."""

OUTCOMES = ("allowed", "refused", "rejected")


class CaseError(Exception):
    """A case that cannot be run as written."""


def rejection_stage(code: str, cause: str) -> str:
    """Say when a rejection turned the intent away, from its code and cause."""
    if code == "invalid_fulfillment":
        return "after the policy allowed it"
    if cause == "unknown_mandate":
        return "unrecorded"
    return "before judgment"


@dataclass
class Duty:
    """A duty a step opened, under the name of the step that opened it."""

    id: str
    opened_by: str
    action: str
    term: ActionTerm
    parent: str | None = None
    breached: bool = False


@dataclass
class Happened:
    """What one submission or one move of the clock did."""

    outcome: str = ""
    because: str = ""
    detail: str = ""
    codes: set[str] = field(default_factory=set)
    duties: list[str] = field(default_factory=list)
    meets: list[str] = field(default_factory=list)
    breached: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)
    problem: str = ""

    def describe(self) -> str:
        """Say what happened in one line."""
        if self.problem:
            return self.problem
        if not self.because:
            parts = [self.outcome]
        elif self.outcome == "rejected":
            stage = rejection_stage(self.because, self.detail)
            cause = f", cause {self.detail}" if self.detail else ""
            parts = [f"rejected {stage} ({self.because}{cause})"]
        elif self.detail and self.detail != self.because:
            parts = [f"{self.outcome} by {self.because} ({self.detail})"]
        else:
            parts = [f"{self.outcome} by {self.because}"]
        if self.meets:
            duty = "the duty" if len(self.meets) == 1 else "the duties"
            parts.append(f"meets {duty} from " + ", ".join(self.meets))
        if self.duties:
            parts.append("opens " + ", ".join(self.duties))
        if self.breached:
            parts.append("breached: " + ", ".join(self.breached))
        if self.follow_ups:
            parts.append("follow-ups: " + ", ".join(self.follow_ups))
        return "; ".join(parts)


@dataclass
class Row:
    """One case's verdict."""

    index: int
    case: str
    brief: str
    expected: str
    actual: str
    ok: bool
    times: int = 1


class Trial:
    """One run of the cases against one sandbox."""

    def __init__(
        self,
        sandbox: Sandbox,
        agents: Mapping[str, str],
        scales: Mapping[str, int],
    ) -> None:
        """Hold the sandbox and what the cases call its agents."""
        self.sandbox = sandbox
        self.client = AxorumClient(sandbox.url)
        self.agents = agents
        self.scales = scales
        self.duties: dict[str, Duty] = {}
        self.mandates = {
            str(held["mandate"]): str(held["name"])
            for held in sandbox.report("mandates").get("mandates", [])
        }

    def amount(self, written: str) -> Amount:
        """Read ``120.00 USD`` at the world's exponent for USD."""
        match = AMOUNT.match(written)
        if match is None:
            raise CaseError(f"{written!r} is not an amount such as '120.00 USD'")
        number, currency = match.groups()
        if currency not in self.scales:
            raise CaseError(f"{currency} is not a currency the world declares")
        try:
            minor = Decimal(number).scaleb(self.scales[currency])
        except InvalidOperation as bad:
            raise CaseError(f"{written!r} is not an amount") from bad
        if minor != minor.to_integral_value():
            raise CaseError(f"{written!r} has more decimals than {currency} has")
        return Amount(int(minor), currency)

    def value(self, raw: object) -> Value:
        """Type one parameter value the way the cases file writes it."""
        if isinstance(raw, bool):
            return Value.bool_(raw)
        if isinstance(raw, int):
            return Value.int_(raw)
        if isinstance(raw, str):
            if AMOUNT.match(raw):
                return Value.amount(self.amount(raw))
            if MONEYISH.match(raw):
                raise CaseError(
                    f"{raw!r} looks like money but is not an amount: write it as '6000.00 USD'"
                )
            if raw.startswith("txn_"):
                return Value.transaction(raw)
            if raw.startswith("party_"):
                return Value.party(raw)
            return Value.text(raw)
        raise CaseError(f"{raw!r} is not a value a case can bind")

    def legs(self, spec: object, term: ActionTerm) -> list[Entry]:
        """Build the journal legs a case's intent posts."""
        if isinstance(spec, list):
            return [self.leg(leg) for leg in spec]
        amounts = [
            value.value
            for value in term.bindings.values()
            if value.kind is ValueKind.AMOUNT and isinstance(value.value, Amount)
        ]
        if not amounts:
            raise CaseError(f"'{term.action}' binds no amount: write its legs out")
        amount = amounts[0]
        spend = default_chart_account("spend", amount.currency)
        if spec == "payment":
            payable = default_chart_account("payable", amount.currency)
            return [Entry.debit(spend, amount), Entry.credit(payable, amount)]
        if spec == "memo":
            return [Entry.debit(spend, amount), Entry.credit(spend, amount)]
        raise CaseError(f"legs are 'payment', 'memo' or a list, not {spec!r}")

    def leg(self, leg: object) -> Entry:
        """One written-out leg: ``{"debit": "acc_...", "amount": "10.00 USD"}``."""
        if not isinstance(leg, dict) or "amount" not in leg:
            raise CaseError(f"a leg names a debit or credit account and an amount: {leg!r}")
        amount = self.amount(str(leg["amount"]))
        if "debit" in leg:
            return Entry.debit(str(leg["debit"]), amount)
        if "credit" in leg:
            return Entry.credit(str(leg["credit"]), amount)
        raise CaseError(f"a leg names a debit or credit account: {leg!r}")

    def duty_for(self, opener: str, case: Mapping[str, Any]) -> Duty:
        """Find the duty a case fulfills, named by the step that opened it.

        A follow-up a breach opened is named by the step that opened the duty
        it follows, too, with the action it owes in ``do``.
        """
        candidates = [
            duty
            for duty in self.duties.values()
            if opener in (duty.opened_by, self.origin(duty))
            and case.get("do", duty.action) == duty.action
            and not duty.breached
        ]
        if len(candidates) != 1:
            raise CaseError(
                f"'{opener}' opened {len(candidates)} duties to {case.get('do', 'act')}: "
                "name the step that opened exactly one, and the action it owes in 'do'"
            )
        return candidates[0]

    def origin(self, duty: Duty) -> str:
        """Name the step that opened the first duty of the chain ``duty`` is in."""
        while duty.parent is not None and duty.parent in self.duties:
            duty = self.duties[duty.parent]
        return duty.opened_by

    def submit(self, name: str, case: Mapping[str, Any]) -> Happened:
        """Submit one case's intent and say what happened."""
        actor = str(case.get("as", ""))
        if actor not in self.agents:
            raise CaseError(f"'as' must name one of the agents: {', '.join(self.agents)}")
        agent = self.agents[actor]
        written = case.get("with", {})
        if not isinstance(written, dict):
            raise CaseError("'with' maps parameter names to values")
        bindings = {key: self.value(raw) for key, raw in written.items()}
        fulfills: list[str] = []
        met: list[str] = []
        if "fulfills" in case:
            met = openers(case)
            duties = [self.duty_for(opener, case) for opener in met]
            if len({duty.action for duty in duties}) != 1:
                raise CaseError("one intent performs one action: name duties that owe the same one")
            term = ActionTerm(duties[0].action, {**duties[0].term.bindings, **bindings})
            fulfills = [duty.id for duty in duties]
        elif "do" in case:
            term = ActionTerm(str(case["do"]), bindings)
        else:
            raise CaseError("an intent names the action it does in 'do'")
        draft = IntentDraft(
            agent=agent,
            attestation=self.sandbox.token(agent),
            action=term,
            entries=self.legs(case.get("legs", "payment"), term),
            fulfills=fulfills,
        )
        try:
            outcome = self.client.submit_pinned(draft)
        except AxorumError as error:
            return rejected(error)
        return self.judged(name, actor, outcome, met if outcome.posted else [])

    def judged(self, name: str, actor: str, outcome: AgentOutcome, met: list[str]) -> Happened:
        """Read a judged outcome, and the engine's explanation of it."""
        explained = self.sandbox.report("explain", transaction=outcome.transaction)
        acted_as = explained.get("actor", {}).get("name")
        if acted_as != actor:
            return Happened(
                problem=(
                    f"acted as {acted_as or 'a party the policy does not name'}, not {actor}: "
                    f"the world must bind this agent to the party id the name {actor} "
                    "derives (check.py --world says which)"
                )
            )
        if outcome.posted:
            winner = explained.get("winning_rule") or {}
            happened = Happened(outcome="allowed", because=str(winner.get("name", "")))
        else:
            refusal = outcome.refusal
            code = refusal.code if refusal is not None else "refused"
            rule = refusal.rule.name if refusal is not None and refusal.rule else ""
            mandate = refusal.mandate if refusal is not None and refusal.mandate else ""
            detail = rule or self.mandates.get(mandate, mandate)
            named = rule if rule and code == "forbidden_by_rule" else code
            happened = Happened(outcome="refused", because=named, detail=detail, codes={code})
            if detail:
                happened.codes.add(detail)
        happened.codes.add(happened.because)
        happened.meets = met
        names = {str(rule["id"]): str(rule["name"]) for rule in explained.get("applied_rules", [])}
        rules = {duty.id: duty.rule for duty in outcome.obligations_pending}
        terms = {duty.id: duty.action for duty in outcome.obligations_pending}
        for created in explained.get("duties_created", []):
            duty = created["duty"]
            owed = terms.get(duty["id"])
            if owed is not None:
                happened.duties.append(names.get(rules.get(duty["id"], ""), owed.action))
                self.duties[duty["id"]] = Duty(duty["id"], name, owed.action, owed)
            else:
                happened.duties.append(unnamed(created))
        return happened

    def advance(self, name: str, offset: str) -> Happened:
        """Move the clock and say which duties were breached and what followed."""
        before = self.sandbox.report("exceptions")
        seen = {self.key(entry) for entry in before.get("exceptions", [])}
        self.sandbox.advance(offset)
        happened = Happened(outcome=f"{offset} passed")
        for entry in self.sandbox.report("exceptions").get("exceptions", []):
            if entry.get("kind") != "breach" or self.key(entry) in seen:
                continue
            duty = self.duties.get(entry["duty"]["id"])
            if duty is None:
                happened.breached.append(str(entry["duty"]["owed_action"]))
                continue
            duty.breached = True
            missed = (
                duty.opened_by if duty.parent is None else f"{self.origin(duty)} ({duty.action})"
            )
            happened.breached.append(missed)
        for open_duty in self.sandbox.obligations():
            if open_duty["id"] in self.duties:
                continue
            term = ActionTerm.from_dict(open_duty["action"])
            parent = self.duties.get(str(open_duty.get("parent")))
            self.duties[open_duty["id"]] = Duty(
                open_duty["id"], name, term.action, term, parent.id if parent else None
            )
            happened.follow_ups.append(term.action)
        return happened

    @staticmethod
    def key(entry: Mapping[str, Any]) -> tuple[str, str]:
        """Tell one exception from another."""
        duty = entry.get("duty") or {}
        return (str(entry.get("kind")), str(duty.get("id", entry.get("tick"))))


def unnamed(created: Mapping[str, Any]) -> str:
    """Name a duty its transaction opened but that was not left pending. Pure.

    Only a pending duty carries the rule that opened it. One broken as it
    opened (its ``by`` deadline already past) is named by the action it owes,
    and marked so: no report names its rule.
    """
    owed = str(created["duty"]["owed_action"]).split(" (")[0].replace(" ", "_")
    broken = (created.get("outcome") or {}).get("status") == "broken"
    return f"{owed} (breached when opened)" if broken else owed


def openers(case: Mapping[str, Any]) -> list[str]:
    """Name the steps whose duties a case fulfills: one name, or a list of them. Pure.

    Several names make one intent meet the duty each step opened, the duties
    it owes taking the first one's captured parameters.
    """
    named = case["fulfills"]
    steps = named if isinstance(named, list) else [named]
    if not steps or not all(isinstance(step, str) for step in steps):
        raise CaseError("'fulfills' names a case, or a list of cases")
    if len(set(steps)) != len(steps):
        raise CaseError("'fulfills' names each case once")
    return steps


def expected(case: Mapping[str, Any]) -> Happened:
    """Read what a case says should happen."""
    if "advance" in case:
        return Happened(
            outcome=f"{case['advance']} passed",
            breached=[str(name) for name in case.get("breached", [])],
            follow_ups=[str(action) for action in case.get("follow_ups", [])],
        )
    outcome = str(case.get("expect", ""))
    if outcome not in OUTCOMES:
        raise CaseError(f"'expect' is one of {', '.join(OUTCOMES)}")
    return Happened(
        outcome=outcome,
        because=str(case.get("because", "")),
        duties=[str(rule) for rule in case.get("duties", [])],
        meets=openers(case) if "fulfills" in case and outcome == "allowed" else [],
    )


def rejected(error: AxorumError) -> Happened:
    """Read an intent turned away before judgment: its error code, and its cause. Pure.

    A ``422 substrate_rejected`` names in its body's ``cause`` which check
    turned it away (``unknown_counterparty`` for a payee the vendor list does
    not have), so a case may expect either.
    """
    code = error.code or type(error).__name__
    cause = error.body.get("cause") if isinstance(error, ApiError) else None
    if not isinstance(cause, str) or not cause:
        return Happened(outcome="rejected", because=code, codes={code})
    return Happened(outcome="rejected", because=code, detail=cause, codes={code, cause})


def matches(want: Happened, got: Happened) -> bool:
    """Whether what happened is what the case expected."""
    if got.problem or want.outcome != got.outcome:
        return False
    if want.because and want.because not in got.codes:
        return False
    return (
        sorted(want.duties) == sorted(got.duties)
        and sorted(want.meets) == sorted(got.meets)
        and sorted(want.breached) == sorted(got.breached)
        and sorted(want.follow_ups) == sorted(got.follow_ups)
    )


def brief_items(policy: str) -> list[str]:
    """List the brief items a policy's header comment names, in order."""
    items: list[str] = []
    for line in policy.splitlines():
        if line.strip().startswith("policy"):
            break
        match = BRIEF_ITEM.match(line.strip())
        if match and match.group(1) not in items:
            items.append(match.group(1))
    return items


def run(trial: Trial, cases: Sequence[Mapping[str, Any]]) -> list[Row]:
    """Run every case in order."""
    rows: list[Row] = []
    for index, case in enumerate(cases, start=1):
        name = str(case.get("case", f"case {index}"))
        want = expected(case)
        times = int(case.get("repeat", 1))
        got = Happened()
        ok = True
        for _ in range(times):
            if "advance" in case:
                got = trial.advance(name, str(case["advance"]))
            else:
                got = trial.submit(name, case)
            if not matches(want, got):
                ok = False
                break
        rows.append(
            Row(
                index,
                name,
                str(case.get("brief", "")),
                want.describe(),
                got.describe(),
                ok,
                times,
            )
        )
    return rows


def report(rows: Sequence[Row], uncovered: Sequence[str], unknown: Sequence[str]) -> str:
    """Write the verdict for a person to read."""
    lines: list[str] = []
    for row in rows:
        label = f"{row.case} (x{row.times})" if row.times > 1 else row.case
        head = f"{'ok  ' if row.ok else 'MISS'}  {row.index:>2}  {row.brief or '-':<4} {label}"
        if row.ok:
            lines.append(f"{head}: {row.actual}")
        else:
            lines.append(head)
            lines.append(f"{'':16}expected  {row.expected}")
            lines.append(f"{'':16}actual    {row.actual}")
    passed = sum(row.ok for row in rows)
    lines.append("")
    lines.append(f"{passed} of {len(rows)} cases behaved as expected.")
    if uncovered:
        lines.append("Brief items with no case: " + ", ".join(uncovered) + ".")
    if unknown:
        lines.append("Cases naming a brief item the policy header lacks: " + ", ".join(unknown))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the cases file the command line names."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    parser.add_argument("cases", type=Path, help="the cases file (JSON)")
    parser.add_argument("--policy", type=Path, help="a draft to try in place of the named one")
    parser.add_argument("--json", action="store_true", help="answer JSON on stdout")
    args = parser.parse_args(argv)

    try:
        spec = json.loads(args.cases.read_text(encoding="utf-8"))
    except (OSError, ValueError) as bad:
        return fail(f"cannot read {args.cases}: {bad}")
    base = args.cases.parent
    world = base / str(spec.get("world", "world.yaml"))
    policy = args.policy or base / str(spec.get("policy", "policy.axp"))
    agents = spec.get("agents", {})
    cases = spec.get("cases", [])
    if not isinstance(agents, dict) or not isinstance(cases, list):
        return fail("the cases file has 'agents' (a map) and 'cases' (a list)")
    if sandbox_binary() is None:
        return fail("no axorum-sandbox binary: pip install axorum-sandbox")
    # A sandbox is one endpoint by design: the client's notice about failover
    # replicas says nothing a person trying cases needs.
    logging.getLogger("axorum").setLevel(logging.ERROR)
    try:
        policy_text = policy.read_text(encoding="utf-8")
    except OSError as bad:
        return fail(f"cannot read {policy}: {bad}")
    listed = brief_items(policy_text)
    if not listed:
        return fail(NO_BRIEF.format(policy=policy))

    try:
        with Sandbox(world, policy=policy) as sandbox:
            currencies = sandbox.snapshot()["world"]["currencies"]
            scales = {str(c["currency"]): int(c["exponent"]) for c in currencies}
            rows = run(Trial(sandbox, agents, scales), cases)
    except CaseError as bad:
        return fail(f"a case cannot run as written: {bad}")
    except SandboxError as bad:
        return fail(f"the sandbox would not run {world} with {policy}: {bad}")

    tried = {row.brief for row in rows if row.brief}
    uncovered = [item for item in listed if item not in tried]
    unknown = sorted(tried - set(listed))
    if args.json:
        print(
            json.dumps(
                {
                    "ok": all(row.ok for row in rows) and not uncovered and not unknown,
                    "cases": [row.__dict__ for row in rows],
                    "uncovered": uncovered,
                    "unknown": unknown,
                },
                indent=2,
            )
        )
    else:
        print(report(rows, uncovered, unknown))
    return 0 if all(row.ok for row in rows) and not uncovered and not unknown else 1


if __name__ == "__main__":
    sys.exit(main())
