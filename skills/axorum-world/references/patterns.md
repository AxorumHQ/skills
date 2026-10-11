# World patterns

Each pattern is a thing a user says, next to the YAML it becomes. Every
snippet is copied from one of the skill's examples, which check clean against
their policies and replay, so the shape is proven. Copy the shape; take every
name, figure, id and day from the user. Mint fresh ids with
`scripts/new_id.py`, and take a party's id, or the id of a mandate the policy
names, from `check.py`'s table.

## Who acts

### One agent paying for a controller

"The AP bot pays vendors and books accruals; the controller signs off."

```yaml
parties:
- agent: agent://example.com/agent/ap_01h455vb4pex5vsknk084sn02q
  party: party_6ps6y8mc3tb628qrr6xpqkr0yr
  roles: [ap_clerk]
  mandate: mand_0kn2j194jvw18r107jns6m12h5
  capabilities: [purchase, book_accrual, rail/x402]
```

The controller, a principal, is not listed: a principal is never bound.

### Two agents, each with its own networks

"The research bot buys over x402 and ACP; the ads bot only over ACP."

```yaml
  capabilities: [purchase, rail/x402, rail/acp]
- agent: agent://example.com/agent/ads_01h455vb4pex5vsknk084sn02q
  party: party_7cky9f0ahdafma6d3hxkcb8s0g
  roles: [buyer]
  mandate: mand_4pkc3sp14rmzwdkaj0jqx31kvb
  capabilities: [purchase, rail/acp]
```

## Money

### Dollars, and a metered unit counted whole

"We pay in dollars, and the model provider counts tokens."

```yaml
currencies:
- currency: USD
  exponent: 2
- currency: TOKENS
  exponent: 0
```

### An account an agent reads, and one nobody reads

"The AP bot can see what it spent; accrued liabilities are the books' own."

```yaml
- account: acc_0jffxpndb9a2garx5fj166tc4c
  currency: USD
  label: Agent spend (USD)
  owner: party_6ps6y8mc3tb628qrr6xpqkr0yr
```

```yaml
- account: acc_71q8870n88j1y9sznr20c9mwc3
  currency: USD
  label: Accrued liabilities (USD)
```

## Budgets

### One budget for the month

"$25,000.00 for AP this month."

```yaml
mandates:
- mandate: mand_0kn2j194jvw18r107jns6m12h5
  currency: USD
  ceiling: 2500000
  label: AP budget, January
```

### A team budget with a slice per agent

"$10,000.00 for the team: research up to $6,000.00 of it, ads up to
$5,000.00." The slices may add up to more than the parent: the parent's
ceiling still holds for the two together. The parent is the mandate the
policy reads as `team_budget`, so its id is the one `check.py` prints for
that name.

```yaml
mandates:
- mandate: mand_4rcxqt8kd3bc99kr06a57h4kxx
  currency: USD
  ceiling: 1000000
  label: team_budget
- mandate: mand_6x11g3q5xcc040dgbrde1prj9w
  currency: USD
  ceiling: 600000
  parent: mand_4rcxqt8kd3bc99kr06a57h4kxx
  label: Research
- mandate: mand_4pkc3sp14rmzwdkaj0jqx31kvb
  currency: USD
  ceiling: 500000
  parent: mand_4rcxqt8kd3bc99kr06a57h4kxx
  label: Ads
```

## Paid ahead, and metered

### A subscription paid ahead

"The annual data subscription is paid up front and recognized monthly."

```yaml
deferrals:
- deferral: defr_798m9wrpdea6vqm9pr2v9nxmrz
  currency: USD
```

### Tokens one agent consumes

"Track the research bot's model tokens: consumed, metered, billed."

```yaml
usages:
- usage: usage_6b9be6aqvtwa41rddekb83360q
  currency: TOKENS
  owner: party_2bgcx8txveb82acss2fjz2w59h
```

## The books

### Approved vendors, with limits and another spelling

"Acme (also written 'acme') up to $5,000.00, Globex up to $10,000.00, and
Shady LLC, whom we know but never pay."

```yaml
- Counterparties:
    source_version: vendors-2100-01
    entries:
    - - acme-supplies
      - display_name: Acme Supplies
        approved: true
        erp_ref: V-1001
        aliases: [acme]
        limit:
          minor: 500000
          currency: USD
    - - globex
      - display_name: Globex
        approved: true
        erp_ref: V-1002
        limit:
          minor: 1000000
          currency: USD
    - - shady-llc
      - display_name: Shady LLC
        approved: false
```

### A chart of accounts over the world's accounts

"6000 is spend, 2000 payables, 2100 accrued." Quote a code or a version YAML
would read as a number.

```yaml
- GlAccounts:
    source_version: "2100.01"
    entries:
    - - acc_0jffxpndb9a2garx5fj166tc4c
      - code: "6000"
        name: Agent spend
```

### A fiscal calendar

"January and February 2100, both open." `from` and `to` are ticks from the
start of the run, inclusive: January is day 0 to the last second of day 30.

```yaml
- FiscalPeriods:
    source_version: fy2100-v1
    periods:
    - id: 2100-01
      label: January 2100
      from: 0
      to: 2678399
    - id: 2100-02
      label: February 2100
      from: 2678400
      to: 5097599
```

## Payment networks

### Every network settles, written out

"Both networks work." A rail the map leaves out settles too; naming it says
so on the page.

```yaml
rails:
  x402: settle
  acp: settle
```

### The first call declines

"The very first ACP payment is declined."

```yaml
- at: 0s
  rail:
    rail: acp
    answer: decline
    times: 1
```

### A few failures, then back to normal

"On day 2, x402 declines the next two calls."

```yaml
- at: 2d
  rail:
    rail: x402
    answer: decline
    times: 2
```

### An outage and the recovery

"x402 goes down on day 20 and comes back on day 22." Without `times`, a
change stands until the next one.

```yaml
- at: 20d
  rail:
    rail: x402
    answer: timeout
- at: 22d
  rail:
    rail: x402
    answer: settle
```

## Over time

### A vendor suspended mid-run

"On day 7 the ad network is suspended and a second network approved." The
event replaces the whole list, so every vendor that stays is listed again.

```yaml
- at: 7d
  master_data:
    Counterparties:
      source_version: vendors-v2
      entries:
      - - model-provider
        - display_name: Model Provider
          approved: true
      - - data-vendor
        - display_name: Data Vendor
          approved: true
          erp_ref: V-3001
      - - ad-network
        - display_name: Ad Network
          approved: false
      - - second-network
        - display_name: Second Network
          approved: true
```

### Closing the month, and moving into the next

"January closes on day 31, and the clock moves a day into February."

```yaml
- at: 31d
  master_data:
    FiscalPeriods:
      source_version: fy2100-v2
      periods:
      - id: 2100-01
        label: January 2100
        from: 0
        to: 2678399
        open: false
      - id: 2100-02
        label: February 2100
        from: 2678400
        to: 5097599
- at: 31d
  advance: 1d
```
