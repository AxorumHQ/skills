# The sandbox world format, `axorum.sandbox-world.v1`

A world is what a sandbox run starts from. It holds the policy, the currencies
amounts are in, and the accounts, budgets and balances it opens. It also holds
the agents it binds, the master data it imports, how each mocked payment rail
answers, and a timeline of events that change the world while the run goes on.
A scenario is a world plus the `script` of one run, which `axorum-sandbox run`
replays.

This file is the whole format. `axorum-sandbox grammar world` prints it as the
installed sandbox reads it. Each rule is a short statement followed by a
minimal example. A YAML block that starts with `version:` is a whole world.
Any other YAML block is a fragment: top-level keys that take the place of the
same keys in the smallest world below. Tests read every block that way, and
each one parses and passes the world check.

## The smallest world

A world needs `version`, `world`, `policy`, `currencies` and `parties`. Every
other key is optional.

```yaml
version: axorum.sandbox-world.v1
world: smallest
policy:
  source: |
    policy {
      role clerk
      action purchase(amount: amount, payee: text)
      party clerk_bot agent roles(clerk)
      party controller principal
      delegation clerk_grant {
        principal controller
        agent clerk_bot
        scope { actions(purchase) roles(clerk) }
      }
      rule permit_purchase { permitted any_in_role(clerk) do purchase priority 1 }
    }
currencies:
- currency: USD
  exponent: 2
parties:
- agent: agent://example.com/agent/clerk_01h455vb4pex5vsknk084sn02q
  party: party_28zwgzaew1a2r92s1y9swtj3nj
  roles: [clerk]
```

## Reading the format

- **YAML is read strictly.** A key the format does not define is refused,
  everywhere but inside the engine payloads a script records (see Script), and
  so are a duplicate key, a merge key (`<<`), a boolean spelled other than
  `true` or `false`, and a tag, except a core tag such as `!!str` or `!!int`
  on a value of that type. Anchors (`&name`) and aliases (`*name`) are
  refused too: write each value out in full. The error names the line and
  column.
- **Keys are case-sensitive.** Every key is snake_case except the three
  master-data kinds: `Counterparties`, `GlAccounts` and `FiscalPeriods`.
- **Time is counted in seconds.** One tick is one second from the start of
  the run. The sandbox clock starts at 2100-01-01T00:00:00Z and moves only when
  the run advances it.
- **A span** (`at`, `advance`) is one or more `<count><unit>` terms. The units
  are `w`, `d`, `h`, `m` and `s`, largest first, each at most once: `90s`,
  `2d`, `1d12h30m`. A bare integer is a count of seconds. A span is written
  back with the largest units that fit and no weeks, so `1w` comes back as
  `7d` and zero as `0s`.
- **Amounts are whole minor units** at the currency's exponent: `250000` at
  exponent 2 is 2,500.00. An amount is a signed 128-bit integer, never a
  decimal.
- **An id** is a prefix, `_`, and a 26-character suffix of lowercase
  Crockford base32 (`0-9` and `a-z` without `i`, `l`, `o` or `u`) whose
  first character is `0` to `7`.

| Prefix | Identifies |
|---|---|
| `acc_` | an account |
| `mand_` | a mandate |
| `defr_` | a deferral balance |
| `usage_` | a usage balance |
| `party_` | a party |
| `txn_` | a transaction, in a script |
| `pol_` | a policy, in a script |

- **A party or mandate the policy names** must be opened under the id its
  name derives. `axorum-sandbox check policy.axp --world world.yaml` prints
  each one. Every other id may be any id with the right prefix.
- **Names.** A world name is 1 to 64 of `a-z`, `0-9` and `-`, starting and
  ending with a letter or digit. A role, an action and a rail are 1 to 64 of
  `a-z`, `0-9` and `_`. A currency code is 3 to 8 uppercase letters.

## Top level

`description` says what the world is for. `seed` is where every key and token
of a run derives from. A run uses `--seed` when given, else the world's
`seed`, else 0. A saved scenario records the seed its run used.

```yaml
description: One clerk who buys from approved vendors.
seed: 7
```

The keys, in the order the sandbox writes them:

| Key | Required | Holds |
|---|---|---|
| `version` | yes | always `axorum.sandbox-world.v1` |
| `world` | yes | the world's name |
| `description` | no | what the world is for |
| `seed` | no | the seed a run starts from |
| `policy` | yes | the policy in force from the start |
| `currencies` | yes | the currencies and their exponents |
| `accounts` | no | the ledger accounts |
| `mandates` | no | the spending ceilings, parent before child |
| `deferrals` | no | the deferral balances |
| `usages` | no | the usage balances |
| `parties` | yes | the agents and the parties they act as |
| `master_data` | no | counterparties, chart of accounts and fiscal calendar |
| `rails` | no | how each mocked rail answers |
| `events` | no | the timeline |
| `script` | no | what agents did in one run; a world with one is a scenario |

