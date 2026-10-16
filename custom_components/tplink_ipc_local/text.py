from homeassistant.components.text import TextEntity
from .entity import CameraEntity


async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data
    async_add_entities([Control(c, d) for d in c.controls if d["kind"] == "text"])


class Control(CameraEntity, TextEntity):
    _attr_native_max = 32

    @property
    def native_value(self):
        return self.value

    async def async_set_value(self, value):
        await self.coordinator.set_control(self.descriptor["key"], value)
