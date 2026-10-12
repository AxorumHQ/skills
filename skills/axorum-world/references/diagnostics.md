# When a world is refused

Six steps can refuse a world, and each says where:

| Step | Script | Refuses | Exit |
|---|---|---|---|
| Reading the world | `check.py`, `run.py` | YAML the format does not define, and a world that does not hold together | 3 |
| Judging the policy against it | `check.py` | the world's own policy, when the world cannot run it as written (`DSL3xxx`) or it does not compile, and each `policy` change on the timeline the world cannot run | 3 |
| Loading it into the engine | `run.py` | a mandate, calendar or counterparty list the ledger refuses, or a policy change on the timeline that does not compile | 3 |
| Playing the timeline | `run.py` | an event the engine refuses, one applied at start included; the run goes on without it | 3 |
| Replaying a scenario | `axorum-sandbox run` | a script step that does not replay as recorded, such as an injected advance the sandbox refuses as it plays, which no live run saves | 1 |
| Publishing | `publish.py` | a world the check refuses, warnings included, and a write the console refuses | 3 |

Fix the first refusal first: a world that cannot be read is never judged or
loaded. Read the message to the user in their words, say which answer of the
interview it touches, propose the fix, and run the loop again. Never weaken
the world (drop a vendor, an event, a capability) to silence a refusal
without asking.

`check.py` judges the world's own policy with every lint, and each `policy`
change on the timeline as the engine makes it: compiled against the world,
never linted, so a lint warning on a change's policy refuses nothing
("Policy changes in the timeline"). `run.py` meets the same problems later:
a change that does not compile, or names a file that cannot be read, stops
the load; one that names a currency the world does not declare (`DSL3001`),
or caps a mandate in another currency than the world opens it in
(`DSL3004`), is refused when the clock reaches it.

## Reading the world

The message names the line and column, then the problem. The format's rules
are in `grammar.md`, under "Reading the format" and "What the world check
refuses".

| The message says | It means | Fix |
|---|---|---|
| ``unknown field `colour`, expected one of ...`` | a key the format does not define, often a typo or a key one level off | use one of the keys the message lists, at the level `grammar.md` shows it |
| ``missing field `periods` `` | a required key is absent; each kind of master data has its own (`entries` for counterparties and the chart, `periods` for the calendar) | add the key the message names |
| `is not a valid AccountId TypeID (prefix 'acc')` | an id that is not 26 characters of base32 after its prefix | mint one with `new_id.py`; a party's id comes from `check.py` |
| `invalid i128` | an amount written as a decimal or with separators | write whole minor units: $10,000.00 at exponent 2 is `1000000` |
| ``an anchor (`&name`): a world refuses anchors and aliases, so write each value out in full`` | a YAML anchor, often set to reuse a vendor's record or an amount | write each value out in full where it is used, with no `&name` |
| ``an alias (`*name`): a world refuses anchors and aliases, so write each value out in full`` | a YAML alias, a value starting with `*`, with no anchor before it | write out in full the value it stands for, or quote a value that starts with `*` |
| `invalid boolean (true or false expected)` | `yes`, `no`, `on` or `off` | write `true` or `false` |
| `currency code contains illegal character` | a code with a lowercase letter, a digit or a symbol | `USD`, `TOKENS`, `CREDITS` |
| `currency code must be 3 to 8 letters, got ...` | a code shorter than 3 letters or longer than 8 | `USD`, `TOKENS`, `CREDITS` |
| `is not a sandbox time span` | a span such as `14days` or `2 d` | `14d`, `1d12h`, `90s`: count then unit, largest unit first |
| ``unknown variant `slow`, expected one of settle, decline, timeout`` | a rail answer that does not exist | a slow or failing network is `timeout` |
| `expected a nonzero u32` | `times: 0` | `times` is 1 or more; leave it out for a change that stands |
| ``is in EUR, which `currencies` does not declare`` | an account, mandate, deferral or usage balance in an undeclared currency | declare the currency, or correct the entry's |
| `is opened twice` | one id used for two entries | mint a fresh id for one of them |
| ``names mandate ..., which no earlier `mandates` entry opens`` | a child mandate or a party names a mandate not opened above it | list the parent first, or correct the id |
| `is not an agent URI` | an agent written as a URL or a name, or a label with a digit or `-`, or one that starts or ends with `_` (`ap2_...`, `ap-clerk_...`, `_ap_...`) | `agent://<host>/<path>/<label>_<suffix>`, the label lowercase letters and `_`, starting and ending with a letter: `aptwo_...` |
| `has no capabilities, so its tokens admit nothing` | `capabilities: []` | list what the policy delegates, or leave the key out to admit everything |
| `event 3 is at 1d, before the event above it at 5d` | the third entry of `events` comes before the one above it (a script step is counted the same way, from one) | list events and steps in time order |
| `event 5 is at 365300d, after the clock's last second at 365250d` | an event or script step later than the clock runs, a thousand years of 365.25 days, so it would never happen | bring its `at` to `365250d` or earlier |
| `script step 1 advances to 365301d, past the clock's last second at 365250d` | a scenario's script injects an `advance` that carries the clock from the step's `at` past its last second; a live run refuses that move and saves no such step, so the script was edited by hand | save the run again instead of editing its script; for a step meant to stay, shorten the advance so its `at` plus the advance is `365250d` or earlier |
| `a master-data entry takes ... bytes as a snapshot writes it, over the 4096 one may take: ...` | one counterparty, chart entry or fiscal period, named at the end, whose record, its id and every field as JSON, is over 4,096 bytes, often a long alias list or a name past ASCII, at two to four bytes a character | shorten that record: fewer or shorter aliases, a shorter display name or label |
| `event 7 changes the policy to an empty source` | a `policy` change on the timeline with no policy text, often a `source:` left blank | write the policy's text under `source`, or name its file beside the world with `file:` |