## Policy

`policy` is the policy in force from the start. `source` holds the policy text
itself, and must not be blank: the smallest world above shows it. `file` names
a policy file, relative to the world file, which `serve` and `run` read from
there. `serve --policy` and `run --policy` run another policy in its place.
`check POLICY --world WORLD` judges the policy it is given against the world
and does not read the world's `policy`. The policy language itself is outside
this reference: the axorum-policy skill guides writing a policy.

```yaml
policy:
  file: policy.axp
```

## Currencies

Each entry declares a currency once, with its exponent: the count of
minor-unit digits, 0 to 18. Every account, mandate, deferral and usage balance
is in a declared currency. A unit that is not money is a currency too: declare
it with exponent 0.

```yaml
currencies:
- currency: USD
  exponent: 2
- currency: USDC
  exponent: 6
- currency: TOKENS
  exponent: 0
```

## Accounts

Each entry opens a ledger account in one currency, in list order. `label` is
its display name. `owner` is the party whose agent may read the account's
balance; an account with no owner is read by nobody. Neither decides a
verdict.

```yaml
accounts:
- account: acc_0jffxpndb9a2garx5fj166tc4c
  currency: USD
  label: Agent spend (USD)
  owner: party_28zwgzaew1a2r92s1y9swtj3nj
- account: acc_118q65km28a9zrw0dbexkpd43v
  currency: USD
```

## Mandates

A mandate is a spending ceiling. Each allowed intent of a party bound to it
draws it down, and so draws down every mandate above it.

- `ceiling` is in minor units of `currency`, and is 0 or more.
- `parent` names a mandate opened earlier in `mandates`, so a parent comes
  before its children.
- A child is in its parent's currency, and its ceiling is at most its
  parent's. Children's ceilings may add up to more than their parent's: the
  parent's own ceiling still bounds what they spend together.
- A chain is at most 8 mandates deep, its root included.
- `label` names the mandate in reports and refusals, ahead of the policy's own
  name for it.

```yaml
mandates:
- mandate: mand_4rcxqt8kd3bc99kr06a57h4kxx
  currency: USD
  ceiling: 500000
  label: team_budget
- mandate: mand_0nxsjgtgxjb91vfgm0benm4k8t
  currency: USD
  ceiling: 100000
  parent: mand_4rcxqt8kd3bc99kr06a57h4kxx
  label: buyer_mandate
```

## Deferrals

A deferral balance holds revenue earned later, or cost paid ahead. It opens at
zero and has no ceiling: intents that defer into it build it, and intents that
recognize from it draw it down, never past what was deferred.

```yaml
deferrals:
- deferral: defr_01k6z8x2c4m9t5v7w3y1q0r2s0
  currency: USD
```

## Usages

A usage balance tracks a metered resource as three running totals, consumed,
metered and billed, each opening at zero. Intents move them, and billed never
passes metered, nor metered consumed. `owner` is required: the party the
balance belongs to.

```yaml
currencies:
- currency: USD
  exponent: 2
- currency: TOKENS
  exponent: 0
usages:
- usage: usage_01k6z8x2c4m9t5v7w3y1q0r2s0
  currency: TOKENS
  owner: party_28zwgzaew1a2r92s1y9swtj3nj
```

## Parties

Each entry binds one agent to the party it acts as. A world binds at least one
agent, and each agent once. A policy's principals are never bound.

- `agent` is the agent's URI:
  `agent://<trust root>/<capability path>/<label>_<26-character suffix>`. The
  capability path is required, one or more segments of lowercase letters,
  digits and `-`. The label is lowercase letters and `_`, starting and ending
  with a letter, and the suffix is 26 characters like the suffix of an id.
  `agent://example.com/agent/clerk2_01h455vb4pex5vsknk084sn02q` is refused:
  its label ends in a digit. The sandbox derives a signing key for each trust
  root and each agent from the seed. For a second agent, change the label
  (`buyer_01h455vb4pex5vsknk084sn02q`) or the suffix alone.
- `party` is the id the policy's party name derives. Run
  `axorum-sandbox check POLICY` first: its JSON verdict lists each party's id
  under `parties`. An agent bound to any other id is judged as a stranger, and
  every intent it submits is refused.
- `roles` are the roles the policy gives that party.
- `mandate` names a mandate opened in `mandates`. Every allowed intent of the
  agent is charged to it. Without one, the agent's intents charge no mandate.
