# OpenSpec + Codex TDD workflow

Install a reusable task orchestrator into an existing project. For each OpenSpec
task, Codex delegates implementation to a TDD developer, gets a separate review,
and makes **one commit containing that task's files and its checkbox**. Tasks run
serially, with an initial review and at most two correction rounds.

The skill is **Markdown only**: `SKILL.md` and `references/protocol.md`.
It contains no scripts, hooks, lock files or workflow runner. Codex follows the
written protocol using native Git, OpenSpec and project test commands. Its
safeguards depend on agent adherence rather than automated enforcement.

Custom agents use Codex's native TOML configuration. The optional installer stays
in this distribution repository; it is never copied into the skill or project.
See [compatibility](docs/compatibility.md) for scope and limitations.

## Install into a project

Runtime requirements: Git, a local Codex client with subagents, OpenSpec, and your
project's normal test tools. The skill has no Python runtime dependency. The
optional installer requires Python 3.11+ with no extra packages.

Clone this bundle separately from your project:

```sh
git clone https://github.com/Jefray-alt/openspec-codex-tdd.git
cd openspec-codex-tdd
git checkout v0.2.0
python3 scripts/manage.py install --project /absolute/path/to/project --dry-run
python3 scripts/manage.py install --project /absolute/path/to/project
```

The project must already have a clean committed Git baseline. If OpenSpec is not
set up, run `openspec init --tools codex` separately, review its files and commit
them first. Installation does not initialize OpenSpec, install packages, change
Git history or make commits.

Installation adds:

- `.agents/skills/openspec-tdd-apply/SKILL.md` and `references/protocol.md`.
- `.codex/agents/openspec_tdd_developer.toml` and `openspec_tdd_reviewer.toml`.
- A marked implementation-routing block appended to `AGENTS.md`.
- `.openspec-tdd-workflow.json`, recording managed file hashes and bundle revision
  for installation/update only. The apply workflow never reads or writes it.

Review and commit the setup before applying tasks. Existing text outside the
`AGENTS.md` block is preserved. Generated OpenSpec skills, OpenSpec project
configuration and Codex configuration are left alone. Unmanaged collisions,
locally edited managed files, ignored destinations and symlinks stop installation
or update before writes. If your project ignores `.agents`, first add a narrow
project ignore exception that preserves the existing rules for other agent files.

Optionally merge relevant fields from [OpenSpec configuration](examples/openspec-config.yaml)
and [Codex settings](examples/codex-config.toml), preserving your own schema and
conventions. Operation guidance is advisory; the skill/routing block describe
this implementation process.

## Use in Codex

Open the target project and invoke:

```text
$openspec-tdd-apply add-greeting
```

Selecting the skill in the app and naming the change also works. Reload if the
skill/custom agents are missing. The installed `AGENTS.md` block routes ordinary
OpenSpec implementation requests, including `$openspec-apply-change`, through the
orchestrator. Codex uses skills rather than generated `/opsx:apply` commands.
`openspec instructions apply` outputs instructions; it does not run agents.
`codex apply` is an unrelated patch-application command.

The orchestrator checks readiness and a clean working tree, then retains the
task baseline, exact candidate, test evidence and review-round count in the
conversation. Each checkbox should deliver one behavior with tests, as in
[the example](examples/tasks.md). The protocol requires:

Developer → observed RED → GREEN → REFACTOR/checks → independent review →
corrections/review if needed → checkbox + isolated commit → next task.

Only the orchestrator commits. It checks the actual diff, explicit staged paths,
one checkbox, resulting commit and clean tree using Git directly. It never pushes
or archives automatically. Read the [execution protocol](payload/.agents/skills/openspec-tdd-apply/references/protocol.md)
for the full written procedure, Markdown review report and recovery behavior.

## Update or remove

From the separate bundle checkout, fetch and select a reviewed tag or full SHA:

```sh
git fetch origin --tags
git checkout v0.2.0
python3 scripts/manage.py update --project /absolute/path/to/project --dry-run
python3 scripts/manage.py update --project /absolute/path/to/project
```

Review and commit the update. The installer verifies prior managed hashes and
removes obsolete managed files, including the v0.1 runtime helper. Finish or stop
any active old workflow before upgrading; preserve its evidence and unresolved
review count. Old local evidence is not deleted or used by the new skill.
Updates from the same revision are idempotent and never overwrite local changes.

```sh
python3 scripts/manage.py uninstall --project /absolute/path/to/project --dry-run
python3 scripts/manage.py uninstall --project /absolute/path/to/project
```

Uninstall removes unchanged managed files and its routing block, preserving
other instructions and possibly empty directories. Installation scripts are
optional packaging tools; they are not called during implementation. OpenSpec
refreshes remain separate and do not patch this custom skill.

## Validate the bundle

```sh
python3 -m unittest discover -s tests -v
```

These tests cover distribution, safe installation/migration and OpenSpec
compatibility. They do not mechanically test or enforce the Markdown workflow.
See [validation notes](docs/validation.md) for independent behavioral evaluation.

License: [MIT](LICENSE).
