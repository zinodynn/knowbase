"""
加密模块
用于加密存储敏感数据（API Key、密码等）
"""
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings


class EncryptionService:
    """加密服务"""
    
    def __init__(self):
        """初始化加密服务"""
        # 确保密钥格式正确
        key = settings.ENCRYPTION_KEY
        if not key or key == "your-encryption-key-change-in-production":
            # 开发环境使用默认密钥
            key = Fernet.generate_key().decode()
        
        # 如果密钥不是有效的 Fernet 密钥，尝试从字符串生成
        try:
            self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception:
            # 使用 SHA256 从任意字符串生成有效密钥
            import hashlib
            import base64
            hash_key = hashlib.sha256(key.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(hash_key)
            self.cipher = Fernet(fernet_key)
    
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
            InvalidToken: 解密失败
        """
        if not ciphertext:
            return ""
        try:
            return self.cipher.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            raise ValueError("解密失败：无效的密文或密钥")


# 全局加密服务实例
encryption_service = EncryptionService()


def encrypt_value(value: str) -> str:
    """加密值的快捷函数"""
    return encryption_service.encrypt(value)


def decrypt_value(value: str) -> str:
    """解密值的快捷函数"""
    return encryption_service.decrypt(value)
