# Rebuilding the 3151 candidate

This target is an unofficial rebase of the Samsung Shared-UID hotfix onto Vector-SR `ccf240320c838ee097b7bd4d996f314d25643cb0`, module version `v1.2 (3151)`. It has not been validated on hardware.

Use the repository's **Build candidate Vector-SR S24U hotfix** workflow for the recorded all-ABI build environment. Its default output is a CI artifact; optional publication creates a new prerelease without replacing 3136.

## Rebuild from the corresponding-source package

The source ZIP contains the patched upstream files and checked-out submodule contents, plus `s24u-hotfix-build/apply_samsung_hotfix.py`, these instructions and `SUBMODULES.txt`. The adjacent release assets also include the exact source patch, source metadata and SHA-256 checksums.

Git metadata is intentionally excluded from source archives. Upstream Gradle derives `versionCode` from `refs/remotes/origin/master` and `versionName` from Git tags. Unzipping the source alone therefore does not restore the version identity. To rebuild the recorded candidate with its correct version, obtain the pinned Git history and apply the included script:

```sh
# Replace this value with the absolute directory where the corresponding-source ZIP was unpacked.
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
git diff --check
bash tests/run-native-regressions.sh
bash tests/run-daemon-regressions.sh
./gradlew zipAll
```

The workflow records Java 21, Android SDK/build tools 36, NDK `29.0.13113456`, Ninja `1.12.1` and the upstream Gradle wrapper. Native and daemon host tests run on Ubuntu. Install/configure those prerequisites independently before a local full build. Compare `git submodule status --recursive` with the included `SUBMODULES.txt`.

The all-ABI release output is `zygisk/release/Vector-SR-v1.2-3151-Release.zip`. For the optional arm64-only output, follow the ABI-filter change in `.github/workflows/build-arm64.yml` at the compatibility repository commit recorded in `SOURCE-METADATA.txt`.

These steps restore the pinned source, patch and version identity. Byte-identical ZIP/APK reproduction is not established; timestamps, signing and build environment can affect final digests. Source reproduction and successful compilation do not establish runtime compatibility or authorize a device installation.