- `capabilities` are what the agent's tokens cover, each below the agent's
  own capability path: an action (`purchase`) or a rail (`rail/x402`). An
  action's `_` becomes `-` in the token, so `pay_vendor` covers
  `<path>/pay-vendor`. A capability is one or more `/`-separated segments of
  `a-z`, `0-9`, `_` and `-`. The gateway turns away, with 403 and before the
  policy is consulted, an intent whose action or declared rail the token does
  not cover.
- Without `capabilities`, the agent's tokens carry its own path, which covers
  every action and every rail. An empty list is refused: its tokens would
  admit nothing.

```yaml
mandates:
- mandate: mand_0nxsjgtgxjb91vfgm0benm4k8t
  currency: USD
  ceiling: 100000
parties:
- agent: agent://example.com/agent/clerk_01h455vb4pex5vsknk084sn02q
  party: party_28zwgzaew1a2r92s1y9swtj3nj
  roles: [clerk]
  mandate: mand_0nxsjgtgxjb91vfgm0benm4k8t
  capabilities: [purchase, rail/x402]
```

## Master data

`master_data` is imported before the first intent, at most one import of each
kind. Each import replaces the whole set of its kind. In a counterparty list
or a chart, an id listed twice keeps its last entry; a calendar that lists a
period id twice is refused when the world loads. `source_version` is the
ERP's marker for the set, free text: quote one that YAML would read as a
number, such as `"2026.09"`. To change a set later in the run, put the new set
in `events`.
Master data is read as strictly as the rest of the world, wherever it
appears: a key its records do not define is refused.

Each entry, a counterparty, an account in the chart or a period in the
calendar, takes at most 4,096 bytes as a run's snapshot writes it: its id
and every field as JSON, with its quotes and punctuation, a character past
ASCII taking two to four bytes and a quote or a backslash two. An entry over
that is refused when the world is read, naming the entry, its size and the
limit, and so is a live master-data event that carries one.

### Counterparties

The counterparty list backs a policy's `approved counterparties`, `per
counterparty(...)` and `counterparty limit(...)`. `entries` is a list of
pairs: the counterparty's canonical id, then its record.

- `display_name` and `approved` are required. `approved: false` keeps a
  counterparty known, so an intent naming it is refused on the record rather
  than turned away.
- `erp_ref` is the ERP's own key for it.
- `aliases` are other spellings that resolve to the canonical id. An alias
  that is a canonical id in the list, its own included, or that two
  counterparties both list, is refused when the world loads.
- `limit` is a spending limit, as `minor` units of a `currency`. Its currency
  is not checked against `currencies`.

```yaml
master_data:
- Counterparties:
    source_version: vendors-v1
    entries:
    - - acme
      - display_name: Acme Supplies
        approved: true
        erp_ref: V-1042
        aliases: [acme inc]
        limit:
          minor: 500000
          currency: USD
    - - shady-llc
      - display_name: Shady LLC
        approved: false
```

### Chart of accounts

The chart backs a policy's `chart of accounts`. `entries` is a list of pairs:
a ledger account id, then the ERP's `code` and `name` for it.

```yaml
master_data:
- GlAccounts:
    source_version: "2026.09"
    entries:
    - - acc_0jffxpndb9a2garx5fj166tc4c
      - code: "6000"
        name: Agent spend
```

### Fiscal calendar

The calendar backs a policy's `open fiscal periods`. Each period has an `id`,
a `label`, and `from` and `to` ticks, both inclusive. A tick is written as a
whole number of seconds from the start of the run, not as a span:
`to: 2678399`, never `to: 31d`. Periods are in order and do not overlap,
`from` is at most `to`, and no two periods share an `id`; a calendar that
breaks one of these is refused when the world loads. `open` says whether the
period takes new postings, and is `true` when absent.

```yaml
master_data:
- FiscalPeriods:
    source_version: fy2100
    periods:
    - id: 2100-01
      label: January 2100
      from: 0
      to: 2678399
    - id: 2100-02
      label: February 2100
      from: 2678400
      to: 5097599
      open: false
```

## Rails

`rails` maps a rail's name to its standing answer: `settle`, `decline` or
`timeout`. A rail the map does not name settles. A mocked rail answers the
call an intent makes when the intent names the rail and the policy allows it.
Its answer is reported beside the outcome, and changes neither the verdict
nor the ledger.

```yaml
rails:
  x402: decline
  acp: timeout
  ap2: settle
