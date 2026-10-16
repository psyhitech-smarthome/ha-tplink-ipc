"""Entities share a physical identity and coordinator."""

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .schema import DOMAIN, read_value


class CameraEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, descriptor):
        super().__init__(coordinator)
        self.descriptor = descriptor
        identity = coordinator.identity
        self._attr_unique_id = identity["id"] + "_" + descriptor["key"]
        self._attr_name = descriptor["name"]
        mac = ":".join(identity["id"][i : i + 2] for i in range(0, 12, 2))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identity["id"])},
            connections={("mac", mac)},
            name=coordinator.entry.title,
            manufacturer="TP-Link",
            model=identity["model"],
            sw_version=identity["firmware"],
            hw_version=identity["hardware"],
            configuration_url=coordinator.client.base,
        )

    @property
    def available(self):
        return super().available and (
            self.descriptor["kind"] == "sensor" or self.value is not None
        )

    @property
    def value(self):
        return read_value(self.descriptor, self.coordinator.data)
