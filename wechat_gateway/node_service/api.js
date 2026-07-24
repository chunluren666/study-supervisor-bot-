/**
 * WeChat Gateway HTTP API
 *
 * 消息状态管理: pending → processing → completed
 * 支持 future push mode (WeChaty → HTTP POST → Python)
 */

const express = require('express');
const app = express();
app.use(express.json());

// ── 配置 ──
const PORT = process.env.WECHAT_GATEWAY_PORT || 8800;
const ADMIN_USERS = (process.env.ADMIN_USERS || '').split(',').filter(Boolean);

// ── 消息存储（带状态管理） ──
const messages = [];
let messageIdCounter = 0;
const MSG_PENDING = 'pending';
const MSG_PROCESSING = 'processing';
const MSG_COMPLETED = 'completed';

// ── 机器人状态 ──
let botStatus = {
  online: false,       // WeChaty 登录状态
  adapter: 'WeChatyAdapter',
  room: process.env.WECHAT_ROOM || '监督',
  startTime: null,
};

// ── 模拟模式 ──
const MOCK_MODE = process.env.MOCK_MODE === 'true' || !process.env.PADLOCAL_TOKEN;

if (MOCK_MODE) {
  console.log('[Gateway] 运行在 MOCK 模式，不连接真实微信');
  botStatus.online = true;
  botStatus.startTime = new Date().toISOString();
  botStatus.adapter = 'MockAdapter';

  // 预置模拟消息
  const mockMessages = [
    { sender: '王老师', content: '今天完成概率论第三章习题，明晚8点前提交，小明和小红负责' },
    { sender: '小明', content: '完成了概率论习题，做了前5道' },
    { sender: '小红', content: '做完了' },
  ];
  mockMessages.forEach(m => addMessage(m.sender, m.content));
}

// ── 工具函数 ──

function addMessage(sender, content, room = botStatus.room) {
  messageIdCounter++;
  const msg = {
    id: `msg_${Date.now()}_${messageIdCounter}`,
    sender: sender,
    content: content,
    room: room,
    time: new Date().toISOString(),
    status: MSG_PENDING,
  };
  messages.push(msg);
  console.log(`[Gateway] 新消息 [${sender}]: ${content.slice(0, 50)}`);
  return msg;
}

function isAdmin(user) {
  return ADMIN_USERS.length === 0 || ADMIN_USERS.includes(user);
}

// ── API 路由 ──

// GET /status — 机器人状态
app.get('/status', (req, res) => {
  const pending = messages.filter(m => m.status === MSG_PENDING).length;
  const processing = messages.filter(m => m.status === MSG_PROCESSING).length;
  const completed = messages.filter(m => m.status === MSG_COMPLETED).length;
  res.json({
    ...botStatus,
    messages: { pending, processing, completed, total: messages.length },
  });
});

// GET /messages — 获取消息列表
// Query: ?status=pending&limit=10&room=监督
app.get('/messages', (req, res) => {
  const { status, limit = 10, room } = req.query;

  let result = messages;

  if (status) {
    result = result.filter(m => m.status === status);
  }
  if (room) {
    result = result.filter(m => m.room === room);
  }

  // 按时间倒序，最新的在前
  result = [...result].sort((a, b) => new Date(b.time) - new Date(a.time));

  // 限制数量
  const limited = result.slice(0, parseInt(limit));

  // 返回的消息自动标记为 processing
  limited.forEach(m => {
    if (m.status === MSG_PENDING) {
      m.status = MSG_PROCESSING;
    }
  });

  res.json({ messages: limited, total: result.length });
});

// PATCH /messages/:id — 更新消息状态
app.patch('/messages/:id', (req, res) => {
  const { id } = req.params;
  const { status } = req.body;

  const msg = messages.find(m => m.id === id);
  if (!msg) {
    return res.status(404).json({ error: 'message not found' });
  }

  if (![MSG_PENDING, MSG_PROCESSING, MSG_COMPLETED].includes(status)) {
    return res.status(400).json({ error: `invalid status: ${status}` });
  }

  msg.status = status;
  console.log(`[Gateway] 消息 ${id} → ${status}`);
  res.json({ success: true, message: msg });
});

// POST /send — 发送消息到群
// Body: { "room": "监督", "text": "消息内容" }
app.post('/send', (req, res) => {
  const { room, text } = req.body;

  if (!text) {
    return res.status(400).json({ error: 'text is required' });
  }

  // 模拟发送
  if (MOCK_MODE) {
    console.log(`[Gateway] [模拟发送 → ${room || botStatus.room}] ${text.slice(0, 100)}`);
    return res.json({ success: true, mock: true, room: room || botStatus.room, text });
  }

  // TODO: 真实 WeChaty 发送逻辑
  console.log(`[Gateway] [发送 → ${room || botStatus.room}] ${text.slice(0, 100)}`);
  res.json({ success: true, room: room || botStatus.room, text });
});

// POST /messages/mock — 手动添加模拟消息（仅 MOCK 模式）
app.post('/messages/mock', (req, res) => {
  if (!MOCK_MODE) {
    return res.status(403).json({ error: 'mock mode is disabled' });
  }
  const { sender, content, room } = req.body;
  if (!sender || !content) {
    return res.status(400).json({ error: 'sender and content are required' });
  }
  const msg = addMessage(sender, content, room);
  res.json({ success: true, message: msg });
});

// DELETE /messages — 清理旧消息 (仅 admin)
app.delete('/messages', (req, res) => {
  const { before } = req.query; // ISO time, 删除此时间之前的 completed 消息
  const { user } = req.body;

  if (!isAdmin(user)) {
    return res.status(403).json({ error: 'admin only' });
  }

  const cutoff = before ? new Date(before) : new Date(Date.now() - 3600000); // 默认1小时前
  const beforeCount = messages.length;
  // 只删除 completed 状态
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].status === MSG_COMPLETED && new Date(messages[i].time) < cutoff) {
      messages.splice(i, 1);
    }
  }
  res.json({ success: true, deleted: beforeCount - messages.length });
});

// ── 推送端点（预留：WeChaty → Python 的 push 模式） ──
// WeChaty 收到消息后 POST 到此端点，Python 服务监听此端口

// POST /push/message — WeChaty 推送新消息
app.post('/push/message', (req, res) => {
  const { sender, content, room } = req.body;
  if (!sender || !content) {
    return res.status(400).json({ error: 'sender and content required' });
  }
  const msg = addMessage(sender, content, room);
  // 如果配置了 Python 回调 URL，转发过去
  const pythonUrl = process.env.PYTHON_CALLBACK_URL;
  if (pythonUrl) {
    try {
      const https = require('https');
      const http = require('http');
      const client = pythonUrl.startsWith('https') ? https : http;
      const url = new URL(pythonUrl);
      const data = JSON.stringify(msg);
      const req2 = client.request({
        hostname: url.hostname,
        port: url.port,
        path: '/callback/message',
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Content-Length': data.length },
      });
      req2.write(data);
      req2.end();
    } catch (e) {
      console.error('[Gateway] push callback failed:', e.message);
    }
  }
  res.json({ success: true, message: msg });
});

// ── 启动 ──
app.listen(PORT, () => {
  console.log(`[Gateway] HTTP API: http://localhost:${PORT}`);
  console.log(`[Gateway] Mode: ${MOCK_MODE ? 'MOCK' : 'LIVE'}`);
  if (MOCK_MODE) {
    console.log(`[Gateway] 模拟消息已就绪，${messages.length} 条待处理`);
  }
});

module.exports = { app, addMessage, botStatus, MOCK_MODE };
