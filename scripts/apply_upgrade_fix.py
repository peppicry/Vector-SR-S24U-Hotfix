#!/usr/bin/env python3
"""Apply the shell-only 3151-r2 update to the pinned, already-patched source tree."""
from pathlib import Path
import hashlib

REPO = Path(__file__).resolve().parents[1]
PINNED = {
    'zygisk/module/customize.sh': '92bf148c7ab3751b83c55701715458091f9c6284f8fd800fe0411324f798ec1c',
    'zygisk/module/service.sh': '87695dc0b87bcec55b547ca0cbe37530c9f48d1b59f833a9c3bc34f21578fb9c',
    'zygisk/module/module.prop': '01b502e457da2844dd2317d218c72ee4c3fb420048c48e97fe8d70e2ccae2ac3',
}


def changes(source_root):
    updates = {}
    originals = {}
    for name, expected in PINNED.items():
        data = (source_root / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f'{name}: unexpected pinned source; no files changed')
        originals[name] = data.decode('utf-8')

    customize = originals['zygisk/module/customize.sh']
    old_files = 'module.prop action.sh service.sh uninstall.sh sepolicy.rule framework/lspd.dex cli daemon.apk daemon manager.apk'
    if customize.count(old_files) != 1 or customize.count('ui_print "- Welcome to Vector-SR!"') != 1:
        raise ValueError('Installer anchors changed; no files changed')
    customize = customize.replace(old_files, old_files + ' upgrade-runtime.sh', 1)
    handover = '''# All payloads and permissions are ready before touching the running framework.
# Do not launch from modules_update: its path changes when the update is applied.
vr_parent="${MODPATH%/*}"
case "$vr_parent" in
    */modules_update) vr_parent="${vr_parent%_update}" ;;
    */modules) ;;
    *) abort "! Cannot determine the active module directory; runtime was not changed" ;;
esac
. "$MODPATH/upgrade-runtime.sh" || abort "! Cannot load the Vector upgrade helper"
vector_stop_runtime "$vr_parent/${MODPATH##*/}" all || abort "! Previous Vector service could not be stopped; restart before retrying"
ui_print "- Upgrade handover prepared. Perform the usual soft restart to activate this version."

'''
    updates['zygisk/module/customize.sh'] = (customize.replace('ui_print "- Welcome to Vector-SR!"', handover + 'ui_print "- Welcome to Vector-SR!"', 1)).encode()
    prop = originals['zygisk/module/module.prop']
    if prop.count('version=${versionName} (${versionCode})') != 1:
        raise ValueError('Version anchor changed; no files changed')
    updates['zygisk/module/module.prop'] = prop.replace('version=${versionName} (${versionCode})', 'version=${versionName} (${versionCode}) - upgrade fix r2', 1).encode()
    for name in ['service.sh', 'upgrade-runtime.sh']:
        updates['zygisk/module/' + name] = (REPO / 'module-overrides' / name).read_bytes()
    return updates


def main():
    root = Path.cwd()
    updates = changes(root)
    for name, data in updates.items():
        (root / name).write_bytes(data)
    print('Applied 3151-r2 automatic Vector runtime handover (shell-only)')


if __name__ == '__main__':
    main()
