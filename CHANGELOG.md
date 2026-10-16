# Changelog

## 0.1.0 — Initial beta

- Extract the existing mainland TP-Link IPC controller into a standalone HA integration.
- Replace single-household constants with explicit config-entry routing and device-derived identity.
- Add strict model/hardware checks and read-only behavior for unverified firmware.
- Isolate talk sessions and unload cleanup per device; keep experimental talk disabled by default.
- Package optional control card, documented admin action service, diagnostics and HACS metadata.
- Add synthetic regression tests and CI. No automatic household runtime upgrade.
