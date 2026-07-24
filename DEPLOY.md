# 生产部署指南 — 企业微信学习监督机器人

## 前置条件

- 一台有公网 IP 的服务器 (阿里云/腾讯云/VPS, 最低 2核2G)
- 企业微信管理后台权限
- 域名 (可选, IP 直连也可以)

## 服务器部署

### 1. 上传代码

```bash
scp -r study-supervisor-bot root@你的服务器IP:/opt/
```

### 2. 安装依赖

```bash
ssh root@你的服务器IP
cd /opt/study-supervisor-bot
pip install fastapi uvicorn apscheduler pycryptodome python-dotenv
```

### 3. 配置 .env

```ini
WECHAT_MODE=wecom
WECOM_CORP_ID=ww8ad10cfcae684624
WECOM_SECRET=你的Secret
WECOM_AGENT_ID=1000002
WECOM_TOKEN=studybot123456
WECOM_AES_KEY=vasIyiTBdhKUO0KvLNR8C4IkXwmtPglBiax56MAh35Q
WECOM_PUBLIC_URL=http://你的公网IP:8000
```

### 4. 开放端口

```bash
# 防火墙
firewall-cmd --add-port=8000/tcp --permanent

# 云服务商安全组: 放行 8000
```

### 5. 启动

```bash
python main.py --web
# 监听 0.0.0.0:8000
```

### 6. 企业微信配置回调

管理后台 → 应用 → 接收消息 → API接收:
- URL: `http://你的公网IP:8000/wecom/callback`
- Token: `studybot123456`
- AESKey: `vasIyiTBdhKUO0KvLNR8C4IkXwmtPglBiax56MAh35Q`

### 7. 配置可信IP

应用管理 → 企业可信IP → 添加服务器公网IP

### 8. 配置开机自启 (Linux)

```bash
cat > /etc/systemd/system/study-bot.service << EOF
[Unit]
Description=Study Supervisor Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/study-supervisor-bot
ExecStart=/usr/bin/python3 main.py --web
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl enable study-bot
systemctl start study-bot
```

## 验证

```bash
# 健康检查
curl http://localhost:8000/

# 企业微信连接
python main.py --wecom-test

# 回调测试
curl "http://localhost:8000/wecom/callback?msg_signature=x&timestamp=1&nonce=a&echostr=hello"
```

## 监控

- 日志: `logs/bot.log`, `logs/wecom.log`
- 仪表盘: `http://服务器IP:8000/dashboard`
- 运行统计: `http://服务器IP:8000/api/runtime`
