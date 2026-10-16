# Migration and validation

## Existing private custom component

This repository uses the same `tplink_ipc_local` domain as the original single-device implementation. Do not install a second copy under another folder or run both in parallel.

1. Back up the current component and dashboard configuration privately.
2. Verify that the existing integration entry's unique ID is the camera's normalized MAC. The historical deployment used that form; entries with another form should be removed through HA and added again after the upgrade.
3. Replace only the custom component files, restart HA, then reload the linked ONVIF entry if necessary. The new integration keeps `onvif_entry_id` and its existing MAC-based property unique IDs. Registry names already assigned by HA remain valid.
4. Replace the old `/local/camera-control-card.js` dashboard resource with `/tplink_ipc_local/camera-control-card.js?v=0.1.0` and explicitly configure this integration's `entry_id` plus its ONVIF camera `entity`.
5. Existing private WebSocket callers must now pass `entry_id`. Hardcoded dashboard links, visitor/AI counters and recorder assumptions were removed.
6. Talk defaults to disabled. Enable it in options only when testing that feature.

The public release is prepared and tested separately; publication does not replace any existing household runtime. Keep original runtime backups outside Git. Never overwrite running `.storage` files with old copies.

## Validation layers

- Synthetic tests cover identity, model/firmware gating, capability narrowing, session expiry, config flow, entry targeting, unload isolation, diagnostics and input validation.
- Read-only device inspection validates model identity and discovered settings using the public client. No credentials or response dumps belong in the repository.
- Historical single-device evidence includes 72 settings parsed and reapplied with matching readback, LED toggled/restored, preset creation/deletion, regions/plans saved unchanged, and talk silence transport. This is evidence for protocol behavior, not a blanket claim for every value or device.
- The public multi-entry packaging and concurrent physical cameras still need wider community testing.

For real-device acceptance, take an original snapshot privately, test small reversible changes, and restore it. Avoid alarms, reboot, disk formatting and upgrades as routine test steps. Validate camera motion/recording physically when relevant; successful API responses alone are insufficient.
