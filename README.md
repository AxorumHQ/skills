# Axorum skills

Agent skills for working with [Axorum](https://axorum.com), the financial-control layer for AI
agents that move money. Each skill is a directory with a `SKILL.md` that tells the agent when to
use it and how, plus the references, examples and scripts it works from.

| Skill | What it does |
| --- | --- |
| [`axorum-policy`](skills/axorum-policy) | Guides a user, through questions, from controls in their own words to a policy (`policy.axp`) that checks clean and is proven on their own examples. It can push the policy to a running sandbox or publish it to the console's policy library. |
| [`axorum-world`](skills/axorum-world) | Guides a user to a sandbox world (`world.yaml`): the budgets, vendor lists, calendars and payment-network behavior their agents are tested against. It checks the world against its policy, plays its timeline, and can publish it to the console. |
| [`axorum`](skills/axorum) | Judgment for an agent that moves money through an Axorum ledger with the `@axorum/mcp` tools: a refusal is a verdict to adapt to, not an error to retry; a justification is audit evidence; and every refusal goes back to the agent's principal. |

The sandbox guide at [axorum.com/docs/sandbox](https://axorum.com/docs/sandbox) covers the
sandbox these skills drive.

## Prerequisites

- **`axorum-policy` and `axorum-world`** run their scripts with Python 3.11 or later and the
  released packages:

  ```shell
  pip install "axorum-sandbox>=0.3.0" "axorum-client>=1.2.0"
  ```

  `axorum-world` needs only `axorum-sandbox`. A script that finds a package missing or too old
  says so and names the `pip install` that fixes it.
- **`axorum`** needs the agent connected to an Axorum ledger through the
  [`@axorum/mcp`](https://www.npmjs.com/package/@axorum/mcp) server (`npm install @axorum/mcp`).
  Its README lists the settings the server reads.

## Install in Claude Code

As a plugin, from this repository's marketplace:

```shell
claude plugin marketplace add AxorumHQ/skills
claude plugin install axorum@axorum
```

Inside a session, `/plugin marketplace add AxorumHQ/skills` and `/plugin install axorum@axorum`
do the same. The skills load as `axorum:axorum-policy`, `axorum:axorum-world` and
`axorum:axorum`, and Claude uses each one when a task matches its description. To pick up a new
release, run `claude plugin update axorum@axorum`.

Or copy the skills you want into your personal skills directory (or a project's
`.claude/skills/`):

```shell
git clone https://github.com/AxorumHQ/skills.git axorum-skills
mkdir -p ~/.claude/skills
cp -R axorum-skills/skills/axorum-policy axorum-skills/skills/axorum-world axorum-skills/skills/axorum ~/.claude/skills/
```

Copy each skill's whole directory: its scripts, references and examples are read from beside its
`SKILL.md`.

## Versions

This snapshot matches **axorum-sandbox 0.3.0**. Each axorum-sandbox release publishes the skills
that match it here, tagged with the release's version (`v0.3.0`), and sets the plugin's version to
the same number.

## License

[Apache-2.0](LICENSE).
