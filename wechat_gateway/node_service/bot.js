/**
 * WeChaty Bot — 微信登录 + 消息监听
 *
 * 当前为占位文件（Phase 1）。
 * Phase 2 接入 PadLocal token 后激活真实微信连接。
 */

const MOCK_MODE = process.env.MOCK_MODE === 'true' || !process.env.PADLOCAL_TOKEN;

if (MOCK_MODE) {
  console.log('[Bot] Mock 模式，跳过 WeChaty 初始化');
  console.log('[Bot] 模拟消息由 api.js 管理');

  module.exports = {
    start: () => console.log('[Bot] Mock bot started'),
    stop: () => console.log('[Bot] Mock bot stopped'),
    send: (room, text) => console.log(`[Bot] [Mock send → ${room}] ${text}`),
  };

} else {
  // ── 真实 WeChaty 连接（Phase 2） ──
  const { WechatyBuilder } = require('wechaty');
  const { PuppetPadlocal } = require('wechaty-puppet-padlocal');

  const bot = WechatyBuilder.build({
    name: 'study-supervisor',
    puppet: new PuppetPadlocal({
      token: process.env.PADLOCAL_TOKEN,
    }),
  });

  const TARGET_ROOM = process.env.WECHAT_ROOM || '监督';

  // 消息处理回调（由外部注入）
  let messageHandler = null;

  function onMessage(handler) {
    messageHandler = handler;
  }

  bot.on('message', async (message) => {
    // 忽略自己发的消息
    if (message.self()) return;

    const room = message.room();
    if (!room) return; // 只处理群消息

    const topic = await room.topic();
    if (topic !== TARGET_ROOM) return; // 只看目标群

    const sender = message.talker();
    const text = message.text();

    console.log(`[Bot] ${sender.name()}: ${text.slice(0, 100)}`);

    if (messageHandler) {
      messageHandler({
        sender: sender.name(),
        content: text,
        room: topic,
        time: new Date().toISOString(),
      });
    }
  });

  bot.on('scan', (qrcode, status) => {
    console.log(`[Bot] QR Code: https://wechaty.js.org/qrcode/${encodeURIComponent(qrcode)}`);
  });

  bot.on('login', (user) => {
    console.log(`[Bot] 登录成功: ${user.name()}`);
  });

  bot.on('logout', (user) => {
    console.log(`[Bot] 已登出: ${user.name()}`);
  });

  module.exports = {
    bot,
    start: () => bot.start(),
    stop: () => bot.stop(),
    onMessage,
    send: async (roomName, text) => {
      const room = await bot.Room.find({ topic: roomName });
      if (room) await room.say(text);
    },
  };
}
