#!/usr/bin/env python3
"""Repackage the verified 3151 binaries with the shell-only runtime handover fix."""
from pathlib import Path, PurePosixPath
import argparse
import copy
import difflib
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import zipfile

REPO = Path(__file__).resolve().parents[1]
BASE_MODULE = 'Vector-SR-v1.2-3151-S24U-SharedUID-Hotfix-Candidate-Release.zip'
BASE_SOURCE = 'Vector-SR-v1.2-3151-S24U-Hotfix-source.zip'
BASE_PATCH = 'Vector-SR-v1.2-3151-S24U-Hotfix.patch'
PINS = {
    BASE_MODULE: 'f29f2505df42f01a9cd09329ded0c74fb3f33bd6ce9089613beea70f45ca7259',
    BASE_SOURCE: 'f238fcfdc74888b6ce15f3c870ace30d7fc60993d0ceff9c79c460ae7da3dd2f',
    BASE_PATCH: '3e79a4cb14d4288765386bdc78a8f342f06dd0bed7a592ab85e68dba80e676d1',
    'SUBMODULES.txt': 'd4b045b3f7c8410edb2bf07996fb633ace2292590a233b2a08e7865c7b00a399',
}
MODULE = 'Vector-SR-v1.2-3151-r2-S24U-SharedUID-Hotfix-Release.zip'
SOURCE = 'Vector-SR-v1.2-3151-r2-S24U-Hotfix-source.zip'
PATCH = 'Vector-SR-v1.2-3151-r2-S24U-Hotfix.patch'
sha = lambda data: hashlib.sha256(data).hexdigest()


def entries(path):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP entries')
        for name in names:
            p = PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name:
                raise ValueError('Unsafe ZIP member: ' + name)
        return {i.filename: (i, archive.read(i)) for i in infos}


