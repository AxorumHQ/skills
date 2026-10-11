# The conversation

The user knows the business: who the agents are, what they buy, from whom,
what the budget is, who signs off, what paperwork follows. They have usually
not thought it through as rules, and do not know the policy language. The
conversation draws the facts out one at a time, writes each down in the control
brief as it is decided, and never fills a gap silently.

## How to ask

- **Start by saying what will happen.** On the first turn, say in two lines
  that a few questions come first, then a draft, then a test on their own
  examples, and ask the first question. Show the brief once it has an item.
- **One question per turn.** Lead with one line on why it matters, then the
  question, then two to four options with one marked as the default. When a
  structured-question tool is available (such as `AskUserQuestion`, which
  takes at most four options), use it, with the default first and labelled
  "(Recommended)"; otherwise write the options as a short lettered list.
- **Options a newcomer can tell apart.** Each option says what would happen
  in their business, with a figure ("a $6,000 payment to Acme is refused"),
  not how the rule is built.
- **Business words only.** Use the left column of the vocabulary table in
  `SKILL.md`. Never ask about roles, delegations, aggregates, priorities or
  modalities by name.
- **Concrete numbers.** "Up to what amount for one payment?" not "Is there a
  threshold?". Offer typical figures as options when the user has none.
- **Defaults are safe ones.** The stricter cap, the shorter deadline, the
  narrower permission, refusal on the record rather than silent rejection.
- **Test each figure against the user's reason.** When the user explains a
  figure with an incident ("it paid one invoice four times in an hour"), check
  that the figure would have stopped it (five a vendor per hour would not have),
  say so, and make the incident a case.
- **"I don't know" is an answer.** Offer the default, record it in the brief as
  an assumption to confirm, and move on.
- **Update the brief after every answer** and show the changed lines, not the
  whole brief, unless the user asks.
- **Stop asking when the brief is complete enough to draft.** Open items that
  do not block a draft go into the brief as open; drafting and trying cases
  often answers them faster than another question.

## Turning a vague ask into questions

"Pay vendors but don't go crazy", "keep the agents on a budget", "make sure
the receipts come in": each hides several separate controls. Name the usual
ones and let the user pick, then ask about each picked one in turn:

> When people say an agent should not go crazy with payments, they usually mean
> some of these. Which of these limits matter to you?
> a. One payment that is too big
> b. Too much going to one vendor over a period
> c. Too much paid out in total, per day or per month
> d. Paying someone not on your vendor list
> (Recommended: a, c and d. b works only if every vendor the agent might pay
> is listed in advance: a payment to one we have never heard of is then
> stopped with no record that it was tried.)

Then, as a second question:

> And which of these habits?
> a. Too many payments too fast
> b. The same bill paid twice
> c. Payments with no receipt or paperwork afterwards
> (Recommended: a and c. b can only be guarded roughly, at most one payment to
> a vendor in a short time, which also stops two real bills to that vendor; and
> like a limit per vendor, it needs every vendor listed in advance.)

Ask each as a multi-select question (four options at most, so the menu is two
questions). Record the ones the user declines under "Not wanted" in the brief,
and ask about each picked one in turn.

