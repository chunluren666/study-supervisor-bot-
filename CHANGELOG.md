# Changelog

## v1.0 Beta (2026-07-24)

### 功能

- 任务管理: AI自动识别任务发布, 提取标题/内容/截止时间/负责人
- 完成审核: 提交证据 → AI判断 → approved/rejected, 区分敷衍/部分/完整
- 学习评分: 完成率40% + 及时率30% + 质量30%
- 风险分析: low/medium/high 三级, 驱动提醒频率
- 智能抽查: 按风险等级优先选择目标, 个性化提问
- 定时提醒: 截止前24h, 逾期警告
- 周报/月报: 个人+群组统计
- 角色系统: student/teacher/admin
- Web 仪表盘: 任务/审核/评分/风险/运行状态
- 运行统计: 微信/AI/任务计数, 7天趋势
- 5种微信适配器: mock / wechaty / weilink / remote / bridge
- Android 微信终端: uiautomator2 + 节点树读取 + ADB发送
- 文件桥接: bridge_in.txt → bridge_out.txt
- 数据库自动备份 (每日 03:00)
- 日志轮转 (7天过期, 50MB压缩)

### 测试结果

- 任务流程: 3/3 场景通过
- 监督策略: 5/5 场景通过
- 产品演示: 9/9 步骤通过
- 运行统计: 12/12 通过

### 已知问题

1. **回退解析器连名人名拆分**: "张三李四负责" 无法正确拆分为["张三","李四"]。DeepSeek API模式下正常工作。低优先级。

2. **Android屏幕锁屏**: 无法通过ADB解锁带密码/生物识别的屏幕。需要手机设置永不休眠。

3. **WeiLink接收消息**: iLink协议仅支持发送, 不支持接收个人微信消息。v1.1考虑替换。

4. **PyTorch/C扩展**: Python 3.8→3.11升级导致部分C扩展(pyclipper, torch)编译版本不匹配。核心功能未受影响。

5. **OCR备选方案未就绪**: cnocr/easyocr因PyTorch问题不可用。uiautomator2节点树读取足够当前需求。

### 技术栈

- Python 3.11
- DeepSeek API (AI)
- uiautomator2 (Android操控)
- SQLite (数据)
- FastAPI + HTML (Web仪表盘)
- APScheduler (定时任务)

### 项目规模

- 14 个核心 .py 文件
- 5 种微信适配器
- 2 套测试套件
- ~3500 行 Python 代码

### 7天测试目标

1. 验证消息收发稳定性
2. 统计持续累加
3. 备份正常生成
4. 日志不超限
5. 无崩溃/死锁/内存泄漏
6. 收集 runtime_stats.json 数据

### v1.1 方向 (根据测试结果决定)

- PadLocal 集成 (完整微信双向)
- OCR 降级方案恢复
- 多群支持
- 成员排行榜优化
- 通知推送 (桌面/邮件)
