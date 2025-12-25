"""
单元测试 - 安全模块
测试密码哈希、JWT Token 等
"""

from datetime import timedelta

import pytest
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    """密码哈希测试"""

    @pytest.mark.unit
    def test_hash_password(self):
        """测试密码哈希"""
        password = "my_secure_password"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 20  # bcrypt hash 通常较长

    @pytest.mark.unit
    def test_verify_password_success(self):
        """测试验证正确密码"""
        password = "my_secure_password"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    @pytest.mark.unit
    def test_verify_password_fail(self):
        """测试验证错误密码"""
        password = "my_secure_password"
        hashed = get_password_hash(password)

        assert verify_password("wrong_password", hashed) is False

    @pytest.mark.unit
    def test_hash_different_each_time(self):
        """测试每次哈希结果不同（salt）"""
        password = "same_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2  # 每次哈希应该不同
        # 但两个哈希都能验证原密码
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTToken:
    """JWT Token 测试"""

    @pytest.mark.unit
    def test_create_access_token(self):
        """测试创建访问令牌"""
        user_id = "test-user-id"
        token = create_access_token(subject=user_id)

        assert token is not None
        assert len(token) > 50  # JWT token 较长

    @pytest.mark.unit
    def test_decode_access_token(self):
        """测试解码访问令牌"""
        user_id = "test-user-id"
        token = create_access_token(subject=user_id)

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "access"

    @pytest.mark.unit
    def test_create_refresh_token(self):
        """测试创建刷新令牌"""
        user_id = "test-user-id"
        token = create_refresh_token(subject=user_id)

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"

    @pytest.mark.unit
    def test_token_expiration(self):
        """测试令牌包含过期时间"""
        token = create_access_token(
            subject="user",
            expires_delta=timedelta(minutes=30),
        )

        payload = decode_token(token)

        assert "exp" in payload

    @pytest.mark.unit
    def test_invalid_token(self):
        """测试无效令牌"""
        payload = decode_token("invalid.token.here")

        assert payload is None

    @pytest.mark.unit
    def test_token_with_extra_data(self):
        """测试带额外数据的令牌"""
        token = create_access_token(
            subject="user",
            extra_data={"role": "admin", "permissions": ["read", "write"]},
        )

        payload = decode_token(token)

        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]


class TestAPIKey:
    """API Key 测试"""

    @pytest.mark.unit
    def test_generate_api_key(self):
        """测试生成 API Key"""
        api_key, _, _ = generate_api_key()

        assert api_key is not None
        assert len(api_key) >= 32  # 足够长

    @pytest.mark.unit
    def test_api_key_unique(self):
        """测试 API Key 唯一性"""
        keys = [generate_api_key() for _ in range(100)]

        # 所有 key 应该都不同
        assert len(set(keys)) == 100
