# Trying a policy on the user's own examples

A policy that compiles can still say the wrong thing. The proof is the user's
examples, run through the real engine: each example becomes a case with the
outcome the user expects, and `try_cases.py` runs them in a throwaway
sandbox and reports which behaved as expected.

## Turning examples into cases

Ask for examples in the user's words, then write one case per example. A user
who has none, or cannot judge a boundary, gets a short table to react to:
propose examples from their own stories, each with the outcome the brief
predicts, and ask which to flip. Check every example against the brief before
drafting; one that contradicts it (a $1,400 flight under a $1,200 cap) goes
back to the brief first.

- **One per brief item at least**, and every case names its item in `brief`.
  `try_cases.py` lists the items in the policy header that no case covers, and
  refuses to run a policy whose header lists none.
- **The boundary on both sides.** For "at most $5,000": $5,000.00 allowed and
  $5,000.01 refused. Caps written with `projected(...) >` allow landing exactly
  on the cap.
- **Each refusal's reason.** `because` names the rule (or the code, for a
  mandate, or the cause, for a rejection), so a refusal for the wrong reason is
  a miss.
- **Each duty, met and missed.** One case opens it, one meets it, and an
  `advance` past the deadline shows a breach and its follow-up.
- **Order matters.** Cases run in sequence against one ledger, so spending
  accumulates: compute the running totals before writing the expectations,
  and say them in the case names ("leaving exactly $500").
- **One refusal at a time.** A case that trips two refusals at one priority is
  recorded under only one of them (`references/semantics.md` section 2), and a
  rule's refusal hides a budget's. Try each limit while the others are clear:
  a per-agent budget before the team total nears its reserve, a per-vendor cap
  on a vendor no other rule is near.

### Planning the timeline

Under several limits at once, lay the cases out before writing them:

1. List the limits with their figures and windows.
2. Put the boundary cases for each limit where nothing else is near its line,
   and advance the clock (`"advance": "2h"`) to empty a rolling window before
   the next limit's cases.
3. Every payment that opens a duty must be met by a later case or listed in a
   later `breached`, or the run reports it.
4. `repeat` sends the same intent, same payee, each time: a limit across
   vendors needs one case per vendor.

When the shared ledger makes a boundary impossible to reach (a reserve that
binds before a share can be filled), say so to the user and record which side
of that limit no case tries.

A rule about a currency the user's world does not pay in ("dollars only",
`references/patterns.md` pattern 5) can only be tried in a world that declares
that currency. Declaring it
for the test is fine: say so to the user, and say in the world file's comment
that the currency is there for the test, since a sandbox serving that world
accepts it.

## The cases file

From `examples/ap-vendor-payments/cases.json`:

```json
{
  "world": "world.yaml",
  "policy": "policy.axp",
  "agents": {
    "ap_bot": "agent://example.com/agent/ap_01h455vb4pex5vsknk084sn02q"
  },
  "cases": [
    {
      "case": "pay Northgate the $8,500 rent",
      "brief": "B3",
      "as": "ap_bot",
      "do": "purchase",
      "with": {
        "amount": "8500.00 USD",
        "payee": "northgate-properties"
      },
      "expect": "allowed",
      "because": "permit_payment",
      "duties": [
        "receipt_for_large_payment"
      ]
    },
    {
      "case": "pay Acme $3,000",
      "brief": "B6",
      "as": "ap_bot",
      "do": "purchase",
      "with": {
        "amount": "3000.00 USD",
        "payee": "acme-supplies"
      },
      "expect": "allowed",
      "because": "permit_payment",
      "duties": [
        "receipt_for_large_payment"
      ]
    },
    {
      "case": "file the receipt for the $3,000 Acme payment",
      "brief": "B6",
      "as": "ap_bot",
      "fulfills": "pay Acme $3,000",
      "legs": [
        {
          "debit": "acc_74kyk4x754bx0abqg32ccevf0q",
          "amount": "3000.00 USD"
        },
        {
          "credit": "acc_0jffxpndb9a2garx5fj166tc4c",
          "amount": "3000.00 USD"
        }
      ],
      "expect": "allowed",
      "because": "permit_receipt"
    },
    {
      "case": "a day and an hour pass with the rent receipt unfiled",
      "brief": "B6",
      "advance": "1d1h",
      "breached": [
        "pay Northgate the $8,500 rent"
      ]
    }
  ]
}
```

