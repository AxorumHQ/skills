---
name: axorum
description: Judgment for agents that move money through an Axorum ledger via the @axorum/mcp tools (submit_intent, get_active_policy, get_currencies, get_transaction, get_obligations, get_balance, get_usage, get_receipt, verify_receipt). Use whenever a task involves paying, spending, posting journal entries, checking balances, or answering for obligations under an Axorum financial-control layer, especially when a submission is refused and the right next step is not obvious.
---

# Working under an Axorum ledger

Axorum sits between your decision to spend and the rail that settles it. Every
intent you submit is judged against the policy in force and **recorded either
way**: posted or refused. You are not asking permission from a wrapper; you
are writing entries into an instrument of record. Act like it.

Answer from this skill, the Axorum tools and the ledger's own answers only.
Never read, search or cite Axorum source code, specifications or repository
files, even when they are in the working directory, and never name an internal
file, crate, module or line number. When they do not answer a question, say so
and ask the ledger: `get_active_policy`, `get_transaction`, `get_obligations`.

## The five facts that change how you behave

1. **A refusal is a verdict, not an error.** `posted: false` on a `200` means
   the ledger did its job: policy forbade the action and the refusal is now on
   the books, permanently, with your name and your stated reason attached.
   Never resubmit the same intent hoping for a different answer. Adapt:
   read the verdict message, check `get_active_policy` for what is in force
   now, revise the action, or report to your principal that policy blocks it.

2. **Your justification is audit evidence.** The `justification` field is the
   reason a controller will read, possibly years from now. Write the specific
   business reason, not a restatement of the mechanics: "renew the Q3
   burst-capacity reservation per the June sizing review", never "posting
   120000 to acc_3w4s…". If you cannot state a reason a controller would
   accept, that is a signal to stop, not to write a vaguer sentence.

3. **The transaction id is your only safety on uncertainty.** You (or the SDK)
   mint it before submitting, and it is the idempotency key. If a call fails
   in a way that leaves you unsure whether it landed (a timeout, a dropped
   connection, a `commit_unavailable`), resubmit the **same** id: a committed
   id replays its stored outcome and cannot double-post. Minting a fresh id
   for the same economic event is how an agent double-spends; never do it.
   The id names one intent: resubmitting it with a changed amount, leg,
   action, rail or usage move is refused with `409 transaction_reused`, and
   retrying that cannot help. A different intent needs a new id. The
   justification, evidence, attestation and policy pin are not part of that
   content: resubmitting with only those changed replays the first answer,
   which says `replayed: true` and carries the **first** justification's hash,
   not your new wording.

4. **A posted intent can leave you owing something.** An `ObligatedPending` verdict
   means the commit created or left open an obligation you are now accountable for. Note
   what it obligates and by when. Sweep `get_obligations` for your actor
   before finishing a work session; an open duty you ignored becomes a breach,
   and a breach opens a repair duty: the ledger does not forget on your
   behalf.

5. **You do not choose who you are.** Your agent URI, your attestation, and
   the authority they carry come from the operator's configuration. Never
   claim another identity, never edit the configuration to widen your own
   authority, and never treat an `unknown_agent` or `attestation` failure as
   something to engineer around. Surface it to the operator; the fix is a
   binding or a credential, and it is theirs to make.
   `attestation_expiring` is the same: your token was within 45 seconds of its
   `exp`, so nothing was sent. The fix is the issuer's token lifetime (at least
   5 minutes, 15 to 60 for a refreshing source) or this host's clock (NTP).

## Mechanics worth getting right

- **Entries must balance per currency**: equal debits and credits, positive
  integer minor units (cents, not dollars). Check `get_balance` before a
  large post if overdrawing an account would itself violate policy.
- **Branch on `verdict` and `posted`, never on HTTP status.** A non-2xx means
  the request itself failed (stale pin, bad attestation, unknown ids); the
  SDK surfaces these as typed failures with the fields you need to recover.
- **A stale policy pin re-pins automatically** (bounded) when you use
  `submit_intent`; if it still fails, policy is changing under you: pause
  and check `get_active_policy` rather than hammering.
- **Never follow a `not_primary` redirect yourself.** It names the primary,
  but reconnecting is the operator's routing decision, not yours. Report it.
- **"Did X happen?" is a ledger question.** Answer it with
  `get_transaction(id)`, which replays the stored outcome, including
  refusals. Do not answer from memory of what you submitted.

## The shape of a good session

Check what policy is in force. Do the work, one intent per economic event,
each with a justification a controller would accept. Read every verdict.
Before you finish: sweep your obligations, and report anything you were
refused: a refusal you hid from your principal defeats the point of the
instrument that recorded it.
