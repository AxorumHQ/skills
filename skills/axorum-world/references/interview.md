# The interview, the world brief and the read-back

A world is the stage a policy plays on: who the agents are, what money and
budgets exist, which vendors and periods the books know, how the payment
networks behave, and what changes on which day. The user knows all of this
about their business. They do not know the file format, and they should not
need to.

Ask one topic at a time, in the order below. Each question carries one line
on why it matters and two to four options with a labelled default. Skip a
question the user's request or the files already answer, and say what was
taken from where. Write the skeleton first (the five keys a world needs to
be read, step 2 of the loop in `SKILL.md`). Its `policy: {file: ...}` names
the policy file as a publish keeps it, a file name alone, up to 80
characters: an ASCII letter or digit first, then ASCII letters, digits, `.`,
`_` or `-` (`ap-month-end.axp`, not `AP policy.axp`). A file of the user's
named otherwise is renamed now, since `check.py` and `run.py` accept the
name and only the publish refuses it. After each answer, write the YAML it
becomes and check it: a refusal about a topic not reached yet is expected,
and the ones about answered topics are fixed. Once the world checks clean,
run it and read the change back.

## The world brief

Keep a running brief at the top of `world.yaml`, as a comment, one line per
topic: the answer in the user's words, then the key it became. Every example
opens with one.

```text
# The interview, answer by answer, and where each answer went:
#   Agents        <who acts, and for whom>        -> parties
#   Currencies    <which money, how it counts>    -> currencies
#   ...
#   Seed          <the seed>                      -> seed
```

Mark an answer the user did not give, but the skill chose as the default,
`(assumed)`, and confirm each one before the world is done.

## 1. Agents, and who they act for

- **Ask**: "Which AI agents will act in this world, and on whose behalf?"
- **Why**: each agent is bound to a party the policy declares, and a world
  agent the policy does not know is refused on everything it tries.
- **Options**: the agents the policy declares (`check.py --policy
  policy.axp` lists them); an agent the policy has no party for, a second
  agent doing a job another already does included (the policy needs a party
  for it first: hand off to the axorum-policy skill); an agent that should be
  refused, kept on purpose to show the refusal.
- **Becomes**: one `parties` entry per agent, with an `agent://` URI and the
  `party:` id the policy's name derives (`check.py --policy policy.axp`
  lists it). A principal, the person who signs off, is never bound.
- **Watch for**: a URI is `agent://<host>/<path>/<label>_<suffix>`, the label
  lowercase letters and `_`, starting and ending with a letter: a second agent
  is `aptwo_...`, never `ap2_...`. One agent, one entry, one party: two agents
  bound to one party are reported as one agent.

## 2. Parties: roles and capabilities

- **Ask**: "What is each agent allowed to touch: which actions, and which
  payment networks?"
- **Why**: the token an agent carries admits only its capabilities. An action
  the policy grants but the token leaves out is turned away before the policy
  is asked.
- **Options**: exactly what the policy delegates (default); narrower, to show
  the gateway turning an action away.
- **Becomes**: `roles` exactly as the policy gives that party, and
  `capabilities`: each action by name and each rail as `rail/<name>`. With no
  `capabilities` key the token covers every action and rail; an empty list is
  refused.

## 3. Currencies

- **Ask**: "Which currencies does the money move in, and is any of it counted
  in whole units, like tokens or credits?"
- **Why**: every amount in the world is a whole number of the currency's
  smallest unit, so the exponent decides what `250000` means.
- **Options**: US dollars in cents, `USD` exponent 2 (default); several fiat
  currencies; a metered unit such as `TOKENS` exponent 0.
- **Becomes**: `currencies`, one entry each. A currency the policy names must
  be declared here (DSL3001).

## 4. Accounts and their owners

- **Ask**: "Which accounts should exist from the start, and which agent may
  read each one?"
- **Why**: an account's owner is the party whose agent may read its balance;
  an account with no owner is read by nobody. Neither decides a verdict.
- **Options**: one spend account per currency, owned by the paying agent
  (default); separate payables or accrual accounts with no reader.
- **Becomes**: `accounts`, each with a fresh id from `new_id.py acc`, its
  currency, a label the reports show, and `owner:` a party id from step 1.

## 5. Ceilings, which become a mandate tree

- **Ask**: "How much may be spent in total, and does any agent or team get a
  smaller slice of it?"
- **Why**: a budget is a mandate: a ceiling the engine charges every
  committed payment against. A slice is a child mandate, never looser than
  its parent.
- **Options**: one budget for everyone (default); a team budget with a slice
  per agent; no budget at all.
