"""Allowlisted diagnostics exclude addresses, credentials and camera content."""


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    return {
        "model": coordinator.identity["model"],
        "hardware": coordinator.identity["hardware"],
        "firmware": coordinator.identity["firmware"],
        "writable": coordinator.identity["writable"],
        "available": coordinator.last_update_success,
        "control_keys": [item["key"] for item in coordinator.controls],
    }
