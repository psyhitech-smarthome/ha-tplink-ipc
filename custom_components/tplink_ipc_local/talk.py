"""Bounded MULTITRANS/PCMA talk channel for mainland TP-Link IPC."""

import asyncio
import hashlib
import json
import re
import secrets
import struct
import time
from .api import CameraError


class TalkChannel:
    def __init__(self, host, user, password):
        self.host, self.user, self.password = host, user, password
        self.reader = self.writer = None
        self.sequence = secrets.randbelow(65536)
        self.timestamp = secrets.randbelow(2**32)
        self.ssrc = secrets.randbelow(2**32)
        self.deadline = time.monotonic() + 90
        self.last_audio = time.monotonic()
        self.lock = asyncio.Lock()
        self.watchdog = None
        self.sender = None
        self.queue = asyncio.Queue(maxsize=40)

    async def exchange(self, request):
        self.writer.write(request.encode())
        await self.writer.drain()
        head = await asyncio.wait_for(self.reader.readuntil(b"\r\n\r\n"), 5)
        text = head.decode("latin1")
        m = re.search(r"Content-Length:\s*(\d+)", text, re.I)
        length = int(m[1]) if m else 0
        if length < 0 or length > 65536:
            raise CameraError("Invalid talk response")
        body = (
            await asyncio.wait_for(self.reader.readexactly(length), 5)
            if length
            else b""
        )
        return text, body

    async def open(self):
        self.deadline = time.monotonic() + 90
        self.last_audio = time.monotonic()
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, 554), 5
            )
            uri = (
                "rtsp://"
                + ("[" + self.host + "]" if ":" in self.host else self.host)
                + "/multitrans"
            )
            client = secrets.token_hex(16)
            head, _ = await self.exchange(
                f"MULTITRANS {uri} RTSP/1.0\r\nCSeq: 0\r\nX-Client-UUID: {client}\r\n\r\n"
            )
            realm = re.search(r'realm="([^"]+)"', head)[1]
            nonce = re.search(r'nonce="([^"]+)"', head)[1]
            md5 = lambda s: hashlib.md5(s.encode()).hexdigest()
            digest = md5(
                md5(self.user + ":" + realm + ":" + self.password)
                + ":"
                + nonce
                + ":"
                + md5("MULTITRANS:" + uri)
            )
            auth = f'Digest username="{self.user}", realm="{realm}", nonce="{nonce}", uri="{uri}", response="{digest}"'
            head, _ = await self.exchange(
                f"MULTITRANS {uri} RTSP/1.0\r\nCSeq: 1\r\nAuthorization: {auth}\r\nX-Client-UUID: {client}\r\n\r\n"
            )
            if "200 OK" not in head:
                raise CameraError("Talk authentication failed")
            session = re.search(r"Session:\s*([^\r\n;]+)", head, re.I)[1]
            body = json.dumps(
                {
                    "type": "request",
                    "seq": 0,
                    "params": {"method": "get", "talk": {"mode": "half_duplex"}},
                },
                separators=(",", ":"),
            )
            head, result = await self.exchange(
                f"MULTITRANS {uri} RTSP/1.0\r\nCSeq: 2\r\nSession: {session}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n{body}"
            )
            parsed = json.loads(result)
            codes = []

            def find_codes(x):
                if isinstance(x, dict):
                    if "error_code" in x:
                        codes.append(x["error_code"])
                    for v in x.values():
                        find_codes(v)
                elif isinstance(x, list):
                    for v in x:
                        find_codes(v)

            find_codes(parsed)
            if "200 OK" not in head or not codes or any(int(c) != 0 for c in codes):
                raise CameraError("Camera refused talk channel")
            self.watchdog = asyncio.create_task(self._expire())
            self.sender = asyncio.create_task(self._stream())
        except Exception:
            await self.close()
            raise CameraError("Could not open camera talk channel") from None

    async def _expire(self):
        while self.writer is not None:
            await asyncio.sleep(1)
            if (
                time.monotonic() > self.deadline
                or time.monotonic() - self.last_audio > 5
            ):
                await self.close()
                return

    async def send(self, alaw):
        if not self.writer or len(alaw) > 3200:
            raise CameraError("Talk channel closed or audio chunk too large")
        async with self.lock:
            self.last_audio = time.monotonic()
            if self.queue.qsize() + (len(alaw) + 159) // 160 > 40:
                raise CameraError("Talk audio queue is full")
            for offset in range(0, len(alaw), 160):
                self.queue.put_nowait(alaw[offset : offset + 160])

    async def _stream(self):
        next_frame = time.monotonic()
        try:
            while self.writer:
                part = await self.queue.get()
                next_frame = max(next_frame, time.monotonic() - 0.04)
                await asyncio.sleep(max(0, next_frame - time.monotonic()))
                if not self.writer:
                    return
                packet = (
                    struct.pack(
                        "!BBHII", 0x80, 8, self.sequence, self.timestamp, self.ssrc
                    )
                    + part
                )
                self.writer.write(b"$" + struct.pack("!BH", 1, len(packet)) + packet)
                await self.writer.drain()
                self.sequence = (self.sequence + 1) % 65536
                self.timestamp = (self.timestamp + len(part)) % (2**32)
                next_frame += len(part) / 8000
                self.queue.task_done()
        except (ConnectionError, OSError):
            await self.close()

    async def close(self):
        task, self.watchdog = self.watchdog, None
        if task and task is not asyncio.current_task():
            task.cancel()
        sender, self.sender = self.sender, None
        if sender and sender is not asyncio.current_task():
            sender.cancel()
        writer, self.writer = self.writer, None
        if writer:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
