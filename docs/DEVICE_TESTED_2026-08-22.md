# Device validation — 2026-08-22

Target: Samsung Galaxy S24 Ultra, arm64, One UI 8.5 environment using Root My Galaxy / KernelSU soft restart.

Validated behaviors:

- Vector-SR module reports `v1.2 (3136)`.
- Hotfix-specific `NameNotFoundException: android.uid.system` count remains 0.
- Log growth returned to normal rather than multi-megabyte flood behavior.
- Phone no longer remains abnormally hot after soft restart.
- One UI X loads in Settings, SystemUI, and system_server.
- Restarting SystemUI restores hooks if SystemUI predates injection.
- Samsung ASKS BuildType Fix loads `dev.siro.asksfix.MainHook` in system_server and functions.
- No reason was found to modify Vector-SR further after stabilization.

Device-tested installable ZIP SHA-256:

`f2d7e6a2a822b96f83479a6d921111351ca8181d44c71d296f76952ea5c24ada`
