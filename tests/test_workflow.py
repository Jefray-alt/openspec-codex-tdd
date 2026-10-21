import json
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / 'payload/.agents/skills/openspec-tdd-apply/scripts/task_guard.py'
MANAGE = ROOT / 'scripts/manage.py'
TASKS = 'openspec/changes/greeting/tasks.md'
TEST = '''import unittest
from greeting import greet
class GreetingTest(unittest.TestCase):
    def test_greeting(self):
        self.assertEqual(greet("Ada"), "Hello, Ada!")
'''


class Repository(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'project'
        self.repo.mkdir()
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Workflow Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        self.git('config', 'core.autocrlf', 'false')
        self.write(TASKS, '## Tasks\n\n- [ ] 1.1 Add greeting\n- [ ] 1.2 Other behavior\n')
        self.write('greeting.py', 'def greet(name):\n    return None\n')
        self.write('user.txt', 'keep me\n')
        self.commit_all()

    def command(self, argv, ok=True):
        result = subprocess.run(argv, cwd=self.repo, capture_output=True, text=True,
                                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'OPENSPEC_TELEMETRY': '0'})
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def git(self, *args, **kwargs):
        return self.command(['git', *args], **kwargs).stdout.strip()

    def write(self, name, data):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)

    def commit_all(self):
        self.git('add', '--all')
        self.git('commit', '-m', 'fixture')

    def guard(self, *args, **kwargs):
        return self.command([sys.executable, str(GUARD), *args], **kwargs)

    def manage(self, mode, *args, **kwargs):
        return self.command([sys.executable, str(MANAGE), mode, '--project', str(self.repo), *args], **kwargs)

    def begin(self):
        return self.guard('begin', '--task-file', TASKS, '--line', '3', '--allow', 'greeting.py',
                          '--allow', 'test_greeting.py', '--test', 'test_greeting.py')

    def phase(self, name, ok=True):
        return self.guard('check', '--phase', name, '--', sys.executable, '-m', 'unittest', 'test_greeting', ok=ok)

    def ready(self):
        self.begin()
        self.write('test_greeting.py', TEST)
        self.phase('red')
        self.write('greeting.py', 'def greet(name):\n    return f"Hello, {name}!"\n')
        self.phase('green')
        self.phase('refactor')
        return json.loads(self.guard('snapshot').stdout)

    def review(self, snap, verdict='pass', reviewer='reviewer', developer='developer', ok=True):
        path = self.base / 'review.json'
        path.write_text(json.dumps(dict(digest=snap['digest'], reviewer_id=reviewer,
                                       developer_id=developer, verdict=verdict,
                                       findings=[] if verdict == 'pass' else [{'defect': 'missing edge case'}],
                                       evidence='Observed assertion RED, passing checks and raw diff inspected.')))
        return self.guard('review', '--report', str(path), ok=ok)


