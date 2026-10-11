# Reading what the engine says

Three kinds of answer come back while a policy is drafted and tried. Read the
code, not the prose, then fix what the code points at. The code tables below
are complete: the checker table lists every code the checker gives, each drawn
by its smallest cause in the last section, and the refusal table every code
the agent plane records. A code missing here is one the engine does not give.

1. **Checker diagnostics** (`check.py`): the draft does not compile
   (`error`), or compiles and provably does not say what was meant (`warning`).
   With `--world`, a `policy` change the world schedules that it cannot run
   fails the check too.
2. **Refusals**: the engine judged an intent and refused it. The refusal is
   recorded on the ledger with its reason. `try_cases.py` shows it as
   `refused`.
3. **Rejections**: the intent never reached judgment. Nothing is recorded.
   `try_cases.py` shows it as `rejected`.

## Checker diagnostics

Each line reads `error[DSLnnnn]` or `warning[DSLnnnn]`, then the message, then
the source line with a caret. Fix every error before reading the lints: an
error can hide others. `check.py` passes `--deny-warnings`, so a lint fails the
check too: a well-structured policy has none.

| Code | Kind | Means | Usual fix |
|---|---|---|---|
| DSL0001 | error | A character the language does not use. | Remove it. Smart quotes pasted from a document do this, and so does a decimal amount: `amount(50.00, USD)` stops at the `.`. |
| DSL0002 | error | A string with no closing quote. | Close the `"`. |
| DSL0003 | error | An unknown `\` escape in a string. | The escapes are `\"`, `\\`, `\n`, `\t` and `\r`. |
| DSL0004 | error | A lone `=` or `!`. | Write `==` or `!=`. |
| DSL0010 | error | A word that is no policy item or rule clause, where one of those starts: a misspelled item (`rol clerk`) or clause (`priorty 10`). Also a clause the rule already has (every clause but `unless` comes at most once: a second `when` or `priority`), and anything after the policy's closing `}`. | Compare the line with `references/grammar.md`; the message says which was expected. Join two `when` conditions in one `when { ... }`, keep one of any other repeated clause, and move text after the policy inside its braces. When another error comes first, fix that one first: it may have closed the policy early. |
| DSL0011 | error | The file ended inside a construct: a rule, a delegation or the policy itself has no closing `}`. | Close the open `{` or `(`. |
| DSL0012 | error | The grammar wants something else at this point, and the message names it: a modality other than `permitted`, `forbidden` or `obligated` (`allowed`); a party kind other than `agent` or `principal`; a name with an upper-case letter or a `-` (`rule Cap`, `rule pay-ok`); a missing `{`, `(`, `do` or `priority`; a term the conditions do not have (`money(5, USD)`). | Write what the message names, in the words of `references/grammar.md`. Names are lower-case letters, digits and `_`. |
| DSL0020 | error | A name longer than 64 characters. | Shorten it to 64 or fewer lower-case letters, digits and `_`. |
| DSL0021 | error | A currency code that is not 3 to 8 upper-case letters. | Write `USD`, `EUR`, `USDC`. A thousands comma does this too: `amount(5,000, USD)` reads `000` as the currency. |
| DSL0022 | error | A number with something other than digits in it (`5k`). | Write plain digits; `_` may group them (`500_000`). Amounts are whole minor units: $5,000.00 is `amount(500000, USD)`. |
| DSL0023 | error | A number out of range for its place: an amount beyond a signed 128-bit count of minor units, a priority beyond a signed 32-bit integer (2,147,483,647), or a negative tick or duration (`within(-5)`). | Check the figure: amounts are minor units (`amount(50000, USD)` is $500.00), and ticks and durations count seconds from zero. |
| DSL0024 | error | An unknown word where a type or a value is named: a parameter type (`action refund(amount: money)`; the types are `bool`, `int`, `amount`, `text`, `party`, `role`, `tick`, `action` and `transaction`), or a value in a `{ param: value }` binding (`txt("acme")`). | Use the word from `references/grammar.md`. |
| DSL0025 | error | An account or transaction id that is not an id (`acc_cash`). | Copy the `acc_...` id the world or the operator gave. |
| DSL0030 | error | A name declared twice, or a key written twice in one list: an action's parameter, a `{ param: value }` binding's key, a capture's target. | Rename or remove one; roles, actions, parties, delegations, aggregates and rules each need unique names, and the keys of each list are unique. |
| DSL0032 | error | A `when`, `unless` or `during` on a duty only a breach opens: an `obligated` rule with no `trigger` that an `on_violation` names. Every breach of the rule that names it opens the duty without reading the clause, so the clause decides nothing. A `permitted` or `forbidden` rule an `on_violation` names, and an `obligated` rule with its own `trigger`, keep these clauses: the rule's verdicts or its trigger read them. | Delete the `when` or the `unless`. In place of `during`, write `within(<seconds>)` or `by(<tick>)`: either sets the duty's deadline from the breach, and a `during` leaves it with none. |
| DSL1000 | error | The policy parses but is not well-formed. The message starts `at rule rule_...:`, naming the rule by its id, not its name, then says what is wrong: a role, action or aggregate used but not declared (`role 'auditor' is used but not declared`); a parameter its action does not take; a type mismatch (`cannot apply '>' to a Text and a Amount`); amounts in two currencies compared (two literals, or an aggregate and a limit); a `trigger` on a rule that is not `obligated`; a cyclic `on_violation` chain; a window that ends before it starts. | Find the rule by the role, action or term the message quotes. Declare what is missing or fix the spelling; for the other causes see the constraint in `references/semantics.md`. |
| DSL2001 | warning | A rule that can never win (or, saying the same, is redundant): an unconditional rule at a higher priority always answers first for every party it covers. | Delete it, give the higher rule a lower priority, or add a `when` guard to the higher rule so this one has something left to decide. |
| DSL2002 | warning | A role nobody holds; a rule whose actors can never act, because no delegation lets the agent perform the action under a role it holds; or a duty nobody can incur, because its trigger never commits for the party the rule names (no rule permits it, no delegation lets the agent perform it under one that does, or an unconditional `forbidden` rule always answers first). | Give a party the role, or add the delegation the help names: `agent <name>` with a scope naming the action (for a duty, its trigger) and the role. Or make the party a principal. |
| DSL2003 | warning | An action no rule lets commit, so every proposal of it is refused: nothing permits it, and no `obligated` rule without a `trigger` answers for it (a follow-up only a breach opens never does). The message names a duty to perform it that can then never be met. | Add the permit the brief implies, or drop the action. |
| DSL2004 | warning | An aggregate no condition reads. | Read it in the rule it was declared for, or delete it. |
| DSL2005 | warning | A duty that can never be breached. A triggered duty with no deadline, or only a `during` window, which bounds when it can open, not when it lapses. Or a duty with no `trigger` and an `on_violation`: the proposal of its action that opens it also performs it, so it is met as it opens and its follow-up never opens. | Add `within(<seconds>)` or `by(<tick>)` (in place of the `during`: a rule carries one temporal). For the follow-up, give the duty a `trigger`, the action that opens it, and a `within` or `by` deadline; or delete the `on_violation` and each follow-up only it opens, as the help names them. |
| DSL2006 | warning | A condition that is always true or always false as written. | Re-read the comparison; a limit compared with itself or two constants is the usual cause. |
| DSL2007 | warning | Two rules that say the same thing. | Keep one; trace both brief items to it. |
| DSL2008 | warning | Opposite verdicts on the same action at one priority, so the tie-break decides. It flags a pair only when both name the actor in the same words, at least one has no `when` and no `unless`, their bound parameters can agree, and they are not both `during` rules: two guarded rules at one priority pass unflagged though one intent can meet both. A duty opened by a `trigger` or only by a breach (an `on_violation` follow-up) never trips it; any other `obligated` rule, at the priority of the permit for its action, does. | Give the rule that should win the higher priority, as the help says: usually the refusal. |
| DSL2009 | warning | A duty that can open but never be discharged: its performer (the agent that owes it, or the party `performed_by specific(...)` names) can never perform the owed action, because no rule permits it, no delegation lets the agent perform it under one that does, or an unconditional `forbidden` rule always answers first. With a deadline each such duty is breached there, opening its follow-up if it has one (the message names it); with none it stays open for good. A `performed_by trigger_party(...)` performer is not judged. | Add the delegation the help names (`agent <performer>` with `scope { actions(<owed action>) roles(<role>) }`), a permit if none reaches the performer, or name a party that may perform it in `performed_by`. |
| DSL3001 | error | A currency the deployment has not declared. | Declare it in the world (`currencies:`), or change the policy's currency. |
| DSL3002 | warning | A currency the deployment declares that an action can never pay in, because a money aggregate on that action sums another currency: such an intent is rejected (`substrate_rejected`, cause `currency_mismatch`), never judged. | Sum `posted` legs, or add an aggregate per currency, or confirm the action is single-currency on purpose. |
| DSL3003 | warning | The policy reads a budget (mandate) the world does not open under the id its name derives, so every term over it reads 0: a `projected(m) > cap` refusal never fires, and a `remaining(m) < floor` refusal always does. | Open the mandate in the world's `mandates` under the id `check.py` prints for that name, or fix the name in the policy. |
| DSL3004 | error | A cap on a budget in another currency than the world opens it in; a deployment refuses to register this. | Write the cap in the mandate's currency, or open the mandate in the cap's. |
| DSL3005 | warning | An agent the policy declares that no world agent is bound to under the id its name derives, so nothing can act as it. | Bind the agent in the world's `parties` under the `party:` id `check.py` prints for that name. |
| DSL3006 | warning | A world agent bound to a party the policy does not declare as an agent, so every intent it submits is refused. | Declare the agent in the policy and give it a delegation, or fix the binding's id; leave it only when the world means to show that agent being refused. |
| DSL3007 | warning | A world agent bound in other roles than exactly the ones the policy gives its party: without one, so no rule written for that role applies to it; with a role the policy declares but does not give the party, so rules written for that role reach it (their duties and `per role` totals always, their permissions and refusals where a delegation to it scopes that role) while the policy's lints read the party without it; or with a role the policy does not declare, which no rule or delegation can name. | Bind it with exactly the roles the policy gives that party: the message prints the `roles: [...]` line. When its only fault is an added declared role, the help also offers giving the party that role in the policy; ask the user which they mean. |
| DSL3008 | warning | A world agent whose `capabilities` leave out an action the policy delegates to it, so every intent to perform that action is turned away (`attestation`, 403) before the policy is consulted. | Add the action to its `capabilities`: the message prints the line. |
| DSL3009 | warning | A rule's `specific(...)`, as its actor or its `performed_by`, names a party the policy does not declare and no world agent acts as, so the rule applies to no intent there, or no intent discharges the duty. Most often a misspelling: an undeclared `specific(...)` compiles, as a party known only at run time. | Fix the name as the help says (it names the closest declared party). When the world is meant to have that party, declare it in the policy and bind an agent to it in the world. |

