import asyncio
from datetime import timedelta, datetime
import logging
import time
from urllib.parse import quote, unquote
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import HomeAssistantError
from .api import CameraError, CameraClient
from .identity import inspect_identity
from .const import CONF_SOURCE
from homeassistant.helpers import entity_registry as er
from .schema import DOMAIN, QUERY, available_controls, read_value


class CameraCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, credentials):
        super().__init__(
            hass,
            logging.getLogger(__name__),
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=15),
        )
        self.client = CameraClient(
            credentials["host"], credentials["username"], credentials["password"]
        )
        self.entry = entry
        self.capabilities = {}
        self.controls = []
        self.control_lock = asyncio.Lock()
        self.firmware = None
        self.identity = {}
        self.alarm_task = None

    def discover(self):
        self.capabilities = {
            mod: self.client.get(mod, names)
            for mod, names in [
                ("video_capability", ["main", "minor"]),
                ("ptz", ["capability"]),
                ("image_capability", ["supplement_lamp"]),
                ("audio_capability", ["device_microphone", "device_speaker"]),
                ("device_info", ["basic_info"]),
            ]
        }
        self.identity = inspect_identity(self.capabilities["device_info"]["basic_info"])
        if self.entry.unique_id != self.identity["id"]:
            raise CameraError("The configured address belongs to a different camera")
        try:
            self.firmware_check(False)
        except CameraError:
            pass
        return self.read_state()

    def firmware_check(self, refresh=False):
        if refresh:
            self.client.action("cloud_config", "check_fw_version", "null")
            time.sleep(2)
        state = self.client.get("cloud_status", ["check_fw_ver"]).get(
            "check_fw_ver", {}
        )
        info = self.client.get("cloud_config", ["new_firmware", "upgrade_info"])
        candidate = info.get("new_firmware", {})
        basic = self.capabilities.get("device_info", {}).get("basic_info", {})
        self.firmware = {
            "checked_at": datetime.now().astimezone().isoformat(),
            "hardware": unquote(basic.get("hw_version", "")),
            "current": unquote(basic.get("sw_version", "")),
            "update_available": candidate.get("fw_new_notify") == "1",
            "candidate": unquote(candidate.get("version", "")) or None,
            "vendor_status": {k: state.get(k) for k in ["action_status", "err_code"]},
            "refresh_requested": bool(refresh),
            "message": "官方通道返回了更新候选"
            if candidate.get("fw_new_notify") == "1"
            else "当前官方通道未返回可升级版本",
            "auto_upgrade": False,
        }
        return self.firmware

    def read_state(self):
        identity = inspect_identity(
            self.client.get("device_info", ["basic_info"])["basic_info"]
        )
        if identity["id"] != self.entry.unique_id:
            self.identity["writable"] = False
            raise CameraError(
                "Camera identity changed; reload after checking its address"
            )
        self.identity = identity
        data = {}
        for module, query in QUERY.items():
            try:
                data[module] = self.client.get(
                    module, query.get("name"), query.get("table")
                )
            except CameraError as error:
                if error.code == -40101:
                    continue
                raise
        return data

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(self.read_state)
        except CameraError as e:
            raise UpdateFailed(str(e)) from None

    async def initialize(self):
        data = await self.hass.async_add_executor_job(self.discover)
        self.controls = available_controls(data, self.capabilities)
        self.async_set_updated_data(data)

    async def set_control(self, key, value):
        self.require_writable()
        d = next((x for x in self.controls if x["key"] == key), None)
        if d is None:
            raise HomeAssistantError("Unsupported control")
        if d["kind"] == "switch":
            if not isinstance(value, bool):
                raise HomeAssistantError("Expected on/off value")
            raw = "on" if value else "off"
        elif d["kind"] == "number":
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not d["min"] <= value <= d["max"]
                or value != int(value)
            ):
                raise HomeAssistantError("Value outside supported range")
            raw = str(int(value))
        elif d["kind"] == "select":
            if value not in d["options"]:
                raise HomeAssistantError("Unsupported option")
            raw = d["options"][value]
        else:
            if not isinstance(value, str) or len(value) > d["max_length"]:
                raise HomeAssistantError("Text is too long")
            raw = quote(value, safe="")
        async with self.control_lock:
            try:
                await self.hass.async_add_executor_job(
                    self.client.set, d["module"], d["section"], {d["field"]: raw}
                )
                new = await self.hass.async_add_executor_job(
                    self.client.get, d["module"], [d["section"]]
                )
                actual = new.get(d["section"], {}).get(d["field"])
                if unquote(str(actual)) != unquote(str(raw)):
                    raise HomeAssistantError(
                        "Camera did not retain the requested value"
                    )
                data = dict(self.data)
                data[d["module"]] = {**data.get(d["module"], {}), **new}
                self.async_set_updated_data(data)
            except CameraError as e:
                raise HomeAssistantError(str(e)) from None

    def presets(self):
        p = self.data.get("preset", {}).get("preset", {})
        return [
            {"id": i, "name": unquote(n)}
            for i, n in zip(p.get("id", []), p.get("name", []))
        ]

    def public_state(self):
        return {
            "entry_id": self.entry.entry_id,
            "name": self.entry.title,
            "writable": self.identity["writable"],
            "talk_enabled": self.entry.options.get("enable_talk", False),
            "controls": [
                {**d, "value": read_value(d, self.data)} for d in self.controls
            ],
            "firmware": self.firmware,
            "presets": self.presets(),
            "online": self.last_update_success,
            "sd": self.data.get("harddisk_manage", {}).get("hd_info", []),
            "regions": {
                m: self.data.get(m, {}).get("region_info", [])
                for m in [
                    "people_detection",
                    "linecrossing_detection",
                    "intrusion_detection",
                    "regionexiting_detection",
                    "cover",
                    "motion_detection",
                ]
            },
            "device": {
                k: unquote(str(v))
                for k, v in self.capabilities.get("device_info", {})
                .get("basic_info", {})
                .items()
                if k in ["device_model", "hw_version", "sw_version"]
            },
            "schedules": {
                m: self.data.get(m, {}).get("arming_schedule", {})
                for m in [
                    "people_detection",
                    "linecrossing_detection",
                    "intrusion_detection",
                    "regionexiting_detection",
                ]
            },
            "record_schedule": self.data.get("record_plan", {}).get("chn1_channel", {}),
        }

    def require_writable(self):
        if not self.identity.get("writable"):
            raise HomeAssistantError("Firmware is unverified; controls are read-only")

    def onvif_entity(self, domain, suffix=None):
        registry = er.async_get(self.hass)
        entries = er.async_entries_for_config_entry(
            registry, self.entry.data[CONF_SOURCE]
        )
        candidates = [
            e
            for e in entries
            if e.domain == domain
            and not e.disabled_by
            and (not suffix or str(e.unique_id).endswith(suffix))
        ]
        if not candidates:
            raise HomeAssistantError("Required ONVIF entity is unavailable")
        return sorted(candidates, key=lambda e: e.entity_id)[0].entity_id

    async def async_shutdown(self):
        if self.alarm_task:
            self.alarm_task.cancel()
            try:
                await self.alarm_task
            except asyncio.CancelledError:
                pass
            self.alarm_task = None
            try:
                await self.hass.async_add_executor_job(
                    self.client.action,
                    "msg_alarm",
                    "manual_msg_alarm",
                    {"action": "stop"},
                )
            except CameraError:
                pass
