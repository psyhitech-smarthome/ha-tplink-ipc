"""Local IPC controls. ONVIF remains responsible for camera media."""

from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components.http import StaticPathConfig
from pathlib import Path

from .const import CONF_SOURCE, DOMAIN
from .coordinator import CameraCoordinator
from .api import CameraError
from . import websocket, services

PLATFORMS = [
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.TEXT,
    Platform.SENSOR,
]


async def async_setup(hass, config):
    websocket.register(hass)
    services.register(hass)
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                "/tplink_ipc_local/camera-control-card.js",
                str(Path(__file__).parent / "www/camera-control-card.js"),
                False,
            )
        ]
    )
    return True


async def async_setup_entry(hass, entry):
    source = hass.config_entries.async_get_entry(entry.data[CONF_SOURCE])
    if source is None or source.domain != "onvif":
        raise ConfigEntryNotReady("Original ONVIF configuration is missing")
    coordinator = CameraCoordinator(hass, entry, source.data)
    try:
        await coordinator.initialize()
    except (CameraError, KeyError, ValueError) as error:
        raise ConfigEntryNotReady(
            "Camera unavailable; check the source ONVIF credentials"
        ) from error
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _reload(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        sessions = hass.data.get(DOMAIN + "_talk", {})
        for key in list(sessions):
            if key[0] == entry.entry_id:
                await sessions.pop(key).close()
        await entry.runtime_data.async_shutdown()
    return unloaded
