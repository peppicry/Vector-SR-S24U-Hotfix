# Upstream, attribution, and licensing

This repository is an **unofficial device-specific modification/build harness** around Vector-SR. It is not affiliated with or endorsed by the upstream developers.

## Vector-SR

- Project: Vector-SR
- Upstream repository: `byemaxx/Vector-SR`
- Current pinned revision: `ccf240320c838ee097b7bd4d996f314d25643cb0`
- Framework version: `v1.2 (3151)`
- Published packaging revision: `3151-r2` (GitHub release); signed payloads are unchanged from the verified 3151 build
- Device evidence: the 3151 manager and One UI X loaded on a Galaxy S25 Ultra after manual recovery; the r2 automatic upgrade path has not been device-tested
- Latest tagged upstream release at review: `v1.2 (3131)`
- Historical device-tested base: `a8f500ddb1c8f53efec6fd02b6520c321db34627`, `v1.2 (3136)`
- Upstream authors credited by the built module: JingMatrix, byemaxx
- Upstream license: **GNU General Public License v3.0 (GPL-3.0)**
- Original modification date: **2026-08-22**; upstream rebase: **2026-10-24**

Vector-SR itself is a fork of the upstream Vector project. Original copyrights, source history, notices, and authorship remain with their respective upstream authors and contributors.

The device-specific changes maintained here are clearly identified as modifications and are distributed under GPL-3.0. The build workflow checks out the pinned upstream tree and submodules, applies the patch, and publishes a corresponding-source archive alongside the binary Release.

The historical Samsung hotfix adds 25 lines across `LegacyDelegateImpl.java` and `XposedBridge.java`; their unpatched blobs are identical between 3136 and 3151. The 3151 rebase keeps the same matching policy and adds one null check to preserve upstream `log(null)` behavior, for 26 inserted lines in total. The script now validates both anchors before writing. The rebase includes 15 upstream commits, including LSPlant/LSPlt updates, daemon compatibility and native logging/ELF fixes. See [the review](docs/REBASE_2026-10-24.md) and [repository audit](docs/AUDIT_2026-10-24.md) for evidence and validation limits.

## Retained One UI 8.5 baseline

The existing [`v1.2-3136-s24u-hotfix`](https://github.com/peppicry/Vector-SR-S24U-Hotfix/releases/tag/v1.2-3136-s24u-hotfix) release and its artifacts remain available without replacement. The 3151 releases use separate tags. Release status describes the packaging revision and does not imply that automatic upgrades have been validated on Android. The historical [One UI X 1.7.0 companion](https://github.com/peppicry/OneUIX-VectorSR-S24U/releases/tag/v1.7.0-vectorsr-s24u) is also still published.

## Support boundary

Problems that occur only with this modified build should be reported to this repository. Please do not send modification-specific reports to Vector-SR or Vector upstream unless the problem is also reproduced on an unmodified upstream build.
