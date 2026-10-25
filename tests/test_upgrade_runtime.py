#!/usr/bin/env python3
"""Linux integration tests: real /proc entries, open APK FDs and disposable processes."""
from pathlib import Path
import argparse
import ctypes
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[1]
SHELL = ['/bin/sh']
MODULE_ZIP = None
CHILD = r'''
import ctypes, os, signal, sys, time
name, apk, cwd, ignore = sys.argv[1:]
ctypes.CDLL(None).prctl(15, name.encode(), 0, 0, 0)
os.chdir(cwd)
held = open(apk, 'rb')
if ignore == 'yes': signal.signal(signal.SIGTERM, signal.SIG_IGN)
print('ready', flush=True)
while True: time.sleep(1)
'''


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vector-upgrade-test-')
        self.root = Path(self.temp.name)
        self.active = self.root / 'modules' / 'zygisk_vector'
        self.active.mkdir(parents=True)
        (self.active / 'daemon.apk').write_bytes(b'old Vector APK')
        self.config = self.root / 'lspd' / 'config' / 'modules_config.db'
        self.config.parent.mkdir(parents=True)
        self.config.write_bytes(b'preserved-user-scopes-and-settings')
        self.children = []
        for name in ['upgrade-runtime.sh', 'service.sh']:
            shutil.copyfile(REPO / 'module-overrides' / name, self.active / name)

    def tearDown(self):
        for child in self.children:
            if child.poll() is None:
                child.kill()  # Only disposable processes created by this test.
            child.wait(timeout=5)
            child.stdout.close()
        self.temp.cleanup()

    def spawn(self, name, apk=None, cwd=None, ignore=False):
        child = subprocess.Popen(
            [name, '-u', '-c', CHILD, name, str(apk or self.active / 'daemon.apk'),
             str(cwd or self.active), 'yes' if ignore else 'no'],
            executable=sys.executable, stdout=subprocess.PIPE, text=True,
            start_new_session=True,
        )
        self.children.append(child)
        self.assertEqual(child.stdout.readline().strip(), 'ready')
        self.assertEqual(Path(f'/proc/{child.pid}/cmdline').read_bytes().split(b'\0')[0], name.encode())
        discovered = subprocess.run(['pidof', name], capture_output=True, text=True).stdout.split()
        self.assertIn(str(child.pid), discovered, 'Host pidof must discover the simulated Android name')
        return child

    def helper(self, mode='all'):
        return subprocess.run(SHELL + ['-c', '. "$1"; vector_stop_runtime "$2" "$3"',
                                      'upgrade-test', str(self.active / 'upgrade-runtime.sh'),
                                      str(self.active), mode], capture_output=True, text=True, timeout=10)

    def assert_alive(self, *children):
        for child in children:
            self.assertIsNone(child.poll(), f'Unexpectedly stopped PID {child.pid}')

    def assert_stopped(self, *children):
        for child in children:
            self.assertEqual(child.wait(timeout=5), -15, 'Only SIGTERM is allowed in the runtime helper')
        self.assertEqual(self.config.read_bytes(), b'preserved-user-scopes-and-settings')

    def service(self, compatible=True):
        fakebin = self.root / 'test-bin'
        fakebin.mkdir(exist_ok=True)
        output = self.root / 'launch.json'
        unshare = fakebin / 'unshare'
        unshare.write_text('#!/usr/bin/env python3\nimport json,os,sys\n'
                           'if sys.argv[1:] == ["--help"]:\n'
                           f' print({"--propagation" if compatible else "toybox unshare -m"!r})\n'
                           'else:\n'
                           ' with open(os.environ["VECTOR_TEST_LAUNCH"],"w") as f:\n'
                           '  json.dump({"cwd":os.getcwd(),"args":sys.argv[1:]},f)\n')
        unshare.chmod(0o755)
        environment = dict(os.environ, PATH=str(fakebin) + ':' + os.environ['PATH'],
                           VECTOR_TEST_LAUNCH=str(output))
        result = subprocess.run(SHELL + [str(self.active / 'service.sh')], env=environment,
                                capture_output=True, text=True, timeout=10)
        return result, output

    def test_new_install_leaves_unrelated_manager_alone(self):
        manager = self.spawn('org.lsposed.manager')
        self.assertEqual(self.helper().returncode, 0)
        self.assert_alive(manager)

    def test_deleted_old_apk_stops_only_vector_and_manager(self):
        daemon = self.spawn('lspd')
        manager = self.spawn('org.lsposed.manager')
        shell = self.spawn('com.android.shell')
        system = self.spawn('system_server')
        zygote = self.spawn('zygote64')
        replacement = self.active / 'new.apk'
        replacement.write_bytes(b'new Vector APK')
        replacement.replace(self.active / 'daemon.apk')
        self.assertEqual(self.helper().returncode, 0)
        self.assert_stopped(daemon, manager)
        self.assert_alive(shell, system, zygote)

    def test_in_place_reinstall_also_stops_old_classes(self):
        daemon = self.spawn('lspd')
        (self.active / 'daemon.apk').write_bytes(b'replaced in the same inode')
        self.assertEqual(self.helper('all').returncode, 0)
        self.assert_stopped(daemon)

    def test_healthy_soft_restart_preserves_daemon_and_manager(self):
        daemon = self.spawn('lspd')
        manager = self.spawn('org.lsposed.manager')
        self.assertEqual(self.helper('stale').returncode, 0)
        result = subprocess.run(SHELL + [str(self.active / 'service.sh')], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('already running', result.stdout)
        self.assert_alive(daemon, manager)

    def test_wrong_daemon_working_directory_is_stale(self):
        daemon = self.spawn('lspd', cwd=self.root)
        self.assertEqual(self.helper('stale').returncode, 0)
        self.assert_stopped(daemon)

    def test_unrelated_lspd_is_not_terminated(self):
        other = self.root / 'another-module'
        other.mkdir()
        other_apk = other / 'daemon.apk'
        other_apk.write_bytes(b'unrelated daemon')
        daemon = self.spawn('lspd', apk=other_apk, cwd=other)
        manager = self.spawn('org.lsposed.manager')
        self.assertEqual(self.helper().returncode, 0)
        self.assert_alive(daemon, manager)

    def test_refusing_sigterm_fails_without_force_kill(self):
        daemon = self.spawn('lspd', ignore=True)
        result = self.helper()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('refusing to force-kill', result.stdout)
        self.assert_alive(daemon)

    def test_service_starts_from_module_directory(self):
        result, output = self.service()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(output.exists())
        launch = json.loads(output.read_text())
        self.assertEqual(launch['cwd'], str(self.active))
        self.assertEqual(launch['args'], ['--propagation', 'slave', '-m', str(self.active / 'daemon'), '--system-server-max-retry=3'])

    def test_service_replaces_stale_daemon_and_uses_correct_cwd(self):
        daemon = self.spawn('lspd')
        manager = self.spawn('org.lsposed.manager')
        replacement = self.active / 'replacement.apk'
        replacement.write_bytes(b'installed 3151 APK')
        replacement.replace(self.active / 'daemon.apk')
        result, output = self.service()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_stopped(daemon, manager)
        self.assertEqual(json.loads(output.read_text())['cwd'], str(self.active))

    def test_incompatible_unshare_does_not_start_daemon(self):
        result, output = self.service(compatible=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('No compatible unshare', result.stdout)
        self.assertFalse(output.exists())

    def install(self, corrupt=False, arch='arm64'):
        if MODULE_ZIP is None:
            self.skipTest('Pass --module-zip to run the complete installer tests')
        self.assertFalse(Path('/data/adb/modules/zygisk_lsposed').exists(), 'Host tests refuse to touch an Android module tree')
        archive = self.root / 'module.zip'
        if corrupt:
            with zipfile.ZipFile(MODULE_ZIP) as src, zipfile.ZipFile(archive, 'w') as dst:
                for item in src.infolist():
                    data = src.read(item.filename)
                    if item.filename == 'manager.apk':
                        data = data + b'corrupt'
                    dst.writestr(item, data)
        else:
            shutil.copyfile(MODULE_ZIP, archive)
        staging = self.root / 'modules_update' / 'zygisk_vector'
        staging.mkdir(parents=True)
        temp = self.root / 'installer-temp'
        temp.mkdir()
        with zipfile.ZipFile(archive) as package:
            customize = self.root / 'customize.sh'
            customize.write_bytes(package.read('customize.sh'))
            (temp / 'module.prop').write_bytes(package.read('module.prop'))
        bootstrap = '''
ui_print() { printf '%s\\n' "$*"; }
abort() { printf '%s\\n' "$*"; exit 1; }
grep_prop() { [ -n "${2:-}" ] || return 0; sed -n "s/^$1=//p" "$2" | head -n 1; }
set_perm_recursive() { :; }
set_perm() { chmod "$4" "$1"; }
# KernelSU supplies BusyBox's -s flag. GNU/uutils hosts call it --status.
sha256sum() {
    if command -v busybox >/dev/null 2>&1; then
        busybox sha256sum "$@"
    elif [ "$*" = '-c -s -' ]; then
        command sha256sum -c --status -
    else
        command sha256sum "$@"
    fi
}
. "$1"
'''
        environment = dict(os.environ, MODPATH=str(staging), TMPDIR=str(temp),
                           ZIPFILE=str(archive), ARCH=arch, IS64BIT='true', API='37')
        result = subprocess.run(SHELL + ['-c', bootstrap, 'installer-test', str(customize)],
                                env=environment, capture_output=True, text=True, timeout=25)
        return result, staging

    def test_complete_installer_automatically_prepares_upgrade(self):
        daemon = self.spawn('lspd')
        manager = self.spawn('org.lsposed.manager')
        result, staging = self.install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_stopped(daemon, manager)
        self.assertIn('Upgrade handover prepared', result.stdout)
        self.assertEqual((staging / 'upgrade-runtime.sh').read_bytes(), (self.active / 'upgrade-runtime.sh').read_bytes())

    def test_corrupt_payload_keeps_old_runtime_running(self):
        daemon = self.spawn('lspd')
        manager = self.spawn('org.lsposed.manager')
        result, _ = self.install(corrupt=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Failed to verify manager.apk', result.stdout)
        self.assert_alive(daemon, manager)

    def test_unsupported_architecture_keeps_old_runtime_running(self):
        daemon = self.spawn('lspd')
        result, _ = self.install(arch='unsupported')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Unsupported platform', result.stdout)
        self.assert_alive(daemon)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--shell', default='/bin/sh')
    parser.add_argument('--module-zip', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if not sys.platform.startswith('linux'):
        parser.error('These integration tests require Linux /proc')
    SHELL = shlex.split(args.shell)
    MODULE_ZIP = args.module_zip.resolve() if args.module_zip else None
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(UpgradeTests)
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'shell': args.shell, 'tests': outcome.testsRun, 'failures': len(outcome.failures),
              'errors': len(outcome.errors), 'skipped': len(outcome.skipped),
              'passed': outcome.wasSuccessful(), 'scope': 'Linux host simulation; no Android device installation'}
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
    sys.exit(0 if outcome.wasSuccessful() else 1)