`world` and `policy` are relative to the cases file. `agents` maps each policy
agent name to the `agent://` URI the world binds to it.

### An intent

| Field | Means |
|---|---|
| `case` | A short name in the user's words; unique, since later cases refer to it. |
| `brief` | The brief item it tries (`B3`). |
| `as` | The agent, by its policy name. |
| `do` | The action. |
| `with` | Its parameters. `"120.00 USD"` is an amount at the world's exponent; `txn_...` a transaction; `party_...` a party; a JSON number an int; `true`/`false` a bool; any other string text. Money written as a person writes it (`"$6,000"`, `"6,000.00 USD"`) is an error, not text. |
| `fulfills` | Meets the duty the named case opened. The duty's action and captured parameters are filled in; `with` adds the rest. A list of case names meets the duty each opened, with one intent that carries the first duty's captured parameters: it is allowed when every listed duty's captures agree with those (none captured, or two $600.00 purchases under an amount-only capture), and `rejected` with `invalid_fulfillment` when one differs, as a captured `trigger_transaction` always does (`references/semantics.md` section 3). Every listed duty must owe the same action. For a follow-up a breach opened, name the case that opened the first duty and put the follow-up's action in `do`. |
| `legs` | `"payment"` (default: debit spend, credit payables, for the first amount parameter), `"memo"` (debit and credit spend: moves nothing between accounts and charges no mandate, for paperwork such as a report that a receipt is missing), or a list of `{"debit": "acc_...", "amount": "10.00 USD"}` and `{"credit": ...}`, as a receipt that moves the payment into receipted expenses does. Before giving paperwork of an agent bound to a mandate any legs, read `semantics.md` section 11. |
| `expect` | `allowed`, `refused` (judged and recorded) or `rejected` (never recorded: turned away before judgment, or after the policy allowed it, as `invalid_fulfillment` is; `try_cases.py` prints which). |
| `because` | The deciding rule's name; for a budget refusal, the budget's name (`travel_mandate`); or a code: a refusal code (`mandate_exceeded`, `denied_by_default`, `not_delegated`, ...) or a rejection (`substrate_rejected`, `invalid_fulfillment`, `attestation`, ...), all in `references/diagnostics.md`. A refusal recorded under a code prints it with the rule or budget beside it: `refused by not_delegated (permit_spend)`, `refused by mandate_exceeded (ads_mandate)`; either name matches. A `substrate_rejected` rejection prints the engine's cause beside it: `rejected before judgment (substrate_rejected, cause unknown_counterparty)`; either matches, and the cause is the one that pins why. Optional, but always give it, and prefer the rule, budget or cause. |
| `duties` | The rules whose duties this intent opens, by name. Omitted means none. A duty broken as it opens (a `by(t)` deadline the run has already passed) is named by the action it owes instead, `"file_receipt (breached when opened)"`: no report names the rule that opened it, and no `advance` lists it as breached, since the exceptions report does not list it. Its `on_violation` follow-up opens with it, under its rule's name, and a later case meets it with `fulfills` naming this case and the follow-up's action in `do`. |
| `repeat` | Submit it this many times; every one must behave as expected. |

### A move of the clock

| Field | Means |
|---|---|
| `advance` | How far: `30s`, `2h`, `1d1h`, `1w`. |
| `breached` | The cases whose duties this breaches, by case name; a missed follow-up as the case that opened the first duty and the follow-up's action, `"pay Acme $3,000 (missing_invoice_note)"`. Omitted means none. |
| `follow_ups` | The actions the breaches oblige next (each `on_violation` duty). |

## Running them

```bash
python <skill-dir>/scripts/try_cases.py cases.json                     # the policy it names
python <skill-dir>/scripts/try_cases.py cases.json --policy draft.axp  # another draft
```

