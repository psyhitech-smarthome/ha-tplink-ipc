import asyncio
import base64
import json
import re
from urllib.parse import quote, unquote
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.exceptions import HomeAssistantError
from .api import CameraError
from .schema import DOMAIN, DETECTION_MODULES
from .talk import TalkChannel


def coordinator(hass, entry_id):
    entry = hass.config_entries.async_get_entry(entry_id)
    if (
        entry is None
        or entry.domain != DOMAIN
        or not getattr(entry, "runtime_data", None)
    ):
        raise HomeAssistantError("Camera entry is not ready")
    return entry.runtime_data


async def action(hass, c, operation, data):
    if operation == "state":
        return c.public_state()
    if operation != "state":
        c.require_writable()
    if operation == "firmware_check":
        refresh = data.get("refresh", False)
        if not isinstance(refresh, bool):
            raise HomeAssistantError("refresh 必须是布尔值")
        return await hass.async_add_executor_job(c.firmware_check, refresh)
    if operation == "set":
        await c.set_control(data["key"], data["value"])
        return c.public_state()
    if operation == "move":
        dirs = {
            "left": {"pan": "LEFT"},
            "right": {"pan": "RIGHT"},
            "up": {"tilt": "UP"},
            "down": {"tilt": "DOWN"},
        }
        if data.get("direction") not in dirs:
            raise HomeAssistantError("无效方向")
        await hass.services.async_call(
            "onvif",
            "ptz",
            {
                "entity_id": c.onvif_entity("camera"),
                "move_mode": "RelativeMove",
                "distance": 0.06,
                "speed": 0.35,
                **dirs[data["direction"]],
            },
            blocking=True,
        )
    elif operation == "stop":
        await hass.services.async_call(
            "onvif",
            "ptz",
            {"entity_id": c.onvif_entity("camera"), "move_mode": "Stop"},
            blocking=True,
        )
    elif operation in ["preset_goto", "preset_save", "preset_delete"]:
        pid = str(data.get("id", ""))
        if pid not in [str(i) for i in range(1, 9)]:
            raise HomeAssistantError("预置位编号必须是 1–8")
        existing = {p["id"] for p in c.presets()}
        if operation != "preset_save" and pid not in existing:
            raise HomeAssistantError("该预置位尚未保存")
        if operation == "preset_save":
            name = data.get("name", "")
            if not isinstance(name, str) or not 1 <= len(name) <= 24:
                raise HomeAssistantError("位置名称需要 1–24 个字符")
            args = {"id": pid, "name": quote(name, safe=""), "save_ptz": "1"}
            op = "set_preset"
        else:
            args = {"id": pid if operation == "preset_goto" else [pid]}
            op = "goto_preset" if operation == "preset_goto" else "remove_preset"
        await hass.async_add_executor_job(c.client.action, "preset", op, args)
    elif operation in ["alarm_start", "alarm_stop"]:
        await hass.async_add_executor_job(
            c.client.action,
            "msg_alarm",
            "manual_msg_alarm",
            {"action": "start" if operation == "alarm_start" else "stop"},
        )
        if operation == "alarm_start":

            async def stop_alarm():
                await asyncio.sleep(15)
                try:
                    await hass.async_add_executor_job(
                        c.client.action,
                        "msg_alarm",
                        "manual_msg_alarm",
                        {"action": "stop"},
                    )
                except CameraError:
                    pass

            if c.alarm_task:
                c.alarm_task.cancel()
            c.alarm_task = hass.async_create_task(stop_alarm())
    elif operation == "region_save":
        module = data.get("module")
        rid = str(data.get("id", ""))
        if module not in DETECTION_MODULES or not re.fullmatch("[1-4]", rid):
            raise HomeAssistantError("区域无效")
        table = c.data.get(module, {}).get("region_info", [])
        section = "region_info_" + rid
        before = next((row[section] for row in table if section in row), None)
        if before is None:
            raise HomeAssistantError("该区域不存在，请选择已有区域")
        points = data.get("points", [])
        count = 2 if module == "linecrossing_detection" else 4
        if (
            not isinstance(points, list)
            or len(points) != count
            or not all(
                isinstance(p, list)
                and len(p) == 2
                and all(
                    isinstance(n, int) and not isinstance(n, bool) and 0 <= n <= 10000
                    for n in p
                )
                for p in points
            )
        ):
            raise HomeAssistantError("区域坐标无效")
        values = {
            f"pt{i + 1}_{axis}": str(p[n])
            for i, p in enumerate(points)
            for n, axis in enumerate(["x", "y"])
        }
        if module == "linecrossing_detection" and "direction" in data:
            direction = data.get("direction", "both")
            if direction not in ["both", "AtoB", "BtoA"]:
                raise HomeAssistantError("越线方向无效")
            values["direction"] = direction
        await hass.async_add_executor_job(c.client.set, module, section, values)
        readback = await hass.async_add_executor_job(
            c.client.get, module, None, ["region_info"]
        )
        after = next(
            (row[section] for row in readback.get("region_info", []) if section in row),
            {},
        )
        if any(after.get(k) != v for k, v in values.items()):
            raise HomeAssistantError("区域保存回读不一致")
    elif operation == "cover_save":
        regions = data.get("regions", [])
        if not isinstance(regions, list) or len(regions) > 4:
            raise HomeAssistantError("最多 4 个遮挡区域")
        values = []
        for r in regions:
            if not isinstance(r, dict) or set(r) != set(
                ["x_coor", "y_coor", "width", "height"]
            ):
                raise HomeAssistantError("遮挡区域格式不正确")
            if not all(
                isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 10000
                for v in r.values()
            ):
                raise HomeAssistantError("区域坐标超出范围")
            if (
                not r["width"]
                or not r["height"]
                or r["x_coor"] + r["width"] > 10000
                or r["y_coor"] + r["height"] > 10000
            ):
                raise HomeAssistantError("矩形超出画面")
            values.append({k: str(v) for k, v in r.items()})
        current = await hass.async_add_executor_job(
            c.client.get, "cover", None, ["region_info"]
        )
        normalized = [
            {k: str(v[k]) for k in ["x_coor", "y_coor", "width", "height"]}
            for row in current["region_info"]
            for v in row.values()
        ]
        if data.get("expected") is None or normalized != data["expected"]:
            raise HomeAssistantError("遮挡区域已更新，请刷新后重试")
        await hass.async_add_executor_job(
            c.client.action, "cover", "add_cover_regions", {"region_info": values}
        )
        result = await hass.async_add_executor_job(
            c.client.get, "cover", None, ["region_info"]
        )
        after = [
            {k: str(v[k]) for k in ["x_coor", "y_coor", "width", "height"]}
            for row in result["region_info"]
            for v in row.values()
        ]
        if after != values:
            raise HomeAssistantError("遮挡区域保存回读不一致")
    elif operation in ["system_reboot", "system_time"]:
        eid = c.onvif_entity(
            "button", "reboot" if operation == "system_reboot" else "setsystemdatetime"
        )
        await hass.services.async_call(
            "button", "press", {"entity_id": eid}, blocking=True
        )
        if operation == "system_reboot":
            return {"rebooting": True}
    elif operation == "schedule_save":
        module = data.get("module")
        if module not in [*DETECTION_MODULES, "record_plan"]:
            raise HomeAssistantError("不支持该计划")
        schedules = data.get("days", {})
        days = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        if not isinstance(schedules, dict) or set(schedules) != set(days):
            raise HomeAssistantError("请提供完整一周计划")
        pattern = r"\d{4}-\d{4}:[12]" if module == "record_plan" else r"\d{4}-\d{4}"
        for slots in schedules.values():
            if not isinstance(slots, list) or len(slots) > 10:
                raise HomeAssistantError("每天最多 10 个时段")
            previous_end = 0
            for slot in slots:
                if not isinstance(slot, str) or not re.fullmatch(pattern, slot):
                    raise HomeAssistantError("时段格式不正确")
                start, end = slot[:4], slot[5:9]

                def minutes(t):
                    h, m = int(t[:2]), int(t[2:])
                    if h > 24 or m > 59 or h == 24 and m != 0:
                        raise HomeAssistantError("时间超出范围")
                    return h * 60 + m

                a, b = minutes(start), minutes(end)
                if a >= b or a < previous_end:
                    raise HomeAssistantError("时段需要递增且不能重叠")
                previous_end = b
        section = "chn1_channel" if module == "record_plan" else "arming_schedule"
        values = {
            day: quote(json.dumps(schedules[day], separators=(",", ":")), safe="")
            for day in days
        }
        await hass.async_add_executor_job(c.client.set, module, section, values)
        result = await hass.async_add_executor_job(c.client.get, module, [section])
        if any(unquote(result[section][k]) != unquote(v) for k, v in values.items()):
            raise HomeAssistantError("计划保存回读不一致")
    else:
        raise HomeAssistantError("不支持该操作")
    await c.async_refresh()
    if operation == "preset_save" and not any(
        p["id"] == pid and p["name"] == name for p in c.presets()
    ):
        raise HomeAssistantError("Preset save readback mismatch")
    if operation == "preset_delete" and any(p["id"] == pid for p in c.presets()):
        raise HomeAssistantError("Preset delete readback mismatch")
    result = c.public_state()
    result["execution_status"] = (
        "submitted"
        if operation
        in ["move", "stop", "preset_goto", "system_time", "alarm_start", "alarm_stop"]
        else "confirmed"
    )
    return result


