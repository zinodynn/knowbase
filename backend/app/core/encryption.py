"""
加密模块
用于加密存储敏感数据（API Key、密码等）
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_DEV_PLACEHOLDER = "your-encryption-key-change-in-production"


def _derive_fernet_key(raw: str) -> bytes:
    """从任意字符串派生稳定的 Fernet 密钥"""
    digest = hashlib.sha256(raw.encode()).digest()
    return base64.urlsafe_b64encode(digest)


class EncryptionService:
    """加密服务"""

    def __init__(self):
        """初始化加密服务"""
        key = settings.ENCRYPTION_KEY
        if not key or key == _DEV_PLACEHOLDER:
            # 开发占位符：使用稳定派生密钥，避免进程重启后无法解密
            self.cipher = Fernet(_derive_fernet_key("knowbase-dev-encryption-key"))
            return

        try:
            self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception:
            raw = key if isinstance(key, str) else key.decode()
            self.cipher = Fernet(_derive_fernet_key(raw))

    def encrypt(self, plaintext: str) -> str:
        """
        加密明文数据

        Args:
            plaintext: 需要加密的明文

        Returns:
            加密后的密文（base64 编码）
        """
        if not plaintext:
            return ""
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        解密密文数据

        Args:
            ciphertext: 需要解密的密文

        Returns:
            解密后的明文

        Raises:
            ValueError: 解密失败
        """
        if not ciphertext:
            return ""
        try:
            return self.cipher.decrypt(ciphertext.encode()).decode()
        except InvalidToken as e:
            raise ValueError("解密失败：无效的密文或密钥") from e


# 全局加密服务实例
encryption_service = EncryptionService()


def encrypt_value(value: str) -> str:
    """加密值的快捷函数"""
    return encryption_service.encrypt(value)


def decrypt_value(value: str) -> str:
    """解密值的快捷函数"""
    return encryption_service.decrypt(value)
