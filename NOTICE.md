# Unofficial modified-build notice

This repository distributes an unofficial, device-specific modification/build of **Vector-SR**. The historical 3136 baseline was tested on a Samsung Galaxy S24 Ultra / One UI 8.5 configuration. The published packaging revision is **3151-r2**, based on framework **1.2 (3151)**. Manager opening and One UI X loading were observed on a Galaxy S25 Ultra after manual recovery; the r2 automatic upgrade path still requires device validation.

It is **not an official Vector-SR or Vector release** and is not affiliated with or endorsed by byemaxx, JingMatrix, Samsung, or other upstream developers.

## Attribution

- Immediate upstream: `byemaxx/Vector-SR`
- Current pinned revision: `ccf240320c838ee097b7bd4d996f314d25643cb0` (framework `v1.2 / 3151`).
- Historical tested base: `a8f500ddb1c8f53efec6fd02b6520c321db34627` (`v1.2 / 3136`).
- Upstream project lineage includes `JingMatrix/Vector` and its credited open-source dependencies.
- Upstream/derived license: GNU General Public License v3.0.
- Original modification date: 2026-08-22; current upstream rebase: 2026-10-24.

Original copyrights and notices remain with their respective authors. The compatibility patch maintained here does not replace upstream attribution.

## Distribution and source

Binary Releases from this repository are accompanied by the corresponding patched source, exact patch diff, source metadata, and checksums. The source archive includes the checked-out contents of upstream submodules used by the build.

The historical One UI 8.5 release remains available separately. Each packaging revision uses a new tag and does not replace earlier releases or their assets. Framework version, packaging revision, GitHub release status and device validation are separate facts. Historical device-test results do not apply automatically to a source rebase.

## Support

If an issue appears only in this modified build, report it here. Upstream maintainers should not be expected to support modification-specific behavior that has not been reproduced on their unmodified releases.

This notice is informational and does not add restrictions beyond GPL-3.0.
