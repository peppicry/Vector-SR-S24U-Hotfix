# Vector-SR S24 Ultra Samsung Shared-UID Hotfix

This project provides a fix for a problem observed with Vector-SR on Samsung devices: after a soft restart, repeated errors could overload the system and cause the phone to heat up.

The original fix was tested on a Galaxy S24 Ultra running One UI 8.5. **3151 is now available as a prerelease**, and its manager opened successfully on a Galaxy S25 Ultra after the upgrade recovery described below.

> [!NOTE]
> This is an unofficial modified project. It is not affiliated with or endorsed by the Vector-SR developers, Vector developers, or Samsung. Credit for the original project remains with JingMatrix, byemaxx, and the other contributors. Please report issues with this modification in this repository.

## Which version should I download?

| Version | Status | Download |
| --- | --- | --- |
| **3151 — prerelease** | Test build. Manager opening and One UI X loading were verified on a Galaxy S25 Ultra running Android 17 / One UI 9, after manual upgrade recovery. | [Download the 3151 module (.zip)](https://github.com/peppicry/Vector-SR-S24U-Hotfix/releases/download/v1.2-3151-s24u-hotfix/Vector-SR-v1.2-3151-S24U-SharedUID-Hotfix-Candidate-Release.zip) · [Release details](https://github.com/peppicry/Vector-SR-S24U-Hotfix/releases/tag/v1.2-3151-s24u-hotfix) |
| **3136 — One UI 8.5** | Previous release retained for users staying on One UI 8.5. The original S24 Ultra test record is in the technical details below. | [Open the 3136 release](https://github.com/peppicry/Vector-SR-S24U-Hotfix/releases/tag/v1.2-3136-s24u-hotfix) |
| **One UI X 1.7.0** | Companion release from the original setup tested on One UI 8.5. | [Open One UI X](https://github.com/peppicry/OneUIX-VectorSR-S24U/releases/tag/v1.7.0-vectorsr-s24u) |

To install 3151 through your module manager, choose **`Vector-SR-v1.2-3151-S24U-SharedUID-Hotfix-Candidate-Release.zip`**. Files with `source` in their names and GitHub's automatic “Source code” links contain source code, not the installable module.

GitHub still labels 3136 as “Latest” because 3151 is a prerelease. The 3151 download is available through the link above.

## Upgrading from 3136 to 3151

If you install 3151 and opening Vector brings up Android's bug report warning instead of the manager, the old background service may still be running. We encountered this on a Galaxy S25 Ultra with Android 17 / One UI 9, even after a KernelSU soft restart.

On that device, the new 3151 manager was already in place, but the background service was still running 3136. The version mismatch prevented the manager from opening.

To recover, we stopped the old service and the manager processes, started the 3151 service, and then performed another soft restart through Root My Galaxy. Settings were preserved. The manager then opened normally, and One UI X loaded again.

**This recovery was performed manually. The current ZIP does not handle this handover automatically**, so reinstalling the module and repeating a soft restart may not be enough.

Seeing `com.android.shell` in the manager is normal: Vector uses that package to host its interface.

Manager opening was confirmed on this S25 Ultra. Other module features and devices still need testing.

If you are staying on **One UI 8.5**, the [3136 release remains available](https://github.com/peppicry/Vector-SR-S24U-Hotfix/releases/tag/v1.2-3136-s24u-hotfix).

## Technical details and history

<details>
<summary>View the fix, tests, build process, and file hashes</summary>

## Modified-version notice

- Original hotfix: **2026-08-22**; current upstream rebase: **2026-10-24**
- Upstream project: `byemaxx/Vector-SR`
- Pinned upstream revision: `ccf240320c838ee097b7bd4d996f314d25643cb0`
- Resulting candidate module version: `v1.2 (3151)`
- Historical device-tested base: `a8f500ddb1c8f53efec6fd02b6520c321db34627`, `v1.2 (3136)`
- Upstream authors credited by the module: JingMatrix, byemaxx
- License: **GNU General Public License v3.0 (GPL-3.0)**

The Vector-SR project, its history, names, and original code remain credited to its upstream authors and contributors. This repository contains only the device-specific modification/build harness and does not claim authorship of Vector-SR itself.

## Why this exists

On the tested Samsung build, legacy Xposed callbacks around `ApplicationPackageManager#getApplicationInfoAsUser("android.uid.system", ...)` caused an exception/log storm after soft restart. `system_server` CPU usage rose dramatically and the phone heated up.

The hotfix does two deliberately narrow things:

1. Bypasses legacy callbacks only when the hooked method is named `getApplicationInfoAsUser` and its first argument is exactly `android.uid.system`, then calls the original method directly and preserves throwable/result semantics.
2. Adds a logging safety net that suppresses only `android.content.pm.PackageManager$NameNotFoundException` whose message is exactly `android.uid.system`. All other legacy errors remain logged.

### Does the official version still need this patch?

As checked on **2026-10-24**, the latest tagged upstream release is `v1.2 (3131)`; current `master` is `v1.2 (3151)` at the pinned commit above. Neither includes this Samsung guard. Both Java files targeted by the hotfix are byte-identical between the original 3136 base and current 3151 upstream.

An isolated host-JVM test using the actual upstream hook-dispatch and logging methods, Android stubs, and a synthetic legacy callback that rethrows the lookup exception reproduced one error log per call on official 3131, 3136 and 3151. With this unchanged hotfix, the exact pseudo-package lookup bypassed legacy callbacks and produced no error logs while preserving the original exception. Ordinary lookups and unrelated errors remained active. This demonstrates the Java failure path; it does **not** reproduce Samsung soft restart, high CPU or heat on hardware. See [the rebase review](docs/REBASE_2026-10-24.md).

The [complete repository audit](docs/AUDIT_2026-10-24.md) also found a null-logging regression in the historical patch, mutable release publication, an unpinned version counter and incomplete standalone rebuild instructions. The candidate corrects those issues without changing the Shared-UID matching policy. [Build instructions](docs/BUILDING.md) record how to restore the pinned source/version identity.

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
- The workflow checks out the immutable upstream revision and its submodules, verifies the expected version, freezes the reference used by upstream's version counter, runs upstream host regressions, applies the patch, verifies the diff, and builds from that tree.
- Every GitHub Release publishes the installable ZIP **and a corresponding-source ZIP containing the patched upstream working tree with checked-out submodule contents**, plus the exact patch diff, source metadata, and SHA-256 checksums.
- `UPSTREAM.md` records the upstream relationship and attribution.
- `NOTICE.md` records the unofficial-build and support boundary.
- `LICENSE` carries GPL-3.0. The workflow verifies that it matches the pinned upstream license before packaging.

This structure is intentionally designed so recipients of the binary have direct access to the source used to produce it.

## Builds

### Current candidate: all-ABI build

Run **Build candidate Vector-SR S24U hotfix**. It uses the original all-ABI packaging strategy, targets 3151, and uploads a CI artifact without publishing a release by default. Enable `publish_prerelease` only to publish the separately named `v1.2-3151-s24u-hotfix` candidate. Publication refuses an existing candidate tag/release and never overwrites the 3136 baseline or marks the candidate as latest.

The modified all-ABI candidate passed [its full CI build and host regressions](https://github.com/peppicry/Vector-SR-S24U-Hotfix/actions/runs/40112689035). On 2026-10-24, its parasitic manager opened on a Galaxy S25 Ultra (SM-S938B), Android 17 / One UI 9, after the manual upgrade recovery described above; IPC binder reinjection and One UI X loading were also observed. This does not validate every module feature, thermal behavior, clean installation, or other firmware.

### Optional: arm64-only build

Run **Build arm64-only Vector-SR hotfix candidate**. It builds the same 3151 rebase with an arm64-only ABI filter. Keep the historical 3136 release as the One UI 8.5 baseline; the new arm64 candidate is not device-tested.

## Device-tested artifact fingerprint

Installable ZIP used for the original device validation:

`SHA-256 f2d7e6a2a822b96f83479a6d921111351ca8181d44c71d296f76952ea5c24ada`

The ZIP currently attached to the historical 3136 GitHub release has a different published fingerprint:

`SHA-256 77db8d571affc95daca7f08e291ef0f1fe89a6b52968704700286559e36e86e1`

That published ZIP is retained as-is. Its digest must not be described as the fingerprint of the original device-tested file above. A matching local copy of the original file was not located during this review.

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

</details>

## License

Vector-SR and this modification use **GPL-3.0**. Credit to the original authors is preserved, and the source code used for each build is attached to its release.

See [LICENSE](LICENSE), [UPSTREAM.md](UPSTREAM.md), and the source archives attached to the published releases.

The software is provided without warranty. Check the documented tests and limitations before choosing a version.
