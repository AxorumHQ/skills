# What the engine does with a policy

`references/grammar.md` says what parses. This file says what a construct does
when an intent is judged, so the verdict can be predicted before the sandbox
returns it. When it does not answer a question, try the question in a sandbox:
what the sandbox answers is what the engine answers.

## Contents

1. How a verdict is reached
2. Priorities and exceptions
3. Duties: triggers, captures, deadlines, fulfilling, reparations
4. Conditions: what each term reads
5. The counterparty registry and the other reference sets
6. Aggregates: scope, window, projected reads
7. Mandates: budgets the world holds
8. Parties, delegations, and how the world binds them
9. Time
10. What cannot be said
11. Paperwork under a mandate

## 1. How a verdict is reached

An agent proposes one action with every parameter bound (`purchase` with
`amount` and `payee`) plus the journal legs that would move money. The engine:

1. **Finds the applicable rules.** A rule applies when its actor matches the
   agent, its action and any bound parameters match, its `during` window holds,
   its `when` guard is true, and a delegation to that agent covers the action
   under the agent's role at this moment.
2. **Decides by priority.** The highest-priority applicable `permitted` or
   `forbidden` rule decides. With none, the verdict is `denied_by_default`.
   A permit that would have applied but no delegation covers is reported as
   `not_delegated`, naming the permit.
3. **Checks the budget.** Only when the policy allows a charge does the engine
   check the mandates the charge rolls up to. A charge past a ceiling is a
   recorded `mandate_exceeded` refusal. A rule refusal therefore always wins
   over a budget refusal: the case shows the rule.
4. **Opens and fulfills duties.** Every `obligated` rule whose trigger matches
   the allowed action opens a duty of its own. The intent meets exactly the
   duties it names in `fulfills`, and no other (section 3).
5. **Records it all**: verdict, deciding rule, its English, duties opened and
   met, the delegation, the master-data versions read. A refusal posts no money
   and is still written down.

Consequences for the draft:

- **Every action an agent performs needs a permit.** Deny-by-default refuses
  the rest. That includes the paperwork actions that meet duties: a duty to
  file a receipt needs a permit for `file_receipt`, or the agent owes what it
  is forbidden to do (`DSL2003` flags it). A follow-up duty does not stand in
  for that permit: a duty only a breach opens never lets its action commit.
- **A refusal is evidence.** Write the forbid so its English is the sentence an
  auditor wants to read.
- **The delegation is part of the policy's meaning.** A permit without a
  covering delegation permits nothing.

## 2. Priorities and exceptions

Every rule carries `priority <n>`; higher wins. The engine lowers the policy to
one ordered list: a rule at authored priority `p` sits at `2p`, and each of its
`unless` defeaters at `2p + 1`, so a defeater outranks its own rule and nothing
else.

Pick priorities as bands and state them in the header comment:

| Band | Holds |
|---|---|
| 1 | Permits: what the agents may do at all |
| 5 | Duties, each `obligated` rule apart from the permits |
| 10 | Refusals: every limit, cap and blocklist |

Opposite verdicts on the same action and actors at one priority leave the
tie-break, not the author, to decide. `DSL2008` flags such a pair only when
both rules name the actor in the same words (`any_in_role(buyer)` twice, not
`any_in_role(buyer)` beside `specific(buyer_bot)`), at least one of them has
no `when` and no `unless`, their bound parameters can agree, and they are not
both `during` rules. Two guarded rules at one priority are never flagged,
though one intent can meet both guards: give opposite rules on one action
distinct priorities whatever the check says. A duty opened by a `trigger`
never competes for the verdict on its action, so its priority is never weighed
against the permits' and never trips this, nor does a duty only a breach
opens (an `on_violation` follow-up); any other `obligated` rule does
compete, and at the priority of the permit for its action it trips
`DSL2008`. Duties get a band of their own so the header reads them apart from
the permits and refusals.