```text
ok     1  B1   pay Acme $120 for supplies: allowed by permit_payment
ok     2  B2   pay Shady LLC, on the list but not approved: refused by vendor_must_be_approved
ok     3  B2   pay a vendor the list has never heard of: rejected before judgment (substrate_rejected, cause unknown_counterparty)
MISS   4  B3   pay Acme $6,000 in one payment
                expected  allowed by permit_payment
                actual    refused by single_payment_cap
...
15 of 16 cases behaved as expected.
```

Here the user expected the $6,000 payment to go through, and B3 refuses it:
the case and the brief disagree, so ask which one is right.

Exit 0 means every case behaved as expected and every brief item has a case;
1 means a miss or an uncovered item; 2 means the cases could not run (the
message says why: a missing package, a policy whose header lists no brief
items, a bad case, a world the sandbox refuses). `--json` prints the same as
one JSON document. With no brief items it runs nothing and shows the header
to write: a `// Brief, and the rules that carry it out:` line, then one
`//   B1  <the control in the user's words>  <rules>` line per control.

Each run starts a fresh sandbox on a free port and stops it afterwards; the
user's own sandbox is never touched. `references/diagnostics.md` says how to
decide whether a miss is the policy's, the case's or the world's fault.

Show the user the table, not just the count. When the cases are many, show
the user's own examples as the table and sum up the rest in one line ("and 40
more steps: the clock moving and the receipts filed on time, all as
expected"). For a miss, say in one sentence what the policy did and what they
expected, and ask which is right before changing anything.

## Replaying saved runs

When the user has a sandbox run worth keeping (an agent's real session, saved
with `axorum-sandbox save-run`), `replay.py` replays it under a draft
and names every recorded step the draft decides differently:

```bash
python <skill-dir>/scripts/replay.py --policy policy.axp runs/*.yaml   # saved runs
python <skill-dir>/scripts/replay.py --policy policy.axp --url http://127.0.0.1:7340
```

With `--url` it first saves the run so far of that sandbox (to `--save`, or a
file beside the policy), then replays it. A saved run carries the policy it
was recorded under, so `axorum-sandbox run` without `--policy` only plays the
recording back: to try a draft, always name it with `--policy`, as `replay.py`
does. The draft stays in force for the whole replay, standing in for every
policy change the run made (a push, or a `policy` event of the world), as the
replay's first line says; each change it stood in for is named under its run.
Each submission is held to its recorded decision: the answer, the deciding
rule, the refusing mandate, and the duties opened, met and breached; an `end of
run` line names a duty the draft's run ends with otherwise than the recording
did. A submission the run recorded refused `stale_policy` goes out with its old
pin and is refused again, except when that pin is the draft itself: under the
draft the agent would never have sent it, so it is listed as `not sent`, with
its reason, and counts neither way. A run that records no submission tries
nothing, and `replay.py` says so.

Exit 0 means no recorded decision changed; 1 means one did, and the output
names the step and what changed; 2 means nothing was replayed: the draft does
not compile (run `check.py` and fix it first), a run could not be loaded or
saved, or a run saved by an older sandbox names its policy file instead of
carrying it (ask the user to save it again).

The AP example's cases, run in a sandbox and saved, then replayed under a
draft that lets the agent make 11 payments an hour instead of 10 (each changed
step also prints its recorded and replayed outcomes as JSON, cut here):

```text
trying the proposed policy draft.axp: in force from each run's start to its end, standing in for every policy change
FAIL  run.yaml: 1 submission(s) answered differently (28 of 28 held to their decisions: the policy in force is not the one they were recorded under)
      step 30 at 1d3h: recorded forbidden_rejected (not posted), replayed permitted (posted), held to its decision
        no longer refused as forbidden_by_rule
        decided by rule hourly_pace, now by rule permit_payment
...
1 scenario(s): 0 matched, 1 diverged, 0 could not be loaded
```