The `DSL3xxx` codes need the world's facts (its currencies, the mandates it
opens, the agents it binds and their roles and capabilities), so they appear only when `check.py` is given
`--world`. With a world, the check also prints each mandate and party the
policy names with the id the world must use for it.

## A policy change the world schedules

With `--world`, `check.py` also judges each `policy` change the world's
timeline schedules against the world, as the change is made when it comes
due, and the first one the world cannot run fails the check, its event
counted from one. A change named by `file` is read first, from the world's
directory joined with the name. A change's lint warnings are neither printed
nor counted: only the policy checked is linted, since a change made mid-run,
such as a freeze, is often one the linter flags and the sandbox makes it all
the same.

An `axorum-sandbox` from before this check passes such a world without
reading its changes. So with `--world`, `check.py` asks the installed one
first, and when it does not judge them, refuses with exit 2 (`does not judge
the policy changes a world schedules`): upgrade it (`pip install -U
axorum-sandbox`) and check again.

| The message says | Means | Usual fix |
|---|---|---|
| `the world cannot run event ...'s policy change: the policy source did not compile` | The policy that event changes to does not compile; its diagnostics read as in the checker table. | Fix that policy, under the event's `source` or in the file it names, then check again. |
| `the world cannot run event ...'s policy change: the policy compiles, but ... so the world cannot run it as written` | The change names a currency the world does not declare (DSL3001), or caps a mandate in another currency than the world opens it in (DSL3004). | As the checker table says for that code, for the change's policy. |
| `changes the policy to ..., which cannot be read` | The path the message names, the world's directory joined with the event's `file` (an absolute `file` as written, with `../` and symlinks followed), holds no file, holds a directory, or holds a file you may not read. The system's reason ends the message. | Put a policy file you can read at that path, or put its text under the event's `source`. |

