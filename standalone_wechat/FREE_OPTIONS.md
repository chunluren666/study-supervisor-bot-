# 免费真实微信接入方案评估

## 方案对比

| | Gewechat | WorkTool | uiautomator2 | iLink 官方 |
|---|---|---|---|---|
| 原理 | iPad协议 | 无障碍服务 | ADB自动化 | 官方API |
| 运行平台 | Linux/Docker | Android手机 | Python+ADB | 任意 |
| 个人微信 | 是 | 是(部分) | 是 | 是 |
| 微信群消息 | 完整 | 是 | 是 | 仅私聊 |
| 免Root | 是(Docker) | 是 | 是 | 是 |
| Http API | 原生REST | 是 | 需自建 | 需SDK |
| 费用 | 免费 | 免费 | 免费 | 免费 |
| 封号风险 | 中(逆向协议) | 低(官方认可) | 中 | 极低(官方) |
| 维护状态 | 2025已停 | 活跃 | 活跃 | 活跃 |
| 开发难度 | 低(API现成) | 中 | 高(需自建) | 低 |
| 影响主电脑 | 零 | 零 | 零 | 零 |

## 推荐: uiautomator2 + 轻量HTTP服务

### 架构

```
[Android手机]  uiautomator2 操控微信
      | USB/WiFi ADB
[旧笔记本]     Python控制器 → HTTP API(:8700)
      | 局域网
[主电脑]       wechat_adapter (remote模式)
```

### 为什么选这个

1. **完全免费** — 不需要任何token或付费服务
2. **长期可用** — ADB是Android官方调试工具,不会像第三方协议那样突然失效
3. **群消息完整** — 直接操控微信App,功能无限制
4. **手机独立运行** — 微信在手机上,完全不碰主电脑
5. **与现有架构兼容** — HTTP API接口与 wechat_server.py 一致

### 替代方案选择

如果追求更低开发成本:
- **Gewechat** (如果还能用) — Docker一键部署,API现成,直接替换remote_adapter的URL即可
- **WorkTool** — 在Android上安装APK,提供HTTP API
