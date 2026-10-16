# Protocol and provenance

The implementation was extracted from a locally developed HA component and generalized for multiple devices. This repository does not vendor or install the reference repositories. The MIT license covers this implementation; it does not grant rights to reference projects or manufacturer documents. Contributors must check upstream licensing before copying code. Several reference repositories do not expose a recognized license through GitHub's API; treat their source as all-rights-reserved unless separately licensed.

## Verified protocol

- GET `/pc/Content.htm`: JSON challenge may arrive with HTTP 401. Require nonce and encrypt type `3`.
- POST `/`: login password is the hexadecimal MD5 of `password + ':' + nonce`, with `encrypt_type: '3'`, `md5_encrypt_type: '1'`.
- POST `/stok=<session>/ds`: `get`, `set`, `do` operations. Session expiry `-40401` allows a single re-login. Unsupported module `-40101` is skipped during capability discovery.
- `device_info/basic_info` identifies model, hardware, firmware and MAC. Firmware changes require renewed verification.
- Query actual video/audio/image/PTZ capabilities. Unknown values stay unknown, never false or zero.
- Saved preset IDs come from the vendor preset table, not the list of eight ONVIF slots. Delete uses an ID array.
- OSD text may return decoded or percent-encoded; normalize both sides before comparing readback.
- Optional talk uses MULTITRANS/RTSP digest authentication and PCMA frames with bounded duration/queue.

The reference device provides H.264 main and sub streams. HA ONVIF owns media in this integration. A separately configured go2rtc/HA WebRTC provider can avoid expensive MJPEG conversion, but that deployment is outside this repository. Never expose a media gateway's management API publicly. No hardcoded stream credentials, STUN service, public endpoint or background telemetry is included.

## References

- [Vendor specification](https://www.tp-link.com.cn/product_4204.html?v=specification)
- [Vendor masking protocol](https://open.tp-link.com.cn/private/V2.0.19/4.14.2)
- [Vendor intrusion region protocol](https://open.tp-link.com.cn/private/V2.0.19/4.14.3)
- [bingooo/hass-tplink-ipc](https://github.com/bingooo/hass-tplink-ipc) — mainland authentication/MULTITRANS research
- [xiaodong-lx/tplink-ipc-control](https://github.com/xiaodong-lx/tplink-ipc-control) — local control field research
- [crybaby4x4/scrypted-tplink-cn-talkback](https://github.com/crybaby4x4/scrypted-tplink-cn-talkback) — mainland talk differences
- [JurajNyiri/pytapo](https://github.com/JurajNyiri/pytapo) — protocol comparison, MIT licensed
- [AlexxIT/go2rtc](https://github.com/AlexxIT/go2rtc) — media reference
- [HA integration development](https://developers.home-assistant.io/docs/creating_integration_manifest/)
