#!/usr/bin/env python3
"""Install/update a checked-out workflow bundle. Python 3.11+, no dependencies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
MANIFEST = '.openspec-tdd-workflow.json'
START = '<!-- openspec-tdd-workflow:start -->'
END = '<!-- openspec-tdd-workflow:end -->'
BLOCK = f'''{START}
For OpenSpec implementation requests (including openspec-apply-change and opsx apply),
load .agents/skills/openspec-tdd-apply/SKILL.md before editing code and use it as
the implementation orchestrator. Delegate each task to a TDD developer and a
separate independent reviewer. Process tasks serially; commit each reviewed task
with only its relevant files and its checkbox. Preserve OpenSpec's readiness and
scope checks. Do not run the stock implementation loop alongside this workflow.
This routing applies only to implementation, not proposal, sync, or archive.
{END}'''


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def payload_files(directory):
    return {str(p.relative_to(directory)): p.read_bytes()
            for p in directory.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}


def safe(root, name):
    rel = Path(name)
    if rel.is_absolute() or '..' in rel.parts or '.git' in rel.parts:
        raise ValueError(f'Unsafe managed path: {name}')
    path = root / rel
    for part in [path, *path.parents]:
        if part == root:
            break
        if part.is_symlink():
            raise ValueError(f'Symlink in managed path: {name}')
    if path.exists() and not path.is_file():
        raise ValueError(f'Not a regular file: {name}')
    return path


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.workflow-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        if path.exists():
            os.chmod(tmp, path.stat().st_mode & 0o777)
        else:
            os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def manage(mode, target, dry_run=False):
    root = Path(target).resolve(strict=True)
    if Path(os.fsdecode(git(root, 'rev-parse', '--show-toplevel')).strip()).resolve() != root:
        raise ValueError('Target must be the Git repository root')
    if git(root, 'status', '--porcelain=v1', '--untracked-files=all', '--ignore-submodules=none'):
        raise ValueError('Working tree/index must be clean, including untracked files')
    git(root, 'rev-parse', '--verify', 'HEAD')
    manifest_path = safe(root, MANIFEST)
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    if old and old.get('format') != 1:
        raise ValueError('Unsupported install manifest')
    if mode != 'install' and not old:
        raise ValueError('No managed installation; use install first')
    if mode == 'install' and old:
        raise ValueError('Already installed; use update')
    prior = old['files'] if old else {}
    bundle = payload_files(SOURCE / 'payload')
    desired = {} if mode == 'uninstall' else bundle
    changes = {}
    for name in sorted(set(prior) | set(desired)):
        path = safe(root, name)
        current = path.read_bytes() if path.exists() else None
        if name in prior:
            if current is None or digest(current) != prior[name]:
                raise ValueError(f'Managed file locally changed/missing: {name}; preserve it and reconcile manually')
        elif current is not None:
            raise ValueError(f'Refusing existing unmanaged file: {name}')
        wanted = desired.get(name)
        if current != wanted:
            changes[name] = wanted
    agents = safe(root, 'AGENTS.md')
    content = agents.read_text() if agents.exists() else ''
    if old:
        oldblock = old['agents_block']
        if content.count(START) != 1 or content.count(END) != 1 or oldblock not in content:
            raise ValueError('Managed AGENTS.md block was edited; reconcile manually')
        new_content = content.replace(oldblock, '' if mode == 'uninstall' else BLOCK, 1)
        if mode == 'uninstall' and not old['agents_existed'] and not new_content.strip():
            new_content = None
    else:
        if START in content or END in content:
            raise ValueError('Unmanaged workflow markers in AGENTS.md')
        new_content = content + ('\n\n' if content and not content.endswith('\n\n') else '') + BLOCK + '\n'
    if new_content != content:
        changes['AGENTS.md'] = new_content.encode() if new_content is not None else None
    if mode == 'uninstall':
        changes[MANIFEST] = None
    else:
        try:
            revision = git(SOURCE, 'rev-parse', 'HEAD').decode().strip()
        except subprocess.CalledProcessError:
            revision = 'uncommitted-source'
        manifest = dict(format=1, version=(SOURCE / 'VERSION').read_text().strip(),
                        source_revision=revision, files={n: digest(d) for n, d in desired.items()},
                        agents_existed=old['agents_existed'] if old else agents.exists(), agents_block=BLOCK)
        data = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
        if not manifest_path.exists() or manifest_path.read_bytes() != data:
            changes[MANIFEST] = data
    # Do not create files hidden by ignore rules; installations should be committed.
    for name in changes:
        if changes[name] is not None and subprocess.run(
                ['git', '-C', str(root), 'check-ignore', '--no-index', '-q', '--', name]).returncode == 0:
            raise ValueError(f'Managed destination is ignored: {name}')
    for name, data in changes.items():
        print(f'{"remove" if data is None else "write "} {name}')
    if dry_run:
        print('Dry run; no files changed.')
        return
    backups = {n: safe(root, n).read_bytes() if safe(root, n).exists() else None for n in changes}
    written = []
    try:
        for name, data in changes.items():
            path = safe(root, name)
            written.append(name)
            if data is None:
                path.unlink(missing_ok=True)
            else:
                atomic(path, data)
    except OSError:
        for name in reversed(written):
            path = safe(root, name)
            if backups[name] is None:
                path.unlink(missing_ok=True)
            else:
                atomic(path, backups[name])
        raise
    print(f'{mode} complete. Review and commit the installation changes before applying tasks.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['install', 'update', 'uninstall'])
    parser.add_argument('--project', required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        manage(args.mode, args.project, args.dry_run)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
