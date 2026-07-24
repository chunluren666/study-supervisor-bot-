# WeCom Adapter — 企业微信接入

基于企业微信官方 API，无需桌面自动化，免费，稳定。

## 配置

在 `.env` 中添加：

```ini
WECHAT_MODE=wecom
WECOM_CORP_ID=ww1234567890abcdef
WECOM_SECRET=xxxxx
WECOM_AGENT_ID=1000002
```

## 启动

```bash
python main.py
```

## 消息流

```
企业微信群消息 → Webhook → WeComAdapter.on_webhook_message()
    → task_manager.process_message() → AI审核
    → WeComAdapter.send_message() → 企业微信API → 群回复
```
