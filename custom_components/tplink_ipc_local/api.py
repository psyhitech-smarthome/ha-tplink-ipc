"""Local JSON interface used by mainland TP-Link IPC firmware.

Protocol references: device web UI, TP-Link developer documentation, and
bingooo/hass-tplink-ipc. No cloud credentials or requests are used.
"""

import hashlib
import json
import threading
import ipaddress
import re
import urllib.error
import urllib.request


class CameraError(Exception):
    """A bounded, credential-free error."""

    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CameraError("Camera redirects are not allowed")


class CameraClient:
    def __init__(self, host, username, password):
        if (
            not isinstance(host, str)
            or len(host) > 253
            or any(c.isspace() or c in "/@?#\\" for c in host)
        ):
            raise CameraError("Invalid camera host")
        try:
            address = ipaddress.ip_address(host)
            authority = f"[{address}]" if address.version == 6 else host
        except ValueError:
            if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host):
                raise CameraError("Invalid camera host")
            authority = host
        self.base = "http://" + authority
        self.host = host
        self.username, self.password = username, password
        self.session = None
        self.lock = threading.Lock()
        self.opener = None

    def _http(self, path, data=None):
        request = urllib.request.Request(
            self.base + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "TP-LINK_APP",
            },
        )
        try:
            if self.opener is None:
                self.opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({}), NoRedirect()
                )
            try:
                response = self.opener.open(request, timeout=6)
            except urllib.error.HTTPError as err:
                response = err
            with response:
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise CameraError("Camera response too large")
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise CameraError("Invalid camera response")
                return result
        except CameraError:
            raise
        except Exception:
            raise CameraError("Camera request failed") from None

    def _login(self):
        challenge = self._http("/pc/Content.htm").get("data", {})
        types = challenge.get("encrypt_type", [])
        if "3" not in types or not challenge.get("nonce"):
            raise CameraError("Camera does not offer the verified authentication mode")
        digest = hashlib.md5(
            (self.password + ":" + challenge["nonce"]).encode()
        ).hexdigest()
        result = self._http(
            "/",
            {
                "method": "do",
                "login": {
                    "username": self.username,
                    "password": digest,
                    "encrypt_type": "3",
                    "md5_encrypt_type": "1",
                },
            },
        )
        if not result.get("stok"):
            raise CameraError("Camera authentication failed")
        self.session = result["stok"]

    def request(self, payload):
        with self.lock:
            for attempt in range(2):
                if not self.session:
                    self._login()
                result = self._http("/stok=" + self.session + "/ds", payload)
                code = result.get("error_code", 0)
                if code == -40401 and attempt == 0:
                    self.session = None
                    continue
                if code != 0:
                    raise CameraError("Camera rejected request (code %s)" % code, code)
                return result
            raise CameraError("Camera session expired")

    def get(self, module, names=None, tables=None):
        query = {}
        if names:
            query["name"] = names
        if tables:
            query["table"] = tables
        return self.request({"method": "get", module: query}).get(module, {})

    def set(self, module, section, values):
        return self.request({"method": "set", module: {section: values}})

    def action(self, module, action, values):
        return self.request({"method": "do", module: {action: values}})