- **Becomes**: `mandates`, the parent first. A mandate the policy reads by
  name (`projected(team_budget)`) uses the id `check.py` prints for it
  (DSL3003); any other gets a fresh id from `new_id.py mand`. An agent is
  charged to one mandate with the party's `mandate:` key.
- **Watch for**: a child above its parent, or in another currency, is refused
  when the world loads.

## 6. Deferrals and usage

- **Ask**: "Is anything paid ahead and recognized over time, like a yearly
  subscription? Is anything metered, like model tokens or API calls?"
- **Why**: a prepaid amount needs a deferral balance, and metered
  consumption needs a usage balance, before an agent can post to either.
- **Options**: neither (default); a deferral; a usage balance owned by the
  agent that consumes it.
- **Becomes**: `deferrals` and `usages`, each with a fresh id
  (`new_id.py defr`, `new_id.py usage`), a currency, and for a usage balance
  an `owner`.

## 7. Counterparties and the chart of accounts, which become master data

- **Ask**: "Which vendors does the business pay, which are approved, and is
  there a limit per vendor? Which ledger accounts, and which fiscal periods,
  does the policy need to know?"
- **Why**: a policy that pays "approved vendors", caps a vendor, or books
  only into open periods reads these lists, and an empty list approves
  nobody.
- **Options**: a vendor list with approvals (default when the policy reads
  approved counterparties); limits per vendor; a chart of accounts; a fiscal
  calendar.
- **Becomes**: `master_data`, one entry per kind: `Counterparties`,
  `GlAccounts`, `FiscalPeriods`, each with a `source_version` naming that
  version of the list. A vendor's id is its canonical name; `aliases` are
  other spellings that resolve to it; `limit` is in minor units. A vendor
  kept with `approved: false` is refused on the record rather than turned
  away as unknown.

## 8. Rail behaviour over time

- **Ask**: "How do the payment networks behave? Does any decline, go down, or
  come back during the run?"
- **Why**: a mocked rail answers each call an allowed intent makes: settle,
  decline or timeout. A decline or timeout is reported beside the verdict and
  changes neither the verdict nor the ledger, which is exactly what an
  agent's retry logic must cope with.
- **Options**: everything settles (default); a standing answer per rail;
  the next few calls decline (`times`); an outage from one day to another (a
  change, then a change back).
- **Becomes**: `rails` for the standing answers, and `rail` events for the
  changes over time. A slow or failing network is `timeout`.

## 9. Merchants the agents pay themselves

- **Ask**: "Does an agent pay a merchant or an API itself, over x402, ACP or
  AP2? If so, what should that merchant do: ask for payment and hand over
  what was paid for, send a reply the agent cannot read, or go quiet?"
- **Why**: the sandbox can play the merchant's side of the exchange, so the
  agent's own payment code meets each reply a real merchant gives, with no
  real money and no network. An agent that only sends intents to Axorum and
  reads the rail answer has nothing to set here: topic 8 covers it.
- **Which part of the exchange the agent meets**: an x402 buyer calls the
  resource, the paid URL; an x402 seller checks and collects a payment
  through a facilitator, its `verify` and `settle` stages. ACP checkout has
  `create`, `read`, `update`, `complete` and `cancel`; AP2 has
  `instruments`, `payment_mandate` and `checkout_mandate`. Each part answers
  as a well-behaved merchant does until an event says otherwise: the x402
  resource asks for payment, then hands over what was paid for, and the
  facilitator verifies and settles. A running sandbox lists every protocol,
  stage, preset and parameter at `/_sandbox/protocols`
  (`sandbox.protocol_catalogue()` in Python). Answer from that list, and
  never invent a preset.
- **Options**, for each part the agent meets:
  - **Paid** (default): asked for payment, it answers HTTP 402 with the
    price; paid, it hands over what was paid for, with a receipt. One
    purchase after another needs `repeat: cycle`.
  - **Payment required at the user's price**: the same, with the price as
    `amount`, in the token's smallest unit.
  - **A reply the agent cannot read**: a 402 whose payment request cannot
    be read (`malformed_challenge`), what was paid for with a receipt that
    cannot be read (`malformed_receipt`), or a body that is not valid JSON
    (`malformed_response`).
  - **A timeout**: the merchant holds the connection and closes it with no
    reply (transport `timeout` with `milliseconds`, 10000 for 10 seconds,
    at most 60000), answers late (`delay`, with `milliseconds` too), or
    drops the reply after accepting the request (`drop_after_accept`).
  - **Retries**: whatever the agent does after a timeout. A retry with the
    same signed payment is recorded as the same payment, not a second one,
    and gets the reply the timed-out call was given, so the body goes on
    that behavior; the next behavior answers only a retry with a new
    payment, which is a second payment.