**Two refusals at one priority.** When two refusals at the same priority both
apply, the intent is refused either way, but the record names only one: the
one whose rule id sorts first. The id derives from the rule's name, so the
choice is fixed but neither alphabetical nor the authored order (a $6,000
payment to Shady LLC in the AP example is recorded under
`vendor_must_be_approved`, not `single_payment_cap`). No lint reports it:
`DSL2008` flags only opposite verdicts at one priority. When it matters which
rule the record names, give the rules distinct priorities (ask the user which
reason the record should give, put that refusal one step higher, 11, and state
it in the header's bands), and let the cases try one refusal at a time
(`references/testing.md`).

Two ways to write an exception:

| Shape | Use when | The record reads |
|---|---|---|
| A higher-priority `forbidden` rule | The exception is itself a control ("never pay an unapproved vendor") | refused by `vendor_must_be_approved` |
| `unless <name> { ... }` on a forbid | One limit has a named carve-out ("except rent") | the forbid does not apply because `rent` held, and the next rule decides |

An `unless` on a permit suppresses that permit only; the verdict falls to the
next applicable rule or to deny-by-default. An `unless` that holds on an
`obligated` rule keeps the duty from opening; on a duty with a `trigger` it
reads the trigger's parameters, as the duty's `when` does. Modalities are
primitive: there is no negated action and no "obligated not to".

## 3. Duties

**Trigger versus owed action.** `obligated specific(bot) do file_receipt
trigger purchase` means: when a `purchase` by `bot` is allowed and the guard
holds (reading the purchase's parameters), `bot` owes a `file_receipt`. The duty
does not take part in the purchase's verdict. A duty with no trigger that is
not a reparation is self-triggered: a committed proposal of the owed action
opens it. When the proposer is its performer, every `capture` copies a
parameter into itself (`amount: trigger_param(amount)`, or a capture of `m`
into `n` with a `when` conjunct `( param(n) == param(m) )`), and its deadline
is not `by(t)`, that same proposal meets it. Such a duty is never missed, so an
`on_violation` on it never opens (`DSL2005`). A duty whose miss
should open a follow-up needs a `trigger`, the action that opens it, and a
`within` or `by` deadline.

**Captures tie the duty to its occasion.** `capture { amount:
trigger_param(amount), purchase: trigger_transaction }` fixes the owed action's
parameters from the trigger: the receipt must carry the purchase's amount and
name the purchase's transaction. Declare a `transaction` parameter on the owed
action to receive `trigger_transaction`. A receipt meets a duty only when
it carries every value the duty captured, so captures decide how many duties one
receipt can meet. Without captures every open duty of the rule owes the same
bare `file_receipt`, and one receipt may name several of them in `fulfills`
and meet them all. `purchase: trigger_transaction` makes each duty owe its own
purchase's transaction, so a receipt can meet only that purchase's duty, and
naming two is rejected (`invalid_fulfillment`). A capture of a value two
purchases can share, an amount alone, lets one receipt meet both whenever
those values agree (two $600.00 purchases). Recommend capturing the
transaction: each receipt then answers for one payment.

**Who performs it.** `performed_by debtor` (the default) has the obligated party
perform it; `performed_by trigger_party(p)` hands it to the party a `party`
parameter of the trigger named (the seller must ship); `performed_by
specific(p)` names one party (a records agent filing receipts for a spending
agent, section 11). The performer must make the request itself, under
its own delegation and permit for the owed action. The duty stays the debtor's:
a miss is recorded against the debtor, whoever was to perform it.

**Meeting a duty takes `fulfills`.** Nothing is met implicitly: an intent of
the owed action that names no duty meets none, and the duty is breached at its
deadline. The intent lists in `fulfills` the ids of the duties it meets, at
most 64, each once. Every duty listed must be open, be this agent's to
perform, owe exactly this action with its captured values, and be at or before
its deadline. When any one fails, the whole intent is rejected with
`invalid_fulfillment`: nothing is recorded and none of the duties it lists is
met. Policy authorization comes first: the fulfilling action needs its own
permit, and `fulfills` is read only on an intent the policy allows. A refused
one is recorded as that refusal, whatever duties it names, and meets nothing.
Only the list's shape is checked first, on every intent: one that repeats an
id or names more than 64 is rejected `invalid_envelope` before judgment.
Paperwork is an intent like any other: the performing agent submits it, with
legs, and nothing is filed for it. When that agent is bound to a mandate, read section 11 before drafting the duty.

**Deadlines.** `within(n)` is breached when the clock passes the trigger time
plus `n` seconds without the duty met. `by(t)` is breached after tick `t`.
`during(a, b)` bounds when the duty can be triggered, not when it lapses: a
duty with only a `during` window is never breached (`DSL2005`), and a rule
carries one temporal, so a duty that must lapse takes `within` or `by` in its
place. A duty can still be met at its deadline tick; the breach is the first
tick after. A breach needs no one to poll: the clock sweep marks it.

**Lifecycle.** A duty opens Active and ends Discharged (met through
`fulfills`) or Violated (its deadline passed first). A duty whose deadline has
already passed when it is triggered (a `by(t)` the clock is past) is born
Violated and opens its reparation at once. Nothing waives, suspends or cancels
an open duty: to keep one from opening, narrow its `when` or give it an
`unless`. Nothing keeps a breach from opening its reparation.

**Reparations.** `on_violation <rule>` names another `obligated` rule. When the
duty is breached, that rule opens a new duty for the same debtor at the breach
time, with its own deadline. It keeps the original trigger: its captures
resolve against the purchase that opened the first duty. A rule reached only
through `on_violation` and with no trigger opens only as a reparation, and on
every breach of the rule that names it: the breach reads none of its `when`,
`unless` or `during`, so the checker refuses each of them there (`DSL0032`).
Its `within(n)` runs from the breach, and a `by(t)` the breach is already past
opens it Violated. A `permitted` or `forbidden` rule an `on_violation` names,
and an `obligated` rule with its own `trigger`, keep those clauses: they go on
deciding that rule's verdicts or when its trigger opens it, and a breach opens
the duty whatever they say. Chains
are acyclic and at most 8 deep. `on_violation` is legal only on an obligated
rule, and the rule it names should be an `obligated` rule too. The checker
accepts a rule of any modality there: a breach then opens a duty to perform
a `permitted` or `forbidden` rule's action, while that rule goes on allowing
or refusing as before. An intent the rule refuses meets nothing, so where it
refuses the duty's own action no agent can meet the duty, and it stays open
until its deadline, if it has one, breaches it. Read each `on_violation`
target in the review.

**One duty per triggering intent.** Each allowed trigger opens its own duty,
even two purchases in the same second; nothing merges them. Its id derives
from the policy, the rule, the debtor, the triggering transaction and the tick
it opened. Two purchases over the line before any receipt leave two open
duties. One receipt meets both only by listing both ids and carrying what
each captured, which a `trigger_transaction` capture rules out (above); a duty
no intent lists is breached at its deadline.

**What the answer says.** An allowed intent's verdict is `ObligatedPending`
when a duty it opened is still open, else `ObligatedFulfilled` when it met
one, else `Permitted`: a receipt that names no duty is `Permitted` and meets
nothing. The answer's `obligations_pending` lists every duty the agent owes or
performs that is open after it, not only the ones it opened. The transaction's
`explain` report lists what this intent opened (`duties_created`) and met
(`duties_discharged`).

**A policy change leaves open duties open.** A duty stays open under the
policy that opened it, with its deadline and its reparation, after another
policy is put in force, even one without the rule. The paperwork that meets it
is judged by the policy in force when it is filed: without a permit there, it
is refused and the duty is breached at its deadline.

## 4. Conditions

A guard is flat CNF: `{ ( a or b ) and ( c ) }`, at most 32 clauses of 16
literals, true when every clause has a true literal. Comparisons are typed;
there is no coercion and no floating point.

| Term | Reads | Type |
|---|---|---|
| `param(k)` | the intent's parameter `k` (the trigger's, on a triggered duty) | as declared |
| `actor` | the acting party | party |
| `now` | the current tick | tick |
| `posted debit USD` | the sum of the intent's debit legs in USD; `credit` for the other side; `in acc_...` narrows to one account | amount |
| `spent(m)` `ceiling(m)` `remaining(m)` `projected(m)` | the mandate's spending (its children's included), ceiling, headroom, and spending including this intent's charge | amount |
| `register(r)` | the aggregate's value so far, in this intent's cell | int for `counts`, else the summed type |
| `projected(register(r))` | the same, including this intent | same |
| `counterparty limit(k)` | the registry's limit for the payee `param(k)` resolves to; right-hand side only | amount |
| `resolved counterparty(k)` | the registry's canonical id for `param(k)`; with `==`, `!=` or `in` only | text |