A changed step is not a failure by itself: it is what the revision does to
real traffic. Read each one to the user ("the $6,000 payment to Acme on day 2
was allowed and would now be refused by single_payment_cap") and ask whether
that is intended. `try_cases.py` remains the loop for drafting; replay answers
"what would this change have done to what already happened".

## Putting it in force

Only after the user has confirmed the read-back and the cases pass, and only
when they ask for it. Look first, then push:

```bash
python <skill-dir>/scripts/push.py policy.axp --dry-run   # $AXORUM_SANDBOX_URL, else http://127.0.0.1:7340
python <skill-dir>/scripts/push.py policy.axp --url http://127.0.0.1:7341
```

`push.py` first checks the policy against the world the user's sandbox is
running: its run so far, as `axorum-sandbox save-run` writes it, not the world
file on disk, with every warning counted as an error. A policy that does not
compile or draws a lint is refused as the policy's to fix; one that draws only
world-fit warnings (`DSL3xxx`) is refused as not fitting the running world. It
then says what the change does to each running total. The engine keeps a total
whose declaration is unchanged and starts a changed one at zero, so `push.py`
compares the declarations of the policy in force and of the draft, as the
engine stores them:

```text
Running totals, if this policy goes in force:
  keep their figures: paid_per_vendor
  start again at zero, their declaration changed: payments_last_hour
```

With `--dry-run` it stops there. Read those lines to the user. A total that
starts again at zero gives the agent its full allowance back ("the hourly count
starts from zero, so ten more payments are possible this hour"): ask before
pushing when one does. Without `--dry-run`, it puts the policy in force with
`axorum-sandbox policy` and passes on what that prints: the id of the policy in
force on stdout and, on stderr, what changed and at what point of the run:

```text
pol_5azg...
the policy in force changed from pol_3j9g... to pol_5azg... at 1d (2100-01-02T00:00:00Z)
```

- Every agent's next intent is judged by the new policy. An agent pinned to
  the old one is refused `409 stale_policy` once; the Axorum SDKs re-pin and
  send again on their own, and an agent on another client must do the same.
- Duties already open stay open under the policy that opened them, deadlines
  and follow-ups included, even when the new one drops their rule. The
  paperwork that meets them is judged by the new policy: drop its permit and
  each receipt still owed is refused and its duty breached. Say so before a
  push that removes a duty or its permit.
- The policy already in force (the same content: comments and layout do not
  count) changes nothing and stales no pin. It still exits 0, with that id on
  stdout and `pol_5azg... is already the policy in force: nothing changed at
  1d (...)` on stderr.
- Every push that reaches the sandbox is a step of the user's run, a refused or
  unchanged one too, so a run saved later replays it.
- `1d` is how far the run has gone. The sandbox's clock starts every run at
  2100-01-01T00:00:00Z: that is not a date the user will see in production,
  and the policy itself has no calendar. Tell the user "one day into the run",
  not the date.

| Exit | Means | Tell the user |
|---|---|---|
| 0 | In force (with `--dry-run`: it would be taken). Also when `axorum-sandbox policy` did not finish but the sandbox's snapshot then names this policy in force: `push.py` says `in force: ...` and prints its id. | What changed, which totals start again. |
| 3 | Nothing changed. The policy does not compile or draws a lint ("this policy does not compile", "this policy draws DSL2004"); the running world cannot run it ("runs a world this policy does not fit (DSL3003)": it names an agent, a budget, an account or a currency that world lacks); or the sandbox refused it, quoted as `the sandbox refused the policy (<code>): <reason>; nothing changed`, with nothing on stdout. | For the policy's own error or lint, fix it and push again. For a world that does not fit, fix the policy where a warning's help says how; a new agent, budget, account or currency needs their sandbox restarted with the new world, which starts a new run. |
| 2 | The policy is not in force. Before anything was sent: the running sandbox's run could not be saved (`could not save the run of the sandbox at ...`, most often because no sandbox answered at the address), or the installed `axorum-sandbox` cannot check the policy, read the running world (it refuses even the policy in force against it, so it is older than the sandbox), or push a policy. After `axorum-sandbox policy` could not finish (no answer within 30 seconds, a dropped connection, an answer it cannot read), the sandbox may already have taken the policy, so `push.py` reads which policy the sandbox's snapshot names in force: `not in force: nothing changed` (the policy in force before still is; a sandbox older than the installed `axorum-sandbox` cannot take a policy while it runs), or `could not tell whether this policy is in force: check the sandbox` (no snapshot, or one naming a third policy). The reason is quoted above `push.py`'s line. | Ask them to start theirs (`axorum-sandbox serve world.yaml`) or to upgrade (`pip install -U axorum-sandbox`); an older running sandbox takes the policy only once they restart it with a newer one, which starts a new run. When `push.py` could not tell, check the sandbox before pushing again: its snapshot names the policy in force. Never start, stop or restart their sandbox. |

## Publishing to the console's library

Only when the user asks for it, after the read-back is confirmed and the cases
pass. Publishing goes through a sandbox connected to the console: the user
sets `AXORUM_SANDBOX_SINK` (the console's address) and `AXORUM_SANDBOX_TOKEN`
(their sandbox's secret, from the console) in their own shell. Never ask for
the token, and never print it.

Which way depends on where the user's world came from. Never copy the policy
to another name to publish it: the user then edits one copy and publishes the
other.

### The world came from the console

`axorum-sandbox pull --output world.yaml` writes the world attached to their
sandbox and, beside it, the policy file it names, under its name in the
library (`serve` with no world file fetches the same two but writes nothing,
so pull them to work on them). Work on that file for the whole session: the
cases' `policy`, `try_cases.py`, `replay.py` and `push.py` all name it, and
the publish sends that same file. `pull` also writes `.axorum-pulled.json`
beside them, what it pulled, and the publish writes only over that: keep it
with the files.

```bash
python <skill-dir>/scripts/publish.py ap_payments.axp --dry-run
python <skill-dir>/scripts/publish.py ap_payments.axp
```

- The file's whole name, `.axp` included, must be the policy's name in the
  library exactly (`ap_payments.axp`), as a pulled world's policy file
  already is; a path to it is fine. Another name is refused, and the refusal
  names the right one.
- It checks the policy alone first, then against the world attached to their
  sandbox in the console (not the world file on disk), with every warning
  counted as an error. A failing check sends nothing.
- With `--dry-run` it publishes nothing and prints one line, such as
  `policy ap_payments.axp (policy_01...): would be updated`, or `unchanged`
  when the library already has this text. Read it to the user.
- Before publishing for real, tell the user three things. The library's copy
  is shared: every world that names it runs the new text from its next
  start, not only theirs. A publish writes only over the text they pulled:
  when someone saved the policy in the console since, it is refused and
  writes nothing. And the library keeps no earlier version or diff.
- A publish changes the library's copy and nothing else. A running sandbox
  keeps the policy in force until a push changes it: to change a running
  one, push as well. `axorum-sandbox serve` started with no world
  file starts on the published text. Runs already recorded keep the policy
  they ran under.

| Exit | Means | Tell the user |
|---|---|---|
| 0 | Published, or with `--dry-run` publishable. The line ends `updated`, `unchanged` or `would be updated`. | Which. After a real update: the library's copy changed, and a running sandbox did not; push as well to change a running one. |
| 3 | Nothing was written: `publish policy` makes one write, and a refusal of it ends `; nothing was written`. The check failed, the file's name is not the library's name for the policy, the attached world writes its policy inline or there is none, someone saved the policy in the console since the pull (`the policy ap_payments.axp changed in the console since you pulled`), and a publish never writes over that save, the file's directory holds no pull of the policy (`this directory holds no pull of the policy ap_payments.axp`), or the console refused the write, among them one it cannot check against the revision it gave (`the console cannot check the write of the policy ap_payments.axp against the revision this publish read, and refused it`). The `axorum-sandbox:` line says why and the `fix:` line what to do. | The reason and its fix. A check finding is fixed by its code (`references/diagnostics.md`), then publish again; a wrong name, by publishing the file the world names. A policy changed in the console since the pull: pull again into another directory (`axorum-sandbox pull --output <dir>/world.yaml`), carry the user's changes into the policy it writes, and publish that file; `--replace` would discard that save, so never reach for it here. A policy never pulled: pull first, the same way, or, only when the user has said to overwrite the console's version, publish again with `--replace`. A write the console cannot check: publish again, and if it refuses the same way, tell an owner of the console. |
| 2 | It could not publish, or did not finish. Nothing was published when a variable is not set, the console's address is plain `http://` to another machine, the console answered a redirect before the write (a redirect is never followed: set `AXORUM_SANDBOX_SINK` to the console's own origin), the console refused the secret, or the installed `axorum-sandbox` cannot publish a policy. When the console stopped answering (a write waits up to 30 seconds) or answered the write with an error or a redirect, it may have stopped at the write with the new text already in the library; `publish.py` says which of the two it was. | Ask them to set the variables in their own shell, as the console's sandbox page shows, to issue the sandbox a new secret in the console when it refused this one, or to upgrade (`pip install -U axorum-sandbox`). When the console stopped answering, ask them to check their connection, then publish the same file again: it ends `updated`, or `unchanged` when the text had landed. |

### The user started locally

When the user wrote `policy.axp` beside a world of their own and wants it in
the library, publish the world, not the policy, looking first. Their
directory holds no pull, so the publish passes `--replace`, which overwrites
the console's version of the world with this file. Pass --replace only when
the user has said to overwrite the console's version.

```bash
axorum-sandbox publish world world.yaml --replace --dry-run
axorum-sandbox publish world world.yaml --replace
```

With `--dry-run`, `--replace` names on stderr each record it would replace,
its current name in the console and the size of its text and of the file's,
such as `with --replace, this publish would replace the world clerk
(world_01...) as the console holds it now, 40 lines (1210 bytes), with
world.yaml, 52 lines (1630 bytes)`. Read it to the user before the real
publish. A save made in the console while the publish runs is still refused,
exit 3 (`the world clerk changed in the console while this publish wrote
it`): look again before publishing again.

It overwrites the world their console sandbox is attached to, its content
and its name, with this file and the name its `world:` line gives (a name
free in their organization, or already that world's). Which world a sandbox
is attached to is set by an owner in the console and never changes from the
command line. It also saves the policy file the world names to the library
under the file's whole name: created when the library has no policy of that
name, updated when it is the attached world's own policy or one this sandbox
created. Any other library policy of that name is refused (exit 3), whatever
its text, and so is one this sandbox created once a person has edited it in
the console; nothing is written. The fix is to rename the policy (the file
and the world's `policy` line that names it, as below), or to ask an owner to
attach that policy to the world in the console.

So a file still named `policy.axp` would go into the library as
`policy.axp`, a name another sandbox may hold. Ask the user what to call it
first, then rename the file and every place that names it (the world's
`policy`, the cases' `policy`) in one step, and check again.

It prints a line for the world and one for its policy, such as
`world clerk (world_01...): updated` and `policy ap.axp (policy_01...): created`
(`would be ...` with `--dry-run`); exit 0 means both landed. Exits 3 and 2
differ from `publish policy`'s, because it makes two writes, the policy first
and then the world, so a stop can come after the policy is in the library:

| Exit | Means | Tell the user |
|---|---|---|
| 3 | Refused, and only one refusal leaves something written: a refusal of the world after the policy's save, which ends `; the policy ap.axp was created, but the world clerk was not written` (or `updated`), so the library already has the new policy text. Any other refusal wrote nothing: the check, a name another record holds, or a write the console refused that ends `; nothing was written`. | What landed, read from that line (with `--json`: `sent`, and the policy's `change`, `null` unless the console confirmed the save). Then do what the `fix:` line says and publish the world again. |
| 2 | It could not publish, or did not finish. Before any write, as for `publish policy`. After one, the line names the save the console did not confirm (with `--json`: `unconfirmed`, `policy` or `world`), which may already be saved, and anything it confirmed before it. | Once the cause is fixed, run the same publish again: it finishes what was not saved, and ends `unchanged` for what had landed. |

Before publishing for real, tell the user the same three things, and a
fourth: every sandbox attached to that world sees the change, and `serve`
with no world file then starts on the published copy.