- **Becomes**: `version: axorum.sandbox-world.v2`, and one `protocol` event
  per change: the `protocol`, the `stage`, and its `behaviors` in the order
  requests meet them. Each behavior is a `preset`, its `parameters`, an
  optional `transport`, and a `match` on whether the request carries a
  payment (`payment_present`). `repeat` says what happens once the list runs
  out: `last` (the default) keeps the last behavior, `cycle` starts over, and
  `once` refuses every later request.
- **Watch for**: a request that does not match the next behavior's `match`
  is answered `400 unmatched_request` and uses nothing up, so an agent that
  pays before it is asked meets that. A new event for a stage replaces that
  stage's whole list. Under `serve`, point the agent at the sandbox in place
  of the merchant: the x402 resource is
  `http://127.0.0.1:<port>/_sandbox/rails/x402/resource`, and its
  facilitator is `.../verify` and `.../settle` beside it. `run.py` sends no
  requests, so it shows each event applied and nothing more; the exchanges
  appear once the agent runs against `serve`, and `save-run` records them.

## 10. The timeline

- **Ask**: "What changes during the run, and on which day? A vendor
  suspended, a period closed, the clock moving on to see what comes due?"
- **Why**: events apply when the clock reaches them, so the policy is tested
  against a world that changes, as the books do.
- **Options**: nothing changes (default); a master-data change on a day; an
  `advance` that moves the clock so duties come due and breach; a policy
  change on a day, so agents re-pin and the new rules decide; a merchant
  that starts to misbehave on a day (topic 9).
- **Becomes**: `events`, in time order, each `at` a span from the start
  (`2d`, `31d`, `1d12h`) with exactly one of `master_data`, `rail`,
  `advance`, `policy` or `protocol`. A master-data event replaces that kind's whole list,
  so copy the entries that stay. A `policy` event names a `file` beside the
  world or holds its `source`; a world to publish holds its `source`, as the
  console keeps no file beside the world.
- **Watch for**: day N is January 1st plus N days, so "the 31st" is `30d`
  and February 1st is `31d`. Under `serve`, an event fires only once the
  agent's test moves the clock to it.

## 11. The seed

- **Ask**: "Should every run of this world be identical?"
- **Why**: every key and token of a run derives from the seed, so one world
  and one seed give one run, on every machine.
- **Options**: a fixed seed such as 42 (default); none, which is 0 unless the
  run is given `--seed`.
- **Becomes**: `seed`.

## The read-back

After each change, and in full when the world is done, read the world back
in the user's words, from the files and from what the engine said, never
from memory. Run it first:

```bash
python <skill-dir>/scripts/run.py world.yaml
```

For `examples/ap-month-end`, it prints, among the rest:

```text
ap-month-end: loaded; the clock moved to 32d (2100-02-02T00:00:00Z)
Events, each at its time (the ones applied as the run started first):
  2d       rail         applied
  5d       master_data  applied
  20d      rail         applied
  22d      rail         applied
  31d      master_data  applied
  31d      advance      applied
Mandate AP budget, January: $0.00 of $25,000.00 spent, $25,000.00 remaining. Held by agent ap_bot.
```

and the read-back is:

> **Who acts**: one agent, the AP bot, paying for the controller. It may
> pay and book accruals, over x402 only.
>
> **Money**: US dollars in cents. Three accounts: agent spend and agent
> payables, which the AP bot reads, and accrued liabilities, which no agent
> reads.
>
> **Budget**: $25,000.00 for January, all of it the AP bot's.
>
> **Books**: three vendors. Acme Supplies (also spelled "acme") and Globex
> are approved, with limits of $5,000.00 and $10,000.00; Shady LLC is not.
> Three ledger accounts. January and February 2100, both open.
>
> **Over the month**: x402 settles. On day 2 (January 3rd) its next two
> calls decline. On day 5 (January 6th) Globex is suspended. On day 20
> (January 21st) x402 goes down, and on day 22 (January 23rd) it is back. On
> day 31 (February 1st) January closes, and the clock moves a day further.
> Each change fires when the clock reaches its day: here run.py moved it to
> day 32 (February 2nd); under `serve`, the agent's test moves it.
>
> **Every run is the same**: seed 7.

Say each day as a day with its date ("day 31, February 1st"), each amount in
the currency ("$25,000.00"), never ticks or minor units. Quote the engine's own sentences (the mandate
and usage lines, the period report) as the engine's wording. Then ask
whether anything is missing or wrong, and confirm each `(assumed)` answer.
A correction goes back to its topic, then the YAML.
