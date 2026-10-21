# Compatibility and validation

Verified on 2026-10-21 with OpenSpec **1.14.3**, Codex CLI
**0.163.0-alpha.10.2**, Git and Python **3.14.4**. Helpers require Python 3.11+;
CI is configured for 3.11 and 3.13. This is an observed baseline, not
a promise that every older/newer release behaves identically.

## Current conventions and primary sources

| Integration | Convention used | Source |
| --- | --- | --- |
| Codex skills | Repository `.agents/skills/<name>/SKILL.md`; explicit `$skill-name` invocation | [OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills) |
| Custom agents | Standalone `.codex/agents/*.toml`, with `name`, `description`, `developer_instructions` | [OpenAI subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents) |
| Agent settings | `[agents] enabled` and `max_concurrent_threads_per_session`; inherit parent model/permissions | [OpenAI subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents) |
| OpenSpec + Codex | Generated skills; Codex command files are skipped | [OpenSpec setup](https://openspec.dev/docs/setup) and [tool matrix](https://github.com/Fission-AI/OpenSpec/blob/main/docs/supported-tools.md) |
| Apply inputs | `status` and `instructions apply --change NAME --json`; task coordinates and context | [OpenSpec skills](https://openspec.dev/docs/skills) |
| Apply guidance | `operations.apply.guidance`; additive advice, separate from artifact `rules` | [OpenSpec customization](https://github.com/Fission-AI/OpenSpec/blob/main/docs/customization.md) |

Current custom-agent files do not use the older `[agents.role] config_file`
registration pattern. Older Codex versions may require that format and an
experimental multi-agent flag. This bundle does not silently write legacy
configuration. Upgrade, or adapt the files against your installed version's
documentation and validate them. No model name or reasoning level is pinned.

## Supported scope

Local OpenSpec planning and implementation files in **the same Git repository**.
Each task's checkbox must be a tracked Markdown `- [ ]` line; a custom schema can
track multiple files if OpenSpec provides a valid path/line for the selected task.
External stores and multi-repository changes cannot satisfy one atomic commit
for code plus checkbox and are deliberately unsupported. A detached HEAD is
permitted by Git but choose a named working branch if you want durable branch
history. Worktrees are supported, with one guard lock shared across the repo.

The guard refuses dirty initial checkouts, staged files, submodules, symlinks in
managed/allowlisted paths and skip-worktree/assume-unchanged index flags. Use a
full checkout with committed setup/planning and no active merge/rebase operation.
Python helpers are platform-neutral; shell examples assume a POSIX terminal.
Windows Python/Git are plausible but were not executed in this validation.

## What the checks prove

Helper integration tests exercise clean-tree and path safeguards, installation,
updates, removal, RED/GREEN/REFACTOR recording, digest freshness, bounded reviews,
explicit staging and a single commit with one checkbox. An OpenSpec CLI smoke
check initializes a disposable project, reads actual apply JSON and verifies
that a refresh preserves this bundle. TOML and skill manifests are validated.

An independent agent evaluates the packaged workflow against a disposable task.
Its result is reported in [validation notes](validation.md). This is a bounded
sample, not a guarantee of model adherence on arbitrary projects. No automated
test can establish semantic review quality merely from a JSON `pass`.

## Limits that matter

- Skills and `AGENTS.md` routing are model instructions, not an OpenSpec runtime
  interception hook. Always use the explicit custom skill when routing is unclear.
- Agent definitions cannot grant a separate read-only sandbox. The reviewer is
  instructed not to write; it inherits the parent session's permissions. The
  orchestrator checks that the candidate stayed unchanged.
- The guard verifies reported identities differ, but does not authenticate them.
  The orchestrator must use actual separate runtime agents and retain their output.
- Exit statuses and phase ordering establish execution records, not whether a
  test failed for the right reason. Reviewers must inspect assertion output,
  acceptance coverage and the diff, and rerun checks where possible.
- Stop all writers during review/commit. The cooperative lock cannot prevent an
  unrelated editor from racing Git. Project hooks and filters remain trusted.
- A failed hook/commit leaves work available for recovery and can leave the
  checkbox/index modified. Do not claim success or retry/amend without inspection.
- Evidence logs live in the Git common directory and are not committed. Retain
  them separately if your team needs an audit trail. Commit only task-relevant
  evidence explicitly required by the project, never incidental logs.