`in` against a plain value is equality; against a reference set it is
membership. `not` negates one literal.

Prefer `posted debit USD` to an `amount` parameter for a money limit: the
parameter is the agent's claim, the legs are what moves.

## 5. The counterparty registry and the other reference sets

Three master-data sets live outside the policy, imported whole with a source
version that every verdict records. In a sandbox the world's `master_data`
imports them: the `axorum-world` skill builds it (the format:
`axorum-sandbox grammar world`, "Master data").

| Set | True when |
|---|---|
| `param(k) in approved counterparties` | the payee names a record with `approved: true` (for an alias, see below) |
| `param(k) in chart of accounts` | the account is listed |
| `param(t) in open fiscal periods` | an open period contains the tick |

All three fail closed: an absent key, an unapproved record, a closed period and
a set never imported are all `false`. `not param(payee) in approved
counterparties` therefore refuses every payment until the list is imported.
Tell the user, in one sentence, that the rule reads a list kept outside the
policy and who keeps it.

**Aliases and the approved check.** This paragraph is the skill's one
statement of how a record's `aliases` are judged; the other references point
here. Aliases resolve for every counterparty read: `per counterparty(k)`
totals, `resolved counterparty(k)`, `counterparty limit(k)`, and `in approved
counterparties`. An alias of an approved record is approved; an alias of an
unapproved one is refused and named by the record's display name. A spelling
that is neither an id nor an alias is not approved.

