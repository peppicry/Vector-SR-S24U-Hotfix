# Vector-SR S24 Ultra Samsung Shared-UID Hotfix

> [!IMPORTANT]
> **Unofficial modified project.** This repository is not affiliated with, sponsored by, or endorsed by **byemaxx/Vector-SR**, **JingMatrix/Vector**, Samsung, or their upstream developers. Modification-specific issues should be reported here rather than upstream unless they are first reproduced on an unmodified upstream build.

Device-tested compatibility hotfix for Vector-SR on a Samsung Galaxy S24 Ultra / One UI 8.5 environment using KernelSU soft restart.

## Modified-version notice

- Modified: **2026-08-22**
- Upstream project: `byemaxx/Vector-SR`
- Pinned upstream revision: `a8f500ddb1c8f53efec6fd02b6520c321db34627`
- Resulting module version: `v1.2 (3136)`
- Upstream authors credited by the module: JingMatrix, byemaxx
- License: **GNU General Public License v3.0 (GPL-3.0)**

The Vector-SR project, its history, names, and original code remain credited to its upstream authors and contributors. This repository contains only the device-specific modification/build harness and does not claim authorship of Vector-SR itself.

## Why this exists

On the tested Samsung build, legacy Xposed callbacks around `ApplicationPackageManager#getApplicationInfoAsUser("android.uid.system", ...)` caused an exception/log storm after soft restart. `system_server` CPU usage rose dramatically and the phone heated up.

The hotfix does two deliberately narrow things:

1. Bypasses legacy callbacks only when the hooked method is named `getApplicationInfoAsUser` and its first argument is exactly `android.uid.system`, then calls the original method directly and preserves throwable/result semantics.
2. Adds a logging safety net that suppresses only `android.content.pm.PackageManager$NameNotFoundException` whose message is exactly `android.uid.system`. All other legacy errors remain logged.

## Device-tested result — 2026-08-22

After installing the all-ABI build on the tested S24 Ultra:

- `NameNotFoundException: android.uid.system` stayed at **0**.
- The previous VectorLegacyBridge log flood stopped.
- `system_server` CPU load returned to normal and the abnormal heating disappeared.
- One UI X continued loading through the legacy bridge.
- Samsung ASKS BuildType Fix (`dev.siro.asksfix`) loaded in `system_server` and worked after a clean soft restart.
- The Samsung real-time network speed option continued working.

Known unrelated One UI X errors (`NetspeedViewController$NetworkSpeedManager$1` and `QSClockQuickStarHelper` missing on this One UI build) are startup/module-compatibility issues and are not part of this Vector bug.

## Required SystemUI-only restart after soft restart

On the tested `SM-S928B` / One UI 8.5 setup, **Vector-SR itself and the One UI X app can both open normally after a KernelSU soft restart**. The observed issue is narrower: One UI X functions that depend on hooks inside `com.android.systemui` can remain inactive even though the Vector framework/manager is otherwise available.

To activate those SystemUI-scoped functions, restart **only Samsung SystemUI** once:

```sh
su -c 'kill $(pidof com.android.systemui)'
```

Android respawns `com.android.systemui` automatically. The status bar / Quick Settings can disappear briefly while the process restarts. Once it returns, the tested setup activates the expected Vector-SR / One UI X functions in SystemUI.

This behavior must **not** be described as Vector-SR failing to open, One UI X failing to open, or the whole framework being dead. It is a **SystemUI-process hook activation/reinjection workaround**. It is also **not a thermal fix** and must not be conflated with the separate heating / `VectorLegacyBridge` log-storm issue addressed by this hotfix.

One execution after the soft restart is sufficient. There is no need to reinstall Vector-SR, restart One UI X, repeat the full soft restart, or repeatedly kill SystemUI when the functions are already active.

## Source, license, and reproducibility

- `scripts/apply_samsung_hotfix.py` contains the complete device-specific source modification.
- The workflow checks out the immutable upstream revision and its submodules, applies that patch, verifies the diff, and builds from that tree.
- Every GitHub Release publishes the installable ZIP **and a corresponding-source ZIP containing the patched upstream working tree with checked-out submodule contents**, plus the exact patch diff, source metadata, and SHA-256 checksums.
- `UPSTREAM.md` records the upstream relationship and attribution.
- `NOTICE.md` records the unofficial-build and support boundary.
- `LICENSE` carries GPL-3.0. The release workflow synchronizes the complete license text directly from the pinned upstream revision before publication.

This structure is intentionally designed so recipients of the binary have direct access to the source used to produce it.

## Builds

### Recommended: device-tested build

Run **Build device-tested Vector-SR hotfix**. This keeps the same ABI packaging strategy as the build that was installed and validated.

### Optional: arm64-only build

Run **Build arm64-only Vector-SR hotfix**. It is smaller and CI-tested for the S24 Ultra architecture. Keep the device-tested build as the recovery baseline.

## Device-tested artifact fingerprint

Installable ZIP used for the original device validation:

`SHA-256 f2d7e6a2a822b96f83479a6d921111351ca8181d44c71d296f76952ea5c24ada`

The later arm64-only CI build produced:

`SHA-256 9adbdd84528cd5e1f9c0d9ddd69c6b292fb2eaa5cdece166d964b849bb5d5a9b`

## Quick regression check

```sh
su -c '
V=$(ls -t /data/adb/lspd/log/verbose_*.log | head -1)
echo -n "android.uid.system: "
grep -c "NameNotFoundException: android.uid.system" "$V"
echo -n "VectorLegacyBridge errors: "
grep -c " E/VectorLegacyBridge " "$V"
ls -lh "$V"
'
```

The hotfix-specific counter should remain `android.uid.system: 0`.

## Support boundary

Please report bugs introduced by this modified build to this repository. Do not expect Vector-SR or Vector upstream maintainers to support behavior that cannot be reproduced on their unmodified builds.

## License

Vector-SR is GPL-3.0 and this derived modification/distribution remains GPL-3.0. See [`LICENSE`](LICENSE), [`UPSTREAM.md`](UPSTREAM.md), and the corresponding source attached to each Release.

No warranty is provided. Preserve the tested baseline unless a new upstream revision is deliberately rebased and revalidated on-device.