Neither per-vendor control is a default, because each costs something the
user must accept. Both read a running total kept per vendor (`per
counterparty(payee)`), and by the engine's design a total for a vendor it
cannot identify is never guessed: a payment to a vendor missing from the
imported vendor list is stopped before any rule answers, `422
substrate_rejected` with cause `unknown_counterparty` ("import the
counterparty, or name a registered one"), and nothing is recorded, not even a
refusal. Choosing either therefore means every vendor is imported first, with
`approved: false` for one to refuse on the record. Without them, the
approved-list rule refuses an unknown vendor on the record: `param(payee) in
approved counterparties` judges a name that resolves to nothing as off the
list, never as an error (`references/semantics.md` section 5).
`examples/ap-vendor-payments/` makes the per-vendor choice: its B4 caps each
vendor, so its world lists every vendor it pays, and its case "pay a vendor the
list has never heard of" is rejected unrecorded.

## The question bank

Ask only what the request has not already answered, roughly in this order. Each
entry says what the answer becomes; that column is for drafting, never for the
user.

### Who acts, and who answers for it

| Ask | Options (default first) | Becomes |
|---|---|---|
| Which agents will this govern, and what is each one's job? | one agent; one agent per job (purchasing, travel, ads) | one `party ... agent` per job, a `role` per kind of job |
| Who is accountable for what the agents do? | the controller (recommended); the team lead; the CFO | the `principal` party in each delegation |
| Should every agent in a job follow the same rules, or does one need its own? | same rules for the job; this agent differs | `any_in_role(...)` versus `specific(...)` |
| Does an agent's authority end on a date? | no end date; ends on a date | a delegation `window` |

### What they do

| Ask | Options | Becomes |
|---|---|---|
| What does each agent do that moves money? | pay a vendor; book travel; buy ads; refund a customer | an `action` per verb |
| What should a rule be able to look at when it does that? | the amount and who is paid (recommended); also a category; also a flag | the action's parameters (`amount`, `payee: text`) |
| For a money limit: the amount the agent states, or the money that actually moves? | the money that moves (recommended) | `posted debit USD` rather than `param(amount)` |
| Which currency? | USD; another | the currency in amounts, aggregates and the world; with two currencies, see the currency note in `references/patterns.md` pattern 5 |

### What is allowed, and what is refused

| Ask | Options | Becomes |
|---|---|---|
| Largest single payment allowed? | a figure; none | a forbid on `posted debit USD > amount(...)` |
| Paid only to vendors on an approved list? | yes, your vendor list; no list | a forbid on `not param(payee) in approved counterparties`, and the list in the world |
| A limit per vendor, or the duplicate-bill guard, needs every vendor listed first, and a payment to one not listed is then stopped with no record. Keep it on those terms? | leave it out, so an unlisted vendor is refused on the record (recommended); keep it and list every vendor | no `per counterparty` total; or the total, with every vendor in the world's list (`approved: false` for one to refuse) |
| Is there an exception to a limit, with a reason the record should name? | no; yes, for ... | an `unless <reason> { ... }` on that forbid |
| Up to what amount does the exception hold? | the expected amount (recommended); any amount | a second clause in the `unless`, `references/patterns.md` pattern 5 |
| Could the same bill be paid twice? | no guard (recommended); at most one payment to a vendor in a short time | no per-invoice key exists (an `X` item); the nearest shape counts payments `per counterparty(payee)` over a short window and refuses the second, which also refuses two real bills to one vendor inside it, and needs every vendor listed first (the row above): say both |

### Totals and budgets

| Ask | Options | Becomes |
|---|---|---|
| Is there a cap on the total, not just one payment? | per agent; per vendor; for the whole team | an aggregate `per party`, `per counterparty(payee)` (every vendor listed first: the unlisted-vendor row above), `global`; or a mandate |
| Over what period? | any rolling 30 days (recommended); each fixed 30-day block; ever | `rolling 2592000`, `calendar 2592000`, `unbounded`; for once a month, 27 days (`references/patterns.md` pattern 6) |
| Is the budget fixed money the agents must never pass together? | yes, a budget; no, just a limit | a mandate in the world (and per-agent mandates carved from it) |
| Should some of the budget stay in reserve? | no; keep a reserve of ... | a forbid on `projected(<mandate>) > amount(ceiling - reserve)`; ask it together with the split: shares that add up to the whole budget leave a reserve rule nothing to do until both are nearly spent, and make the shares unreachable together |
| How many payments in how long? | no pace limit; a figure per hour or day | a `counts ... per party over rolling n` aggregate and a forbid on it |

Say how a cap behaves at the line: the payment that would cross it is the one
refused, and one landing exactly on it is allowed. Ask if that is right.

### What a payment obliges afterwards

| Ask | Options | Becomes |
|---|---|---|
| After a payment, does the agent owe anything? | a receipt; an approval; a report; nothing | an `obligated` rule triggered by the payment, plus a permit for the owed action |
| For every payment, or above an amount? | above an amount; every payment | a `when` on the duty |
| By when? | within one day (recommended); three days; a week | `within(86400)`, `within(259200)`, `within(604800)`; tell the user the time counts from the payment itself |
| Should the receipt name the payment it is for and carry its amount? | yes (recommended); no, one receipt may then clear several purchases' duties | `capture { amount: trigger_param(amount), purchase: trigger_transaction }` |
| If it is missed, what follows? | it is recorded as missed (always); also a follow-up such as a missing-receipt report within a day | `on_violation` naming a second duty with its own deadline; the first duty keeps its `trigger` and its `within`, or it is never missed |
| Who files the paperwork? | the agent that paid (recommended when it has no budget); another agent | `performed_by`; an agent under a budget: `references/semantics.md` section 11 first |
| Who hears about a miss? | (a fact to state, not a question) | the engine records the miss and opens the follow-up, and sends no message: say who reads the misses, and put it in the hand-back's "What it relies on" |

## The control brief

Keep it in the conversation from the first answer, and copy the items into
the policy's header comment when drafting. Every control gets a `B` number when
it is first written down, decided or not: a default taken for an unanswered
question is a `B` item marked `(assumed)` until the user confirms it. `A` items
are only assumptions that produce no rule (who keeps the vendor list). The
numbers never change once given, so cases and rules can refer to them: a
correction amends its item and keeps the number, and a new control takes the
next one.

```text
Control brief: <what it governs, in a line>

Agents
  <name>: <its job>, accountable to <principal>

Controls
  B1  <one control, in the user's words, with figures>
  B2  <a default the user has not confirmed> (assumed)

Assumed (please confirm)
  A1  <an assumption that produces no rule>

Open
  O1  <a question still to answer, and why it matters>

Cannot be expressed
  X1  <what was asked>: <nearest shape offered>, <accepted or open>

Not wanted
  <a control the user declined, so it is not asked again>
```

Confirm the brief before drafting: show it whole once, and ask whether
anything is missing or wrong. Then ask about each `(assumed)` item and each `A`
item by itself: "looks right" to the whole brief confirms the brief, not the
assumptions in it.

## Reading the policy back

After the policy checks clean, read every rule back in the brief's order:

```text
B3  No single payment over $5,000.00, except the rent to Northgate
    Properties, up to $8,500.00.
    Rule single_payment_cap, with the exception named rent.
    The engine's wording: "Any party in the role 'ap_clerk' is forbidden to
    perform 'purchase'. It applies only when the amount debited in USD is
    greater than $5,000.00. It is overridden by the exception 'rent' whenever
    the parameter 'payee' equals the text "northgate-properties", and the
    amount debited in USD is at most $8,500.00; a firing exception outranks
    this rule."
```

- First line: the brief item, in the user's words, with dollars and days.
  This is the line the user judges; everything after it is evidence.
- Second: the rule that carries it out, and its exception if any.
- Third: the engine's rendering for that rule, as `check.py --world` printed
  it and labelled as the engine's wording. It is what an auditor will read.
  Leave out the checker's heading and priority (the leading "Rule 5", the
  dash and "single_payment_cap.", and "(authored priority 10)"): the number
  is the rule's place in the checker's alphabetical list, not the brief's.
  Quote the rest without editing it. For a long duty, quote the sentences
  that carry the item's figures (who must, what, by when, what follows) and
  say the full wording is in the policy's check. Checked without a world, it
  prints amounts in minor units ("500000 USD (in minor units)"): quote the
  `--world` rendering instead.
