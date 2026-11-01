"""测试 app/core/security.py — JWT 安全工具"""

import pytest
import jwt
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("my_secure_password")
        assert hashed != "my_secure_password"
        assert verify_password("my_secure_password", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True


class TestJWTAccessToken:
    def test_create_and_decode(self):
        token = create_access_token("user-1", extra={"phone": "13800138000"})
        payload = decode_token(token)
        assert payload["sub"] == "user-1"
        assert payload["phone"] == "13800138000"
        assert payload["type"] == "access"

    def test_expired_token_raises(self):
        import time
        # 用极短的有效期创造过期 token，手动构建
        from app.config import settings
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        payload = {
            "sub": "user-1",
            "iat": now - timedelta(seconds=7201),
            "exp": now - timedelta(seconds=1),
            "type": "access",
        }
        expired = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(expired)

    def test_invalid_token_raises(self):
        with pytest.raises(jwt.DecodeError):
            decode_token("not.a.valid.token")
        with pytest.raises(jwt.DecodeError):
            decode_token("")


class TestJWTRefreshToken:
    def test_create_and_decode(self):
        token = create_refresh_token("user-1")
        payload = decode_token(token)
        assert payload["type"] == "refresh"
        assert payload["sub"] == "user-1"
