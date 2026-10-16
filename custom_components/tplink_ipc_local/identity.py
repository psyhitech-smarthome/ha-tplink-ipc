"""Identity is derived from the camera, never its IP or display name."""

import re
from urllib.parse import unquote

from .api import CameraError
from .const import FIRMWARE, HARDWARE, MODEL


def inspect_identity(basic):
    model = unquote(str(basic.get("device_model", "")))
    hardware = unquote(str(basic.get("hw_version", "")))
    firmware = unquote(str(basic.get("sw_version", "")))
    if model != MODEL or hardware != HARDWARE:
        raise CameraError("Unsupported model or hardware revision")
    mac = re.sub(r"[:-]", "", str(basic.get("mac", ""))).lower()
    if not re.fullmatch(r"[0-9a-f]{12}", mac):
        raise CameraError("Camera did not return a valid stable identity")
    return {
        "id": mac,
        "model": model,
        "hardware": hardware,
        "firmware": firmware,
        "writable": firmware == FIRMWARE,
    }