## Refused: recorded with a reason

A refusal posts no money and is written down with its code, the rule or
mandate that refused, and the engine's English for it. Quote that English to
the user: it is the sentence an auditor will read.

| Code | Means | What to change |
|---|---|---|
| `forbidden_by_rule` | A `forbidden` rule applied and outranked every permit. Names the rule. | Nothing, when the brief wanted this refusal. Otherwise the rule's condition or priority. |
| `denied_by_default` | No rule permits this action for this actor. | Add the permit the brief implies, or accept the refusal: deny-by-default is the safety net. |
| `not_delegated` | A permit matched, but no delegation to this agent covers the action, its role or this moment. Names the permit. | The delegation's `scope` or `window`, not the rule. |
| `reason_archived` | A replayed answer for a refusal whose record was compacted; the reason lives in the archive. | Nothing in the policy. It does not arise in a fresh sandbox. |
| `mandate_exceeded` | The policy would have allowed the charge, but it takes a mandate in the charged chain past its ceiling. Names the mandate. | The mandate's ceiling in the world, or nothing, when the budget is doing its job. A rule refusal always wins over this one. |
| `mandate_revoked` | The policy would have allowed the charge, but a mandate in the chain is revoked. | The world: reopen or rebind the agent. |

## Rejected: never recorded

