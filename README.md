# TP-Link IPC Local for Home Assistant

[![Test](https://github.com/psyhitech-smarthome/ha-tplink-ipc/actions/workflows/test.yml/badge.svg)](https://github.com/psyhitech-smarthome/ha-tplink-ipc/actions)

国内版 TP-Link IPC 的 Home Assistant 本地控制集成。通过既有 ONVIF 配置复用设备连接，以原生实体提供图像、声音、侦测、录像和 OSD 设置，并附带可选控制卡片。

**状态：0.1.0 测试版。** 目前只支持 **TL-IPC4ADW / 硬件 1.0**，验证固件为 **1.0.6 Build 251124 Rel.69070n**。相同硬件的未知固件只读；其他型号/硬件拒绝配置。它不是通用 Tapo 集成，也不是 TP-Link 官方产品。

## 功能

- 按设备实际能力生成 `switch`、`number`、`select`、`text`：参考设备有 72 项设置。
- SD 卡状态、有效预置位列表两个 `sensor`；无卡不等于录像配置不可读。
- 云台微调/停止、预置位保存/调用/删除、校时、重启、限时报警。
- 已有侦测区域、每周布防和 SD 录像计划、最多四个遮挡矩形。
- 每设备独立 config entry、MAC 身份、实体和控制锁；地址变更不会生成新的设备身份。
- HA 管理员控制接口和 `tplink_ipc_local.control` 服务，适用于自动化和受信任的工具。
- **实验性半双工对讲默认关闭**：协议/静音数据传输验证过，现场可听语音尚未验收。

视频继续使用 HA ONVIF 摄像头实体。卡片嵌入 HA `picture-entity` 或你指定的 `live_config`；WebRTC 能否使用取决于 HA/媒体网关配置。本仓库不安装 go2rtc、不建立公网端口、不要求 HomeHub。

## 安装

需要 Home Assistant **2026.10.0 或以上**；自动化测试使用 2026.10.1。

### HACS 自定义仓库

1. HACS → 自定义仓库，填 `https://github.com/psyhitech-smarthome/ha-tplink-ipc`，类型选择 **Integration**。
2. 下载 TP-Link IPC Local，重启 HA。
3. 在 HA 中先配置 **ONVIF**，确认设备账号密码有效。
4. 设置 → 设备与服务 → 添加集成 → **TP-Link IPC Local**，选择对应 ONVIF 条目。

这是 HACS 自定义仓库安装方式，尚未加入 HACS 默认目录。

也可手动将 `custom_components/tplink_ipc_local` 复制到 HA 的 `config/custom_components/` 后重启。

### 可选控制卡片

在仪表盘资源中添加 JavaScript Module：

```text
/tplink_ipc_local/camera-control-card.js?v=0.1.0
```

在 HA 开发者工具 → 模板中，可用 `{{ config_entry_id('switch.your_camera_control') }}` 查找本集成的 entry ID；注意要用本集成实体，不是 ONVIF 实体。然后添加：

```yaml
type: custom:tplink-ipc-controls
entry_id: YOUR_TPLINK_IPC_ENTRY_ID
entity: camera.your_onvif_camera
title: 摄像头
```

卡片需管理员账号。`entity` 用于显示视频，应属于选定设备；控制命令始终按 `entry_id` 路由。设备状态在线不等于视频正在播放，播放器实际画面才是媒体连通性的依据。

## 动作与权限

普通设置使用 HA 的标准实体服务。复杂操作使用：

```yaml
action: tplink_ipc_local.control
data:
  entry_id: YOUR_TPLINK_IPC_ENTRY_ID
  operation: preset_goto
  data:
    id: "1"
```

详见 [动作接口](docs/ACTIONS.md)。自定义 WebSocket 和有用户上下文的复杂服务调用要求管理员；HA 自动化属于受信任的系统上下文。不要向外部客户端提供管理员 token。

所有动作只访问当前配置设备；保存属性、区域、计划和预置位需要回读。移动/停止/调用预置位/校时/报警仅表示请求已接受，**不声称物理动作结果已确认**。重启会中断视频；格式化和固件升级没有提供。

## 配置与维护

凭据由源 ONVIF 配置管理，不复制到卡片或新条目。修改 ONVIF 密码或主机后，重新加载本集成；删除源 ONVIF 条目会让控制集成不可用。设备返回的 MAC 必须与配置时一致，避免 DHCP 地址换给另一台摄像头后误控制。

选项可启用实验性对讲，需 HTTPS 安全上下文和浏览器麦克风授权。上限 90 秒、5 秒无音频关闭；离开页面或断开连接会清理，卸载一台摄像头不影响其他摄像头会话。对讲不是全双工。

从原有私人定制版迁移，请先读 [迁移与验证](docs/MIGRATION.md)。不要直接覆盖 HA `.storage` 文件。

## 已知限制与证据

- 协议此前在真实参考设备运行过，72 项同值写入回读、指示灯实际开关/恢复、预置位及部分命令有验收记录；不代表每个取值的物理效果都测过。
- 本次通用化新增身份、配置、生命周期、隔离和错误处理测试；多台实体设备并发尚未现场验收。
- 原有独立 HomeHub 客户端的 iPad WebRTC 约 20 fps 是媒体设计参考，**不等于本仓库自动提供或已验收同样的视频性能**。
- 对讲话音、录像检索/回放、固件升级、格式化、Wi-Fi 配网、云账号管理尚未完成。
- 固定焦距镜头；不虚构自动对焦、光学变焦、雨刷或未发现的巡航能力。
- 当前控件名称/卡片以中文为主；配置界面有中文和英文翻译。

## 开发与贡献

```sh
python -m venv .venv
. .venv/bin/activate
pip install homeassistant==2026.10.1
python -m unittest discover -s tests -v
python -m compileall -q custom_components
node --check custom_components/tplink_ipc_local/www/camera-control-card.js
python scripts/check_public_tree.py
```

只使用合成测试数据。增加型号请提交脱敏的身份、能力响应和测试，不能简单放宽型号检查。问题报告不要包含密码、token、完整 RTSP 地址、真实 MAC、摄像头画面或 `.storage` 文件。

协议说明和参考项目见 [协议与来源](docs/PROTOCOL.md)。代码采用 [MIT](LICENSE)；上游资料和项目保持各自权利及许可证。
