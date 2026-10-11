# The world a policy is tried in

A policy names roles, parties and mandates; a world says who the agents are,
which budgets exist, which vendors are known and which currencies are in use.
`try_cases.py` runs the cases in a fresh sandbox built from the world, and the
user's own sandbox serves one too. Keep `world.yaml` beside `policy.axp` and
`cases.json`.

This reference covers only what ties a world to a policy: the policy file, the
agents' bindings and who an agent is, the budgets a rule reads, what the cases
need, and the check that holds them together. Building or changing anything else in a world
(accounts, budgets, the vendor list, the chart, events) is the `axorum-world`
skill's work. The format itself, whole and current, is printed by:

```bash
axorum-sandbox grammar world
```

## Start from something that runs

Never write a world from nothing. In order of preference:

1. **The user already has one.** A world file of their own: copy it and change
   only what the brief needs. The world attached to their sandbox in the
   console: `axorum-sandbox pull --output world.yaml` writes it with the policy
   file it names beside it, and both are worked on in place under the names
   they came with (`references/testing.md`, "The world came from the
   console").
2. **An example in this skill**: `examples/ap-vendor-payments/` (one agent,
   a vendor list, per-vendor caps) or `examples/team-budget/` (two agents,
   a team budget with a mandate per agent). Copy the directory.
3. **Neither fits** (the brief needs agents, budgets or a vendor list neither
   has): build it with the `axorum-world` skill, from the brief's agents,
   budgets and vendors, then come back to bind it here.

## The policy file

```yaml
policy:
  file: policy.axp                   # relative to the world file
```

`check.py --world`, `try_cases.py` and `axorum-sandbox serve` read the policy
from there. `try_cases.py --policy draft.axp` tries another draft in its
place.

## The agents

```yaml
parties:
- agent: agent://example.com/agent/ap_01h455vb4pex5vsknk084sn02q
  party: party_6ps6y8mc3tb628qrr6xpqkr0yr     # the id `ap_bot` derives
  roles: [ap_clerk]
  capabilities: [purchase, file_receipt]
```

- `agent`: the agent's `agent://` URI, which the cases' `agents` map names.
  Its label, before the last `_`, is lowercase letters and `_`, starting and
  ending with a letter: a second agent is `aptwo_01h455...` or
  `travel_01h455...`, never `ap2_...`. The whole form is the `axorum-world`
  skill's (`references/grammar.md` there, "Parties").
- `party`: the id the policy party's name derives. When it is not, the agent's
  intents are judged as a stranger's and refused (`references/semantics.md`
  section 8).
- `roles`: exactly the roles the policy gives that party (`party ads_bot agent
  roles(marketing)` binds with `roles: [marketing]`). A missing role means no
  rule written for it reaches the agent; an added one brings rules written for
  it that the policy's checks do not see (`DSL3007`).
- `mandate`: optional, the `mand_` id of the budget every allowed intent of
  this agent charges. `examples/team-budget/` binds `ads_bot` to `ads_mandate`;
  its records agent names none, so the paperwork it files charges nothing.
  Paperwork an agent bound to a budget files is charged to that budget:
  `references/semantics.md` section 11.
- `capabilities`: every action the agent proposes, paperwork actions included.
  A missing one is a 403 `attestation` rejection before the policy is
  consulted; `check.py --world` reports a delegated action the list leaves
  out (`DSL3008`). Leaving the field out gives the agent a token for every
  action, so the gateway turns nothing away and every intent reaches the
  policy.

**One party per agent**, even for agents that do the same job (three AP
agents paying the same vendors), as the `axorum-world` skill binds them: a
party for each in the policy, with the same role. Two agents bound to one
party share every `per party` total, and the reports name the party by one
agent URI whichever agent acted, so the user cannot tell which agent paid.
Write the rules the agents share for the role (`any_in_role`), so no rule is
written twice, and any total meant to count them together `per role <role>`,
`global`, `per counterparty(...)` or against a budget they share. A `per
counterparty(...)` total has a cost: a payee missing from the vendor list is
then turned away before judgment, with nothing recorded, so it is drafted only
when the user asks for a per-vendor limit; by default there is none
(`references/semantics.md` section 5, `references/conversation.md`).

A principal is never bound in the world; only agents are.

## Who an agent is

An agent is its `agent://` URI. The world binds the URI to a party, and the
party is what the policy knows: its roles, the delegations to it and the rules
that name it. A URI the world does not bind is no one: its intents are
rejected `401 unknown_agent`, and the sandbox mints it no token.