def rewrite(path, original, updates):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        for name in sorted(set(original) | set(updates)):
            if name in original:
                info, old = original[name]
                info = copy.copy(info)
                data = updates.get(name, old)
            else:
                info = zipfile.ZipInfo(name, (2026, 10, 25, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                data = updates[name]
            target.writestr(info, data)


def verify_module(contents):
    files = {n: data for n, (_, data) in contents.items() if not n.endswith('/')}
    for name, data in files.items():
        if name.endswith('.sha256'):
            if name[:-7] not in files or data.decode().strip() != sha(files[name[:-7]]):
                raise ValueError('Checksum mismatch: ' + name)
        elif files.get(name + '.sha256', b'').decode().strip() != sha(data):
            raise ValueError('Missing checksum: ' + name)
    return files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-dir', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--test-report', action='append', default=[], type=Path)
    args = parser.parse_args()
    if len(args.repository_commit) != 40 or any(c not in '0123456789abcdef' for c in args.repository_commit):
        parser.error('repository-commit must be a complete Git commit hash')
    for name, expected in PINS.items():
        if sha((args.base_dir / name).read_bytes()) != expected:
            raise ValueError('Unverified base artifact: ' + name)
    reports = [json.loads(p.read_text()) for p in args.test_report]
    for report in reports:
        if not report['passed'] or report['skipped'] or report['tests'] < 13:
            raise ValueError('Incomplete or failed integration tests')

    old_module = entries(args.base_dir / BASE_MODULE)
    old_files = verify_module(old_module)
    old_source = entries(args.base_dir / BASE_SOURCE)
    spec = importlib.util.spec_from_file_location('upgrade_patch', REPO / 'scripts/apply_upgrade_fix.py')
    patcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(patcher)
    with tempfile.TemporaryDirectory(prefix='vector-source-preflight-') as temp:
        source_root = Path(temp)
        for name in patcher.PINNED:
            path = source_root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(old_source[name][1])
        source_changes = patcher.changes(source_root)

    module_changes = {name.removeprefix('zygisk/module/'): data for name, data in source_changes.items()}
    module_changes['module.prop'] = module_changes['module.prop'].decode().replace('${versionName}', 'v1.2').replace('${versionCode}', '3151').encode()
    for name, data in list(module_changes.items()):
        module_changes[name + '.sha256'] = sha(data).encode()

    args.output.mkdir(parents=True, exist_ok=True)
    rewrite(args.output / MODULE, old_module, module_changes)
    new_files = verify_module(entries(args.output / MODULE))
    unchanged = []
    for name, data in old_files.items():
        if name not in module_changes:
            if new_files[name] != data:
                raise ValueError('Unexpected binary change: ' + name)
            if not name.endswith('.sha256'):
                unchanged.append(name)
    for name in ['manager.apk', 'daemon.apk', 'framework/lspd.dex']:
        if name not in unchanged:
            raise ValueError('Signed APK/framework must stay byte-identical')

    # A final context line can be a single space; stripping it corrupts hunk counts.
    combined_patch = (args.base_dir / BASE_PATCH).read_text().replace('\r\n', '\n')
    if not combined_patch.endswith('\n'):
        combined_patch += '\n'
    for name, data in sorted(source_changes.items()):
        before = old_source[name][1].decode() if name in old_source else ''
        combined_patch += ''.join(difflib.unified_diff(before.splitlines(keepends=True), data.decode().splitlines(keepends=True),
                                                     fromfile='a/' + name if before else '/dev/null', tofile='b/' + name))
    (args.output / PATCH).write_bytes(combined_patch.encode())

    # Check that recipients can apply the complete patch to the pinned source.
    java_paths = ['legacy/src/main/java/org/matrix/vector/legacy/LegacyDelegateImpl.java',
                  'legacy/src/main/java/de/robv/android/xposed/XposedBridge.java']
    with tempfile.TemporaryDirectory(prefix='vector-patch-check-') as temp:
        check_root = Path(temp)
        for name in list(patcher.PINNED) + java_paths:
            path = check_root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(old_source[name][1])
        git = ['git', '-c', 'core.autocrlf=false', '-c', 'core.eol=lf', '-C', temp]
        subprocess.run(git + ['apply', '-R', str((args.base_dir / BASE_PATCH).resolve())], check=True)
        subprocess.run(git + ['apply', '--check', '--whitespace=error-all', str((args.output / PATCH).resolve())], check=True)
        subprocess.run(git + ['apply', str((args.output / PATCH).resolve())], check=True)
        for name in java_paths:
            if (check_root / name).read_bytes() != old_source[name][1]:
                raise ValueError('Java patch mismatch: ' + name)
        for name, data in source_changes.items():
            if (check_root / name).read_bytes() != data:
                raise ValueError('Upgrade source patch mismatch: ' + name)

    source_changes.update({
        's24u-hotfix-build/scripts/apply_upgrade_fix.py': (REPO / 'scripts/apply_upgrade_fix.py').read_bytes(),
        's24u-hotfix-build/scripts/package_upgrade_release.py': Path(__file__).read_bytes(),
        's24u-hotfix-build/BUILDING.md': (REPO / 'docs/BUILDING.md').read_bytes(),
        's24u-hotfix-build/docs/BUILDING.md': (REPO / 'docs/BUILDING.md').read_bytes(),
        's24u-hotfix-build/docs/RELEASE_3151_R2.md': (REPO / 'docs/RELEASE_3151_R2.md').read_bytes(),
        's24u-hotfix-build/tests/test_upgrade_runtime.py': (REPO / 'tests/test_upgrade_runtime.py').read_bytes(),
    })
    for name in ['service.sh', 'upgrade-runtime.sh']:
        source_changes['s24u-hotfix-build/module-overrides/' + name] = (REPO / 'module-overrides' / name).read_bytes()
    rewrite(args.output / SOURCE, old_source, source_changes)
    new_source = entries(args.output / SOURCE)
    for name, (_, data) in old_source.items():
        if name not in source_changes and new_source[name][1] != data:
            raise ValueError('Unrelated source entry changed: ' + name)

    (args.output / 'SUBMODULES.txt').write_bytes((args.base_dir / 'SUBMODULES.txt').read_bytes())
    validation = 'Linux host installer/service integration tests passed; automatic upgrade has not been device-tested' if reports else 'Packaging preflight; integration tests not yet recorded'
    metadata = f'''Project: unofficial Vector-SR Samsung S24 Ultra Shared-UID hotfix
Upstream commit: ccf240320c838ee097b7bd4d996f314d25643cb0
Module framework version: v1.2 (3151)
Packaging revision: 3151-r2, automatic upgrade handover
Compatibility repository commit: {args.repository_commit}
Original binary build commit: 457572da71ff6c03e6b2b1dcc6a072b56aae15a3
Original module SHA-256: {PINS[BASE_MODULE]}
Validation: {validation}
Change scope: installer, startup scripts, runtime helper and displayed module revision only
manager.apk, daemon.apk, framework DEX and native binaries are byte-identical to the verified original 3151 build.
Their original matching signing identity is preserved; manager signature verification is unchanged.
The source ZIP includes the complete patched upstream tree and checked-out submodules, exact patch, upgrade helper and packaging/rebuild scripts.
License: GNU General Public License v3.0 (GPL-3.0)
'''
    (args.output / 'SOURCE-METADATA.txt').write_bytes(metadata.encode())
    evidence = {'validation': validation, 'host_reports': reports,
                'unchanged_binary_files': unchanged,
                'preserved_apk_sha256': {name: sha(new_files[name]) for name in ['manager.apk', 'daemon.apk']},
                'changed_module_files': sorted(n for n in module_changes if not n.endswith('.sha256')),
                'module_checksums_verified': len([n for n in new_files if n.endswith('.sha256')]),
                'complete_source_patch_applies': True}
    (args.output / 'UPGRADE-TESTS.json').write_text(json.dumps(evidence, indent=2) + '\n')
    names = [MODULE, SOURCE, PATCH, 'SOURCE-METADATA.txt', 'SUBMODULES.txt', 'UPGRADE-TESTS.json']
    sums = ''.join(f'{sha((args.output / name).read_bytes())}  {name}\n' for name in sorted(names))
    (args.output / 'SHA256SUMS.txt').write_bytes(sums.encode())
    print(json.dumps({'module': MODULE, 'sha256': sha((args.output / MODULE).read_bytes()),
                      'changed_module_files': evidence['changed_module_files'], 'validation': validation}, indent=2))


if __name__ == '__main__':
    main()
