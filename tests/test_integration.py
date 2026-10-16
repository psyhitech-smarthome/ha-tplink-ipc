"""Synthetic regression tests. Never contact a real camera."""

import asyncio
import json
import unittest
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.exceptions import HomeAssistantError
from custom_components.tplink_ipc_local.api import CameraClient, CameraError
from custom_components.tplink_ipc_local.identity import inspect_identity
from custom_components.tplink_ipc_local.schema import available_controls, read_value
from custom_components.tplink_ipc_local import websocket as ws
from custom_components.tplink_ipc_local import async_unload_entry
from custom_components.tplink_ipc_local.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.tplink_ipc_local.config_flow import CameraConfigFlow
from custom_components.tplink_ipc_local.coordinator import CameraCoordinator
from custom_components.tplink_ipc_local import services


def basic(**kwargs):
    return {
        "device_model": "TL-IPC4ADW",
        "hw_version": "1.0",
        "sw_version": "1.0.6 Build 251124 Rel.69070n",
        "mac": "02:00:00:00:00:01",
        **kwargs,
    }


async def executor(function, *args):
    return function(*args)


def fake_coordinator():
    client = NS(action=MagicMock(), set=MagicMock(), get=MagicMock())
    c = NS(
        client=client,
        control_lock=asyncio.Lock(),
        data={},
        entry=NS(entry_id="camera-a", options={}),
        require_writable=MagicMock(),
        presets=MagicMock(return_value=[]),
        public_state=lambda: {"controls": []},
        async_refresh=AsyncMock(),
    )
    return c


