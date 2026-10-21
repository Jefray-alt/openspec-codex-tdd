# Validation record

Run date: 2026-10-21. Local environment: Linux, Python 3.14.4, OpenSpec 1.14.3,
Codex CLI 0.163.0-alpha.10.2. All work used new disposable repositories, plus
this new bundle repository. Existing project repositories were not modified.

## Automated checks

`python3 -m unittest discover -s tests -v`: **26 tests passed**.

Coverage includes:

- Successful task creates exactly one commit, only its relevant files and one checkbox.
- Dirty user files, staged changes, moved HEAD and premature checkbox edits stop.
- Initial RED cannot follow production edits; passing/empty test runs are not RED.
- First GREEN reruns the same focused RED command; final checks are required.
- Changed candidates, stale reviews and failed command launches invalidate completion.
- Developer/reviewer IDs must differ; three rejections exhaust the budget;
  a third-round PASS can commit; a blocked review stops immediately.
- A failing Git hook creates no commit and preserves the work/index for recovery.
- Repository locks, symlink escapes, installation collisions and local customizations.
- Dry-run, install, idempotent update, uninstall and exclusion of generated Python caches.
- Actual OpenSpec initialization, apply task coordinates, operation guidance,
  and persistence of custom skills/agents/routing through `openspec update`.

The skill creator's `quick_validate.py` also passed. Agent and example TOML parsed
successfully. GitHub Actions is configured to repeat helper tests on Python 3.11
and 3.13, plus the OpenSpec 1.14.3 smoke check. Those CI jobs are separate from
the local result reported here.

## Independent agent forward tests

A separate evaluating agent installed the workflow into a newly initialized
OpenSpec fixture, then introduced an unrelated user edit. Apply discovery found
the pending task, and guard begin refused before implementation. The edit was
preserved byte-for-byte, the checkbox stayed unchecked and no task commit occurred.

On a second clean fixture, the evaluator orchestrated a separate developer and
a fresh reviewer with raw requirements, files and evidence. The developer's
initial test asserted greeting behavior while the committed stub returned None.
Observed RED: assertion failure, exit 1. Focused GREEN: exit 0. Final regression
discovery: exit 0. The reviewer independently inspected the complete candidate
and raw logs, reran focused/discovery tests, verified the candidate digest, and
returned PASS with no findings on the first review round.

The resulting task commit (`1f58c7f` in the disposable fixture) contained exactly
`greeting.py`, `test_greeting.py` and the task tracking file. The one selected
checkbox was checked and the final working tree was clean. The fixture hash is
local test evidence, not a commit in this distribution repository.

The forward test used generic Codex subagents with the supplied role instructions,
as supported by the protocol fallback; it did not verify named custom-agent
selection by every Codex client. The fixture was installed before the final
Python-cache filtering and exact-GREEN-command improvements; the final automated
suite verifies those changes. This bounded example supports the workflow, but
does not prove model adherence or review quality on arbitrary future tasks.

The evaluation also found that recursive payload copying could include generated
Python cache files. The final installer filters them out and a regression test
checks this behavior. Final task results and distribution files contain no such
caches.
