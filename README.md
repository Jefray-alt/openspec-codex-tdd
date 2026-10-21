# OpenSpec + Codex TDD workflow

Install a reusable task orchestrator into an existing project. For each OpenSpec
task, Codex delegates implementation to a TDD developer, gets a separate review,
and makes **one commit containing that task's files and its checkbox**. Tasks run
serially. Reviews allow an initial round and at most two correction rounds.

This is a skill and agent bundle with Git/TDD safeguards, not a background daemon
or an OpenSpec plugin. The skill directs Codex; Python helpers enforce the
mechanical checks. See [the limitations](docs/compatibility.md) before adopting it.

## Install into a project

Requirements: Git, Python 3.11+, a current local Codex client with subagents,
OpenSpec, and working project test commands. No Python dependencies are needed.
Clone this bundle separately from your project:

```sh
git clone https://github.com/Jefray-alt/openspec-codex-tdd.git
cd openspec-codex-tdd
# Optionally check out a reviewed tag or full commit SHA before installing.
python3 scripts/manage.py install --project /absolute/path/to/project --dry-run
python3 scripts/manage.py install --project /absolute/path/to/project
```

The project must already have a clean committed Git baseline. If it does not yet
use OpenSpec, initialize it separately with `openspec init --tools codex`, review
the generated files, and commit them first. The installer does not initialize
OpenSpec, install packages, run network code, change Git history, or make commits.

Installation adds:

- `.agents/skills/openspec-tdd-apply/`: orchestrator, protocol and task guard.
- `.codex/agents/openspec_tdd_developer.toml` and `openspec_tdd_reviewer.toml`.
- A marked routing block appended to `AGENTS.md`.
- `.openspec-tdd-workflow.json`: installed file hashes and source revision.

Review and commit these installation changes in a setup commit before applying
tasks. Existing text outside the `AGENTS.md` block is preserved. The installer
does not overwrite generated OpenSpec skills, `openspec/config.yaml`, or Codex
configuration. Existing unmanaged collisions, edited managed files, ignored
destinations and symlinks stop installation/update before any writes.

Optionally merge the relevant [OpenSpec configuration](examples/openspec-config.yaml)
and [Codex settings](examples/codex-config.toml) into your project. Keep your
existing schema, context and rules. The OpenSpec operation guidance field is
advisory; the skill and routing block carry this workflow's instructions.

## Use in Codex

Open the target project in Codex. Reload/restart if the skill or custom agents
are missing, then explicitly invoke:

```text
$openspec-tdd-apply add-greeting
```

In the desktop app, selecting the skill and naming the change also works.
The installed `AGENTS.md` block routes ordinary OpenSpec implementation requests
(including `$openspec-apply-change add-greeting`) through the orchestrator.
Codex currently uses skills rather than generated `/opsx:apply` commands.
`openspec instructions apply ...` outputs instructions; it does not execute the
orchestrator itself. `codex apply` is a separate Codex patch-application command.

The orchestrator reads OpenSpec's current readiness, task locations and context;
it stops if the plan is blocked. Commit planning artifacts before starting. Each
checkbox should describe a behavior with tests in the same task, as in
[the sample task](examples/tasks.md). If TDD cannot be meaningfully demonstrated,
the workflow stops for a plan revision rather than inventing a failing test.

Developer → observed RED → GREEN → REFACTOR/checks → independent review →
corrections/review if needed → checkbox + isolated commit → next task.

Only the orchestrator commits. It never pushes or archives on its own.
The [execution protocol](payload/.agents/skills/openspec-tdd-apply/references/protocol.md)
defines commands, review JSON, evidence, retry limits and recovery.

## Update or remove

From your separate bundle checkout, fetch and inspect the desired revision:

```sh
git fetch origin --tags
# Select a reviewed revision explicitly; example for this initial release:
git checkout v0.1.0
python3 scripts/manage.py update --project /absolute/path/to/project --dry-run
python3 scripts/manage.py update --project /absolute/path/to/project
```

Review and commit the target project's update. Future versions are installed by
checking out their tag or full SHA and running the same update command. Re-running
update from the same revision is idempotent. Updates verify the prior manifest's
hashes before replacing/removing managed files; they do not clobber local edits.
To customize a managed file, preserve your patch and reconcile it with upstream
manually; there is intentionally no force-overwrite option.

```sh
python3 scripts/manage.py uninstall --project /absolute/path/to/project --dry-run
python3 scripts/manage.py uninstall --project /absolute/path/to/project
```

Uninstall removes unchanged managed files and only its marked `AGENTS.md` block;
it preserves other text and can leave empty directories. Review and commit removal.
OpenSpec upgrades are separate: run `openspec update` as appropriate, then verify
the routing still applies. This bundle does not patch OpenSpec-generated files.

## Verify the bundle

```sh
python3 -m unittest discover -s tests -v
```

Tests use temporary repositories; they do not touch your projects or need model
credentials. See [compatibility and validation](docs/compatibility.md) for the
verified baseline and the distinction between helper tests and model execution.

License: [MIT](LICENSE).