```

## Events

`events` is the timeline. Each event is `at`, a span from the start of the
run, and exactly one change beside it: `master_data`, `rail`, `advance` or
`policy`.

- Events are listed in time order. Events at the same `at` apply in list
  order.
- An event applies when the run's clock reaches its `at`. The clock moves only
  when the run advances it: by an `advance` event, by `axorum-sandbox inject`,
  or by the developer's clock control, and under `run` up to each script
  step's `at` before the step plays. An event at `0s` applies as the run
  starts.
- The clock runs at most 1000 years of 365.25 days from the start of the run,
  to its last second at `365250d`. A move past it by `inject` or the clock
  control is refused, and the clock stays where it was; a scheduled `advance`
  stops at the last second; an `at` past it, and a script step whose `inject`
  advances past it from its `at`, are refused when the world is checked. A
  step whose `inject` advances past it from where an earlier step or event
  left the clock is refused when `run` replays it, and the replay fails.
- `master_data` replaces one kind's whole set, written as a `master_data`
  entry is. When the engine refuses the import, the run records the refusal
  and nothing changes.
- `rail` changes how one rail answers. Without `times`, the new answer stands
  from then on, and replaces any counted answer still pending. With `times`,
  a count of 1 or more, the rail's next calls get it, and then the rail
  answers as it did before.
- `advance` moves the clock on by a span from the event's `at`, so duties
  come due and breach on schedule. Every event the move passes applies at its
  own `at`.
- `policy` puts another policy in force, as `axorum-sandbox policy` does in a
  running `serve`. It is written as the world's `policy` is: the text under
  `source`, which must not be blank, or a file under `file`, relative to the
  world file and read when the world loads. From then on the new policy
  decides, and an agent's next intent pinned to the policy before it is
  refused `409 stale_policy` until the agent re-pins. A change to the policy
  already in force changes nothing. `save-run` writes the file's text under
  `source`, so a scenario carries every policy its run changed to.
  `axorum-sandbox publish world` needs `source`: the console keeps the world
  alone, with no file beside it, and publish refuses a change by `file`.

```yaml
events:
- at: 0s
  rail:
    rail: x402
    answer: decline
    times: 1
- at: 2d
  master_data:
    Counterparties:
      source_version: vendors-v2
      entries:
      - - acme
        - display_name: Acme Supplies
          approved: false
- at: 7d
  advance: 1d
- at: 14d
  policy:
    file: policy.axp
```

## One event, for `inject`

`axorum-sandbox inject FILE` applies one event to a running `serve` now. The
file holds one `events` entry without its `at`.

```yaml event
advance: 1d
```

```yaml event
rail:
  rail: x402
  answer: timeout
```

A policy change carries its policy under `source`: a running `serve` has no
world file to read a `file` beside, and refuses one. `axorum-sandbox policy
FILE` reads a policy file and puts it in force, which is the shorter way.

```yaml event
policy:
  source: |
    policy {
      role clerk
      action purchase(amount: amount, payee: text)
      party clerk_bot agent roles(clerk)
      party controller principal
      delegation clerk_grant {
        principal controller
        agent clerk_bot
        scope { actions(purchase) roles(clerk) }
      }
      rule permit_purchase { permitted any_in_role(clerk) do purchase priority 2 }
    }
```

## Script

A scenario is a world with a `script`: what agents did in one run, which
`axorum-sandbox save-run` writes. `run` replays it from the same seed and
holds each submission to the answer the script recorded. A different answer
is a regression, and `run` exits 1. Steps are in time order. Events from the
timeline are not steps, since a replay fires them again.

A scenario carries the policy its run ran under: `save-run` writes it as the
scenario's `policy.source`, though the world named a `file`. `run` replays a
scenario under the policy it carries, each answer held byte for byte, and
`run --policy` tries another one against it. A scenario whose `policy` names a
`file` was recorded before scenarios carried their policy: `run` replays it
under that file as the file reads now, and under `--policy` does not load it.

- `submit` is an intent an agent sent. `at` is when, `intent` is the intent
  as sent, and `expect` is the answer it got.
- `expect` holds `outcome` when the intent was judged. A refusal by the policy
  is an outcome too, posting nothing. `expect` holds `refused` when the
  gateway turned the intent away before judging it: its HTTP `status` and
  error `body`.
- `rail` is what the mocked rail answered, present only when the intent names
  a rail and its outcome let the call through. A step that records a rail
  answer for an intent that names no rail, or that the gateway refused, is
  refused.
- `inject` is a change made live, or a manual advance, written as an `events`
  entry is. A live policy change is an `inject` with its `policy.source`,
  recorded whether the sandbox put it in force or refused it: a replay makes
  the change again, and a refused one is refused again.
- `outcome`, beside an `inject`'s change, is what the change did when the run
  made it. `applied` is a change that took effect, and a policy change's names
  the policy it put in force. `unchanged` is a policy change to the policy
  already in force, which changed nothing. `refused` is a change the engine
  refused, with its HTTP `status`, its `error` code (`invalid_policy` for a
  policy that does not compile), its `message`, cut to 400 characters, and
  `diagnostics`, how many compile diagnostics the refusal listed (0 for any
  other refusal). The diagnostics themselves are not recorded: checking the
  change's `source` gives them again. A policy change's `refused` names the
  policy its source compiles to, when it compiles. A run records `outcome` on
  every `inject`; a step a person writes leaves it out, and a replay does not
  hold a change to it, since what a change did shows in the answers after it.

Three keys hold engine payloads, the agent plane's own documents. `save-run`
writes them, a person never does, and this reference does not repeat their
fields. Each is a schema in the agent plane's contract, which a running
sandbox serves at `/api/openapi.json`
(`curl http://127.0.0.1:7340/api/openapi.json`), as `axorum serve` does:

