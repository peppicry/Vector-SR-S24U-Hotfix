# Building 3151 packaging revisions

The framework remains Vector-SR `v1.2 (3151)` at upstream commit `ccf240320c838ee097b7bd4d996f314d25643cb0`. Revision r2 changes the installer and startup scripts, adds a runtime handover helper and displays the packaging revision in `module.prop`.

The published r2 ZIP reuses the verified 3151 manager APK, daemon APK, framework DEX and native binaries byte for byte. It preserves their matching signing identity. It does not disable manager signature verification or change the Samsung Shared-UID Java guard.

## Reproduce the published r2 package

The **Package and release 3151 automatic upgrade fix** workflow downloads four exact assets from the original 3151 release. `scripts/package_upgrade_release.py` verifies their pinned SHA-256 digests before using them:

- `Vector-SR-v1.2-3151-S24U-SharedUID-Hotfix-Candidate-Release.zip`
- `Vector-SR-v1.2-3151-S24U-Hotfix-source.zip`
- `Vector-SR-v1.2-3151-S24U-Hotfix.patch`
- `SUBMODULES.txt`

Place those files in `base/` and check out the compatibility repository commit recorded in the r2 `SOURCE-METADATA.txt` (`66058f01336099126943e935a352dc50c9c9f9f3`). Reproducing r2 requires that historical source, not the current `main` branch. Run:

```sh
python3 scripts/package_upgrade_release.py --base-dir base --output out --repository-commit "$(git rev-parse HEAD)"
python3 tests/test_upgrade_runtime.py --shell /bin/sh --module-zip out/Vector-SR-v1.2-3151-r2-S24U-SharedUID-Hotfix-Release.zip --report dash-report.json
python3 tests/test_upgrade_runtime.py --shell 'busybox ash' --module-zip out/Vector-SR-v1.2-3151-r2-S24U-SharedUID-Hotfix-Release.zip --report ash-report.json
python3 scripts/package_upgrade_release.py --base-dir base --output out --repository-commit "$(git rev-parse HEAD)" --test-report dash-report.json --test-report ash-report.json
(cd out && sha256sum --check SHA256SUMS.txt)
```

These Linux tests use disposable processes with real `/proc` entries and open APK file descriptors. They run the complete installer against the corrected ZIP, including a corrupt-payload case that must leave the old service running. They never install anything on an Android device.

The packager verifies all internal module checksums, checks that unrelated binary/source contents remain unchanged, and verifies that the complete source patch applies. It includes the test reports and preserved APK hashes in `UPGRADE-TESTS.json`.

## Prepare a new packaging revision

The current scripts take the packaging revision from `PACKAGING_REVISION` in `scripts/apply_upgrade_fix.py`. The packager derives the module/source/patch names, displayed module revision, source metadata and release-note filename from that value. A changed package must use a fresh revision; never republish r2.

Use the same pinned inputs above. Run the packager, run both host test commands against its new module filename, then rerun the packager with both passing reports. This produces corresponding sources and checksums for the new revision without rebuilding signed payloads.

Push-triggered workflow runs only build, test and upload artifacts. Manual runs also default to no publication. Explicit `publish_prerelease=true` on `main` can upload a new draft with its own tag and publish it only after every asset is attached; an existing tag or API lookup failure aborts publication. Earlier releases are never edited by this workflow. New prereleases do not replace the current Latest release.

## Recompile the complete framework from source

The corresponding-source ZIP includes the patched upstream files, checked-out submodules and build tools under `s24u-hotfix-build/`. Its scripts and overrides allow the same source changes to be applied to a clean pinned checkout. Git metadata is excluded, so restore the references used by upstream's version counter:

```sh
SOURCE_ROOT=/absolute/path/to/unpacked-source

git clone --no-checkout https://github.com/byemaxx/Vector-SR.git vector-build
git -C vector-build checkout --detach ccf240320c838ee097b7bd4d996f314d25643cb0
git -C vector-build submodule update --init --recursive
git -C vector-build/external/lsplant submodule update --init --recursive lsplant/src/main/jni/external/dex_builder

cd vector-build
test "$(git rev-list --count HEAD)" = '3151'
test "$(git describe --tags --abbrev=0 --match 'v[0-9]*' HEAD)" = 'v1.2'
git update-ref refs/remotes/origin/master "$(git rev-parse HEAD)"
python3 "$SOURCE_ROOT/s24u-hotfix-build/apply_samsung_hotfix.py"
python3 "$SOURCE_ROOT/s24u-hotfix-build/scripts/apply_upgrade_fix.py"

git diff --check
bash tests/run-native-regressions.sh
bash tests/run-daemon-regressions.sh
./gradlew zipAll
```

The recorded full build uses Java 21, Android SDK/build tools 36, NDK `29.0.13113456`, Ninja `1.12.1` and the upstream Gradle wrapper. Compare `git submodule status --recursive` with `SUBMODULES.txt`. The all-ABI output is `zygisk/release/Vector-SR-v1.2-3151-Release.zip`.

A fresh full compilation may use a different signing key and will not reproduce the published APK bytes automatically. The r2 packaging workflow deliberately avoids recompiling or re-signing the verified 3151 APKs.

## Validation limits

The original 3151 manager and One UI X loading were observed on a Galaxy S25 Ultra after manual recovery. The r2 automatic installer path is covered by Linux host integration tests; on-device automatic-upgrade validation is separate. Successful source/build/host checks do not prove every module feature, thermal behavior or compatibility with other firmware. A recognized current daemon is preserved before checking blockers for a new start. If no current daemon is recognized, an unidentified lspd or readable debug APK override leaves the runtime untouched with an inconclusive diagnostic and neutral service status. After one launch, a bounded observation can positively attribute a current process in two samples using its PID, start-time token, working directory and APK descriptor. It does not assume that the background launcher's PID is the daemon's PID, attribute process origin or prove Binder availability. Missing descriptors, a disappearing launcher or timeout remain inconclusive; the service returns neutral status and does not retry, stop processes or request an Android restart. Neutral status is not evidence that the framework is active. The existing daemon recovery policy is unchanged.
