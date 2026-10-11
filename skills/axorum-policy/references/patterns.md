# From what the user says to what the policy says

Each pattern pairs a control as a finance user says it with the policy text
that carries it out. Every snippet is copied from
`examples/ap-vendor-payments` or `examples/team-budget`, where it compiles
with no lint and its cases pass. Copy the shape, rename to the user's words,
and re-check.

## Contents

1. Header: the brief, traced to rules
2. Who may act: party, role, delegation
3. The permit everything else overrides
4. Only approved vendors
5. A cap on one payment, with a named exception
6. A rolling total per vendor
7. A pace limit
8. A duty tied to the payment that opened it
9. A follow-up when a duty is missed
10. A team budget split between agents, with a reserve
11. A limit for one agent only
12. Authority that ends, and paperwork that outlives it
13. More shapes in the starters

## 1. Header: the brief, traced to rules

Every policy opens with the brief, each item mapped to the rules (or world
objects) that carry it out, the deny-by-default statement, and the time units.
`try_cases.py` reads the `B` items from it and reports any item no case tries.

```axp
// Brief, and the rules that carry it out:
//   B1  The AP agent may pay vendors.                      permit_payment
//   B2  Only vendors approved on the vendor list are paid. vendor_must_be_approved
//   B3  No single payment over $5,000.00, except the rent  single_payment_cap
//       to Northgate Properties, up to $8,500.00.          (unless rent)
//   B4  No vendor receives more than $20,000.00 in any     vendor_30_day_cap
//       30 days.
//   B5  At most 10 payments in any hour.                   hourly_pace
//   B6  A payment over $2,500.00 needs its receipt filed   receipt_for_large_payment,
//       within one day.                                    permit_receipt
//
// Anything no rule above allows is refused: the engine denies by default.
// Times are in seconds: one day is 86,400, thirty days 2,592,000.
```

A brief item a world object carries (a mandate) names it with `(world)`:

```axp
//   B2  The ads agent spends at most $7,000.00.            ads_mandate (world)
```

## 2. Who may act: party, role, delegation

> "One AP agent, and the controller answers for it."

```axp
  role ap_clerk

  action purchase(amount: amount, payee: text)
  action file_receipt(amount: amount, purchase: transaction)

  party ap_bot agent roles(ap_clerk)
  party controller principal

  delegation ap_grant {
    principal controller
    agent ap_bot
    scope { actions(purchase, file_receipt) roles(ap_clerk) }
  }
```

- `purchase(amount: amount, payee: text)` is the shape the SDK's one-call
  `authorize` proposes; keep it for paying agents.
- The delegation lists every action the agent performs, the paperwork it owes
  included. A missing one makes the agent's intents `not_delegated`.
- With two agents, give each its own delegation, scoped to what that agent
  does:

```axp
  delegation ads_grant {
    principal marketing_lead
    agent ads_bot
    scope { actions(purchase) roles(marketing) }
  }
```

## 3. The permit everything else overrides

> "The AP agent may pay vendors."

```axp
  // B1: the AP agent may pay a vendor. Every refusal below outranks this.
  rule permit_payment {
    permitted any_in_role(ap_clerk) do purchase
    priority 1
  }
```

Every refusal sits at a higher priority, so it wins. Without a permit, nothing
is ever allowed.

## 4. Only approved vendors

> "Only pay vendors on our approved list."

```axp
  // B2: a vendor the vendor list does not mark approved is refused.
  rule vendor_must_be_approved {
    forbidden any_in_role(ap_clerk) do purchase
    when { ( not param(payee) in approved counterparties ) }
    priority 10
  }
```

- Reads the vendor list in the world's `master_data`. How a payee sent under
  one of a vendor's aliases is judged: `references/semantics.md` section 5,
  "Aliases and the approved check".
- A vendor marked `approved: false` is refused on the record. A vendor the list
  has never heard of is refused too, unless an aggregate `per
  counterparty(payee)` is declared (pattern 6): then it is rejected before
  judgment. Make the user choose (`references/semantics.md` section 5).

## 5. A cap on one payment, with a named exception

> "Nothing over $5,000 in one go, except the rent, which is $8,500."

```axp
  // B3: a payment that moves more than $5,000.00 is refused, unless it is
  // the rent to Northgate Properties, which moves at most $8,500.00.
  rule single_payment_cap {
    forbidden any_in_role(ap_clerk) do purchase
    when { ( posted debit USD > amount(500000, USD) ) }
    unless rent {
      ( param(payee) == text("northgate-properties") )
      and ( posted debit USD <= amount(850000, USD) )
    }
    priority 10
  }
```