| Key | Schema | What it is |
|---|---|---|
| `script[].submit.intent` | `IntentEnvelope` | the body of `POST /api/v1/intents` |
| `script[].submit.expect.outcome` | `AgentOutcome` | its `200` answer |
| `script[].submit.expect.refused.body` | `ApiError` | its error answer |

The format does not check the keys inside these payloads: they are recorded
engine values, not checked key by key, so a key the contract does not define,
such as `memo: hi` inside an `intent`, still loads.

A run of the smallest world with two accounts: the clock moved on an hour,
a purchase that settled over x402, the clock moved on to day 3, and an intent
pinned to a policy no longer in force. `run` replays it as recorded.

```yaml
accounts:
- account: acc_0jffxpndb9a2garx5fj166tc4c
  currency: USD
  label: Agent spend (USD)
  owner: party_28zwgzaew1a2r92s1y9swtj3nj
- account: acc_118q65km28a9zrw0dbexkpd43v
  currency: USD
script:
- inject:
    at: 0s
    advance: 1h
    outcome:
      applied: {}
- submit:
    at: 1h
    intent:
      agent: agent://example.com/agent/clerk_01h455vb4pex5vsknk084sn02q
      attestation: >-
        v4.public.eyJhZ2VudF9rZXkiOiJqVE1pZkZtR0hTTEFxMHM5R0lGb2l0SDJaV3BCMDkvS1hsSi9HM2pUNFVNPSIsImFnZW50X3VyaSI6ImFnZW50Oi8vZXhhbXBsZS5jb20vYWdlbnQvY2xlcmtfMDFoNDU1dmI0cGV4NXZza25rMDg0c24wMnEiLCJjYXBhYmlsaXRpZXMiOlsiYWdlbnQiXSwiZXhwIjoiMjEwMC0wMS0wMlQwMTowMDowMC4wMDBaIiwiaWF0IjoiMjEwMC0wMS0wMVQwMTowMDowMC4wMDBaIiwiaXNzIjoiZXhhbXBsZS5jb20iLCJqdGkiOiIwM3FjcGZuaG0wZjAwYTZhcjk0bWY5MTczYyJ90ecyPOoO3LVX5tUBMWubrYVfDb96jCLM1nJHOdtx77-xEDbPWwa8oElNaNToCj0kp6u9vpwTu4P_I9Yh70g8Ag
      transaction: txn_03qcpfnhm0e008000000000001
      entries:
      - account: acc_118q65km28a9zrw0dbexkpd43v
        side: Debit
        amount:
          minor: 12500
          currency: USD
      - account: acc_0jffxpndb9a2garx5fj166tc4c
        side: Credit
        amount:
          minor: 12500
          currency: USD
      action:
        action: purchase
        bindings:
          amount:
            Amount:
              minor: 12500
              currency: USD
          payee:
            Text: acme
      evidence: []
      justification: invoice 1042
      policy: pol_57q1s3amg8a708meyd8hw7f87e
      rail: x402
      minted_at_ms: 4102448400000
    expect:
      outcome:
        transaction: txn_03qcpfnhm0e008000000000001
        commit_tick: 3600
        verdict: Permitted
        posted: true
        policy: pol_57q1s3amg8a708meyd8hw7f87e
        obligations_pending: []
        justification_hash: 09eef89be5c5610690ed95f066ec2e01072d4a934cd25aad4cbb3411102737e7
        provenance:
          Recorded:
            policy: pol_57q1s3amg8a708meyd8hw7f87e
            semantics: 7
            verdict: Permitted
            applied:
            - rule_0ffqx02j1abw4tvmm8cjvqphwg
            defeated: []
            winning: rule_0ffqx02j1abw4tvmm8cjvqphwg
            obligations:
              created: []
              discharged: []
              violated: []
            delegation:
            - deleg_4fcqd1n994br3brg9y1951zfe8
            evidence:
            - 09eef89be5c5610690ed95f066ec2e01072d4a934cd25aad4cbb3411102737e7
    rail: settle
- inject:
    at: 1h
    advance: 2d23h
    outcome:
      applied: {}
- submit:
    at: 3d
    intent:
      agent: agent://example.com/agent/clerk_01h455vb4pex5vsknk084sn02q
      attestation: >-
        v4.public.eyJhZ2VudF9rZXkiOiJqVE1pZkZtR0hTTEFxMHM5R0lGb2l0SDJaV3BCMDkvS1hsSi9HM2pUNFVNPSIsImFnZW50X3VyaSI6ImFnZW50Oi8vZXhhbXBsZS5jb20vYWdlbnQvY2xlcmtfMDFoNDU1dmI0cGV4NXZza25rMDg0c24wMnEiLCJjYXBhYmlsaXRpZXMiOlsiYWdlbnQiXSwiZXhwIjoiMjEwMC0wMS0wNVQwMDowMDowMC4wMDBaIiwiaWF0IjoiMjEwMC0wMS0wNFQwMDowMDowMC4wMDBaIiwiaXNzIjoiZXhhbXBsZS5jb20iLCJqdGkiOiIwM3FjeTNkdjAwZnNqYTVzODlja2Zha3ZiNiJ9ecVC5cSz1RjG2_CGApdLfvXvNX7Ol704TZKrlHGzlTqeLV8R7_A5ybcf7Be1ZV71VQy_cvFZ380GuNKS1zTfDw
      transaction: txn_03qcy3dv00e008000000000002
      entries:
      - account: acc_118q65km28a9zrw0dbexkpd43v
        side: Debit
        amount:
          minor: 4000
          currency: USD
      - account: acc_0jffxpndb9a2garx5fj166tc4c
        side: Credit
        amount:
          minor: 4000
          currency: USD
      action:
        action: purchase
        bindings:
          amount:
            Amount:
              minor: 4000
              currency: USD
          payee:
            Text: acme
      evidence: []
      justification: invoice 1043
      policy: pol_400k9r0n0xa2ft4dk2rp7v42mg
      minted_at_ms: 4102704000000
    expect:
      refused:
        status: 409
        body:
          active: pol_57q1s3amg8a708meyd8hw7f87e
          error: stale_policy
          message: "stale policy pin: pinned 'pol_400k9r0n0xa2ft4dk2rp7v42mg' but 'pol_57q1s3amg8a708meyd8hw7f87e' is in force"
          pinned: pol_400k9r0n0xa2ft4dk2rp7v42mg
```