class GuardTests(Repository):
    def test_success_is_one_commit_with_only_task_files_and_one_checkbox(self):
        initial = self.git('rev-parse', 'HEAD')
        snap = self.ready()
        self.review(snap)
        result = json.loads(self.guard('commit', '--message', 'feat: greeting task 1.1').stdout)
        self.assertEqual(self.git('rev-list', '--count', initial + '..HEAD'), '1')
        self.assertEqual(self.git('rev-parse', 'HEAD^'), initial)
        self.assertEqual(set(result['files']), {TASKS, 'greeting.py', 'test_greeting.py'})
        text = (self.repo / TASKS).read_text()
        self.assertIn('- [x] 1.1', text)
        self.assertIn('- [ ] 1.2', text)
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertEqual((self.repo / 'user.txt').read_text(), 'keep me\n')

    def test_dirty_user_work_is_preserved(self):
        self.write('user.txt', 'uncommitted user work\n')
        self.guard('begin', '--task-file', TASKS, '--line', '3', '--allow', 'test_greeting.py',
                   '--test', 'test_greeting.py', ok=False)
        self.assertEqual((self.repo / 'user.txt').read_text(), 'uncommitted user work\n')

    def test_initial_red_rejects_production_changes_and_green_before_red(self):
        self.begin()
        self.write('test_greeting.py', TEST)
        self.phase('green', ok=False)
        self.write('greeting.py', 'def greet(name):\n    return "changed"\n')
        self.phase('red', ok=False)

    def test_passing_test_is_not_red(self):
        self.begin()
        self.write('test_greeting.py', 'import unittest\nclass Passing(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n')
        self.phase('red', ok=False)

    def test_empty_test_run_is_not_red(self):
        self.begin()
        self.write('test_greeting.py', 'import unittest\n')
        self.phase('red', ok=False)

    def test_missing_command_invalidates_existing_pass(self):
        snap = self.ready()
        self.review(snap)
        self.guard('check', '--phase', 'refactor', '--', 'definitely-nonexistent-workflow-command', ok=False)
        self.guard('commit', '--message', 'failed checks', ok=False)

    def test_final_checks_and_pass_are_required(self):
        self.begin()
        self.write('test_greeting.py', TEST)
        self.phase('red')
        self.write('greeting.py', 'def greet(name):\n    return f"Hello, {name}!"\n')
        self.phase('green')
        self.guard('snapshot', ok=False)
        self.phase('refactor')
        self.guard('commit', '--message', 'no review', ok=False)

    def test_first_green_must_rerun_the_red_command(self):
        self.begin()
        self.write('test_greeting.py', TEST)
        self.phase('red')
        self.write('greeting.py', 'def greet(name):\n    return f"Hello, {name}!"\n')
        self.guard('check', '--phase', 'green', '--', sys.executable, '-m', 'unittest', 'discover', ok=False)
        self.phase('green')

    def test_mutation_invalidates_tests_and_review(self):
        snap = self.ready()
        self.review(snap)
        self.write('greeting.py', 'def greet(name):\n    return f"Hello, {name}!"  # changed\n')
        self.guard('commit', '--message', 'stale', ok=False)
        self.phase('refactor')
        self.review(snap, ok=False)
        self.guard('commit', '--message', 'still stale', ok=False)

    def test_out_of_scope_staging_and_checkbox_edits_stop(self):
        self.ready()
        self.write('user.txt', 'another writer\n')
        self.guard('snapshot', ok=False)
        self.write('user.txt', 'keep me\n')
        self.git('add', 'greeting.py')
        self.guard('snapshot', ok=False)

    def test_checkbox_cannot_change_before_review(self):
        self.ready()
        self.write(TASKS, (self.repo / TASKS).read_text().replace('- [ ]', '- [x]', 1))
        self.guard('snapshot', ok=False)

    def test_same_actor_cannot_review_and_three_rejections_exhaust_budget(self):
        snap = self.ready()
        self.review(snap, reviewer='same', developer='same', ok=False)
        for _ in range(3):
            self.review(snap, verdict='changes_requested')
        self.review(snap, ok=False)
        self.phase('refactor', ok=False)
        self.guard('commit', '--message', 'exhausted', ok=False)

    def test_third_round_pass_can_commit(self):
        snap = self.ready()
        self.review(snap, verdict='changes_requested')
        self.review(snap, verdict='changes_requested')
        self.review(snap)
        self.guard('commit', '--message', 'feat: third review passed')

    def test_blocked_review_stops_immediately(self):
        snap = self.ready()
        self.review(snap, verdict='blocked')
        self.review(snap, ok=False)
        self.guard('commit', '--message', 'blocked', ok=False)

    def test_head_move_stops(self):
        self.begin()
        self.git('commit', '--allow-empty', '-m', 'another actor')
        self.guard('snapshot', ok=False)

    def test_lock_and_abort_preserve_work(self):
        self.begin()
        self.begin_failure = self.guard('begin', '--task-file', TASKS, '--line', '3', '--allow',
                                       'test_greeting.py', '--test', 'test_greeting.py', ok=False)
        self.write('test_greeting.py', TEST)
        self.guard('abort')
        self.assertEqual((self.repo / 'test_greeting.py').read_text(), TEST)

    def test_hook_failure_preserves_work_and_creates_no_commit(self):
        snap = self.ready()
        self.review(snap)
        before = self.git('rev-parse', 'HEAD')
        hook = self.repo / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        self.guard('commit', '--message', 'hook fails', ok=False)
        self.assertEqual(self.git('rev-parse', 'HEAD'), before)
        self.assertTrue(self.git('diff', '--cached', '--name-only'))
        self.assertIn('- [x] 1.1', (self.repo / TASKS).read_text())

    def test_symlink_escape_rejected(self):
        outside = self.base / 'outside'
        outside.mkdir()
        (self.repo / 'escape').symlink_to(outside, target_is_directory=True)
        self.git('add', 'escape')
        self.git('commit', '-m', 'symlink fixture')
        self.guard('begin', '--task-file', TASKS, '--line', '3', '--allow', 'escape/test.py',
                   '--test', 'escape/test.py', ok=False)
        self.assertEqual(list(outside.iterdir()), [])


