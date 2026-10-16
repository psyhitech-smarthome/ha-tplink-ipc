# TP-Link IPC Local

Independent Home Assistant integration. Canonical checkout on mac-1: ~/psyhitech/ha-tplink-ipc.
Never add camera credentials, household addresses, identifiers, images, HA .storage files or runtime logs.
Keep the integration usable without HomeHub or a cloud account. Preserve firmware gating and explicit config-entry targeting.
Tests must use synthetic fixtures. Real-device validation defaults to read-only; never run alarms, reboot, format or upgrade as routine CI.
Commands: python -m unittest discover -s tests -v; python -m compileall -q custom_components; node --check custom_components/tplink_ipc_local/www/camera-control-card.js.
Run tests in the documented HA Python environment. Do not install development dependencies into the live HA environment.
