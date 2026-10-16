"""Link one discovered camera to an existing ONVIF configuration."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .api import CameraClient, CameraError
from .const import CONF_SOURCE, CONF_TALK, DOMAIN
from .identity import inspect_identity


class CameraConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        entries = {
            e.entry_id: e for e in self.hass.config_entries.async_entries("onvif")
        }
        if not entries:
            return self.async_abort(reason="onvif_required")
        errors = {}
        if user_input is not None:
            source = entries.get(user_input.get(CONF_SOURCE))
            if source is None:
                errors["base"] = "onvif_required"
            else:
                try:
                    client = CameraClient(
                        source.data["host"],
                        source.data["username"],
                        source.data["password"],
                    )
                    basic = await self.hass.async_add_executor_job(
                        client.get, "device_info", ["basic_info"]
                    )
                    identity = inspect_identity(basic["basic_info"])
                except (CameraError, KeyError, ValueError):
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(identity["id"])
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=source.title, data={CONF_SOURCE: source.entry_id}
                    )
        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SOURCE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": key, "label": value.title}
                                for key, value in entries.items()
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return CameraOptionsFlow()


class CameraOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TALK,
                        default=self.config_entry.options.get(CONF_TALK, False),
                    ): bool,
                }
            ),
        )
