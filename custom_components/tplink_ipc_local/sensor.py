from homeassistant.components.sensor import SensorEntity
from .entity import CameraEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([Storage(entry.runtime_data), Presets(entry.runtime_data)])


class Storage(CameraEntity, SensorEntity):
    def __init__(self, c):
        super().__init__(c, {"key": "sd_status", "name": "SD 卡状态", "kind": "sensor"})

    @property
    def native_value(self):
        rows = self.coordinator.data.get("harddisk_manage", {}).get("hd_info", [])
        disk = next(iter(rows[0].values())) if rows else {}
        return {
            "offline": "未检测到存储卡",
            "normal": "正常",
            "abnormal": "异常",
            "full": "已满",
        }.get(disk.get("status"), disk.get("status", "未知"))

    @property
    def extra_state_attributes(self):
        rows = self.coordinator.data.get("harddisk_manage", {}).get("hd_info", [])
        disk = next(iter(rows[0].values())) if rows else {}
        return {k: disk.get(k) for k in ["total_space", "free_space", "rw_attr"]}


class Presets(CameraEntity, SensorEntity):
    def __init__(self, c):
        super().__init__(
            c, {"key": "presets", "name": "已保存预置位", "kind": "sensor"}
        )

    @property
    def native_value(self):
        return len(self.coordinator.presets())

    @property
    def extra_state_attributes(self):
        return {"presets": self.coordinator.presets(), "capacity": 8}