Every intent carries a token for the agent that sends it. In a sandbox,
`axorum-sandbox token '<agent-uri>'` mints one from the world, issued at the
sandbox clock's now; `try_cases.py` mints a fresh one for every case. A token
is a credential: never paste one into a reply. Before any rule is read, the
intent is rejected `403 attestation` when its token:

- was not signed by the issuer the world trusts for that agent (a token from
  another world, or the same world under another `seed`, is not);
- was minted for another agent;
- has expired: a sandbox token lasts one day of the sandbox's clock, so an
  agent of the user's own sandbox mints a new one once the clock has moved a
  day past it;
- does not carry the action among its capabilities (the binding's
  `capabilities` above, `DSL3008`).

Neither rejection reaches the policy or is recorded, so no rule is named and
no report lists it. An intent that passes is judged as the bound party's.

**Separate agents keep separate records.** Each party has its own `per party`
totals, its own duties and its own lines in the reports, which name it by its
agent URI. Two URIs bound to one party share all of them (above).

## The budgets a rule reads

```yaml
mandates:
- mandate: mand_4rcxqt8kd3bc99kr06a57h4kxx   # the id the policy's name derives
  currency: USD
  ceiling: 1000000                            # minor units: $10,000.00
  label: team_budget
- mandate: mand_60mys3wfeebmptzjresxs7z855
  currency: USD
  ceiling: 700000
  parent: mand_4rcxqt8kd3bc99kr06a57h4kxx     # carved from team_budget
  label: ads_mandate
```

A mandate the policy reads by name (`projected(team_budget)`) must be opened
under the id that name derives; `check.py --world` prints it. A mandate no
rule reads (an agent's own budget, charged because the agent is bound to it)
may take any `mand_` id, and reports name it by its `label`. The examples
open every budget under the id its name derives, so a rule added later can
read it by that name.

## What the cases need from a world

- **Accounts.** `try_cases.py` posts a payment as a debit to the default
  chart's `spend` account and a credit to its `payables` account, in the
  payment's currency; paperwork posts the legs its case gives. A receipt that
  moves the payment into receipted expenses needs that account as well. The
  examples declare all three for USD; for another currency, print the first
  two ids with the SDK:

  ```bash
  python -c 'from axorum import default_chart_account as a; print(a("spend", "EUR"), a("payable", "EUR"))'
  ```

- **Currencies.** Every currency the policy uses is declared in `currencies`
  (`DSL3001`).
- **The vendor list.** A policy that reads `approved counterparties`, `per
  counterparty(...)` or `counterparty limit(...)` needs the vendors in the
  world's `master_data`. How a payee missing from it is judged (refused, or
  turned away before judgment): `references/semantics.md` section 5.

## Bind the world to the policy

Party and mandate ids derive from the names in the policy, so a world is
bound to one set of names. Check both together after every edit to either:

```bash
python <skill-dir>/scripts/check.py policy.axp --world world.yaml
```

It reports:

- a mandate the policy reads that the world does not open under its id
  (`DSL3003`: it would read 0, so a `projected(m) > cap` rule never fires);
- a cap on a mandate in another currency than the world opens it in
  (`DSL3004`);
- a policy agent no world agent is bound to under its id (`DSL3005`);
- a world agent bound to a party the policy does not declare (`DSL3006`);
- a world agent bound with other roles than exactly the ones the policy gives
  its party: one missing, one added, or one the policy does not declare
  (`DSL3007`);
- a world agent whose `capabilities` leave out an action the policy delegates
  to it (`DSL3008`);
- a currency the policy uses that the world does not declare (`DSL3001`).

After the rendering it lists the id each name derives, to paste into the
world:

```text
  team_budget              mandate: mand_4rcxqt8kd3bc99kr06a57h4kxx

  ads_bot                  agent     party: party_7cky9f0ahdafma6d3hxkcb8s0g
  marketing_lead           principal party: party_21hhfz7c62a76s9qnse4tvfm6j
```

Renaming a party or a mandate in the policy changes its id: re-run the check
and update the world in the same step.

## The user's own sandbox

The user runs their sandbox themselves: `axorum-sandbox serve world.yaml`
listens on `http://127.0.0.1:7340` (`--port` to change it). Never start, stop
or restart it. `push.py` changes its policy in place (`references/testing.md`,
"Putting it in force"), and `replay.py --url` saves its run so far and replays
it under a draft. `axorum-sandbox inject <event.yaml>` applies one world event
(`advance: 1d`, a master-data import) to it, which changes the user's run:
inject only when the user asks for that event.