These are HTTP errors, not verdicts. Nothing is recorded, so no auditor sees
them. Most turn the intent away before judgment; `invalid_fulfillment`, and
`unknown_mandate` on a charge the policy would commit, come after the policy
allowed it. When the brief wants a refusal on the record, make the intent
reach judgment and have a rule refuse it.

| Code | Status | Usual cause while drafting |
|---|---|---|
| `substrate_rejected` | 422 | A payee the counterparty registry does not know, under a `per counterparty(...)` aggregate, `resolved counterparty(...)` or `counterparty limit(...)`; an amount in another currency than a `sums <action>(<param>) ... in <CUR>` total on its action (`DSL3002`); a mandate the ledger does not hold, charged by an intent the policy would commit, or read by a rule judging it while the intent charges it; or legs that do not balance. Its `cause` and message name which: an unknown payee is `unknown_counterparty` (import the counterparty, or name a registered one), an amount in the other currency `currency_mismatch`, a mandate never opened `unknown_mandate`. |
| `invalid_fulfillment` | 422 | An intent the policy allows names a duty in `fulfills` that is not open, is not this agent's to perform, owes a different action or parameters, or is past its deadline. One bad id rejects the whole intent: none of the duties it names is discharged. An intent the policy refuses is recorded as that refusal instead, whatever duties its `fulfills` names. |
| `multi_currency_mandate_charge` | 422 | One mandate-bound intent moved money out in two currencies. |
| `unknown_agent` | 401 | The `agent://` URI is not bound to a party in the world. |
| `attestation` | 403 | The agent's token was refused: another issuer signed it, it was minted for another agent, it has expired, or it lacks the capability for this action (`references/world.md`, "Who an agent is"). For a missing capability, add the action to the world party's `capabilities`. |
| `invalid_envelope` | 422 | The request body is malformed, a `fulfills` that repeats an id or names more than 64 included, whether or not the policy would allow the intent; a bug in the caller, not the policy. |

## When a case misses

`try_cases.py` prints `MISS` with what happened. Decide which side is wrong
before editing anything, and say which to the user:

- **The policy is wrong**: it does not do what the brief says. Fix the rule,
  re-check, re-try.
- **The case is wrong**: the user's example contradicts another brief item, or
  the arithmetic was off. Ask the user which item wins, update the brief, then
  the case.
- **The world is wrong**: a missing capability, an unbound agent, a payee not
  in the registry, a mandate with the wrong ceiling. Fix the world, not the
  policy. `check.py --world` catches most of these before a try.
- **Two refusals applied, and the other one is named**: both sit at one
  priority, and the record names only one (`references/semantics.md` section
  2). Ask which reason the record should give, and raise that refusal one step.

## A verdict in the user's own sandbox

When a decision in the user's running sandbox surprises them, read the
engine's own account of it before changing anything. The activity report lists
every intent with its transaction id, its actor, its amount and the rule that
blocked it:

