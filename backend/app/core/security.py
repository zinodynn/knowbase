"""
安全模块
密码哈希、JWT Token、API Key 管理
"""
from datetime import datetime, timedelta
from typing import Optional, Any
import secrets
import hashlib

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_data: Optional[dict] = None
) -> str:
    """
    创建 JWT access token
    
    Args:
        subject: token 主题（通常是 user_id）
        expires_delta: 过期时间增量
        extra_data: 额外数据
    
    Returns:
        JWT token 字符串
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "type": "access"
    }
    
    if extra_data:
        to_encode.update(extra_data)
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建 JWT refresh token
    
    Args:
        subject: token 主题（通常是 user_id）
        expires_delta: 过期时间增量
    
    Returns:
        JWT token 字符串
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh"
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """
    解码 JWT token
    
    Args:
        token: JWT token 字符串
    
    Returns:
        解码后的 payload，验证失败返回 None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_api_key() -> tuple[str, str, str]:
    """
    生成 API Key
    
    Returns:
        (完整 key, key 哈希, key 前缀)
    """
    # 生成 32 字节随机 key
    raw_key = secrets.token_urlsafe(32)
    # 添加前缀
    full_key = f"kb_{raw_key}"
    # 前缀用于显示
    key_prefix = full_key[:10]
    # 哈希用于存储
    key_hash = hash_api_key(full_key)
    
    return full_key, key_hash, key_prefix


def hash_api_key(api_key: str) -> str:
    """
    对 API Key 进行哈希
    
    Args:
        api_key: 原始 API Key
    
    Returns:
        哈希后的字符串
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, key_hash: str) -> bool:
    """
    验证 API Key
    
    Args:
        api_key: 原始 API Key
        key_hash: 存储的哈希
    
    Returns:
        是否匹配
    """
    return hash_api_key(api_key) == key_hash