Four live policy changes, as a run records them: one put in force, one to
the policy already in force, one the engine refused because it does not
compile, and one it refused at registration, which names the policy its
source compiles to.

```yaml
script:
- inject:
    at: 2h
    policy:
      source: "policy {\n  role clerk\n}\n"
    outcome:
      applied:
        policy: pol_57q1s3amg8a708meyd8hw7f87e
- inject:
    at: 3h
    policy:
      source: "policy {\n  role clerk\n}\n"
    outcome:
      unchanged:
        policy: pol_57q1s3amg8a708meyd8hw7f87e
- inject:
    at: 4h
    policy:
      source: "policy {"
    outcome:
      refused:
        status: 422
        error: invalid_policy
        message: the policy does not compile
        diagnostics: 1
- inject:
    at: 5h
    policy:
      source: |
        policy {
          role buyer
          action purchase(amount: amount)
          party buyer_party principal roles(buyer)
          rule cap {
            permitted any_in_role(buyer) do purchase
            when { ( param(amount) <= amount(50000, EUR) ) }
            priority 1
          }
        }
    outcome:
      refused:
        policy: pol_1y0c6zc47bb05a2ffwwnycv8z1
        status: 422
        error: substrate_rejected
        message: "policy pol_1y0c6zc47bb05a2ffwwnycv8z1 cannot be registered: it names currency 'EUR' (line 7, column 45), which is not declared on this deployment, so no amount it compares could be read back; use a declared currency code, or have an operator declare this one with 'axorum currency declare --code EUR --exponent <digits>', then try again"
        diagnostics: 0
```

## What the world check refuses

Reading a world checks that it holds together, and reports every problem it
finds, grouped by kind. A problem names an event or a script step by its place
in the list, counting from one, so `event 3` is the third entry of `events`:

- a blank policy `source`, the world's or an event's;
- a currency declared twice;
- an account, mandate, deferral or usage balance in a currency `currencies`
  does not declare;