```bash
curl -s '<their sandbox>/_sandbox/report?kind=activity'
curl -s '<their sandbox>/_sandbox/report?kind=explain&transaction=txn_...'
```

The explain report's `text` says, in order: what the agent tried, the outcome,
the rule that decided with its rendering and priority, the authority it acted
under, the money that moved, the vendor-list version, and the policy in force.
Its other fields carry the same facts as data (`winning_rule`,
`defeated_rules`, `duties_created`, `refused_counterparty`, ...). Read the
`text` to the user, then decide as for a miss: the policy, the agent's intent
or the world.

Once a vendor list under another `source_version` has been imported since a
refusal (an injected master-data import), neither report describes the vendor
any more: the activity report's line names only the rule that refused it, and
the explanation names that rule and the list version the decision used. To
tell the user why it was refused, find the list with that `source_version`
(the world's `master_data`, or the import the user injected) and read the
vendor's entry there, not the list as it stands now.

## The smallest cause of each code

Each block below is the smallest change that draws its code, which shows one
cause in full. Tests run every block, so each code here is one the checker
gives. A block is lines added just before the last `}` of this policy, which
checks clean against the smallest world `axorum-sandbox grammar world` prints:

```axp
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
```

An error's block draws that error first; a lint's block draws that lint and
no other. A `DSL3xxx` code needs the world: its `yaml` block is a fragment
whose top-level keys take the place of the same keys in that smallest world,
and the code is drawn when the policy is checked against it.

```axp
// DSL0001: a decimal amount
  rule cap { forbidden any_in_role(clerk) do purchase when { ( param(amount) > amount(50.00, USD) ) } priority 10 }
```

```axp
// DSL0002: a string with no closing quote
  rule pay_acme { permitted any_in_role(clerk) do purchase { payee: text("acme) } priority 1 }
```

```axp
// DSL0003: an unknown escape
  rule pay_acme { permitted any_in_role(clerk) do purchase { payee: text("a\qb") } priority 1 }
```

```axp
// DSL0004: a lone `=`
  rule cap { forbidden any_in_role(clerk) do purchase when { ( param(amount) = amount(500000, USD) ) } priority 10 }
```

```axp
// DSL0010: a misspelled rule clause
  rule cap { forbidden any_in_role(clerk) do purchase priorty 10 }
```

```axp
// DSL0011: a rule with no closing brace, so the policy has none
  rule cap { forbidden any_in_role(clerk) do purchase priority 10
```

```axp
// DSL0012: a modality the language does not have
  rule cap { allowed any_in_role(clerk) do purchase priority 10 }
```

```axp
// DSL0020: a name of 65 characters
  rule cap_on_purchases_over_five_thousand_dollars_for_the_clerk_agent_x { forbidden any_in_role(clerk) do purchase priority 10 }
```

```axp
// DSL0021: a currency in lower case
  rule cap { forbidden any_in_role(clerk) do purchase when { ( param(amount) > amount(500000, usd) ) } priority 10 }
```

```axp
// DSL0022: a letter in a number
  rule cap { forbidden any_in_role(clerk) do purchase when { ( param(amount) > amount(5k, USD) ) } priority 10 }
```

```axp
// DSL0023: a negative duration
  rule purchase_again { obligated any_in_role(clerk) do purchase trigger purchase within(-5) priority 5 }
```

```axp
// DSL0024: a parameter type the language does not have
  action refund(amount: money)
```

```axp
// DSL0025: an account id that is not an id
  rule cap { forbidden any_in_role(clerk) do purchase when { ( posted debit USD in acc_cash > amount(500000, USD) ) } priority 10 }
```

```axp
// DSL0030: a role declared twice
  role clerk
```

```axp
// DSL0032: a `when` on a duty only a breach opens
  action report()
  rule report_purchase { obligated any_in_role(clerk) do report trigger purchase within(3600) on_violation report_late priority 5 }
  rule report_late { obligated any_in_role(clerk) do report within(86400) when { ( now > tick(0) ) } priority 5 }
```

```axp
// DSL1000: a role used but not declared
  rule cap { forbidden any_in_role(auditor) do purchase priority 10 }
```

```axp
// DSL2001: an unconditional refusal above the permit
  rule refuse_purchase { forbidden any_in_role(clerk) do purchase priority 10 }
```

```axp
// DSL2002: a role nobody holds
  role auditor
```

```axp
// DSL2003: an action nothing permits
  action refund(amount: amount)
```

```axp
// DSL2004: a total nothing reads
  aggregate spent sums purchase(amount) per party over unbounded in USD
```

```axp
// DSL2005: a duty with no deadline
  rule purchase_again { obligated any_in_role(clerk) do purchase trigger purchase priority 5 }
```

```axp
// DSL2005: a duty bounded only by a `during` window
  rule purchase_again { obligated any_in_role(clerk) do purchase trigger purchase during(0, 86400) priority 5 }
```

```axp
// DSL2005: a follow-up on a duty met as it opens
  rule purchase_again { obligated any_in_role(clerk) do purchase within(86400) on_violation report_missed priority 5 }
  rule report_missed { obligated any_in_role(clerk) do purchase within(86400) priority 5 }
```

```axp
// DSL2006: two constants compared
  rule cap { forbidden any_in_role(clerk) do purchase when { ( amount(5, USD) > amount(10, USD) ) } priority 10 }
```

```axp
// DSL2007: the permit again under another name
  rule permit_purchase_again { permitted any_in_role(clerk) do purchase priority 1 }
```

```axp
// DSL2008: a refusal at the permit's priority
  rule cap { forbidden any_in_role(clerk) do purchase when { ( param(amount) > amount(500000, USD) ) } priority 1 }
```

```axp
// DSL2009: a duty its performer may never discharge
  rule controller_follow_up { obligated any_in_role(clerk) do purchase trigger purchase within(86400) performed_by specific(controller) priority 5 }
```

```axp
// DSL3001: a currency the world does not declare
  rule cap { forbidden any_in_role(clerk) do purchase when { ( param(amount) > amount(500000, EUR) ) } priority 10 }
```

```axp
// DSL3002: a total in USD, in a world that also pays in EUR
  aggregate spent sums purchase(amount) per party over unbounded in USD
  rule budget { forbidden any_in_role(clerk) do purchase when { ( projected(register(spent)) > amount(1000000, USD) ) } priority 10 }
```

```yaml
# DSL3002
currencies:
- currency: USD
  exponent: 2
- currency: EUR
  exponent: 2
```

```axp
// DSL3003: a budget the world does not open
  rule travel_cap { forbidden any_in_role(clerk) do purchase when { ( projected(travel) > amount(400000, USD) ) } priority 10 }
```

```axp
// DSL3004: a cap in USD on a budget the world opens in EUR
  rule travel_cap { forbidden any_in_role(clerk) do purchase when { ( projected(travel) > amount(400000, USD) ) } priority 10 }
```

```yaml
# DSL3004
currencies:
- currency: USD
  exponent: 2
- currency: EUR
  exponent: 2
mandates:
- mandate: mand_7xw13c5bagaad8gmfnk9fzcwhb
  currency: EUR
  ceiling: 500000
```

```axp
// DSL3005: an agent the world does not bind
  party ads_bot agent roles(clerk)
```

```axp
// DSL3009: a rule for a party nobody declares or binds
  rule ads_pay { permitted specific(ads_bot) do purchase priority 1 }
```

```yaml
# DSL3006: an agent bound to a party the policy does not declare
parties:
- agent: agent://example.com/agent/clerk_01h455vb4pex5vsknk084sn02q
  party: party_28zwgzaew1a2r92s1y9swtj3nj
  roles: [clerk]
- agent: agent://example.com/agent/ads_01h455vb4pex5vsknk084sn02q
  party: party_7cky9f0ahdafma6d3hxkcb8s0g
  roles: [clerk]
```

```yaml
# DSL3007: the agent bound without its role
parties:
- agent: agent://example.com/agent/clerk_01h455vb4pex5vsknk084sn02q
  party: party_28zwgzaew1a2r92s1y9swtj3nj
  roles: []
```

```yaml
# DSL3008: a token that cannot carry `purchase`
parties:
- agent: agent://example.com/agent/clerk_01h455vb4pex5vsknk084sn02q
  party: party_28zwgzaew1a2r92s1y9swtj3nj
  roles: [clerk]
  capabilities: [submit]
```
