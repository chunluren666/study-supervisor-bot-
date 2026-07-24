# WeChat Adapter Interface

All WeChat adapters must implement `BaseWechatAdapter` from `wechat_adapter.py`.

## Required Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `receive_message()` | `dict` or `None` | Get next pending message. Format: `{"id","sender","content","room","time","status"}` |
| `send_message(text, room)` | `bool` | Send text to specified room |
| `get_status()` | `dict` | Adapter status: `{"online","adapter","room",...}` |
| `start()` | None | Initialize and connect |
| `stop()` | None | Cleanup and disconnect |

## Adapters

| ID | Class | Status | Notes |
|----|-------|--------|-------|
| `mock` | `MockAdapter` | Production (testing) | Preset messages, no WeChat needed |
| `weilink` | `WeiLinkAdapter` | Partial (send only) | iLink protocol, free |
| `wechaty` | `WeChatyAdapter` | Production (full) | HTTP bridge to Node.js WeChaty service |
| `bridge` | `FileBridge` | Debug only | Reads `bridge_in.txt`, writes `bridge_out.txt` |

## One-Click Switch

Edit `.env` or `config.py`:

```python
WECHAT_MODE = "mock"     # Testing
WECHAT_MODE = "weilink"  # iLink (send only)
WECHAT_MODE = "wechaty"  # PadLocal (full)
```

Or via env var:

```bash
set WECHAT_GATEWAY_MODE=wechaty && python main.py
```

## Adding a New Adapter

1. Create `wechat_gateway/python_adapter/xxx_adapter.py`
2. Implement `BaseWechatAdapter`
3. Register in `wechat_adapter.py` factory function
4. Add to `.env` mode options

## Message Flow

```
WeChat → Adapter.receive_message() → task_manager.process_message() → AI
                                                                      ↓
WeChat ← Adapter.send_message() ←────────────────── reply text
```

## Role System

| Role | Publish Tasks | View All Stats | Modify Tasks |
|------|---------------|----------------|--------------|
| `student` | No | No | No |
| `teacher` | Yes | Yes | No |
| `admin` | Yes | Yes | Yes |

## PadLocal Setup

1. Register at https://padlocal.com, get token
2. Set in `.env`: `PADLOCAL_TOKEN=xxx`
3. Set `WECHAT_GATEWAY_MODE=wechaty`
4. Start Node.js gateway: `cd wechat_gateway/node_service && node api.js`
5. Scan QR code with WeChat small account
6. Run: `python main.py`
