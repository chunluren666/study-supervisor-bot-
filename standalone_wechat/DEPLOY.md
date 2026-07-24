# 独立微信服务器部署指南

将桌面自动化的微信操作隔离到独立设备，主电脑 AI 监督系统通过 HTTP 远程控制。

```
[主电脑]  main.py + AI监督系统
              │ HTTP
[独立设备] wechat_server.py + WeChat PC + 微信小号
              │ pyautogui
         [微信窗口]
```

---

## 方案对比

| | 旧电脑 | 虚拟机 | 安卓手机 |
|---|---|---|---|
| 硬件成本 | 自有旧笔记本(0元) | 0元(VirtualBox) | 旧手机(0元) |
| 系统要求 | Windows 10+ | Windows 10+ VM | Android 7+ |
| WeChat运行 | PC版完整功能 | PC版完整功能 | 手机版(功能受限) |
| pyautogui兼容 | 完美 | 需注意分辨率 | 不支持 |
| 稳定性 | 极高(独立硬件) | 中(宿主机影响) | 低(杀后台) |
| 网络要求 | 同局域网 | 桥接网络 | WiFi |
| 推荐 | 首选 | 临时测试 | 备选 |

---

## 方案A: 旧电脑 (推荐)

### 准备
- 一台闲置 Windows 10/11 笔记本
- 连接电源 + 不关机 + 合盖不休眠
- 连接局域网 (与主电脑同一路由器)

### 步骤
```bash
# 1. 旧电脑: 安装 Python 3.10+
# 2. 安装微信 PC版, 用微信小号登录
# 3. 复制 standalone_wechat/ 到旧电脑
# 4. 安装依赖
pip install pyautogui pyperclip

# 5. 启动微信服务器
set WECHAT_ROOM=监督
python wechat_server.py

# 6. 确认 API 可用 (旧电脑IP, 如 192.168.1.100)
curl http://192.168.1.100:8700/status

# 7. 主电脑: 配置远程适配器
# 在 config.py 或 .env 中:
WECHAT_REMOTE_URL=http://192.168.1.100:8700
```

### 注意事项
- 电源设置: 永不睡眠, 合盖不操作
- WeChat窗口保持打开, 不要最小化
- 防火墙开放 8700 端口
- 建议插网线而非WiFi

---

## 方案B: 虚拟机

### 准备
- VirtualBox (免费) 或 VMware
- Windows 10/11 ISO
- 4GB+ 内存分配给VM

### 步骤
```bash
# 1. 创建 Windows 虚拟机
# 2. 网络: 桥接模式 (独立IP)
# 3. VM内安装 Python + WeChat PC
# 4. 同样运行 wechat_server.py
```

### 注意事项
- WeChat PC可能检测到虚拟机并限制功能
- 虚拟机需一直运行, 宿主机重启则VM也重启
- 分辨率保持固定, 否则 pyautogui 坐标偏移

---

## 方案C: 安卓手机

### 说明
安卓版 WeChat 没有 pyautogui, 需要用 Accessibility Service 或 ADB 模拟点击。

备选方案:
- 使用 `uiautomator2` (Python) 替代 pyautogui
- Android 模拟器 (如 MuMu, 雷电) 在 PC 上运行

该方案需要额外开发, 暂不提供完整代码。

---

## 主电脑适配器配置

在工厂函数中注册远程适配器:

```python
# wechat_adapter.py
create_adapter("remote", server_url="http://192.168.1.100:8700", room_name="监督")
```
