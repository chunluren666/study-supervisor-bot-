# 公网隧道设置 — 企业微信回调

## 方案 A: cloudflared (推荐, 免费, 无需注册)

1. 浏览器下载: https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe

2. 运行:
```cmd
cloudflared-windows-amd64.exe tunnel --url http://localhost:8000
```

3. 记录显示的 `https://xxxx.trycloudflare.com`

## 方案 B: ngrok (免费, 需注册)

1. 下载: https://ngrok.com/download
2. 运行: `ngrok.exe http 8000`
3. 记录 `https://xxxx.ngrok-free.app`

## 企业微信后台配置

1. 管理后台 → 应用 → 接收消息 → 设置API接收
2. URL: `https://xxxx.trycloudflare.com/wecom/callback`
3. Token: `123456`
4. EncodingAESKey: 点击随机生成
5. 保存 → 企业微信发送 GET 请求验证

## 验证成功标志

curl 测试:
```bash
# 本地验证
curl "http://localhost:8000/wecom/callback?msg_signature=x&timestamp=1&nonce=a&echostr=hello"
# 应返回: hello

# 公网验证 (替换为你的隧道URL)
curl "https://xxxx.trycloudflare.com/wecom/callback?msg_signature=x&timestamp=1&nonce=a&echostr=hello"
```

## 配置 .env

```ini
WECOM_TOKEN=123456
WECOM_AES_KEY=随机生成的43位AESKey
```
