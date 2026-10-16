from homeassistant.components.number import NumberEntity
from .entity import CameraEntity


async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data
    async_add_entities([Control(c, d) for d in c.controls if d["kind"] == "number"])


class Control(CameraEntity, NumberEntity):
    @property
    def native_value(self):
        return self.value

    @property
    def native_min_value(self):
        return self.descriptor["min"]

    @property
    def native_max_value(self):
        return self.descriptor["max"]

    @property
    def native_step(self):
        return 1

    @property
    def native_unit_of_measurement(self):
        return self.descriptor.get("unit")

    async def async_set_native_value(self, value):
        await self.coordinator.set_control(self.descriptor["key"], value)