- Then, only where the engine's words differ from the user's, a short gloss
  from the table below.

| The engine says | Say |
|---|---|
| principal | the person who answers for the agent |
| delegation, "grants ... authority" | the permission that person gives the agent |
| obligated | must |
| clock-beats | seconds (259,200 is three days) |
| register, "the register 'paid_per_vendor'" | the running total (per vendor) |
| reparation, contrary-to-duty | the follow-up |
| "Reparations resolve their own captures against this same original transaction" | the follow-up is about the same payment |
| "Only the party ..., authenticated as the performer, may fulfill this duty; responsibility for breach remains with the debtor" | only that agent can file it, and a miss still counts against the agent that paid |
| Rule 6 ('report_missing_receipt') | the rule report_missing_receipt |

Then say what deny-by-default refuses that the brief does not mention ("any
action other than paying and filing receipts is refused"), and anything worth
a second look (a cap that allows landing exactly on it, an unknown vendor being
turned away). Ask the user to confirm each item or say which is wrong. A wrong
item goes back to the brief, then the policy, then the check and the cases.

## When the user is not there

For a one-shot request with nobody to answer, do not stall: draft under the
safe defaults, mark every control taken by default `(assumed)` and list the
other assumptions as `A` items, in the header comment and the reply, and say
that the policy is a proposal until they are confirmed.

A per-vendor total (a limit per vendor, or the duplicate-bill guard) goes by
what the request says, since nobody is there to weigh its cost:

- **Asked for:** an explicit request wins. Draft it beside the approved-list
  rule, and state its cost in the read-back as a decision the user made: a
  vendor missing from the imported vendor list is turned away as
  `unknown_counterparty` before any rule answers, with nothing recorded, so
  every vendor must be imported first. A duplicate-bill guard has a second
  cost, stated beside the first: it counts payments per vendor, not per bill,
  so it also refuses two real bills to one vendor inside its window. List each
  cost as an `A` item.
- **Not asked for:** the default applies. Draft no `per counterparty` total,
  so the approved-list rule refuses an unknown vendor on the record, and offer
  the total as an `O` item that says what it needs: "a limit per vendor: every
  vendor listed first; a payment to an unlisted one is then stopped with no
  record".
