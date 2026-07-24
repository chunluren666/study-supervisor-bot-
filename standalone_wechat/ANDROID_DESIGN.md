# 方案B: Android + uiautomator2 详细设计

## 一、前置条件确认

| 条件 | 要求 | 说明 |
|------|------|------|
| Android 版本 | 7.0+ (API 24) | uiautomator2 支持 4.4+，7.0+ 更稳定 |
| Root | **不需要** | 通过 ADB 调试模式即可，无需解锁 |
| 微信版本 | 8.0.x 任意 | uiautomator2 不依赖微信内部API，不挑版本 |
| 开发者选项 | 需开启 | USB调试 + "允许模拟点击" |
| ADB | 需安装 | Android SDK Platform Tools |
| Python | 3.8+ | 运行在控制电脑上 |

## 二、架构设计

```
[Android手机] 微信App (微信小号登录)
      ↑ uiautomator2 (ADB/USB或WiFi)
      │
[控制电脑]  android_controller.py
      │     HTTP Server (:8700)
      │
[主电脑]    remote_adapter.py → AI监督系统
```

### 为什么需要"控制电脑"？

uiautomator2 通过 ADB 向手机发送指令。ADB 可以USB连接，也可以WiFi连接。

- **方案B1**: 控制电脑 = 旧笔记本 (USB连着手机)
- **方案B2**: 控制电脑 = 主电脑 (WiFi ADB连着手机)

如果不希望主电脑装ADB驱动，用旧笔记本做控制电脑。如果主电脑可以直接WiFi ADB连接手机，则不需要额外设备。

## 三、技术原理

```
uiautomator2
  ↓ ADB协议
手机上 atx-agent (守护进程)
  ↓ Android Accessibility API
操作微信界面 (点击/滑动/输入)
  ↓
像真人一样使用微信
```

### 安全分析

- uiautomator2 使用 **Google 官方 Android Testing 框架**
- 通过无障碍服务操控界面，工信部认可
- **不是 Hook、不是注入、不是逆向协议**
- 微信看到的只是普通触摸事件
- 封号风险：**极低** (与真人操作无异)

## 四、微信操作实现

### 打开群聊

```
1. d.app_start("com.tencent.mm")          # 启动微信
2. d(text="通讯录").click()                # 点通讯录
3. d(text="群聊").click()                  # 点群聊
4. d(text="监督").click()                  # 点目标群
```

### 读取消息

```
1. d(className="android.widget.ListView")  # 消息列表
2. 找最后一个 TextView                      # 最后一条消息
3. .get_text()                              # 获取文字
```

### 发送消息

```
1. d(className="android.widget.EditText")  # 输入框
2. .set_text("回复内容")                     # 输入文字
3. d(text="发送").click()                   # 点发送
```

## 五、开发步骤

### 步骤1: 环境准备 (10分钟)

```bash
# 手机上: 开启开发者选项 → USB调试 → "允许模拟点击"
# 电脑上:
pip install uiautomator2 weditor
python -m uiautomator2 init   # 安装 atx-agent 到手机
```

### 步骤2: 验证连接 (5分钟)

```python
import uiautomator2 as u2
d = u2.connect()  # USB连接
print(d.info)     # 应显示手机信息
d.app_start("com.tencent.mm")  # 启动微信
```

### 步骤3: 实现核心操作 (30分钟)

移植 `android_controller.py` (已创建骨架)

### 步骤4: 联调测试 (30分钟)

手动测试: 打开群 → 读消息 → 发消息

### 步骤5: HTTP API 封装 (已就绪)

`remote_adapter.py` 直接可用，无需修改

## 六、预计难点

| 难点 | 解决方案 |
|------|---------|
| Ui控件定位不稳定 | weditor 可视化查看控件树，改用坐标点击 |
| 微信版本更新UI变化 | 用 text/className 而非坐标，兼容性好 |
| ADB连接断开 | watchdog 自动重连 + USB优先 |
| 消息列表滚动 | `d.swipe()` 模拟手指滑动 |
| 群名搜索不到 | 先进入群聊列表，用 scroll + text查找 |

## 七、稳定性分析

| 因素 | 预期 |
|------|------|
| 手机不重启 | 一次配置，长期运行 |
| ADB连接 | USB连接最稳，WiFi偶尔断 |
| 微信不闪退 | 正常使用不会 |
| 后台被杀 | 无障碍服务保活 |
| atx-agent | 手机重启后自动启动 |
| 建议 | 每周重启一次手机 |

## 八、与 PadLocal 对比

| | uiautomator2 | PadLocal |
|---|---|---|
| 费用 | **0元** | $30/年 |
| 硬件 | 需要Android手机 | 不需要 |
| 原理 | UI自动化(真实操作) | iPad协议(云端) |
| 封号风险 | **极低** | 低 |
| 7x24运行 | ✅ 手机充电放着 | ✅ 云端 |
| 微信版本 | 任意 | 需兼容 |
| 群消息 | ✅ | ✅ |
| 开发难度 | 中(需调试UI) | 低(API现成) |
| 维护成本 | 微信大改版需调 | PadLocal升级即可 |
| 推荐场景 | 有闲置Android手机 | 无手机/追求稳定 |

## 九、最终建议

如果你有一台闲置 Android 手机 (Android 7+):
→ **方案B完全可行，零成本，极低封号风险**

如果没有：
→ 花$30/年买 PadLocal，省心省力
