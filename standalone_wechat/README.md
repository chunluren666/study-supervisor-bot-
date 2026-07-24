# 独立微信服务器 — 三种免费方案

所有方案都通过 HTTP API (端口8700) 与主电脑 AI 监督系统通信, 微信操作隔离到独立设备。

## 方案选择

```
有旧笔记本? → wechat_server.py (pyautogui, Windows)
有Android手机? → android_controller.py (uiautomator2)
有Linux服务器? → gewechat_adapter.py (Docker, iPad协议)
```

## 方案A: 旧笔记本 (wechat_server.py)

- 系统: Windows 10+
- 安装: `pip install pyautogui pyperclip`
- 启动: `python wechat_server.py`
- 微信: PC版, 小号登录
- 优点: 开发成熟, 已验证可用
- 缺点: 需要整台电脑

## 方案B: Android手机 (android_controller.py)

- 系统: Android 7+
- 安装: `pip install uiautomator2 && python -m uiautomator2 init`
- 启动: `python android_controller.py`
- 微信: 手机版, 小号登录
- 优点: 旧手机即可, 功耗低
- 缺点: uiautomator2需调试

## 方案C: Linux + Docker (gewechat_adapter.py)

- 系统: Linux (CentOS/Ubuntu)
- 部署: `docker run -d -p 2531:2531 gewe/gewe`
- iPad协议, 扫码登录
- 优点: 原生REST API, 最稳定
- 缺点: 需Linux服务器, 同省限制

## 主电脑配置

任一方案启动后, 主电脑配置远程连接:

```python
# config.py
WECHAT_MODE = "remote"
WECHAT_REMOTE_URL = "http://192.168.1.100:8700"
```

## HTTP API 规范

所有方案使用同一接口:

```
GET  /status     → {"online": true, "queue_size": 3}
GET  /messages   → {"messages": [{...}]}
POST /send       → {"text": "回复内容", "room": "监督"}
```