class InstallerTests(Repository):
    def test_payload_excludes_generated_python_caches(self):
        spec = importlib.util.spec_from_file_location('workflow_manager', MANAGE)
        manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(manager)
        payload = self.base / 'payload'
        (payload / '__pycache__').mkdir(parents=True)
        (payload / 'SKILL.md').write_text('keep')
        (payload / '__pycache__/module.pyc').write_bytes(b'cache')
        (payload / 'legacy.pyc').write_bytes(b'cache')
        (payload / 'legacy.pyo').write_bytes(b'cache')
        self.assertEqual(manager.payload_files(payload), {'SKILL.md': b'keep'})

    def test_install_update_uninstall_preserves_existing_instructions(self):
        self.write('AGENTS.md', 'Existing project instructions.\n')
        self.commit_all()
        self.manage('install', '--dry-run')
        self.assertFalse((self.repo / '.openspec-tdd-workflow.json').exists())
        self.manage('install')
        self.assertTrue((self.repo / '.codex/agents/openspec_tdd_developer.toml').exists())
        self.assertTrue((self.repo / 'AGENTS.md').read_text().startswith('Existing project instructions.'))
        self.commit_all()
        self.manage('update')
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.manage('uninstall')
        self.assertEqual((self.repo / 'AGENTS.md').read_text().strip(), 'Existing project instructions.')
        self.assertFalse((self.repo / '.codex/agents/openspec_tdd_reviewer.toml').exists())

    def test_update_refuses_committed_local_customizations_without_partial_writes(self):
        self.manage('install')
        self.commit_all()
        name = '.codex/agents/openspec_tdd_developer.toml'
        self.write(name, (self.repo / name).read_text() + '\n# local customization\n')
        self.commit_all()
        self.manage('update', ok=False)
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertIn('# local customization', (self.repo / name).read_text())

    def test_install_collision_does_not_write_other_files(self):
        self.write('.codex/agents/openspec_tdd_reviewer.toml', '# mine\n')
        self.commit_all()
        self.manage('install', ok=False)
        self.assertFalse((self.repo / '.agents/skills/openspec-tdd-apply/SKILL.md').exists())

    def test_dirty_untracked_and_symlink_targets_refused(self):
        self.write('untracked.txt', 'user work')
        self.manage('install', ok=False)
        (self.repo / 'untracked.txt').unlink()
        outside = self.base / 'outside'
        outside.mkdir()
        (self.repo / '.agents').symlink_to(outside, target_is_directory=True)
        self.commit_all()
        self.manage('install', ok=False)
        self.assertEqual(list(outside.iterdir()), [])

    def test_modified_agents_block_refused(self):
        self.manage('install')
        self.commit_all()
        self.write('AGENTS.md', (self.repo / 'AGENTS.md').read_text().replace('TDD developer', 'custom developer'))
        self.commit_all()
        self.manage('update', ok=False)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_agent_definitions_parse(self):
        for path in (ROOT / 'payload/.codex/agents').glob('*.toml'):
            parsed = tomllib.loads(path.read_text())
            self.assertTrue({'name', 'description', 'developer_instructions'} <= parsed.keys())
        tomllib.loads((ROOT / 'examples/codex-config.toml').read_text())


@unittest.skipUnless(shutil.which('openspec'), 'OpenSpec CLI not installed')
class OpenSpecSmokeTest(Repository):
    def test_real_apply_coordinates_guidance_and_update_survival(self):
        # OpenSpec writes only inside this disposable repository.
        self.command(['openspec', 'init', '--tools', 'codex', '--no-animation'])
        self.command(['openspec', 'new', 'change', 'add-greeting'])
        folder = 'openspec/changes/add-greeting/'
        self.write(folder + 'proposal.md', '## Why\nNeed greeting.\n## What Changes\nAdd greeting.\n## Impact\ngreeting.py\n')
        self.write(folder + 'design.md', '## Design\nA pure greet(name) function.\n')
        self.write(folder + 'specs/greeting/spec.md', '## ADDED Requirements\n### Requirement: Greeting\nThe system SHALL greet by name.\n#### Scenario: Name\n- **WHEN** name is Ada\n- **THEN** return Hello, Ada!\n')
        self.write(folder + 'tasks.md', (ROOT / 'examples/tasks.md').read_text())
        self.write('openspec/config.yaml', (ROOT / 'examples/openspec-config.yaml').read_text())
        result = self.command(['openspec', 'instructions', 'apply', '--change', 'add-greeting', '--json'])
        data = json.loads(result.stdout)
        self.assertNotEqual(data['state'], 'blocked')
        self.assertEqual(data['tasks'][0]['line'], 3)
        self.assertTrue(data['tasks'][0]['sourcePath'].endswith('tasks.md'))
        self.assertTrue(any('openspec-tdd-apply' in g for g in data['operationGuidance']))
        self.commit_all()
        self.manage('install')
        self.commit_all()
        names = ['AGENTS.md', '.agents/skills/openspec-tdd-apply/SKILL.md',
                 '.codex/agents/openspec_tdd_developer.toml']
        previous = {n: (self.repo / n).read_bytes() for n in names}
        self.command(['openspec', 'update'])
        self.assertEqual(previous, {n: (self.repo / n).read_bytes() for n in names})


if __name__ == '__main__':
    unittest.main()
