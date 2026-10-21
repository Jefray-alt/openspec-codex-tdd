# Compatibility and validation

Conventions checked on 2026-10-21 with OpenSpec **1.14.3** and Codex CLI
**0.163.0-alpha.10.2**. This is an observed baseline, not a guarantee for every
older/newer client. The skill runs through ordinary agent tools; it has no
additional runtime package dependency. The optional repository installer and
distribution tests use Python 3.11+ (locally exercised with Python 3.14.4).

## Current conventions and primary sources

| Integration | Convention used | Source |
| --- | --- | --- |
| Skill | `.agents/skills/<name>/SKILL.md`, invoked with `$skill-name` | [OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills) |
| Agents | Standalone `.codex/agents/*.toml` containing name, description and developer instructions | [OpenAI subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) |
| Permissions | Parent permissions are inherited; model/reasoning settings can be configured | [OpenAI subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) |
| OpenSpec/Codex | Generated skills; Codex command files skipped | [OpenSpec setup](https://openspec.dev/docs/setup) |
| Apply | Current status/instructions JSON, task coordinates and context files | [OpenSpec skills](https://openspec.dev/docs/skills) |
| Guidance | `operations.apply.guidance` is additive advice, separate from artifact rules | [OpenSpec customization](https://github.com/Fission-AI/OpenSpec/blob/main/docs/customization.md) |

The skill contains only Markdown. TOML files are declarative Codex agent
configuration, not executable helpers. The optional `scripts/manage.py` remains
outside the skill and is used only to install/update/remove bundle files. The
installation manifest is packaging metadata, not implementation state.

Current agents use standalone TOML rather than the older `[agents.role]`
`config_file` registration. Older clients may need legacy configuration and
experimental multi-agent flags; upgrade or adapt against their documentation.
The bundle intentionally inherits the parent model and reasoning settings.

## Supported scope

Local planning and implementation in the same Git repository, with a tracked
Markdown task checkbox. Custom schemas can track several files when the selected
task can be uniquely located. External stores/multiple repositories cannot put
code and checkbox in one atomic Git commit and are unsupported.

Use one clean full checkout or selected worktree, with no concurrent writers,
unfinished Git operation, submodules, sparse checkout, symlinked task file or
hidden index entries. The orchestrator must inspect these conditions itself;
there is no runtime gate or lock. Native commands/tests must be available in the
parent session. Shell examples assume a POSIX terminal; Windows was not tested.

## Limits

- Skill/AGENTS routing is written guidance, not an OpenSpec interception hook.
  Use the explicit custom skill when routing is unclear.
- Clean-tree checks, file scope, temporal TDD, current review, retry counting,
  explicit staging and commit verification are agent responsibilities. There is
  no automatic gate, persisted retry counter, content fingerprint or identity
  authentication. Keep the task ledger and actual evidence in the conversation.
- A separate reviewer is required, but a different model or isolated read-only
  OS sandbox is not guaranteed. Custom agents inherit parent permissions.
- Every candidate change after review requires fresh checks/review within the
  existing budget. Git hooks/filters and unrelated editors can change files;
  stop on unexpected changes rather than claim stale approval remains valid.
- A failed commit can leave a checked checkbox and staged files. Preserve them
  and report the actual state; do not blindly retry, reset or amend.
- Distribution tests validate installation/migration, not model behavior.
  Independent forward tests are bounded samples, not a guarantee on future tasks.

## Migration from v0.1

The updater removes the old managed `scripts/task_guard.py` only when its hash
still matches the previous installation manifest. Local modifications stop the
update for manual reconciliation. No new implementation helper replaces it.
Finish or explicitly stop active v0.1 agents before updating. Keep old local
Git-directory evidence if needed; the Markdown skill never reads it or resets
an unresolved review budget. Generated local caches/empty directories may need
reviewed cleanup; never delete unrelated files to make the skill look empty.
