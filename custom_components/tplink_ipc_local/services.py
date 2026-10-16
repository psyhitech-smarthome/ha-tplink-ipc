"""Documented admin action service for automations and trusted local tools."""

import voluptuous as vol
from homeassistant.core import SupportsResponse
from homeassistant.helpers.service import async_register_admin_service
from .const import DOMAIN
from .websocket import action, coordinator

OPERATIONS = [
    "state",
    "set",
    "move",
    "stop",
    "preset_goto",
    "preset_save",
    "preset_delete",
    "region_save",
    "cover_save",
    "schedule_save",
    "alarm_start",
    "alarm_stop",
    "system_time",
    "system_reboot",
    "firmware_check",
]


def register(hass):
    async def handle(call):
        c = coordinator(hass, call.data["entry_id"])
        operation = call.data["operation"]
        if operation in ["state", "set"]:
            return await action(hass, c, operation, call.data["data"])
        async with c.control_lock:
            return await action(hass, c, operation, call.data["data"])

    async_register_admin_service(
        hass,
        DOMAIN,
        "control",
        handle,
        schema=vol.Schema(
            {
                vol.Required("entry_id"): str,
                vol.Required("operation"): vol.In(OPERATIONS),
                vol.Optional("data", default={}): dict,
            }
        ),
        supports_response=SupportsResponse.OPTIONAL,
    )
