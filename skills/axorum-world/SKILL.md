---
name: axorum-world
description: This skill should be used when someone wants to build, revise, review, fix or publish an Axorum sandbox world (world.yaml), or describes the stage their agents should be tested on in the sandbox, such as "set up a sandbox world for our AP agent", "give the sandbox agents a team budget", "add our vendors to the world", "make the sandbox's payment network flaky", "make the x402 merchant return a malformed 402", "make the facilitator time out", "close the month on day 31 in the world", "simulate an outage", "the world check fails", or "publish my world to the console". It guides a user who may know nothing of the world format, one topic at a time, to a world that checks clean against its policy and plays its timeline, read back in plain words. The world holds the budgets, vendor lists and calendars; the rules that read them are the policy's. Not for writing the policy itself (the axorum-policy skill), nor for submitting intents as an agent (the axorum skill).
---

# Guiding a user to a world that says what they mean

A sandbox world is the stage an Axorum policy is tested on: the agents and
who they act for, the currencies, accounts and budgets, the vendors, chart of
accounts and fiscal calendar the books know, how each payment network
behaves, and what changes on which day. The sandbox serves it to the user's
real agents, so a world that is wrong tests the wrong thing, silently.

The user is usually a controller, a finance lead or a developer building an
agent. They know their vendors, budgets and month-end. They do not know the
world format and should not need to. Ask, one topic at a time; never fill a
gap silently. Prove every change with the engine: its world check, its load,
and its own account of the timeline.

## Answer from this skill and the sandbox, never from source

Answer from this skill's references, the `axorum-sandbox` CLI and the
sandbox's own answers only. Never read, search or cite Axorum source code,
specifications or repository files, even when they are in the working
directory, and never name an internal file, crate, module or line number. When
the references do not answer a question, say so and try it in a sandbox: what
the sandbox answers is what the engine answers.

## Speak the user's language

Questions and replies use the left column. The right column belongs in the
file only.

| Say | Not |
|---|---|
| the agent, who it acts for, who signs off | party, binding, principal |
| what the agent is allowed to touch | capabilities, token scope |
| a budget, a slice of the team budget | mandate, child mandate, ceiling |
| $2,500.00 | 250000 minor units |
| day 3 (January 4th), day 31 (February 1st), a day later | tick 259200, `at: 3d`, span |
| the vendor list, approved vendors | Counterparties, master data |
| the chart of accounts, the fiscal calendar | GlAccounts, FiscalPeriods |
| paid ahead, recognized over time | deferral balance |
| metered usage, model tokens | usage balance |
| the payment network declines, goes down, is back | rail answer, decline, timeout, settle |
| the merchant asks for payment, hands over what was paid for, sends a garbled reply, never answers | protocol endpoint, stage, preset, transport |
| the vendor list as of day 7 | a master-data event, source_version |
| every run comes out the same | seed |

A payment network and a merchant are two different things to test. A rail
answer is what Axorum reports beside its verdict when an intent names the
rail: the agent reads it from Axorum. A protocol endpoint is the merchant, or
the merchant's facilitator, that the agent itself calls over HTTP, speaking
x402, ACP or AP2: the sandbox plays that side of the exchange. Use a rail
answer when the test is how the agent handles Axorum's report. Use a protocol
endpoint when the agent pays a merchant itself and the test is how it handles
what the merchant says back. A world can hold both.

## The scripts