@websocket_api.websocket_command(
    {
        vol.Required("type"): DOMAIN + "/control",
        vol.Required("entry_id"): str,
        vol.Required("operation"): str,
        vol.Optional("data", default={}): dict,
    }
)
@websocket_api.async_response
async def control(hass, connection, msg):
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "需要管理员账户")
        return
    try:
        c = coordinator(hass, msg["entry_id"])
        if msg["operation"] in ["set", "state"]:
            result = await action(hass, c, msg["operation"], msg["data"])
        else:
            async with c.control_lock:
                result = await action(hass, c, msg["operation"], msg["data"])
        connection.send_result(msg["id"], result)
    except (HomeAssistantError, CameraError, KeyError, ValueError, TypeError) as e:
        text = (
            str(e)
            if isinstance(e, (HomeAssistantError, CameraError))
            else "无效的控制参数"
        )
        connection.send_error(msg["id"], "camera_control_failed", text)


@websocket_api.websocket_command(
    {
        vol.Required("type"): DOMAIN + "/talk",
        vol.Required("entry_id"): str,
        vol.Required("operation"): vol.In(["start", "audio", "stop"]),
        vol.Optional("audio"): str,
    }
)
@websocket_api.async_response
async def talk(hass, connection, msg):
    if not connection.user.is_admin:
        connection.send_error(msg["id"], "unauthorized", "需要管理员账户")
        return
    sessions = hass.data.setdefault(DOMAIN + "_talk", {})
    key = (msg["entry_id"], id(connection))
    try:
        if msg["operation"] == "start":
            for old in list(sessions):
                if sessions[old].writer is None:
                    sessions.pop(old, None)
            if any(k[0] == msg["entry_id"] for k in sessions):
                raise CameraError("对讲通道已被占用，请先结束当前对讲")
            c = coordinator(hass, msg["entry_id"])
            c.require_writable()
            client = c.client
            if not c.entry.options.get("enable_talk", False):
                raise CameraError("Experimental talk is disabled")
            channel = TalkChannel(client.host, client.username, client.password)
            sessions[key] = channel
            try:
                await channel.open()
            except Exception:
                sessions.pop(key, None)
                raise

            def disconnected():
                ch = sessions.pop(key, None)
                if ch:
                    hass.async_create_task(ch.close())

            connection.subscriptions[msg["id"]] = disconnected
            connection.send_result(
                msg["id"],
                {
                    "ready": True,
                    "sample_rate": 8000,
                    "encoding": "PCMA",
                    "max_seconds": 90,
                },
            )
        elif msg["operation"] == "audio":
            if key not in sessions:
                raise CameraError("对讲未启动")
            audio = msg.get("audio", "")
            if len(audio) > 4400:
                raise CameraError("音频片段过大")
            await sessions[key].send(base64.b64decode(audio, validate=True))
            connection.send_result(msg["id"], {})
        else:
            channel = sessions.pop(key, None)
            if channel:
                await channel.close()
            connection.send_result(msg["id"], {})
    except (CameraError, HomeAssistantError, ValueError, ConnectionError, OSError):
        channel = sessions.pop(key, None)
        if channel:
            await channel.close()
        connection.send_error(msg["id"], "talk_failed", "对讲连接失败或已结束，请重试")


def register(hass):
    websocket_api.async_register_command(hass, control)
    websocket_api.async_register_command(hass, talk)
