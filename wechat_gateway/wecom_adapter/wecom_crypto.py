# -*- coding: utf-8 -*-
"""
WeCom 加解密 — URL验证 + AES消息解密 + XML解析
企业微信官方回调模式, 符合官方加解密库规范
"""

import base64, hashlib, random, struct, socket, time, logging
from Crypto.Cipher import AES

log = logging.getLogger("wecom_crypto")


class WXBizMsgCrypt:
    """企业微信消息加解密"""

    def __init__(self, token: str, encoding_aes_key: str, corp_id: str):
        self.token = token
        self.corp_id = corp_id
        self.aes_key = base64.b64decode(encoding_aes_key + "=")
        if len(self.aes_key) != 32:
            raise ValueError(f"Invalid AES key length: {len(self.aes_key)}")

    # ── URL验证 ──

    def verify_url(self, msg_signature: str, timestamp: str, nonce: str,
                   echostr: str) -> tuple:
        """验证回调URL: 解密echostr并返回明文"""
        sign = self._signature(timestamp, nonce, echostr)
        if sign != msg_signature:
            log.warning(f"签名验证失败: expected={sign}, got={msg_signature}")
            return -1, ""
        try:
            plain = self._decrypt(echostr)
            return 0, plain
        except Exception as e:
            log.error(f"解密echostr失败: {e}")
            return -1, ""

    # ── 消息解密 ──

    def decrypt_msg(self, msg_signature: str, timestamp: str, nonce: str,
                    post_data: str) -> tuple:
        """解密回调消息, 返回 (errcode, xml_content)"""
        import xml.etree.ElementTree as ET
        try:
            xml_tree = ET.fromstring(post_data)
            encrypt = xml_tree.find("Encrypt")
            if encrypt is None:
                return -1, ""
            encrypted = encrypt.text
        except Exception:
            return -1, ""

        sign = self._signature(timestamp, nonce, encrypted)
        if sign != msg_signature:
            log.warning(f"消息签名验证失败")
            return -1, ""

        try:
            plain = self._decrypt(encrypted)
            return 0, plain
        except Exception as e:
            log.error(f"解密消息失败: {e}")
            return -1, ""

    # ── 内部方法 ──

    def _signature(self, timestamp: str, nonce: str, data: str) -> str:
        """生成SHA1签名"""
        params = sorted([self.token, timestamp, nonce, data])
        return hashlib.sha1("".join(params).encode()).hexdigest()

    def _decrypt(self, encrypted: str) -> str:
        """AES-256-CBC 解密"""
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        raw = base64.b64decode(encrypted)
        decrypted = cipher.decrypt(raw)
        # PKCS7 unpad
        pad = decrypted[-1]
        if isinstance(pad, int):
            decrypted = decrypted[:-pad]
        else:
            decrypted = decrypted[:-ord(pad)]
        # 解析: random(16) + msg_len(4) + msg + corpid
        content = decrypted[16:]
        msg_len = socket.ntohl(struct.unpack("I", content[:4])[0])
        result = content[4:4 + msg_len].decode("utf-8")
        return result


# ── XML 解析 ──

def parse_wecom_xml(xml_str: str) -> dict:
    """解析企业微信回调消息XML"""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml_str)
        return {
            "ToUserName": root.findtext("ToUserName", ""),
            "FromUserName": root.findtext("FromUserName", ""),
            "CreateTime": root.findtext("CreateTime", ""),
            "MsgType": root.findtext("MsgType", ""),
            "Content": root.findtext("Content", ""),
            "MsgId": root.findtext("MsgId", ""),
            "AgentID": root.findtext("AgentID", ""),
            "ChatId": root.findtext("ChatId", ""),
            "ChatType": root.findtext("ChatType", ""),
        }
    except Exception as e:
        log.error(f"XML解析失败: {e}")
        return {}