- `posted debit USD` reads the money that moves, not the amount the agent
  claims.
- `>` means $5,000.00 itself is allowed. Ask whether "nothing over" includes
  the figure.
- The exception is named, so the record says which exception let a payment
  through.
- Bound the exception. "Except the rent" without a figure lets any amount to
  that vendor through; ask what the rent is and cap the exception there, as
  above.
- The exception compares the payee exactly as the agent sent it: `northgate`
  does not match. To compare the vendor whichever spelling names it, use
  `resolved counterparty(payee)` (`references/semantics.md` section 5).
- `posted debit USD` reads US dollars only: a payment in another currency
  moves $0.00 of them and passes every dollar cap. When the world declares a
  second currency, add a refusal `when { ( posted debit USD == amount(0, USD)
  ) }` ("a payment not in US dollars is refused"), or a cap per currency, and
  tell the user why.

## 6. A rolling total per vendor

> "No vendor gets more than $20,000 in any 30 days."

```axp
  // What each vendor was paid over the last 30 days (2,592,000 seconds).
  aggregate paid_per_vendor sums posted debit USD purchase per counterparty(payee) over rolling 2592000
```

```axp
  // B4: the payment that would take a vendor past $20,000.00 in 30 days is
  // refused. Landing exactly on $20,000.00 is allowed.
  rule vendor_30_day_cap {
    forbidden any_in_role(ap_clerk) do purchase
    when { ( projected(register(paid_per_vendor)) > amount(2000000, USD) ) }
    priority 10
  }
```

- `projected` counts this payment, so the payment that would cross is refused.
- Declaring it means every vendor is listed first: a payment to one the list
  has never heard of is stopped before any rule answers (`substrate_rejected`,
  cause `unknown_counterparty`), unrecorded. It is the user's choice, never a
  default (`references/conversation.md`); the AP example makes it.
- "Any 30 days" is `rolling`; "each calendar month" has no exact form: offer a
  fixed 30-day block (`calendar 2592000`) or the rolling window.
- For a payment allowed once a month (rent, a retainer), a 30-day window
  refuses next month's payment whenever the month between is shorter:
  February 1 to March 1 is 28 days. Use 27 days (2,332,800 seconds), and tell
  the user that two payments 27 days apart both go through.
- Per vendor means the registry must know every payee (pattern 4).

## 7. A pace limit

> "No more than 10 payments an hour."

```axp
  // How many payments the agent made in the last hour (3,600 seconds).
  aggregate payments_last_hour counts purchase per party over rolling 3600
```

```axp
  // B5: the eleventh payment inside an hour is refused.
  rule hourly_pace {
    forbidden any_in_role(ap_clerk) do purchase
    when { ( projected(register(payments_last_hour)) > int(10) ) }
    priority 10
  }
```

## 8. A duty tied to the payment that opened it

> "Anything over $2,500 needs a receipt within a day."

```axp
  // B6: a payment that moves more than $2,500.00 opens a duty to file its
  // receipt within one day (86,400 seconds). The receipt names the payment
  // it is for, so one receipt never clears another payment's duty.
  rule receipt_for_large_payment {
    obligated any_in_role(ap_clerk) do file_receipt
    trigger purchase
    capture { amount: trigger_param(amount), purchase: trigger_transaction }
    when { ( posted debit USD > amount(250000, USD) ) }
    within(86400)
    priority 5
  }

  // B6: the AP agent may file a receipt, so the duty above can be met.
  rule permit_receipt {
    permitted any_in_role(ap_clerk) do file_receipt
    priority 1
  }
```

- The owed action declares a `transaction` parameter to receive
  `trigger_transaction`.
- The receipt is filed with `fulfills` naming the duty, and with legs that
  move the payment from spend into receipted expenses. That charges nothing
  here because the AP agent holds no mandate. When the agent that owes the
  paperwork is bound to a mandate, read `semantics.md` section 11 before
  drafting the duty.
- Priority 5 is the duties' band from the header. A duty opened by a trigger
  never competes with the permits for a verdict, so the band is for the
  reader: no lint weighs it against the permits at 1.

## 9. A follow-up when a duty is missed

> "Receipts within three days; if one is still missing, the agent reports it
> within another day."