`<skill-dir>` below is this skill's directory. Run the scripts from the
directory holding the user's files. They need Python 3.11 or later and `pip
install axorum-sandbox`. Each prints prose for a person (`check.py` and
`run.py` print JSON with `--json`), and exits 0 when all is well, 3 when the
world is refused (by the check, the engine or the console), and 2 when it
could not do its job (no sandbox binary that can, a file it cannot find, a
console out of reach).

## Where to start

- **A new world** starts from a sandbox created in the console: `pull` it,
  edit it here, and publish it back (the last section). Then the interview
  from topic 1. Read `policy.axp` first if there is one: its agents, roles
  and budgets decide the parties and the mandates the policy reads. A world
  that stays on disk starts from the skeleton instead (step 2).
- **A revision** (a `world.yaml` exists): read it and its brief, ask only
  about the change, then the loop for what it touches.
- **A check that fails**: the message, by step, in `references/diagnostics.md`.
- **A review**: run `check.py` and `run.py`, read the world back, and list
  what the brief promises that the YAML does not carry.
- **A scenario** (a world with a `script`, which `axorum-sandbox save-run`
  writes): never edit the script by hand; `run` fails on a step a live run
  could not have saved, and names it (`references/diagnostics.md`). A scenario
  carries the policy it was recorded under; to compare a draft policy, replay
  it with `axorum-sandbox run scenario.yaml --policy draft.axp`. The draft
  stands in for that policy and for every policy change the scenario makes,
  each named on stderr. Each step whose decision changed, and each `end of
  run` line, is what the draft changes, with two exceptions. A step `not sent`
  is one the agent would not have sent under the draft, as its pin went stale
  in a change the draft stands in for. And `end of run not compared: …` is no
  change the draft made, but the scenario not replaying under its own policy,
  so the end was not compared at all: run it without `--policy` to see where,
  and save the run again. A scenario whose `policy` names a `file` was
  recorded before scenarios carried their policy and does not load under
  `--policy`: save the run again first. Its world is revised through the loop
  like any other.
- **Publishing**: the last section.

## Fixed facts, never asked

- **Time is in seconds from the start of the run.** The sandbox clock starts
  at 2100-01-01T00:00:00Z, and day N is January 1st plus N days: `30d` is
  January 31st, `31d` is February 1st. Turn every date the user names into
  its day, and read every day back with its date. Write spans as `2d`,
  `1d12h`; fiscal periods and other ticks as plain seconds, with the day in a
  comment. The clock runs a thousand years, to `365250d`, and no event or
  script step may come later.
- **Events fire when the clock reaches them.** `run.py` moves the clock one
  day past the last event, and no further than `365250d`; the events at `0s`,
  and any a `0s` advance reaches, apply as the run starts. Under `serve`,
  nothing moves it but the agent's test (`sandbox.advance("7d")`,
  `POST /_sandbox/advance`) and, once reached, the world's own `advance`
  events.
- **The version.** A world is
  `version: axorum.sandbox-world.v1` unless it holds protocol content: a
  `protocol` event that sets a protocol endpoint (topic 9), or a scenario's
  recorded protocol step or injected protocol change. That world is
  `version: axorum.sandbox-world.v2`, and one that still says `v1` is
  refused. The sandbox reads both, so a world with no protocol content keeps
  `v1`.
- **Amounts are whole minor units**: `250000` at exponent 2 is $2,500.00.
  A protocol endpoint's price is the protocol's own: x402 asks in the token's
  smallest unit, so `"250000"` of a six-decimal token such as USDC is 0.25.
- **Ids**: mint accounts, mandates, deferrals and usage balances with
  `python <skill-dir>/scripts/new_id.py acc mand ...`. A party, and a mandate
  the policy names, use the id their name derives; `check.py --policy
  policy.axp` lists them before the world exists. Never invent one.
- **Files live together**: `world.yaml` beside the `policy.axp` it names with
  `policy: {file: policy.axp}`, a file name alone, up to 80 characters: an
  ASCII letter or digit first, then ASCII letters, digits, `.`, `_` or `-`.
  The console's library keeps a policy by that name, so a publish refuses
  any other, a path included, though `check.py` and `run.py` accept it.
- **The examples are a starting shape, not the user's figures.** Copy a
  pattern's structure; take every name, figure and day from the user.

## The loop

### 1. Interview

One topic per turn, in this order: agents and who they act for; their roles
and what they may touch; currencies; accounts and who reads them; budgets
(the mandate tree); anything paid ahead or metered; vendors, the chart of
accounts and the fiscal calendar; how the payment networks behave over time;
the merchants the agents pay themselves, and how each answers; the timeline;
the seed. At topic 1, when there is no policy yet or an agent
does a job the policy has no party for, hand off first (the policy section
below). Each question carries why it matters and two to four options with a
labelled default. Use a structured-question tool such as
`AskUserQuestion` when available. The question bank, the brief template and
what each answer becomes are in `references/interview.md`.

### 2. Write the YAML

Start from the skeleton, the five keys a world needs before it can be read:
`version`, `world`, `policy`, `currencies` (the policy's, confirmed at topic
3) and `parties` (from topic 1). After each answer, write the keys it
becomes, starting from the closest pattern (`references/patterns.md`) and
the exact rules in `references/grammar.md`, the format's own reference. Keep the world brief at
the top of `world.yaml` current: the answer in the user's words, and the key
it became.

### 3. Check

```bash
python <skill-dir>/scripts/check.py world.yaml
```

It reads the world strictly, then judges its policy against it: currencies,
the mandates and agents the policy names, under the ids their names derive,
and the roles and capabilities the policy expects. Each policy change the
timeline schedules is judged against the world too, its lint warnings not
counted; an `axorum-sandbox` too old to judge them is refused, exit 2, with
the upgrade to install. Exit 0 is required by the read-back: no error and
no warning. Mid-interview, a refusal about a topic not reached yet is
expected (`DSL3007` before roles, `DSL3003` before budgets); fix the ones
about answered topics. Fix by step and code (`references/diagnostics.md`).

### 4. Run

```bash
python <skill-dir>/scripts/run.py world.yaml
```

It loads the world into the engine in a throwaway sandbox, moves the clock
one day past the last event, and prints what the world opened, each event
as applied or refused, and the engine's own account: the period, every
budget and who holds it, every usage balance. No agent acts, so no money
moves. Exit 0 is required unless the world means to show a refused change.

### 5. Read back

Read the world back in the user's words, from the files and the run, in the
order of the interview: who acts, money, budgets, the books, what happens
over the run, the seed. Days as days, amounts in the currency. Quote the
engine's own sentences as the engine's wording. Ask whether anything is
missing or wrong, and confirm each `(assumed)` answer. The template and a
worked read-back are in `references/interview.md`.

### 6. Revise

A correction goes back to its topic, then steps 2 to 5 again. The loop ends
when the done criteria hold.

## The policy belongs to the axorum-policy skill

The world names its policy (`policy: {file: policy.axp}`) and never writes
rules. The budget and the vendor list live in the world; the rules that read
them live in the policy. When there is no policy yet, when an agent has no
party of its own in the policy, or when the user wants a control changed,
hand the brief's agents, roles and budgets to the axorum-policy skill, which
writes and proves `policy.axp`, and come back to check the world against it.

One party per agent, even for agents that do the same job. Two agents bound
to one party share every `per party` total, and the reports name the party
by one agent URI whichever agent acted, so the user cannot tell which agent
paid. A second agent therefore needs a party of its own in the policy, with
the same role: ask the axorum-policy skill for it, with the rules the agents
share written for the role (`any_in_role`) and any total meant to count them
together written `per role`, `global`, `per counterparty(...)` or against a
budget they share.

The policy-against-world codes come back here. `DSL3003` and `DSL3005` to
`DSL3008` are fixed in the world: open the mandate, bind the agent, write its
roles and capabilities. `DSL3001` (declare the currency, or correct the
policy's), `DSL3002` and `DSL3004` (which currency is meant, the world's or
the policy's) are decided with the user. `DSL3009` (a `specific(...)` naming
a party nothing declares or binds) is most often the policy's misspelling,
and its help names the closest party. Every other code is the policy's.

## Publish, when asked

A world in the console belongs to a sandbox. A new world starts from a
sandbox created in the console: with that sandbox's secret set
(`AXORUM_SANDBOX_SINK` and `AXORUM_SANDBOX_TOKEN`), `axorum-sandbox pull
--output world.yaml` fetches its world and the policy file it names, the
loop edits them, and publishing sends them back. `pull` says so when the
sandbox has no world attached yet.

Publish only after the read-back is confirmed and the world checks and runs
clean:

```bash
python <skill-dir>/scripts/publish.py world.yaml --dry-run
python <skill-dir>/scripts/publish.py world.yaml
```

The sandbox checks the world again, counting a warning as an error, then
writes the policy file the world names and then the world, its name
included, as the world attached to that sandbox. The secret may write
nothing else.

- **The policy**: a file named like the world's current policy updates it,
  or leaves it as it is when the text is the same, and so does one named
  like a policy this sandbox created that nobody has edited since; a name
  new to the console's library creates a policy. A name held by any other
  library policy is refused, one this sandbox created that a person has
  since edited included: rename the policy file and the world's
  `policy: {file: ...}` line to publish your own copy, or ask an owner of
  that policy to attach it to the world in the console.
- **The world**: updated, or renamed when its `world:` line changed. A name
  another world in the organization holds is refused: rename the world in
  its `world:` line, not the policy file.

`--dry-run` says what would be written and writes nothing. `publish.py`
prints each change the console confirmed, from the sandbox's report, such as
`policy ap.axp: created` and `world payables: renamed from clerk`.

- **Exit 0**: published. Say what was written, from those lines.
- **Exit 3**: the check or the console refused it, and says why. A sandbox
  with no world attached is refused before anything is written: attach a
  world to the sandbox in the console, then publish. A save made in the
  console since the pull, or a world never pulled, is refused before
  anything is written too: `references/diagnostics.md` gives the fix. Pass
  --replace only when the user has said to overwrite the console's version.
  When the console refused the world after the policy was written, it says
  which policy was written. Fix it through the loop, or rename what the
  reason names, and publish again.
- **Exit 2**: it could not do its job, and says why: a sandbox too old to
  publish (`pip install -U axorum-sandbox`), a variable missing, the console
  out of reach, or a write the console did not confirm. An unconfirmed write
  may have landed: once the cause is fixed, running the same publish again
  finishes the job, and says `unchanged` for what had landed. Never claim
  the world was published.

A publish changes only the console library's copy. When a change landed,
the sandbox says so through `publish.py`: a running `serve` keeps the world it
started with until it is restarted, and the next `serve` with no world file
serves the published copy.

## Done

All of these hold, or the reply says which does not and why:

1. `check.py` exits 0: the world holds together and its policy binds to it.
2. `run.py` exits 0, or the brief says which refused event is meant.
3. Every topic of the interview is answered or marked `(assumed)` in the
   brief, and the user confirmed the read-back.
4. Published, if they asked: `publish.py` exited 0.

## Hand back

Keep the reply short; the files carry the detail.

1. **Where it is**: the files written or changed.
2. **What it holds**: the read-back, one line per topic, in the user's words.
3. **Proof**: "checks clean against policy.axp; run.py moved the clock to day
   32 (February 2nd) with every event applied", with any refusal worth a
   second look.
4. **Please confirm**: each `(assumed)` answer, one line each.
5. **What it relies on**, only when true: the policy's agent and budget
   names, a vendor list an approved-vendor rule reads, a calendar a period
   rule reads.

Leave out ids, minor-unit arithmetic and the full YAML.

## Resources

| File | Use it for |
|---|---|
| `references/interview.md` | The question bank, the world brief and the read-back, worked |
| `references/patterns.md` | What a user says, next to the checked YAML it becomes |
| `references/grammar.md` | The world format's reference: every key, rule and default (a copy of `axorum-sandbox grammar world`) |
| `references/diagnostics.md` | Every refusal by step: reading, policy against world, timeline policy changes, loading, events, replaying a scenario, publishing |
| `examples/ap-month-end/` | One AP agent through month end: vendor limits, a chart, a fiscal close, a flaky network |
| `examples/api-team/` | Two agents under a team budget with slices, metered tokens, a prepaid subscription, two networks |
| `examples/paid-research/` | One agent paying a data API over x402 that asks for payment, garbles a reply and drops an answer (version 2) |
| `scripts/check.py` | Read the world and judge its policy against it; with `--policy` alone, list the ids a world needs |
| `scripts/run.py` | Load the world and play its timeline in a throwaway sandbox |
| `scripts/new_id.py` | Mint fresh ids for accounts, mandates, deferrals and usage balances |
| `scripts/publish.py` | Publish the world and the policy it names to the console, through its sandbox |