## Policy against the world

`check.py` judges the policy against the world before anything runs, and
prints the id each mandate and party the policy names must be opened under.
These codes are this skill's to fix, in the world, unless the fix below or
the user says the policy is what is wrong; then the axorum-policy skill
takes it.

| Code | Means | Fix in the world |
|---|---|---|
| `DSL3001` | the policy names a currency the world does not declare; an error | declare it in `currencies`, or ask whether the policy's currency is wrong |
| `DSL3002` | a currency the world declares can never pay on some action, because a running total over that action sums another currency | confirm the currency is meant for that action; otherwise the policy needs a total per currency (axorum-policy) |
| `DSL3003` | the policy reads a mandate the world does not open under the id its name derives, so every term over it reads 0 | open the mandate under the id `check.py` prints for that name |
| `DSL3004` | the policy caps a mandate in another currency than the world opens it in; an error | open the mandate in the cap's currency, or ask whether the cap is wrong |
| `DSL3005` | an agent party the policy declares has no world agent bound to it, so nothing acts as it | bind an agent with `party:` the id `check.py` prints for that name |
| `DSL3006` | a world agent is bound to a party the policy does not declare as an agent, so every intent it submits is refused | bind it under the id of the policy's agent; keep it only when the world means to show that agent refused |
| `DSL3007` | a world agent is bound in roles other than exactly the ones the policy gives its party: without one of them, with a declared role the party does not hold, or with one the policy does not declare | write the `roles: [...]` line the message prints |
| `DSL3008` | a world agent's `capabilities` leave out an action the policy delegates to it, so the gateway turns that action away | add the action to `capabilities`: the message prints the line |
| `DSL3009` | ``rule `stop_bot` names `specific(buyer_bto)`, a party the policy does not declare and no agent in the world acts as, so the rule applies to no intent in the world`` (for a duty's `performed_by`: ``so no intent in the world discharges the duty``): the name matches no party the policy declares and no world agent is bound to it | most often a misspelling, which is the policy's to fix (axorum-policy): the help names the closest party, ``did you mean `buyer_bot`?``. When the world is meant to have that party, the policy declares it as an agent party and the world binds an agent to it with `party:` the id `check.py` prints |
| `DSL3010` | ``the policy takes 600123 of the 524288 characters a policy may take of a run's snapshot (...)``, or of the 1048576 bytes it may take as the sandbox sends it: a run's snapshot carries the policy's rule table, its document and its parties, and a policy may take half of what a run may, in characters and in bytes; an error | nothing in the world: the policy is too large, which is the policy's to fix (axorum-policy): cut rules, or shorten their names, conditions and text values. Each refusal writes the refusing rule's paragraph again, twice in each of the run's activity and exceptions reports, so a long text value costs again at every refusal |

Every other code (`DSL0xxx`, `DSL1xxx`, `DSL2xxx`) is about the policy text
itself, and belongs to the axorum-policy skill.

## Policy changes in the timeline

`check.py` judges each policy change the timeline schedules against the
world, as the change is made when it comes due, and stops at the first one
the world cannot run, counting events from one. A change named by `file` is
read first, as `run.py` reads it: from the world's directory joined with the
name. A script step's change is not judged: it records what a run was sent.
A change's lint warnings are neither printed nor counted: a change made
mid-run, such as a freeze, is often one the linter flags, and the sandbox
makes it all the same.

An `axorum-sandbox` from before this check passes such a world without
reading its changes. So `check.py` asks the installed one first, and when it
does not judge them, refuses with exit 2 (`does not judge the policy changes
a world schedules`): upgrade it (`pip install -U axorum-sandbox`) and check
again.

| The message says | It means | Fix |
|---|---|---|
| `the world cannot run event ...'s policy change: the policy source did not compile` | the text under that event's `source`, or in the file it names, is not a policy | hand the change's policy to the axorum-policy skill with the problems the message lists |
| `the world cannot run event ...'s policy change: the policy compiles, but ... so the world cannot run it as written` | the change names a currency the world does not declare (`DSL3001`), or caps a mandate in another currency than the world opens it in (`DSL3004`) | as "Policy against the world" says for that code: fix the world, or ask whether the change's currency is what is wrong (axorum-policy) |
| `changes the policy to ..., which cannot be read` | the path the message names, the world's directory joined with the event's `file` (an absolute `file` as written, with `../` and symlinks followed), holds no file, holds a directory, or holds a file you may not read; the system's reason ends the message | put a policy file you can read at that path, or the policy's text under the change's `source` |

## Loading the world

`run.py` loads the world into the engine as `serve` does, and says `did not
load` with the engine's reason.

| The engine says | It means | Fix |
|---|---|---|
| `ceiling ... exceeds its parent ... (a child may not be looser than its parent)` | a slice above the budget it is carved from | lower the slice, or raise the parent, as the user decides |
| `currency ... does not match its parent ... currency` | a slice in another currency than the budget it is carved from | open the slice in its parent's currency; a budget in another currency is a mandate of its own, with no `parent` |
| `fiscal calendar is not well-formed` | periods out of order, overlapping, or with `from` after `to` | list periods in time order, each starting after the last one ends |
| `counterparty import is not well-formed` | an alias that is also a counterparty's id in the list, or one two counterparties both list | give each alias to one counterparty, and never an id in the list |
| a policy diagnostic | the policy does not compile | run `check.py`, then hand the policy to the axorum-policy skill |
| `event ...: the policy does not compile: ...` | a `policy` change on the timeline puts in force a policy that does not compile, which stops the load as the world's own policy would | hand that policy to the axorum-policy skill; `axorum-sandbox check next.axp --world world.yaml` lists its problems |

A policy file that cannot be read, the world's own or one a `policy` change
names by `file:`, stops the load with the path tried, the world's directory
joined with the name: put a policy file you can read at that path.

## Refused events

An event the engine refuses changes nothing, and the run goes on. `run.py`
prints it as `REFUSED, nothing changed:` with the engine's reason, and its
exit is 3. An event applied at start (at `0s`, or reached by a `0s` advance)
is no different, and `run.py` lists it first. The usual cause is a
master-data event whose new list the ledger refuses, such as a calendar out
of order: fix the list in the event as you would in `master_data`. A
`policy` change the deployment refuses when the clock reaches it, such as one
in a currency the world does not declare, is refused the same way, and the
policy in force stays. When the world means to show a refused change, say so
in the world brief, and expect the exit.

## Replaying a scenario

`axorum-sandbox run scenario.yaml` replays a scenario's script and fails,
exit 1, on a step that does not replay as recorded. The world check reads an
injected `advance` from its step's own `at`; the replay meets it where the
clock stands, and names a step it refuses there, counted from one. A live
run refuses that move and saves no step, so such a step was edited in by
hand.

| The message says | It means | Fix |
|---|---|---|
| `script step 2 advances to 365300d, past the clock's last second at 365250d` | the step's injected `advance` is in reach from its own `at`, but an earlier step or a scheduled event left the clock later, and from there the advance passes the clock's last second | save the run again instead of editing its script; for a step meant to stay, shorten the advance so it ends at `365250d` or earlier from where the clock stands |

## Publishing

`publish.py` hands the world to `axorum-sandbox publish world`, which checks
it as `check.py` does, a warning on its own policy counted as an error and
each scheduled policy change compiled against it, before writing anything:
a check refusal reads as in the sections above. The console's own refusals
give its reason. The ones a world can cause:

| The world | It means | Fix |
|---|---|---|
| names a policy file held by a library policy this sandbox did not create, or by one it created that a person has since edited | the sandbox may point its world only at the policy it runs or one it created that nobody has edited | rename the policy file and the world's `policy: {file: ...}` line to publish your own copy, or ask an owner of that policy to attach it to the world in the console |
| has a `world:` name another world in the organization holds | a sandbox publishes only to the world attached to it | rename the world in its `world:` line, not the policy file |
| names its policy file by a path, or by a name the library cannot keep a policy under (`policies/ap.axp`, `ap policy.axp`, `_ap.axp`, `ap+v2.axp`, `política.axp`, or past 80 characters) | the console's library keeps a policy by a file name alone, up to 80 characters: an ASCII letter or digit first, then ASCII letters, digits, `.`, `_` or `-` | rename the policy file to such a name, keep it beside the world, and name it alone (`policy: {file: ap-policy.axp}`) |
| has a top-level `script`, as a scenario does, even an empty one (`script: []`) | a world in the console holds no script, since a script belongs to a sandbox run, not to the published world | publish the world without its `script` key; keep the scenario on disk for `axorum-sandbox run`, or save its steps as a scenario under Scenarios in the console |
| changes its policy on the timeline to a file (`policy: {file: next.axp}`) | the console keeps the world alone, with no file beside it, so it could never load that change | write the change's policy text inline, under `source:` |
| changes its policy on the timeline to one it cannot run (`the world cannot run event 7's policy change: ...`) | the changed-to policy does not compile, names a currency the world does not declare (`DSL3001`), or caps a mandate in another currency than the world opens it in (`DSL3004`), so the console could not run the change | hand that policy to the axorum-policy skill; `axorum-sandbox check next.axp --world world.yaml` lists its problems |

A sandbox with no world attached refuses every publish, exit 3, before
anything is written (`has no world attached in the console`): attach a world
to the sandbox in the console, then publish again.

A publish writes only over what `pull` fetched into the world's directory,
which it keeps there in `.axorum-pulled.json`: keep that file with the world.
A save of the world or its policy made in the console since the pull, an
owner's among them, refuses the publish before it writes anything, exit 3
(`the world clerk changed in the console since you pulled; nothing was
written`): a publish never writes over it. Pull again into another directory
(`axorum-sandbox pull --output <dir>/world.yaml`), carry the changes into
what it writes, and publish from there. A world published from a directory
that holds no pull of it is refused the same way (`this directory holds no
pull of the world clerk`), unless the console holds that text already: pull
first, the same way, or publish again with `--replace`
(`publish.py world.yaml --replace`), which overwrites the console's version
of each record with the files. Pass --replace only when the user has said to
overwrite the console's version. Never pass it to clear a save made since
the pull: it would discard that save. With `--dry-run`, it names each record
it would replace, its current name in the console and the size of its text
and of the file's; a save made in the console while it runs is still
refused (`the world clerk changed in the console while this publish wrote
it`).

A console that cannot check a write against the revision it gave refuses
it, exit 3 (`the console cannot check the write of the world clerk against
the revision this publish read, and refused it`), and the publish never
sends it again: publish again, and if the console refuses it the same way,
tell an owner of the console.

The console can refuse the world after the policy was written: the exit is
3, and `publish.py` says which policy was written. Fix what the reason names
and publish again; the policy then reads `unchanged`.

Exit 2 is never a verdict on the world. It names what stopped the job (a
sandbox too old to publish, a variable missing, the console out of reach, a
write the console did not confirm) and what the console confirmed. A write
it did not confirm may have landed, and so may anything when the sandbox's
report cannot be read: once the cause is fixed, running the same publish
again finishes the job, and says `unchanged` for what had landed.
