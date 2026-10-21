# Validation record

## v0.2.0: Markdown-only skill

The installed skill consists of `SKILL.md` and `references/protocol.md`. Native
Codex agent definitions remain declarative TOML. No executable helper is installed
or invoked by the workflow. The optional distribution installer remains outside
the skill, with tests for safe installation, updates, removal and migration.

The current validation checks include skill frontmatter, agent/example TOML,
Markdown-only installed contents, unchanged-instruction preservation, dry-run,
idempotent updates, file collisions, dirty-tree and symlink refusals, local-edit
protection, safe removal of the previous managed runtime file, and actual
OpenSpec apply coordinates/guidance plus refresh survival.

On 2026-10-21, `python3 -m unittest discover -s tests -v` passed all **11**
distribution/migration/compatibility tests. The skill creator's
`quick_validate.py` also passed. Local environment: Linux, Python 3.14.4 and
OpenSpec 1.14.3. CI remains configured for Python 3.11/3.13 and the same OpenSpec
baseline; its result is separate from these local checks.

These checks validate packaging. They do not establish that an agent will follow
TDD, count retries accurately, preserve candidate freshness or review well.
Independent behavioral evaluation is recorded below.

## Independent Markdown-only forward tests

A separate evaluator used the v0.2.0 development payload in disposable local
OpenSpec repositories. Actual separate developer and reviewer agents used the
generic-agent fallback with the supplied TOML instructions, each started without
forked context. No runtime helper, replacement script, hook or workflow state
file was used. Test evidence and review rounds stayed in the conversation.

The developer wrote three assertions for ordinary, empty and Unicode names
against a committed greet(name) stub returning None. Before production edits,
the focused command failed with three intended assertion failures (exit 1);
native Git inspection showed production still matched the baseline. The exact
same focused command then passed (exit 0), as did final full discovery and
whitespace checks. No forced refactoring was needed.

The fresh independent reviewer inspected raw requirements, complete tracked/new
files and actual output, independently reran the checks, and returned PASS with
no findings on round 1. Both agents finished before staging. Native Git checks
verified the candidate was unchanged, the staged paths were exact, and only the
selected checkbox changed in the tracking file.

The resulting fixture commit `5bc6ce81c4af33120b8e4ff2121f2262ac78c6c8`
contained exactly `greeting.py`, `test_greeting.py` and the task file. Its parent
matched the recorded baseline, its tree matched precommit `git write-tree`, the
working tree/index were clean, and refreshed OpenSpec reported `all_done`, 1/1.
This is a local fixture commit, not a distribution repository commit.

In a separate dirty-tree fixture, the evaluator observed an unrelated user edit
and stopped before development, tests, checkbox updates or commits. The edit's
content hash, HEAD and unchecked task were preserved, with an empty index.

These trials demonstrate agent compliance on bounded examples, not mechanical
enforcement or a guarantee for arbitrary future tasks. Named custom-agent
selection in every Codex client and adversarial/concurrent writers were not
validated.

## Earlier v0.1.0 validation

The initial scripted version passed 26 local tests, GitHub Actions and a separate
developer/reviewer task trial. Those runtime-guard tests and their guarantees do
not apply to v0.2.0: the helper has been removed. Historical evidence remains in
the `v0.1.0` Git tag rather than being presented as validation of this workflow.
