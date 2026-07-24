# Android 微信机器人 — 运行指南

## 手机设置

```
1. 设置 → 显示 → 屏幕超时 → 永不
2. 设置 → 电池 → 省电模式 → 关闭
3. 设置 → 电池 → 后台限制 → 微信: 无限制
4. 设置 → 开发者选项 → USB调试: 开启
5. 设置 → 开发者选项 → 保持唤醒(充电时): 开启
6. 插上充电器 (长期运行)
```

## 启动步骤

```bash
# 1. 手机: 解锁, 打开微信, 保持前台
# 2. 确保微信小号已登录

# 3. 电脑: 启动控制器
python -m wechat_gateway.android_controller.android_controller

# 4. 验证
curl http://localhost:8700/status
```

## API 接口

```
GET  /status    → 微信状态 + 设备信息
GET  /messages  → 待处理消息队列
POST /send      → 发送群消息 {"text":"...", "room":"监督"}
```

## 健康监控

- 每30秒检查: 屏幕是否亮, 微信是否前台, 是否登录
- 发现异常自动恢复: 唤醒屏幕, 重启微信

## 接入AI监督系统

主电脑配置:
```python
# .env
WECHAT_MODE=remote
WECHAT_REMOTE_URL=http://<controller_ip>:8700
```

## 故障排查

| 问题 | 处理 |
|------|------|
| 设备offline | 重插USB线, adb kill-server && adb start-server |
| 读不到文本 | 检查是否在分身空间, 微信是否前台 |
| 发不出消息 | 检查微信是否登录, 输入框是否存在 |
