# One UI X — Vector-SR S24 Ultra compatibility build

This branch does **not** modify the installed Vector-SR hotfix and does not change the `main` branch baseline. It is a test-only compatibility build until the Samsung Settings toggle is validated on-device.

It builds a minimally patched copy of upstream One UI X 1.7.0, pinned to:

- Repository: `SoClear/OneUIX`
- Commit: `78e2ef1d10320aab293631f97ec636cf64d4cbea`
- Upstream version: `1.7.0 (9)`
- Patched versionName: `1.7.0-vectorsr-s24u-compat1`

## Why this patch exists

On the tested S24 Ultra / One UI 8.5 setup, the native Samsung network-speed indicator can remain visible while the Settings toggle disappears.

Upstream One UI X currently overrides only:

`CscFeature_Common_SupportZProjectFunctionInGlobal`

Recent Samsung builds also gate the Settings preference with:

`CscFeature_Setting_SupportRealTimeNetworkSpeed`

The compatibility patch:

1. Hooks `SemCscFeature#getBoolean` in both `com.android.settings` and `com.android.systemui`.
2. Hooks **all overloads** of `getBoolean`, instead of relying on one signature.
3. Returns `true` only for the two network-speed CSC feature keys above.
4. Adds a diagnostic Xposed log marker:
   `[OneUIX-VectorSR] network-speed CSC hooks active in <package>`

No network-speed unit conversion is included in this compatibility-only build. The Mbps/Gbps change should be layered on only after the Settings toggle is confirmed restored.

## Expected Vector-SR behavior

The device-tested Vector-SR hotfix remains unchanged. Its Samsung patch only bypasses legacy callbacks for the exact `ApplicationPackageManager#getApplicationInfoAsUser("android.uid.system", ...)` probe and suppresses only the matching `NameNotFoundException`. This One UI X compatibility patch runs in Settings/SystemUI and does not alter that hotfix path.

## Validation after installing and activating One UI X

After a clean soft restart, open Samsung Settings once, then run:

```sh
su -c '
V=$(ls -t /data/adb/lspd/log/verbose_*.log 2>/dev/null | head -1)
echo "===== OneUIX Vector-SR hooks ====="
grep -F "[OneUIX-VectorSR] network-speed CSC hooks active" "$V" || true

echo
echo "===== Samsung network_speed setting ====="
settings get system network_speed
'
```

Expected log coverage includes both:

- `com.android.settings`
- `com.android.systemui`

Then check:

`Settings -> Notifications -> Advanced settings`

The real-time network-speed toggle should be present again.

## Regression safety check

The original Vector-SR hotfix counter should remain clean:

```sh
su -c '
V=$(ls -t /data/adb/lspd/log/verbose_*.log 2>/dev/null | head -1)
echo -n "android.uid.system: "
grep -c "NameNotFoundException: android.uid.system" "$V" 2>/dev/null || true
echo -n "VectorLegacyBridge errors: "
grep -c " E/VectorLegacyBridge " "$V" 2>/dev/null || true
'
```

The important hotfix-specific value remains `android.uid.system: 0`.