- an id opened twice among the accounts, the mandates, the deferrals or the
  usage balances;
- a mandate whose `parent` is not opened earlier in `mandates`, or a party
  whose `mandate` is not opened in `mandates`;
- a world with no parties, an `agent` that is not an agent URI, or an agent
  bound twice;
- a capability that is not a path below the agent, or an empty
  `capabilities` list;
- a master-data kind imported twice in `master_data`;
- a master-data entry that takes more than 4,096 bytes as a snapshot writes
  it, in `master_data`, an event or a script step;
- an event before the event above it, or a script step before the step above
  it;
- an event or a script step whose `at` is past the clock's last second,
  `365250d`, or a script step whose `inject` advances the clock from its `at`
  past it;
- a script step that records a rail answer for an intent that names no rail,
  or that the gateway refused.

## What loading refuses

`serve` and `run` then load the world into the engine, which refuses, and the
command exits 2:

- a policy that does not compile, the world's or a `policy` event's, and a
  `policy` event's `file` that cannot be read;
- a mandate ceiling below 0, or a child mandate in another currency than its
  parent, above its parent's ceiling, or deeper than 8;
- a fiscal calendar whose periods are out of order or overlap, one with
  `from` after `to`, or one that lists a period id twice;
- a counterparty alias that is a canonical id in the list, or that two
  counterparties both list.

`axorum-sandbox check policy.axp --world world.yaml` judges the policy it is
given against the world before either runs, whatever the world's `policy`
names: a currency the world does not declare, a mandate or party the world
does not open under the id its name derives, roles or capabilities that do
not match the policy's, and a `specific(...)` naming a party the policy does
not declare and no agent is bound to (codes DSL3001 to DSL3009).

## Defaults

| When this is absent | The world has |
|---|---|
| `description` | no description |
| `seed` | the run's `--seed`, else 0 |
| `accounts`, `mandates`, `deferrals`, `usages` | none opened |
| `master_data` | no counterparty list, chart or calendar |
| `rails` | every rail settling |
| `events` | no timeline |
| `script` | a world, not a scenario |
| an account's `label` and `owner` | its id in prose, and no reader |
| a mandate's `parent` | a root mandate |
| a mandate's `label` | the policy's name for it in reports, else its id |
| a party's `roles` | no roles |
| a party's `mandate` | no mandate charged |
| a party's `capabilities` | tokens that cover every action and rail |
| a counterparty's `erp_ref`, `aliases` and `limit` | no ERP key, no other spellings, no limit |
| a fiscal period's `open` | `true` |
| a rail change's `times` | the answer stands from then on |
| a submit step's `rail` | no rail was called |

## A whole world

Two buyers draw down a team budget, each through a mandate of its own, and pay
only approved vendors. The x402 rail times out twice on day 3, and Globex
loses its approval on day 10.

```yaml
version: axorum.sandbox-world.v1
world: team-buyers
description: Two buyers under one team budget, paying approved vendors.
seed: 1
policy:
  source: |
    policy {
      role buyer
      action purchase(amount: amount, payee: text)
      party buyer_bot agent roles(buyer)
      party ads_bot agent roles(buyer)
      party controller principal
      delegation buyer_grant {
        principal controller
        agent buyer_bot
        scope { actions(purchase) roles(buyer) }
      }
      delegation ads_grant {
        principal controller
        agent ads_bot
        scope { actions(purchase) roles(buyer) }
      }
      rule permit_approved_vendor {
        permitted any_in_role(buyer) do purchase
        when { (param(payee) in approved counterparties) }
        priority 1
      }
    }
currencies:
- currency: USD
  exponent: 2
accounts:
- account: acc_0jffxpndb9a2garx5fj166tc4c
  currency: USD
  label: Agent spend (USD)
- account: acc_118q65km28a9zrw0dbexkpd43v
  currency: USD
  label: Agent payables (USD)
mandates:
- mandate: mand_4rcxqt8kd3bc99kr06a57h4kxx
  currency: USD
  ceiling: 500000
  label: team_budget
- mandate: mand_0nxsjgtgxjb91vfgm0benm4k8t
  currency: USD
  ceiling: 300000
  parent: mand_4rcxqt8kd3bc99kr06a57h4kxx
  label: buyer_mandate
- mandate: mand_60mys3wfeebmptzjresxs7z855
  currency: USD
  ceiling: 300000
  parent: mand_4rcxqt8kd3bc99kr06a57h4kxx
  label: ads_mandate
parties:
- agent: agent://example.com/agent/buyer_01h455vb4pex5vsknk084sn02q
  party: party_6pfhxzyav7atbvnxa2wh4wdsex
  roles: [buyer]
  mandate: mand_0nxsjgtgxjb91vfgm0benm4k8t
  capabilities: [purchase, rail/x402]
- agent: agent://example.com/agent/ads_01h455vb4pex5vsknk084sn02q
  party: party_7cky9f0ahdafma6d3hxkcb8s0g
  roles: [buyer]
  mandate: mand_60mys3wfeebmptzjresxs7z855
  capabilities: [purchase]
master_data:
- Counterparties:
    source_version: vendors-v1
    entries:
    - - acme
      - display_name: Acme Supplies
        approved: true
        aliases: [acme inc]
    - - globex
      - display_name: Globex
        approved: true
        limit:
          minor: 200000
          currency: USD
    - - shady-llc
      - display_name: Shady LLC
        approved: false
- GlAccounts:
    source_version: "2100.01"
    entries:
    - - acc_0jffxpndb9a2garx5fj166tc4c
      - code: "6000"
        name: Agent spend
    - - acc_118q65km28a9zrw0dbexkpd43v
      - code: "2000"
        name: Agent payables
- FiscalPeriods:
    source_version: fy2100
    periods:
    - id: 2100-01
      label: January 2100
      from: 0
      to: 2678399
rails:
  x402: settle
events:
- at: 3d
  rail:
    rail: x402
    answer: timeout
    times: 2
- at: 10d
  master_data:
    Counterparties:
      source_version: vendors-v2
      entries:
      - - acme
        - display_name: Acme Supplies
          approved: true
          aliases: [acme inc]
      - - globex
        - display_name: Globex
          approved: false
      - - shady-llc
        - display_name: Shady LLC
          approved: false
```

