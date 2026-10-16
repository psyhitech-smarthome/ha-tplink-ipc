# Actions

Use `tplink_ipc_local.control` with `entry_id`, `operation`, and optional `data`. The equivalent authenticated WebSocket message type is `tplink_ipc_local/control` with the same fields. WebSocket callers must be administrators. No device address, password or arbitrary method can be supplied by the caller.

| Operation | Data | Result |
| --- | --- | --- |
| `state` | `{}` | Discovered controls, values, compatibility, presets, regions and schedules |
| `set` | `{key, value}` | Property saved and normalized readback verified |
| `move` | `{direction: left/right/up/down}` | ONVIF relative movement, distance 0.06, speed 0.35; accepted only |
| `stop` | `{}` | ONVIF stop; accepted only |
| `preset_save` | `{id: "1".."8", name}` | Save current position; readback verifies entry, not coordinates |
| `preset_goto` | `{id}` | Existing preset only; accepted only |
| `preset_delete` | `{id}` | Existing preset removed; readback verified |
| `region_save` | `{module, id, points}` | Edit existing region; 2 points for crossing line, 4 otherwise; integer coordinates 0–10000 |
| `cover_save` | `{regions, expected}` | Up to 4 rectangles; expected previous values prevent stale updates |
| `schedule_save` | `{module, days}` | Full week; ordered, non-overlapping intervals; readback verified |
| `alarm_start` | `{}` | Alarm accepted, automatic stop scheduled after 15 seconds |
| `alarm_stop` | `{}` | Stop request accepted |
| `system_time` | `{}` | Source ONVIF time synchronization requested |
| `system_reboot` | `{}` | Source ONVIF reboot requested; interrupts media |
| `firmware_check` | `{refresh: false}` | Read vendor candidate metadata; true asks the device to refresh; never upgrades |

Detection modules: `people_detection`, `linecrossing_detection`, `intrusion_detection`, `regionexiting_detection`. `schedule_save` also supports `record_plan`. Days must include `monday` through `sunday`, each a list of up to 10 intervals: `0800-1200` for detection; `0000-2400:1` for continuous or `0000-2400:2` for event SD recording. Device support and a working SD card are separate requirements.

A cover rectangle has `x_coor`, `y_coor`, `width`, `height` integers. `expected` is the prior list with string values as returned by the device. Region saving does not enable detection; cover saving does not turn on the cover switch.

Unknown firmware is read-only. Transport errors do not prove a write failed before reaching the camera. After an uncertain outcome, refresh before retrying; do not blindly repeat movement, preset overwrite, alarm or reboot actions.

## Experimental talk

`tplink_ipc_local/talk` accepts explicit `entry_id` and `operation: start|audio|stop`. Audio is base64-encoded PCMA at 8000 Hz, at most 3200 decoded bytes per message. One client owns a device's channel; different devices have isolated sessions. Administrator access and the integration's experimental talk option are required. The card asks for microphone permission only on a user action. Protocol handshake and silence transport were tested previously; audible speech is not yet verified.