class ProtocolTests(unittest.TestCase):
    def test_stable_identity_and_firmware_gate(self):
        self.assertTrue(inspect_identity(basic())["writable"])
        self.assertFalse(inspect_identity(basic(sw_version="future"))["writable"])
        self.assertEqual(inspect_identity(basic())["id"], "020000000001")
        for change in [{"hw_version": "2.0"}, {"device_model": "Tapo"}, {"mac": ""}]:
            with self.assertRaises(CameraError):
                inspect_identity(basic(**change))

    def test_reject_host_injection(self):
        for host in [
            "example.com/path",
            "user@example.com",
            "host\nHeader:x",
            "host:80",
            "",
        ]:
            with self.assertRaises(CameraError):
                CameraClient(host, "fixture", "fixture")
        self.assertEqual(CameraClient("::1", "fixture", "fixture").base, "http://[::1]")

    def test_expired_session_retries_once(self):
        c = CameraClient("camera.invalid", "fixture", "fixture")
        c.session = "expired"
        c._login = MagicMock(side_effect=lambda: setattr(c, "session", "new"))
        c._http = MagicMock(
            side_effect=[{"error_code": -40401}, {"error_code": 0, "led": {}}]
        )
        c.get("led", ["config"])
        c._login.assert_called_once()
        self.assertEqual(c._http.call_count, 2)

    def test_unknown_values_are_not_off_or_zero(self):
        d = {"module": "m", "section": "s", "field": "f", "kind": "switch"}
        self.assertIsNone(read_value(d, {"m": {"s": {"f": "invalid"}}}))
        self.assertFalse(read_value(d, {"m": {"s": {"f": "off"}}}))
        d.update(kind="number", min=0, max=100)
        for value in ["nan", "oops", "101"]:
            self.assertIsNone(read_value(d, {"m": {"s": {"f": value}}}))

    def test_optional_capabilities_are_narrowed(self):
        state = {
            "audio_config": {"microphone": {"mute": "off"}},
            "video": {"main": {"encode_type": "H264"}},
        }
        caps = {
            "audio_capability": {"device_microphone": {"mute": "0"}},
            "video_capability": {"main": {"encode_types": ["H264"]}},
        }
        controls = available_controls(state, caps)
        self.assertEqual([c["key"] for c in controls], ["main_encode_type"])


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_registers_admin_handler_and_target(self):
        hass = NS()
        c = fake_coordinator()
        with patch.object(services, "async_register_admin_service") as register:
            services.register(hass)
        args, kwargs = register.call_args
        self.assertEqual(args[1:3], ("tplink_ipc_local", "control"))
        with self.assertRaises(Exception):
            kwargs["schema"]({"operation": "state"})
        call = NS(data={"entry_id": "camera-b", "operation": "state", "data": {}})
        with patch.object(services, "coordinator", return_value=c) as get:
            self.assertEqual(await args[3](call), {"controls": []})
        get.assert_called_once_with(hass, "camera-b")

    async def test_text_write_normalizes_readback(self):
        descriptor = {
            "key": "osd_text",
            "kind": "text",
            "module": "OSD",
            "section": "label_info_1",
            "field": "text",
            "max_length": 32,
        }
        c = NS(
            identity={"writable": True},
            require_writable=lambda: None,
            controls=[descriptor],
            control_lock=asyncio.Lock(),
            data={},
            hass=NS(async_add_executor_job=executor),
            async_set_updated_data=MagicMock(),
            client=NS(
                set=MagicMock(),
                get=MagicMock(return_value={"label_info_1": {"text": "测试名称"}}),
            ),
        )
        await CameraCoordinator.set_control(c, "osd_text", "测试名称")
        c.async_set_updated_data.assert_called_once()

    async def test_invalid_value_never_reaches_device(self):
        c = NS(
            require_writable=lambda: None,
            controls=[{"key": "brightness", "kind": "number", "min": 0, "max": 100}],
            client=NS(set=MagicMock()),
        )
        for value in [True, -1, 101, float("nan"), "50", 1.5]:
            with self.assertRaises(HomeAssistantError):
                await CameraCoordinator.set_control(c, "brightness", value)
        c.client.set.assert_not_called()

    async def test_session_failure_not_retried_forever(self):
        c = CameraClient("camera.invalid", "fixture", "fixture")
        c.session = "old"
        c._login = MagicMock(side_effect=lambda: setattr(c, "session", "new"))
        c._http = MagicMock(return_value={"error_code": -40401})
        with self.assertRaises(CameraError):
            c.get("led", ["config"])
        self.assertEqual(c._http.call_count, 2)

    async def test_onvif_entity_resolution_uses_source_entry(self):
        c = NS(hass=NS(), entry=NS(data={"onvif_entry_id": "source-b"}))
        entries = [
            NS(
                domain="button",
                disabled_by=None,
                unique_id="device_setsystemdatetime",
                entity_id="button.renamed_clock",
            )
        ]
        with (
            patch(
                "custom_components.tplink_ipc_local.coordinator.er.async_get",
                return_value=NS(),
            ),
            patch(
                "custom_components.tplink_ipc_local.coordinator.er.async_entries_for_config_entry",
                return_value=entries,
            ) as lookup,
        ):
            self.assertEqual(
                CameraCoordinator.onvif_entity(c, "button", "setsystemdatetime"),
                "button.renamed_clock",
            )
        self.assertEqual(lookup.call_args.args[1], "source-b")

    async def test_explicit_entry_target(self):
        a, b = fake_coordinator(), fake_coordinator()
        entries = {
            "a": NS(domain="tplink_ipc_local", runtime_data=a),
            "b": NS(domain="tplink_ipc_local", runtime_data=b),
            "other": NS(domain="onvif", runtime_data=a),
        }
        hass = NS(config_entries=NS(async_get_entry=entries.get))
        self.assertIs(ws.coordinator(hass, "b"), b)
        for key in ["missing", "other"]:
            with self.assertRaises(HomeAssistantError):
                ws.coordinator(hass, key)

    async def test_unload_only_own_talk_session(self):
        a, b = NS(close=AsyncMock()), NS(close=AsyncMock())
        entry = NS(entry_id="a", runtime_data=NS(async_shutdown=AsyncMock()))
        hass = NS(
            data={"tplink_ipc_local_talk": {("a", 1): a, ("b", 2): b}},
            config_entries=NS(async_unload_platforms=AsyncMock(return_value=True)),
        )
        self.assertTrue(await async_unload_entry(hass, entry))
        a.close.assert_awaited_once()
        b.close.assert_not_awaited()
        self.assertIn(("b", 2), hass.data["tplink_ipc_local_talk"])

    async def test_unknown_firmware_blocks_actions(self):
        c = fake_coordinator()
        c.require_writable.side_effect = HomeAssistantError("read only")
        with self.assertRaises(HomeAssistantError):
            await ws.action(NS(), c, "alarm_start", {})
        c.client.action.assert_not_called()
        self.assertEqual(await ws.action(NS(), c, "state", {}), {"controls": []})

    async def test_preset_delete_array_and_readback(self):
        c = fake_coordinator()
        c.presets.side_effect = [[{"id": "2", "name": "Fixture"}], []]
        result = await ws.action(
            NS(async_add_executor_job=executor), c, "preset_delete", {"id": "2"}
        )
        c.client.action.assert_called_once_with(
            "preset", "remove_preset", {"id": ["2"]}
        )
        self.assertEqual(result["execution_status"], "confirmed")

    async def test_invalid_regions_and_schedules_do_not_write(self):
        c = fake_coordinator()
        c.data = {"people_detection": {"region_info": [{"region_info_1": {}}]}}
        for op, data in [
            (
                "region_save",
                {"module": "people_detection", "id": "1", "points": [[True, 1]] * 4},
            ),
            ("schedule_save", {"module": "record_plan", "days": []}),
            (
                "cover_save",
                {"regions": [{"x_coor": 0, "y_coor": 0, "width": 10001, "height": 1}]},
            ),
        ]:
            with self.assertRaises(HomeAssistantError):
                await ws.action(NS(), c, op, data)
        c.client.set.assert_not_called()

    async def test_diagnostics_allowlist(self):
        c = NS(
            identity=inspect_identity(basic()),
            last_update_success=True,
            controls=[{"key": "led", "value": "private"}],
        )
        data = await async_get_config_entry_diagnostics(None, NS(runtime_data=c))
        result = json.dumps(data)
        self.assertNotIn("020000000001", result)
        self.assertNotIn("private", result)
        self.assertNotIn("host", data)

    async def test_flow_no_onvif(self):
        flow = CameraConfigFlow()
        flow.hass = NS(config_entries=NS(async_entries=lambda domain: []))
        result = await flow.async_step_user()
        self.assertEqual(result["reason"], "onvif_required")

    async def test_flow_validates_before_create(self):
        flow = CameraConfigFlow()
        source = NS(
            entry_id="source-a",
            title="Test camera",
            data={
                "host": "camera.invalid",
                "username": "fixture",
                "password": "fixture",
            },
        )
        flow.hass = NS(
            config_entries=NS(async_entries=lambda domain: [source]),
            async_add_executor_job=executor,
        )
        with (
            patch.object(CameraClient, "get", return_value={"basic_info": basic()}),
            patch.object(flow, "async_set_unique_id", new=AsyncMock()) as unique,
            patch.object(flow, "_abort_if_unique_id_configured"),
        ):
            result = await flow.async_step_user({"onvif_entry_id": "source-a"})
        unique.assert_awaited_once_with("020000000001")
        self.assertEqual(result["data"], {"onvif_entry_id": "source-a"})
        self.assertNotIn("password", result["data"])


if __name__ == "__main__":
    unittest.main()
