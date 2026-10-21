import json
import importlib.util
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
MANAGE = ROOT / 'scripts/manage.py'
TASKS = 'openspec/changes/greeting/tasks.md'


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

    def manage(self, mode, *args, **kwargs):
        return self.command([sys.executable, str(MANAGE), mode, '--project', str(self.repo), *args], **kwargs)



class InstallerTests(Repository):
    def legacy_install(self):
        self.manage('install')
        manifest_path = self.repo / '.openspec-tdd-workflow.json'
        manifest = json.loads(manifest_path.read_text())
        # Model the previous manifest's obsolete managed file without requiring
        # distribution history (tests also work from ZIPs/shallow clones).
        name = '.agents/skills/openspec-tdd-apply/scripts/task_guard.py'
        old = b'# Obsolete managed runtime fixture; never executed.\n'
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(old)
        manifest['files'][name] = hashlib.sha256(old).hexdigest()
        manifest['version'] = '0.1.0'
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        self.commit_all()

    def test_upgrade_removes_old_runtime_and_installs_markdown_only(self):
        self.legacy_install()
        self.manage('update', '--dry-run')
        legacy = self.repo / '.agents/skills/openspec-tdd-apply/scripts/task_guard.py'
        self.assertTrue(legacy.exists())
        self.manage('update')
        self.assertFalse(legacy.exists())
        skill = self.repo / '.agents/skills/openspec-tdd-apply'
        files = {str(p.relative_to(skill)) for p in skill.rglob('*') if p.is_file()}
        self.assertEqual(files, {'SKILL.md', 'references/protocol.md'})
        manifest = json.loads((self.repo / '.openspec-tdd-workflow.json').read_text())
        self.assertEqual(manifest['version'], (ROOT / 'VERSION').read_text().strip())
        self.assertNotIn(str(legacy.relative_to(self.repo)), manifest['files'])

    def test_modified_legacy_runtime_is_preserved_on_update_failure(self):
        self.legacy_install()
        legacy = self.repo / '.agents/skills/openspec-tdd-apply/scripts/task_guard.py'
        legacy.write_text(legacy.read_text() + '\n# local edits\n')
        self.commit_all()
        self.manage('update', ok=False)
        self.assertIn('# local edits', legacy.read_text())
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_fresh_install_has_only_markdown_in_skill(self):
        self.manage('install')
        skill = self.repo / '.agents/skills/openspec-tdd-apply'
        files = {str(p.relative_to(skill)) for p in skill.rglob('*') if p.is_file()}
        self.assertEqual(files, {'SKILL.md', 'references/protocol.md'})

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
