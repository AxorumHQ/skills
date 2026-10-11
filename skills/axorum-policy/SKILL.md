---
name: axorum-policy
description: This skill should be used when someone wants to write, revise, review or fix an Axorum policy (policy.axp), or describes controls for AI agents that spend money, such as "write a policy for our AP agent", "pay vendors but don't go crazy", "keep the agents on a budget", "receipts within a day", "only approved vendors", "change the policy in my sandbox", "publish the policy to the console", or when a policy fails to check or a sandbox verdict surprises them. It guides a user who may know nothing of the policy language, through questions, to a checked policy proven on their own examples, and on request pushes it to their sandbox or publishes it to the console's policy library. Not for submitting intents as an agent (the `axorum` skill).
---

# Guiding a user to a policy that says what they mean

An Axorum policy is the control surface for agents that move money: what they
may do, what is refused, what a payment obliges them to do next, and what
follows a miss. The engine judges every intent against the policy in force and
records the verdict. A policy is a financial control, read by a controller and
enforced by a machine, so it has to be both readable and exactly right.

The user is usually a controller, a finance lead or a founder. They know their
vendors, budgets, deadlines and who signs off. They have often not thought the
control through, and do not know the policy language. Guide them there with
questions, one at a time, and never fill a gap silently. Prove every claim with
the engine: its checker, its English rendering, and its verdicts on the user's
own examples.

## Answer from this skill and the sandbox, never from source

Answer from this skill's references, the `axorum-sandbox` CLI and the
sandbox's own answers only. Never read, search or cite Axorum source code,
specifications or repository files, even when they are in the working
directory, and never name an internal file, crate, module or line number. When
the references do not answer a question, say so and try it in a sandbox: what
the sandbox answers is what the engine answers.

## Speak the user's language

Questions and replies use the left column. The right column belongs in the
file and in drafting only.

| Say | Not |
|---|---|
| vendor, supplier, the approved list | counterparty, registry, reference set |
| may, is refused, must, if that is missed | permitted, forbidden, obligated, breach, violation |
| the follow-up | reparation, contrary-to-duty, on_violation |
| a running total, a cap, a budget | aggregate, register, projected, mandate |
| which rule wins | priority |
| who signs off | principal |
| what the agent is allowed to touch | delegation, scope |
| the money that actually moves | posted debit, journal legs |
| $2,500.00, three days | minor units, 250000, ticks, 259200 |
| the details on the payment | parameter, binding |

The engine's rendering uses some words on the right ("obligated", "register",
"clock-beats"). Quote it as the engine's wording and gloss them beside it from
the table in `references/conversation.md`.

## The scripts