**Unknown payees: refusal or rejection.** `param(k) in approved
counterparties` is `false` for a payee the registry has never seen, so the
forbid fires and the refusal is recorded. A `per counterparty(k)` aggregate,
`resolved counterparty(k)` or `counterparty limit(k)` cannot place an unknown
payee at all: the intent is rejected before judgment, `422 substrate_rejected`
with cause `unknown_counterparty` ("import the counterparty, or name a
registered one"), and nothing is recorded, even when a higher forbid would have
refused it. That is the engine's design: a total is never kept for a vendor
it cannot identify. A policy with a per-vendor cap therefore rejects unknown vendors outright.
Present this to the user as a choice: keep the per-vendor cap and have every
vendor imported (with `approved: false` for those to refuse on the record), or
drop the per-vendor cap and keep every unknown vendor's refusal on the record,
the default (`references/conversation.md`).

`counterparty limit(k)` reads the record's optional `limit`. A registered
record with no limit makes the comparison false: no limit is not a zero cap.

## 6. Aggregates

An aggregate is declared up front and kept by the ledger as each intent
commits; a rule reads it in constant time and never scans history.
`counts <action>` adds one per allowed intent; `sums <action>(<param>)` adds
the parameter; `sums posted debit USD <action>` adds the posted legs.

**Scope** picks the cell an intent adds to and reads: `per party` (the actor),
`per role r` (only actors holding `r` add), `per counterparty(k)` (the resolved
payee; `within each mandate root` splits it per top-level budget), `per rail r`
(only intents that declared rail `r` add; a direct submission declares none),
`global`.

**Window**: `rolling n` is the last `n` seconds; `calendar n` is fixed
`n`-second periods from tick 0 that reset at each boundary (not the fiscal
calendar); `unbounded` is everything since the aggregate was declared.

**Projected reads are the preventive cap.** `projected(register(r)) > cap`
folds the intent in, so the intent that would cross the cap is the one
refused, and one landing exactly on the cap is allowed. `register(r) > cap`
reads only what came before, so it refuses the intent after the one that
crossed. Use `projected` unless the brief says otherwise.

**Money aggregates are single-currency.** A `sums` over an amount parameter
ends `in USD`, and an intent on its action in another currency never reaches
judgment: it is rejected (`substrate_rejected`, cause `currency_mismatch`), so
nothing is recorded and no rule names it. `DSL3002` warns when that closes an action to a currency the
world declares. A `sums posted` reads only the matching legs and turns nothing
away for currency. A count carries no currency.

**Changing a declaration resets it.** A byte-identical declaration keeps its
total across a policy change; a changed or new one starts at zero from the
change, and a dropped one is gone. Changing a window or a currency resets the
figure. Mention it before a live push.

## 7. Mandates

A mandate is a budget the world (or, in production, the operator) opens, with
a currency, a ceiling and optionally a parent it is carved from. Each agent in
the world names the mandate its intents charge. The ledger enforces every
ceiling up the parent chain on every allowed charge, with no rule in the
policy: two agents under one team budget can never spend more than it together.
A charge past a ceiling is a recorded `mandate_exceeded` refusal naming the
mandate.

**What a charge is.** For each account, debits minus credits in a currency;
the charge is the sum of the positive parts. Any move between two distinct
accounts is charged, a reclass between the agent's own accounts included, and
it is charged to every mandate up the parent chain. Only a debit and a credit
of the same amount on the same account move nothing and charge nothing.
Paperwork that posts legs is charged like any other intent: section 11 says
what to tell the user.

**Reading a mandate in a rule.** A policy may also read a mandate by name:
`projected(team_budget) > amount(950000, USD)` refuses the spend that would
leave less than a $500.00 reserve. The name derives a fixed mandate id, and the
world must open the mandate under exactly that id, which `check.py` prints. A
mandate the world never opened under that id reads 0 in every term: a
`projected(m) > cap` rule then never fires and a `remaining(m) < floor` rule
always fires. `check.py --world` reports a mandate read by name that the
world does not open (`DSL3003`). No intent is charged to a mandate the world
never opened: the world refuses an agent bound to one. A deployment can bind
an agent to a mandate its ledger does not hold. Its intents are judged: one
the policy refuses is recorded as that refusal, and one the policy would
commit is rejected (`422 substrate_rejected`, cause `unknown_mandate`),
recording nothing. A rule that reads that mandate (`projected(m)`,
`remaining(m)`, ...) while judging an intent charged to it stops the intent
the same way, unrecorded; read while judging an intent that does not charge
it, it reads 0, as above.

`projected(m)` counts the intent's charge when it rolls up to `m`: charged to
`m` or to a mandate carved from it. Every cap on one mandate is in that
mandate's currency.

Use a mandate for "this agent, or these agents together, never spend more than
X". Add a rule reading it for a line inside the budget: a reserve, a softer
limit, a refusal that names a rule instead of the mandate.

## 8. Parties, delegations, and the world

A `party <name> agent roles(...)` is an agent; a `party <name> principal` is
the human or organization that grants it authority. A `delegation` names one
principal, one agent, and a scope: the actions, the roles, and optionally a
`window(start, end)` in ticks of the ledger's clock, both ends included. A
delegation grants nothing beyond the rules: it makes the rules addressed to its
roles apply to that agent.

A party's name derives its id. The world binds each agent's `agent://` URI to a
party id; when that id is the one the policy party's name derives, the rules
and the delegation naming the party reach the agent. When it is not, the agent
acts as a stranger the delegations do not cover: every intent comes back
`denied_by_default` or `not_delegated`, and a `specific(...)` rule never
matches. `check.py --world` reports a policy agent with no world agent bound
under its derived id (`DSL3005`), a world agent bound to a party the policy
does not declare as an agent (`DSL3006`), and a binding whose `roles` are not
the ones the policy gives the party (`DSL3007`). A policy may instead name a
party by its id (`party party_6ps6...` is a valid name), which binds an
existing world party as is.

A `specific(p)` rule names one party, usually one the policy declares. The
checker also accepts a name the policy does not declare, as a party known only
when the policy runs (its id derived from the name), so a misspelled name
compiles and the rule reaches no party the user meant. `check.py --world`
warns about it (`DSL3009`) when no world agent acts as that party either, and
its help names the closest declared party; `check.py` without a world says
nothing. List every such name for the user and ask whether it is a party known
only at run time or a misspelling. An `any_in_role(r)` rule reaches every party the world gives role
`r`, delegation permitting.

**A window's end stops the paperwork too.** Once a delegation's `window` has
closed, its agent can perform nothing under it, duties it still owes included:
a purchase made just before the end owes a receipt the agent can no longer
file, and the miss is recorded. When the brief has an end date and a duty,
give the performer of the paperwork a delegation whose window runs past the
last deadline (the records agent of section 11 has its own), and say so in the
read-back. `references/patterns.md` pattern 12 shows the two delegations.

## 9. Time

The ledger has its own clock: a tick counter the substrate assigns, identical
on every replica, with no wall clock in the language. One tick is one second
in the sandbox and in a deployment at its default `tick_interval_ms = 1000`.
Write every deadline, window and period in seconds and put the civil meaning
in a comment beside the number: `within(259200) // three days`.

| Civil | Seconds |
|---|---|
| one hour | 3,600 |
| one day | 86,400 |
| one week | 604,800 |
| 30 days | 2,592,000 |

The engine's English calls a tick a "clock-beat" ("within 259,200
clock-beats"); translate it back to days when reading a rule to the user. In a
sandbox, time moves only when a case advances it (`"advance": "3d1h"`).

## 10. What cannot be said

Nested modalities, negated actions, a reparation on a `forbidden` rule,
sub-delegation, arbitrary temporal logic ("eventually", "until"), inline set
literals, floating point, history queries outside a declared aggregate, a
total or count kept per invoice number (an aggregate groups by agent, role,
vendor or rail, or not at all), and civil calendars (business days, month
ends, calendar dates) are not in the language. When a
brief item needs one, say so plainly, offer the nearest shape (a `calendar`
window of a fixed length, a duty with a reparation, a list kept in the
registry), and record the gap in the brief as accepted or open. Never invent
syntax.

## 11. Paperwork under a mandate

This section states one engine behavior and the choices it leaves the user.
Read it whenever an agent bound to a mandate would perform paperwork (a
receipt, a report) that posts legs.

**What happens.** A mandate is charged for every allowed intent its agent
submits, paperwork included (section 7, "What a charge is"). Filing a receipt
the usual way moves the spend from one account to another (spend to receipted
expenses, as the sandbox's `purchase-receipts` starter does), so the agent's
mandate, and every mandate it is carved from, is charged the receipt's amount
a second time. In `examples/team-budget`, a travel agent with a $4,000.00
share that books $1,200.00 and files its own receipt that way has used
$2,400.00 of its share and of the team budget.

**Say so plainly, before drafting the duty, and offer the choices:**

a. **A separate agent with no budget files the paperwork** (recommended when
   the user can run one). The duty stays the spending agent's, and
   `performed_by specific(<records agent>)` says who performs it. The records
   agent gets its own party, role, delegation and permit for the paperwork
   actions; the world binds it with no `mandate`. Its reclass charges nothing,
   and the books show each receipt as a real entry. `examples/team-budget`
   does this.
b. **Record the paperwork without moving money between accounts**: legs that
   debit and credit the same account (`"legs": "memo"` in a case). It charges
   nothing, but the entry nets to zero: the spend stays where the purchase put
   it, so receipted and unreceipted spend cannot be told apart in these books.
c. **Leave it**, and accept that each receipt counts against the budget again.
   Size the budget for it, or the agent runs out at half its real spending.

An agent bound to no mandate (the AP agent in `examples/ap-vendor-payments`)
is not affected: its receipt is a plain reclass and charges nothing.
