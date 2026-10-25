Vector-SR **1.2 (3151), packaging revision r2**, with the automatic upgrade fix.

## Install this ZIP

Choose **`Vector-SR-v1.2-3151-r2-S24U-SharedUID-Hotfix-Release.zip`** in your module manager, then perform the usual soft restart through KernelSU / Root My Galaxy. The installer does not initiate a phone restart on its own.

Files with `source` in their names and GitHub's automatic “Source code” links are for rebuilding, not installation.

## What was fixed?

When upgrading from 3136, the old Vector background service could survive installation and a soft restart. It then rejected the 3151 manager, and Android's bug report warning appeared instead of Vector.

This revision validates the installation files first, then automatically stops the previous Vector service and manager processes. The usual soft restart starts the installed 3151 service from the correct module directory. You no longer need to run manual commands to replace the old service.

The startup script also checks for stale Vector processes. A healthy current service is preserved during later soft restarts. Process checks use both the process name and its open Vector APK; unrelated daemons, `com.android.shell`, Zygote and `system_server` are not terminated by the upgrade helper. Configuration and module scopes are preserved.

The manager APK, daemon APK, framework DEX and native binaries are unchanged from the verified 3151 candidate. Their matching signing identity and manager signature verification are preserved.

## Validation

The installer and service scripts are tested on Linux with disposable processes that hold real APK file descriptors. Coverage includes upgrades, reinstalls, later soft restarts, corrupt packages, unrelated processes and a daemon that refuses to stop. `UPGRADE-TESTS.json` records the results and unchanged binary hashes; `SHA256SUMS.txt` covers all attached files.

The original 3151 manager and One UI X loading were observed on a Galaxy S25 Ultra with Android 17 / One UI 9 after manual recovery. **The new automatic installation path has not yet been tested on an Android device.** Host tests do not establish every module feature, thermal behavior or compatibility with other firmware.

Seeing `com.android.shell` in the manager is normal: Vector uses that package to host its interface.

## Previous versions and source

The [3136 release remains available for users staying on One UI 8.5](https://github.com/peppicry/Vector-SR-S24U-Hotfix/releases/tag/v1.2-3136-s24u-hotfix).

This is a new packaging revision of the same 3151 framework. The original candidate is retained for traceability. The corresponding-source ZIP, complete source patch, build metadata and checksums are attached.

This is an unofficial modification, not affiliated with or endorsed by byemaxx/Vector-SR, JingMatrix/Vector, Samsung or their upstream developers. Credit to the original authors and the GPL-3.0 license are preserved. Please report modification-specific issues in this repository.