```axp
  // B7, B9: every travel booking opens a duty to file its receipt within
  // three days (259,200 seconds). The receipt names the booking it is for.
  // The duty is the travel agent's; the records agent performs it.
  rule receipt_for_travel {
    obligated specific(travel_bot) do file_receipt
    trigger purchase
    capture { amount: trigger_param(amount), purchase: trigger_transaction }
    performed_by specific(records_bot)
    within(259200)
    on_violation report_missing_receipt
    priority 5
  }

  // B8, B9: a receipt still missing after three days must be reported
  // within one more day (86,400 seconds), naming the same booking. The
  // records agent performs it too.
  rule report_missing_receipt {
    obligated specific(travel_bot) do report_missing_receipt
    capture { amount: trigger_param(amount), purchase: trigger_transaction }
    performed_by specific(records_bot)
    within(86400)
    priority 5
  }
```

- The follow-up has no trigger: it opens only when the first duty is missed,
  and its captures read the original booking.
- The first duty has a `trigger` and a `within` deadline, so it can be missed.
  Without the trigger it would open on a `file_receipt` by the travel agent,
  not on a booking, and the travel agent may not file one, so it never opens
  (`DSL2002`). A duty with no trigger whose own proposer performs it, with
  every capture a copy of a parameter into itself, is met by the proposal that
  opens it: it is never missed, and the check reports `DSL2005` on its
  `on_violation`. A capture of one parameter into another counts as a copy
  when a `when` conjunct holds the two equal (`param(n) == param(m)`). A
  `during` window alone never lapses either.
- Both owed actions need permits and a delegation for the agent that performs
  them (`permit_receipt`, `permit_report` and `records_grant` in the example).
  Without the delegation the check reports `DSL2009` (the duty can open and
  never be discharged) and `DSL2002` on the permit.
- `performed_by` names who may meet the duty; without it, the agent that
  booked must. Here a records agent with no budget files the paperwork, so
  filing never counts as travel spending: `references/semantics.md` section 11
  says when to offer that.

## 10. A team budget split between agents, with a reserve

> "$10,000 for the campaign: ads up to $7,000, travel up to $4,000, and keep
> $500 back."

The budgets are mandates in the world: `team_budget` with a $10,000.00
ceiling, and `ads_mandate` and `travel_mandate` carved from it
(`references/world.md`). The ledger enforces all three ceilings with no rule.
The reserve is a rule that reads the team budget:

```axp
  // B5: the spend that would leave less than $500.00 of the $10,000.00 team
  // budget is refused, whichever agent makes it.
  rule keep_reserve {
    forbidden any_in_role(marketing) do purchase
    when { ( projected(team_budget) > amount(950000, USD) ) }
    priority 10
  }
```

- `projected(team_budget)` counts a charge to either child mandate.
- A rule refusal wins over a budget refusal, so once the reserve is reached
  `keep_reserve` names the refusal, not `team_budget`.
- The world must open `team_budget` under the id its name derives, or the
  rule never fires (`check.py --world` reports it).

## 11. A limit for one agent only

> "No single trip over $1,500."

```axp
  // B6: a travel booking that moves more than $1,500.00 is refused.
  rule travel_trip_cap {
    forbidden specific(travel_bot) do purchase
    when { ( posted debit USD > amount(150000, USD) ) }
    priority 10
  }
```

## 12. Authority that ends, and paperwork that outlives it

> "The agents can spend until the end of May."

A delegation's scope takes `window(<start>, <end>)` in ticks of the ledger's
clock, both ends included: `scope { actions(purchase) roles(marketing)
window(0, 7948800) }` lets the agent act from the start of the run through 92
days (7,948,800 seconds). The ticks count from the ledger's start (in a
sandbox, the start of the run), never from a push, and the policy has no
calendar dates: tell the user the date the window ends on depends on when the
run or the deployment starts, and record that in the hand-back's "What it
relies on". The `agent-payments` starter shows a window in a checked policy.

A window also ends every duty the agent still owes under that delegation
(`references/semantics.md` section 8): a booking on the last day owes a
receipt nobody can file. End the spending, not the paperwork: put the window
on the delegation for the spending action only, and give the paperwork its own
delegation with no window, or one that runs past the last deadline and its
follow-up. When a separate records agent files the paperwork (pattern 9), its
own delegation already does this.

## 13. More shapes in the starters

`axorum-sandbox new <starter> --dir <dir>` writes a checked policy and world.
Read them for these shapes:

| Starter | Shape |
|---|---|
| `agent-payments` | each vendor's own limit from the vendor list (`counterparty limit(payee)`), and a delegation that ends (`window`) |
| `daily-budget` | a rolling daily spend per agent |
| `purchase-rate-limit` | a pace limit read without `projected` |
| `spending-mandate` | an agent under a mandate, with no rule reading it |
| `purchase-receipts` | a receipt duty above an amount |