## Protocol-aware worlds and recordings, version 2

Protocol mock configuration and exchanges require `axorum.sandbox-world.v2`.
Ledger-only worlds and recordings retain version 1 and their original bytes.
The new engine reads both versions. A protocol simulation exercises a local
merchant, facilitator or credential-provider endpoint without real money or
external networking. The legacy `rails` map still describes post-ledger rail
answers; protocol endpoints describe the actual HTTP interactions an agent sees.

The `events[].protocol` payload uses the engine-owned catalogue in
`protocol-catalogue.json`. It enumerates supported protocols, stages, presets,
parameter formats, bounded transport faults, quick sequences and assertions.
Its strict JSON contract, and the `script[].protocol` exchange contract, are in
the version 2 snapshot schema (`protocol_change` and `protocol_step`),
shipped with the npm and Python sandbox packages. Python exposes it as
`snapshot_schema("v2")`. These two engine payloads are governed by that schema and
the catalogue, rather than a duplicate list of fields in this reference.

```yaml event
protocol:
  protocol: x402
  stage: resource
  behaviors:
  - preset: payment_required
  - preset: paid
  repeat: last
  assertions:
    max_requests: 2
    max_effects: 1
    final_status: 200
    sequences_consumed: true
    receipt_present: true
```

A portable exchange records safe request projections and hashes, its planned
response, its typed transport effect, its synthetic side-effect identity and
whether a retry reused an existing effect. Tokens, signatures, delegated
mandates and original request bodies are never recorded. Replays compare the
entire execution without sleeping or making network requests. Regression
assertions are evaluated explicitly when a scenario runs in CI; resuming an
unfinished recording only verifies its recorded behavior.

```yaml
version: axorum.sandbox-world.v2
world: local-protocol
policy:
  source: |
    policy {
      role clerk
      action purchase(amount: amount, payee: text)
      party clerk_bot agent roles(clerk)
      party controller principal
      delegation clerk_grant {
        principal controller
        agent clerk_bot
        scope { actions(purchase) roles(clerk) }
      }
      rule permit_purchase { permitted any_in_role(clerk) do purchase priority 1 }
    }
currencies: [{currency: USD, exponent: 2}]
parties:
- agent: agent://example.com/agent/clerk_01h455vb4pex5vsknk084sn02q
  party: party_28zwgzaew1a2r92s1y9swtj3nj
  roles: [clerk]
events:
- at: 0s
  protocol: {protocol: x402, stage: resource, behaviors: [{preset: malformed_response}]}
script:
- protocol:
    at: 0s
    execution:
      request:
        protocol: x402
        stage: resource
        method: GET
        path: /_sandbox/rails/x402/resource
        body_hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        idempotency_hash: null
        fields: {payment_present: false, requirements_match: false}
      response: {status: 200, headers: {content-type: application/json, Axorum-Sandbox: simulation}, body: '{invalid-sandbox-json'}
      transport: {kind: immediate}
      effect: null
      deduplicated: false
```
