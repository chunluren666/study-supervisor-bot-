# 生产运行部署文档 v1.0 Beta

## 架构

```
[Android手机] 微信小号 (永不休眠 + USB充电)
      │ ADB/USB
[控制电脑]   android_controller.py (HTTP :8700)
      │ 局域网
[主电脑]     main.py → AI监督系统 + Web仪表盘
```

## 启动流程

### 1. 手机端 (一次性设置)

```
设置 → 显示 → 屏幕超时 → 永不
设置 → 电池 → 省电模式 → 关闭
设置 → 开发者选项 → USB调试 → 开启
设置 → 开发者选项 → 充电时保持唤醒 → 开启
插上充电器
打开微信，进入主界面
```

### 2. 控制电脑 (Android 服务)

```bash
cd study-supervisor-bot
python -m wechat_gateway.android_controller.android_controller
# 验证: curl http://localhost:8700/status
```

### 3. 主电脑 (AI 监督系统)

```bash
cd study-supervisor-bot

# 一键启动
start.bat

# 或手动
python main.py                          # Mock 测试
python main.py --web                    # Web 仪表盘
WECHAT_MODE=remote python main.py       # 连接 Android
```

### 4. 验证所有服务

```bash
curl http://localhost:8700/status   # Android 服务
curl http://localhost:8000/         # Web API
curl http://localhost:8000/api/runtime  # 运行统计
```

## 异常恢复

| 异常 | 自动恢复 | 手动恢复 |
|------|---------|---------|
| Android断开 | 健康监控30s自动重连 | 重插USB线 |
| 微信退出 | 自动调用 app_start | 手动解锁手机 |
| 微信不在前台 | 自动 ensure_foreground | 检查是否锁屏 |
| AI接口失败 | 3次重试 → fallback匹配 | 检查DEEPSEEK_API_KEY |
| 数据库锁 | 3次重试 + WAL模式 | 删除 .db-wal .db-shm |
| 端口占用 | - | taskkill 旧进程 |

## 定时任务

| 时间 | 任务 |
|------|------|
| 每30分钟 | 检查到期任务提醒 |
| 10:00 | 每日智能抽查 |
| 20:00 | 周一统计汇报 |
| 03:00 | 数据库备份 |
| 04:00 | 日志轮转 |

## 日志位置

```
logs/
├── bot.log                 主程序
├── android_controller.log  Android服务
├── weilink_adapter.log     WeiLink
├── remote_adapter.log      远程适配器
└── bridge.log             文件桥接
```

保留7天，单文件>50MB自动压缩，总>500MB删旧。

## 备份

每天凌晨3点自动备份到 `backups/supervisor_YYYYMMDD_HHMMSS.db`，保留最近7份。

## 开关机

```bash
# 开机: 手动启动控制电脑+主电脑服务
# 关机: Ctrl+C 停止, 或运行 stop.bat
```

## 7天测试检查清单

- [ ] Day 1: 消息收发正常
- [ ] Day 3: 统计正确累加
- [ ] Day 5: 备份正常生成
- [ ] Day 7: 日志未超额
- [ ] 全程: 无崩溃/无死锁/无内存泄漏
