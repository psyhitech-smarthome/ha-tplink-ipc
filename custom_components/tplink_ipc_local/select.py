from homeassistant.components.select import SelectEntity
from .entity import CameraEntity


async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data
    async_add_entities([Control(c, d) for d in c.controls if d["kind"] == "select"])


class Control(CameraEntity, SelectEntity):
    @property
    def current_option(self):
        return self.value

    @property
    def options(self):
        return list(self.descriptor["options"])

    async def async_select_option(self, option):
        await self.coordinator.set_control(self.descriptor["key"], option)
