"""Controls supported by the audited TL-IPC4ADW firmware."""

from urllib.parse import unquote
import math

DOMAIN = "tplink_ipc_local"
CONTROLS = []


def add(key, name, kind, module, section, field, group, **extra):
    CONTROLS.append(
        dict(
            key=key,
            name=name,
            kind=kind,
            module=module,
            section=section,
            field=field,
            group=group,
            **extra,
        )
    )


for key, name, module, section, field, group in [
    ("privacy", "隐私遮蔽", "lens_mask", "lens_mask_info", "enabled", "常用"),
    ("cover", "画面局部遮挡", "cover", "cover", "enabled", "常用"),
    ("led", "状态指示灯", "led", "config", "enabled", "常用"),
    ("tracking", "智能跟踪", "target_track", "target_track_info", "enabled", "侦测"),
    (
        "person_tracking",
        "人形跟踪",
        "target_track",
        "target_track_info",
        "people_enabled",
        "侦测",
    ),
    (
        "motion_detection",
        "摄像头移动侦测",
        "motion_detection",
        "motion_det",
        "enabled",
        "侦测",
    ),
    (
        "person_detection",
        "摄像头人形侦测",
        "people_detection",
        "detection",
        "enabled",
        "侦测",
    ),
    (
        "tamper_detection",
        "遮挡侦测",
        "tamper_detection",
        "tamper_det",
        "enabled",
        "侦测",
    ),
    ("cry_detection", "哭声侦测", "cry_detection", "detection", "enabled", "侦测"),
    (
        "line_detection",
        "越线侦测",
        "linecrossing_detection",
        "detection",
        "enabled",
        "侦测",
    ),
    (
        "intrusion_detection",
        "区域入侵侦测",
        "intrusion_detection",
        "detection",
        "enabled",
        "侦测",
    ),
    (
        "exit_detection",
        "区域离开侦测",
        "regionexiting_detection",
        "detection",
        "enabled",
        "侦测",
    ),
    (
        "alarm_enabled",
        "声光报警总开关",
        "msg_alarm",
        "chn1_msg_alarm_info",
        "enabled",
        "报警",
    ),
    (
        "alarm_sound",
        "报警声音",
        "msg_alarm",
        "chn1_msg_alarm_info",
        "sound_alarm_enabled",
        "报警",
    ),
    (
        "alarm_light",
        "报警闪光",
        "msg_alarm",
        "chn1_msg_alarm_info",
        "light_alarm_enabled",
        "报警",
    ),
    ("mic_mute", "麦克风静音", "audio_config", "microphone", "mute", "声音"),
    (
        "noise_cancel",
        "麦克风降噪",
        "audio_config",
        "microphone",
        "noise_cancelling",
        "声音",
    ),
    ("wide_dynamic", "宽动态", "image", "common", "wide_dynamic", "画面"),
    (
        "person_color",
        "人形全彩增强",
        "image",
        "switch",
        "full_color_people_enhance",
        "夜视",
    ),
    (
        "overexposure",
        "人形过曝抑制",
        "image",
        "switch",
        "overexposure_people_suppression",
        "夜视",
    ),
    ("sd_recording", "SD 卡录像开关", "record_plan", "chn1_channel", "enabled", "存储"),
    ("sd_loop", "SD 卡循环覆盖", "harddisk_manage", "harddisk", "loop", "存储"),
    ("osd_date", "显示日期时间", "OSD", "date", "enabled", "画面"),
    ("osd_week", "显示星期", "OSD", "week", "enabled", "画面"),
    ("osd_label", "显示画面名称", "OSD", "label_info_1", "enabled", "画面"),
]:
    add(key, name, "switch", module, section, field, group)

for key, name, module, section, field, group, low, high, unit in [
    ("brightness", "亮度", "image", "common", "luma", "画面", 0, 100, None),
    ("contrast", "对比度", "image", "common", "contrast", "画面", 0, 100, None),
    ("saturation", "饱和度", "image", "common", "saturation", "画面", 0, 100, None),
    ("sharpness", "锐度", "image", "common", "sharpness", "画面", 0, 100, None),
    ("wdr_gain", "宽动态强度", "image", "common", "wd_gain", "画面", 0, 100, None),
    (
        "mic_volume",
        "麦克风音量",
        "audio_config",
        "microphone",
        "volume",
        "声音",
        0,
        100,
        "%",
    ),
    (
        "speaker_volume",
        "扬声器音量",
        "audio_config",
        "speaker",
        "volume",
        "声音",
        0,
        100,
        "%",
    ),
    (
        "motion_sensitivity",
        "移动侦测灵敏度",
        "motion_detection",
        "motion_det",
        "digital_sensitivity",
        "侦测",
        1,
        100,
        None,
    ),
    (
        "person_sensitivity",
        "人形侦测灵敏度",
        "people_detection",
        "detection",
        "sensitivity",
        "侦测",
        1,
        100,
        None,
    ),
    (
        "tamper_sensitivity",
        "遮挡侦测灵敏度",
        "tamper_detection",
        "tamper_det",
        "digital_sensitivity",
        "侦测",
        1,
        100,
        None,
    ),
    (
        "cry_sensitivity",
        "哭声侦测灵敏度",
        "cry_detection",
        "detection",
        "digital_sensitivity",
        "侦测",
        1,
        100,
        None,
    ),
    (
        "color_keep",
        "全彩保持时间",
        "image",
        "switch",
        "full_color_min_keep_time",
        "夜视",
        5,
        600,
        "s",
    ),
    (
        "white_intensity",
        "白光亮度等级",
        "image",
        "switch",
        "wtl_intensity_level",
        "夜视",
        1,
        5,
        None,
    ),
    (
        "track_return",
        "跟踪后回位等待",
        "target_track",
        "target_track_info",
        "back_time",
        "侦测",
        10,
        600,
        "s",
    ),
]:
    add(
        key, name, "number", module, section, field, group, min=low, max=high, unit=unit
    )

