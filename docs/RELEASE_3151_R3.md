Vector-SR framework **1.2 (3151)**, packaging revision **r3**, proposed as a separate prerelease.

## Changes from r2

- Keep the signed APKs, framework DEX, native binaries and Samsung hotfix unchanged.
- Preserve a recognized current daemon before checking blockers for a new start.
- If only an unidentified lspd or debug APK override is found, leave the runtime untouched and report an inconclusive start decision with neutral service status.
- After one launch, look for a positively attributable current process in two samples without assuming the launcher's PID is the daemon's PID. Missing APK descriptors, launcher exit or timeout remain inconclusive and do not trigger another launch or termination.
- Separate automatic build/test runs from explicit manual prerelease publication. Never replace r2, 3136 or any existing release.

## Validation limits

A positive observation establishes that an attributable current process was present in two samples. It does not establish process origin, Android Binder readiness, successful reinjection or continued operation afterward. An inconclusive result is not daemon failure; neutral service exit status is not proof that the framework is active. The observer requests no Android restart. The daemon's existing recovery policy is unchanged.

The 26 passing host test executions recorded for r2 belong to r2. This revision requires fresh host results attached in `UPGRADE-TESTS.json`; no Android automatic-upgrade validation is claimed.

The [3151-r2 release](https://github.com/peppicry/Vector-SR-S24U-Hotfix/releases/tag/v1.2-3151-s24u-hotfix-r2) and the [3136 release for One UI 8.5](https://github.com/peppicry/Vector-SR-S24U-Hotfix/releases/tag/v1.2-3136-s24u-hotfix) remain available with their original assets.
