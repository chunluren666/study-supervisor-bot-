# 免费 PaaS 部署方案 — 0元公网HTTPS

## 推荐平台

| 平台 | HTTPS | 24/7 | Python | 部署方式 | 休眠 |
|------|:--:|:--:|:--:|------|:--:|
| **Koyeb** | ✅ | ✅ | ✅ | Docker | 无 |
| Render | ✅ | ⚠️ | ✅ | Docker/Git | 15min无请求 |
| Fly.io | ✅ | ✅ | ✅ | Docker | 无(3VM免费) |

**推荐 Koyeb** — 免费 1 核/512MB/2.5GB 存储，HTTPS 自动，永不休眠。

## Koyeb 部署 (5分钟)

### 1. 注册
https://app.koyeb.com → 用 GitHub 登录

### 2. 部署
点击 Create App → 选择 Docker → 填写：

- **Docker image**: `python:3.11-slim`
- **Build**: Dockerfile
- **Port**: `8000`
- **Environment variables**:

```
WECOM_CORP_ID=ww8ad10cfcae684624
WECOM_SECRET=你的Secret
WECOM_AGENT_ID=1000002
WECOM_TOKEN=studybot123456
WECOM_AES_KEY=vasIyiTBdhKUO0KvLNR8C4IkXwmtPglBiax56MAh35Q
WECHAT_MODE=wecom
DEEPSEEK_API_KEY=你的DeepSeekKey
```

### 3. 拿到公网 URL
部署完成后得到 `https://xxx.koyeb.app`

### 4. 企业微信配置
URL: `https://xxx.koyeb.app/wecom/callback`
Token/AESKey: 同上

## 本地验证 Docker

```bash
# 构建
docker build -t study-bot .

# 测试运行
docker run -p 8000:8000 --env-file .env study-bot

# curl 验证
curl http://localhost:8000/
```