for key, name, module, section, field, group, options in [
    (
        "night_mode",
        "夜视模式",
        "image",
        "switch",
        "night_vision_mode",
        "常用",
        {
            "红外黑白": "inf_night_vision",
            "日夜全彩": "wtl_night_vision",
            "人形侦测全彩": "md_night_vision",
        },
    ),
    (
        "flip",
        "画面翻转",
        "image",
        "switch",
        "flip_type",
        "画面",
        {
            "正常": "off",
            "左右镜像": "left_and_right",
            "上下翻转": "up_and_down",
            "旋转180度": "center",
        },
    ),
    (
        "ir_mode",
        "红外切换",
        "image",
        "common",
        "inf_type",
        "夜视",
        {"自动": "auto", "开启": "on", "关闭": "off"},
    ),
    (
        "exposure",
        "曝光模式",
        "image",
        "common",
        "exp_type",
        "画面",
        {"自动": "auto", "手动": "manual"},
    ),
    (
        "shutter",
        "快门速度",
        "image",
        "common",
        "shutter",
        "画面",
        {x: x.replace("/", "%2f") for x in ["1/25", "1/50", "1/100", "1/250", "1/500"]},
    ),
    (
        "white_balance",
        "白平衡",
        "image",
        "common",
        "wb_type",
        "画面",
        {
            "自动": "auto",
            "日光": "day_light",
            "自然光": "nature",
            "白炽灯": "incandescent",
            "暖光": "warm",
            "手动": "manual",
        },
    ),
]:
    add(key, name, "select", module, section, field, group, options=options)

add(
    "osd_text", "画面名称", "text", "OSD", "label_info_1", "text", "画面", max_length=32
)

DETECTION_MODULES = {
    "people_detection": "人形",
    "linecrossing_detection": "越线",
    "intrusion_detection": "入侵",
    "regionexiting_detection": "离开区域",
}
for module, label in DETECTION_MODULES.items():
    for key, name in [
        ("msg_push_enabled", "原厂 App 通知"),
        ("sound_alarm_enabled", "报警声音"),
        ("light_alarm_enabled", "报警闪光"),
        ("record_enabled", "SD 卡事件录像"),
    ]:
        add(
            module + "_" + key,
            label + name,
            "switch",
            module,
            "notify_list",
            key,
            "事件联动",
        )

QUERY = {}
for d in CONTROLS:
    QUERY.setdefault(d["module"], {"name": []})
    if d["section"] not in QUERY[d["module"]]["name"]:
        QUERY[d["module"]]["name"].append(d["section"])
QUERY["preset"] = {"name": ["preset"]}
QUERY["harddisk_manage"]["table"] = ["hd_info"]
QUERY["video"] = {"name": ["main", "minor"]}
QUERY["cover"]["table"] = ["region_info"]
QUERY["motion_detection"]["table"] = ["region_info"]
for module in DETECTION_MODULES:
    QUERY[module]["name"].append("arming_schedule")
    QUERY[module]["table"] = ["region_info"]


def available_controls(state, capabilities):
    result = [
        dict(d)
        for d in CONTROLS
        if d["field"] in state.get(d["module"], {}).get(d["section"], {})
    ]
    audio = capabilities.get("audio_capability", {}).get("device_microphone", {})
    result = [
        d
        for d in result
        if not (d["key"] == "mic_mute" and audio.get("mute") == "0")
        and not (d["key"] == "noise_cancel" and audio.get("noise_cancelling") == "0")
    ]
    modes = (
        capabilities.get("image_capability", {})
        .get("supplement_lamp", {})
        .get("night_vision_mode_range")
    )
    if isinstance(modes, list):
        for d in result:
            if d["key"] == "night_mode":
                d["options"] = {k: v for k, v in d["options"].items() if v in modes}
        result = [d for d in result if d["kind"] != "select" or d["options"]]
    for stream, label in [("main", "主码流"), ("minor", "子码流")]:
        cap = capabilities.get("video_capability", {}).get(stream, {})
        for field, name, source in [
            ("encode_type", "编码", "encode_types"),
            ("resolution", "分辨率", "resolutions"),
            ("bitrate", "码率", "bitrates"),
            ("frame_rate", "帧率", "frame_rates"),
            ("bitrate_type", "码率模式", "bitrate_types"),
        ]:
            choices = cap.get(source, [])
            if (
                not isinstance(choices, list)
                or not choices
                or field not in state.get("video", {}).get(stream, {})
            ):
                continue
            options = {
                str(int(v) & 65535) + " fps"
                if field == "frame_rate"
                else (v + " kbps" if field == "bitrate" else v): v
                for v in choices
            }
            result.append(
                dict(
                    key=stream + "_" + field,
                    name=label + name,
                    kind="select",
                    module="video",
                    section=stream,
                    field=field,
                    group="编码",
                    options=options,
                )
            )
    return result


def read_value(d, state):
    raw = state.get(d["module"], {}).get(d["section"], {}).get(d["field"])
    if raw is None:
        return None
    if d["kind"] == "switch":
        return True if raw == "on" else False if raw == "off" else None
    if d["kind"] == "number":
        try:
            value = float(raw)
        except (ValueError, TypeError):
            return None
        return value if math.isfinite(value) and d["min"] <= value <= d["max"] else None
    if d["kind"] == "text":
        return unquote(str(raw))
    if d["kind"] == "select":
        return next(
            (
                k
                for k, v in d["options"].items()
                if unquote(str(v)) == unquote(str(raw))
            ),
            None,
        )
    return raw
