from homeassistant.components.switch import SwitchEntity
from .entity import CameraEntity


async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data
    async_add_entities([Control(c, d) for d in c.controls if d["kind"] == "switch"])


class Control(CameraEntity, SwitchEntity):
    @property
    def is_on(self):
        return self.value

    async def async_turn_on(self, **kwargs):
        await self.coordinator.set_control(self.descriptor["key"], True)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.set_control(self.descriptor["key"], False)
