# Vector-SR S24 Ultra Samsung Shared-UID Hotfix

Private build harness for a device-tested Vector-SR hotfix used on Samsung Galaxy S24 Ultra / One UI 8.5 with KernelSU soft restart.

## Why this exists

On the tested Samsung build, legacy Xposed callbacks around `ApplicationPackageManager#getApplicationInfoAsUser("android.uid.system", ...)` caused an exception/log storm after soft restart. `system_server` CPU usage rose dramatically and the phone heated up.

The hotfix does two deliberately narrow things:

1. Bypasses legacy callbacks only when the hooked method is named `getApplicationInfoAsUser` and its first argument is exactly `android.uid.system`, then calls the original method directly and preserves its throwable/result semantics.
2. Adds a logging safety net that suppresses only `android.content.pm.PackageManager$NameNotFoundException` whose message is exactly `android.uid.system`. All other legacy errors are still logged.

## Upstream pin

- Upstream: `byemaxx/Vector-SR`
- Commit: `a8f500ddb1c8f53efec6fd02b6520c321db34627`
- Resulting module version: `v1.2 (3136)`

The upstream source is checked out during CI; this repository stores only the device-specific patch/build harness.

## Device-tested result — 2026-08-22

After installing the all-ABI build on the S24 Ultra:

- `NameNotFoundException: android.uid.system` stayed at **0**.
- The previous VectorLegacyBridge log flood stopped.
- `system_server` CPU load returned to normal and the abnormal heating disappeared.
- One UI X continued loading through the legacy bridge.
- Samsung ASKS BuildType Fix (`dev.siro.asksfix`) loaded in `system_server` and worked after a clean soft restart.
- The Samsung real-time network speed option continued working.

Known unrelated One UI X errors (`NetspeedViewController$NetworkSpeedManager$1` and `QSClockQuickStarHelper` missing on this One UI build) are startup-only and are not part of this Vector bug.

## Builds

### Recommended: device-tested build

Run **Build device-tested Vector-SR hotfix**. This keeps the same ABI packaging strategy as the build that was installed and tested.

### Optional: arm64-only build

Run **Build arm64-only Vector-SR hotfix**. It is smaller and CI-tested for the S24 Ultra architecture. Keep the device-tested build as the recovery baseline.

## Device-tested artifact fingerprint

Installable ZIP used for the original validation:

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

## Important

This is a device-specific private patch, not an upstream replacement. Do not merge it into unrelated Root My Galaxy source trees. Preserve the tested baseline unless a new Vector-SR upstream version is deliberately rebased and revalidated on-device.
