# 企业微信机器人配置指南

## 前提

- 一个手机号（注册企业微信）
- 一个微信群（企业微信内部群或外部群）

## 步骤

### 1. 注册企业微信

浏览器打开 https://work.weixin.qq.com/

用手机号注册 → 填写企业名称(随意) → 完成

### 2. 创建应用

登录管理后台 → 应用管理 → 自建 → 创建应用

- 应用名称: `学习监督机器人`
- 应用Logo: 随意上传
- 可见范围: 全公司

### 3. 获取三个凭证

| 凭证 | 位置 | 说明 |
|------|------|------|
| CorpID | 我的企业 → 企业信息 | 以 `ww` 开头 |
| Secret | 应用详情页 | 点击"查看"后发送到企业微信 |
| AgentID | 应用详情页 | 纯数字如 `1000002` |

### 4. 配置 .env

```ini
WECHAT_MODE=wecom
WECOM_CORP_ID=ww1234567890abcdef
WECOM_SECRET=你的Secret
WECOM_AGENT_ID=1000002
```

### 5. 测试连接

```bash
python main.py --wecom-test
```

看到 "Token OK" 即配置成功。

### 6. 添加机器人到群

企业微信客户端 → 目标群 → 右上角 → 群机器人 → 添加 → 选择应用

### 7. 配置接收消息（可选, Webhook模式）

管理后台 → 应用管理 → 接收消息 → 设置API接收

- URL: `http://你的公网IP:8000/wecom/callback`
- Token: 随机字符串(10位以上)
- EncodingAESKey: 点击"随机获取"

### 8. 启动

```bash
python main.py
```

### 故障排查

| 问题 | 解决 |
|------|------|
| Token获取失败 | 检查 CorpID/Secret 是否正确 |
| 发送消息失败 | 检查 AgentID, 确认应用已添加到群 |
| 收不到消息 | 检查 Webhook URL 是否可达 |