`<skill-dir>` below is this skill's directory. Run the scripts from the
directory holding the user's files; they need Python 3.11 or later and `pip
install axorum-sandbox axorum-client`. Without `axorum-sandbox`, `check.py`
checks the policy alone with the `axorum` CLI, and refuses (exit 2) when a
world is named, since nothing else can check one. It refuses a world the same
way when the installed `axorum-sandbox` is too old to judge the policy
changes the world schedules: upgrade it (`pip install -U axorum-sandbox`).

## Where to start

- **A new policy**: the loop from phase 1.
- **A revision** (a `policy.axp` exists): read it, `world.yaml` and
  `cases.json` first, rebuild the brief from the header, ask only about the
  change, then phases 4 to 7 for what it touches. A policy with no brief in
  its header (a starter, or one from the console) gets one first: read each
  rule back, ask the user which control it carries, in their words and
  figures, and write the `B` items into the header before trying any case
  (`try_cases.py` refuses a policy without them).
- **The policy their console sandbox runs**: `axorum-sandbox pull --output
  world.yaml` writes the world and the policy file it names (they set the
  console connection in their own shell; `references/testing.md`, "The world
  came from the console"), then it is a revision of that file.
- **A check that fails**: phase 4, by code, with `references/diagnostics.md`.
- **A verdict in their sandbox that surprises them**: read the engine's
  account of it first (`references/diagnostics.md`, "A verdict in the user's
  own sandbox"), then decide whether the policy, the agent's intent or the
  world is wrong, and enter the loop where that belongs.
- **A review**: run `check.py --world`, read the policy back (phase 5), and
  list what the brief in its header promises that no rule or case carries.
  List too every `specific(...)` name the policy does not declare as a party:
  it compiles as a party known only at run time, and only `check.py --world`
  warns about one (`DSL3009`), when no world agent acts as it either. Ask the
  user which each one is.

## Fixed facts, never asked

- **Time is in seconds.** One tick is one second in the sandbox and at a
  deployment's default. One day is 86,400; write the civil meaning in a comment
  beside every number.
- **Amounts are whole minor units**: `amount(250000, USD)` is $2,500.00 at
  exponent 2. Write the dollar figure in the comment.
- **Files live together** in the working directory, or the directory the user
  names: `policy.axp`, `world.yaml`, `cases.json`. A world pulled from the
  console names its policy file by its library name: that file is the policy
  for the whole session, wherever these steps say `policy.axp`. A revision
  keeps what holds, changes what the user asks, and keeps the brief numbering.
- **The examples are a starting shape, not the user's figures.** Copy a
  pattern's structure; take every figure, name and period from the user.
- **Deny-by-default always holds.** Anything no rule permits is refused.

## The loop

Work through the phases in order. A later phase that finds a problem sends the
work back to the phase that owns it, and the loop runs until the done criteria
hold.

### 1. Discover

Ask what the request has not answered, one question per turn, each with one
line on why it matters and two to four options with a labelled default (the
safer one). Use a structured-question tool such as `AskUserQuestion` when
available. Turn a vague ask ("don't go crazy") into the usual separate controls
and let the user pick. Keep a running **control brief**: every control a `B`
item in the user's words with figures, marked `(assumed)` until the user
confirms it; assumptions that produce no rule, `A1`, ...; open questions `O1`,
...; anything the language cannot say, `X1`, ..., with the nearest shape
offered; and the controls the user declined. Show the changed lines after each
answer. The question bank, the brief template and the vague-ask menu are in
`references/conversation.md`.

### 2. Confirm the brief

Show the whole brief once and ask whether anything is missing or wrong, then
confirm each `(assumed)` and `A` item by itself. Draft only from a brief the
user has confirmed. With nobody to answer (a one-shot request), draft under the
safe defaults and mark the result a proposal until those items are confirmed.

### 3. Collect examples

Ask for concrete examples in the user's words ("the agent pays Acme $6,000",
"the receipt comes in two days late"), each with the outcome the user expects,
and record them: at least one per brief item, both sides of every limit, each
refusal's reason, each duty met and missed. A user with none gets a short
table of proposed examples from their own stories to flip. An example that
contradicts the brief goes back to the brief now. The examples become cases
once the draft names the actions and the world binds the agents (phase 6).

### 4. Draft and check

Start from the closest example or pattern (`references/patterns.md`) and the
world it runs in (`references/world.md`). Then check until clean:

```bash
python <skill-dir>/scripts/check.py policy.axp --world world.yaml
```

Exit 0 is required: no error and no lint. Fix by code
(`references/diagnostics.md`); never weaken a rule to silence a lint without
asking. A well-structured policy has:

- a header comment with the brief table mapping every `B` item to its rules
  (or to a world object, marked `(world)`), the deny-by-default statement,
  and the time units;
- an intent comment above every rule naming its `B` item, with figures in
  dollars and days;
- priority bands, stated: permits 1, duties 5, refusals 10 (a defeater
  outranks only its own rule);
- names that read well in an audit report, one scheme throughout:
  `permit_...` for permits, the limit for refusals (`single_payment_cap`),
  the owed paperwork for duties (`receipt_for_travel`);
- no dead, duplicate or unreachable rule, no unread aggregate, and every owed
  action permitted and delegated;
- every `specific(...)` naming a declared party, or one the user confirmed is
  known only at run time (it compiles; only `check.py --world` warns, with
  `DSL3009`, and only when no world agent acts as it);
- every `on_violation` naming an `obligated` rule (the checker accepts any
  rule there).

What constructs mean at judgment time is in `references/semantics.md`; the
exact syntax is in `references/grammar.abnf`, and each construct in brief is in
`references/grammar.md`.

### 5. Read back

Read every rule back in the brief's order: the brief item in the user's
words first, then the rule that carries it out, then the engine's rendering
for that rule as `check.py --world` printed it, labelled as the engine's
wording, without the checker's leading "Rule N" heading and its "(authored
priority n)", with its unfamiliar words glossed. Then say what
deny-by-default refuses that the brief does not mention, and anything worth a
second look (a cap allows landing exactly on it; an unknown vendor is turned
away rather than refused). Ask the user to confirm each item. A correction
goes back to the brief, then the draft. The template is in
`references/conversation.md`.

### 6. Try

Write the examples as cases (`references/testing.md`, which also says how to
lay out cases under several limits: they share one ledger), then:

```bash
python <skill-dir>/scripts/try_cases.py cases.json
```

It serves the world in a throwaway sandbox on a free port, runs every case
through the engine, prints expected against actual, and lists brief items with
no case. Show the table. For each miss, decide with the user whether the
policy, the case or the world is wrong, then fix that one and run again. When
the user has saved sandbox runs, `replay.py --policy policy.axp <runs>` shows
which recorded decisions the draft would change; read each change to the user
and ask whether it is intended.

### 7. Put it to use, when asked

Only after the read-back is confirmed and every case passes. Ask where it
goes, as one question: live in their running sandbox, so the agents' next
intents are judged by it; into the console's library, as the text of the
policy their console sandbox's world names; or both. Publish to the library
only when the user asks for it.

**Live.** Look first:

```bash
python <skill-dir>/scripts/push.py policy.axp --url <their sandbox> --dry-run
```

It checks the policy against the world their sandbox is actually running and
says which running totals keep their figures and which start again at zero.
Tell the user; when a total starts again, ask before going on. Then push
without `--dry-run`: the policy is in force from the sandbox's current time,
and a refused policy changes nothing. Never start, stop or restart the user's
sandbox: when nothing answers, ask them to start it.

**The library.** It goes through their sandbox's console connection, the
`AXORUM_SANDBOX_SINK` and `AXORUM_SANDBOX_TOKEN` they set in their own shell
(never ask for the token). When their world came from the console, publish
the policy file it names, the one worked on all session, looking first:

```bash
python <skill-dir>/scripts/publish.py <the file the world names> --dry-run
```

It checks the policy against the world attached to that sandbox in the
console and says whether publishing would update the library's copy. Before
publishing without `--dry-run`, tell the user that the copy is shared by every
world that names it, that a publish writes only over the text they pulled,
and that no earlier version is kept. When they started locally with
`policy.axp`, publish the world instead (`axorum-sandbox publish world
--replace`), which overwrites the world their console sandbox is attached to,
for every sandbox attached to it, and adds or updates its policy in the
library under the file's name. Pass --replace only when the user has said to
overwrite the console's version. Never copy the policy to another name to
publish it.

What to tell the user first, the exit codes and what to say for each are in
`references/testing.md`.

## Done

All of these hold, or the reply says which does not and why:

1. `check.py --world` exits 0: compiles, no lint, world bound.
2. Every brief item maps to a rule or a world object, in the header table.
3. Every example the user gave is a case, and `try_cases.py` exits 0.
4. The user confirmed the read-back, item by item.
5. Pushed to the user's sandbox, published to the library, or both, as they
   asked.

## Hand back

Keep the reply short; the files carry the detail.

1. **Where it is**: the files written or changed.
2. **What it does**: one sentence per brief item, in the user's words, with
   dollars and days.
3. **The engine's wording**: one line saying that each rule's sentence in
   the read-back is what an auditor will read; quote again only the rules
   changed since the read-back.
4. **Proof**: "14 of 14 cases behaved as you expected", with any case worth a
   second look.
5. **Please confirm**: each item still `(assumed)` and each `A` item, one line
   each.
6. **Cannot be expressed**: each `X` item and the nearest shape taken.
7. **What it relies on**, only when true: the vendor list, a budget opened in
   the world, a paperwork action the agent must perform with `fulfills`, who
   reads the misses, and when the clock starts for anything with an end date.

Leave out construct names, minor-unit arithmetic and the full policy text.

## Resources

| File | Use it for |
|---|---|
| `references/conversation.md` | The question bank, vague-ask menu, brief and read-back templates |
| `references/patterns.md` | A control as the user says it, next to the checked policy text |
| `references/semantics.md` | What each construct does when an intent is judged |
| `references/grammar.abnf` | The exact syntax, as an ABNF grammar: where blanks go, which tokens may touch, which keywords may be names |
| `references/grammar.md` | Each construct in brief |
| `references/world.md` | Binding a world to the policy: the policy file, party and mandate ids, what the cases need, the user's sandbox. Building a world is the `axorum-world` skill's |
| `references/testing.md` | The cases format, try, replay, push and publish |
| `references/diagnostics.md` | Checker codes, a scheduled policy change the world cannot run, refusal codes, rejections, and whose fault a miss is |
| `examples/ap-vendor-payments/` | One AP agent: approved vendors, a payment cap with a bounded exception, per-vendor and pace limits, a receipt duty |
| `examples/team-budget/` | Two agents under one team budget with a reserve, a per-agent rule, a receipt duty with a follow-up that a records agent with no budget files |
| `scripts/check.py` | Compile, lint and bind to the world; prints the engine's rendering |
| `scripts/try_cases.py` | Run the cases in a throwaway sandbox |
| `scripts/replay.py` | Replay saved runs under a draft |
| `scripts/push.py` | Put a policy in force in the user's running sandbox |
| `scripts/publish.py` | Publish a policy to the console's library through the user's sandbox |
