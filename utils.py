"""DeriveSci-Backend/utils.py
Copyright (c) 2026 Louis Liu  All rights reserved.

用户身份认证与安全认证管理的核心工具模块。

本模块实现了基于双 Token 机制（短效 Access Token + 长效 Refresh Token）的完整安全生命周期管理，
包含 Token 的签发存储、合规验证、安全轮转、主动注销、状态拉黑以及路由访问控制（装饰器）。
"""

import time
import functools

from flask_jwt_extended import (
    get_jwt_identity,
    verify_jwt_in_request,
    create_access_token,
    create_refresh_token,
    decode_token,
)

from models import find_user
from extensions import jwt, redis_client

__all__ = [
    "get_current_user",
    "login_required",
    "create_tokens",
    "save_refresh_token",
    "revoke_refresh_token",
    "validate_refresh_token",
    "rotate_refresh_token",
    "blacklist_access_token",
]

REFRESH_KEY = "jwt:refresh:{}"
BLACKLIST_KEY = "jwt:blacklist:{}"


def get_current_user():
    """获取当前用户。"""
    uid = get_jwt_identity()
    return None if uid is None else find_user(uid)


def optional_login(f):
    """可选的身份验证拦截装饰器。
    拦截传入了凭证但凭证过期，或者凭证代表的用户不存在的请求，并将用户对象作为第一个参数传递给被装饰的函数；
    若无凭证，则将 None 作为第一个参数传递给被装饰的函数。
    """

    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return f(None, *args, **kwargs)

        uid = get_jwt_identity()
        if not uid:
            return {"code": "INVALID_TOKEN", "msg": "Invalid token."}, 401

        try:
            uid = int(uid)
        except ValueError:
            return {"code": "INVALID_CREDENTIALS", "msg": "Invalid user ID."}, 401

        user = find_user(int(uid))
        if not user:
            return {"code": "INVALID_CREDENTIALS", "msg": "User not found."}, 404

        return f(user, *args, **kwargs)

    return decorated_function


def login_required(f):
    """身份验证拦截装饰器。
    拦截未携带凭证，或者凭证过期，或者凭证代表的用户不存在的请求，并将用户对象作为第一个参数传递给被装饰的函数。
    """

    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return {"code": "LOGIN_REQUIRED", "msg": "Login required."}, 401

        uid = get_jwt_identity()
        if not uid:
            return {"code": "INVALID_TOKEN", "msg": "Invalid token."}, 401

        try:
            uid = int(uid)
        except ValueError:
            return {"code": "INVALID_CREDENTIALS", "msg": "Invalid user ID."}, 401

        user = find_user(int(uid))
        if not user:
            return {"code": "INVALID_CREDENTIALS", "msg": "User not found."}, 404

        return f(user, *args, **kwargs)

    return decorated_function


def create_tokens(user):
    """创建 Access Token 和 Refresh Token。"""
    access_token = create_access_token(
        identity=str(user.uid),
        additional_claims={"userName": user.name, "isAdmin": user.isadmin},
    )
    refresh_token = create_refresh_token(identity=str(user.uid))
    save_refresh_token(refresh_token, user.uid)
    return access_token, refresh_token


def save_refresh_token(refresh_token, user_id):
    """签发 Refresh Token。"""
    payload = decode_token(refresh_token)
    jti, exp = payload["jti"], payload["exp"]
    ttl = exp - int(time.time())
    if ttl > 0:
        redis_client.setex(REFRESH_KEY.format(jti), ttl, str(user_id))


def revoke_refresh_token(refresh_token):
    """注销 Refresh Token。"""
    if not refresh_token:
        return
    try:
        payload = decode_token(refresh_token)
        jti = payload["jti"]
        redis_client.delete(REFRESH_KEY.format(jti))
    except Exception:
        pass


def validate_refresh_token(refresh_token):
    """检验 Refresh Token 是否有效。"""
    payload = decode_token(refresh_token)
    jti = payload["jti"]
    return redis_client.exists(REFRESH_KEY.format(jti))


def rotate_refresh_token(old_refresh_token):
    """轮转 Refresh Token。
    先注销 Refresh Token，再重新创建 Access Token 和 Refresh Token。"""
    payload = decode_token(old_refresh_token)
    uid = payload["sub"]
    user = find_user(int(uid))
    revoke_refresh_token(old_refresh_token)
    return create_tokens(user)


def blacklist_access_token(jwt_payload):
    """拉黑 Access Token。"""
    jti, exp = jwt_payload["jti"], jwt_payload["exp"]
    ttl = exp - int(time.time())
    if ttl > 0:
        redis_client.setex(BLACKLIST_KEY.format(jti), ttl, "1")


@jwt.token_in_blocklist_loader
def check_blacklist(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    key = BLACKLIST_KEY.format(jti)
    return redis_client.exists(key)


@jwt.expired_token_loader
def expired(jwt_header, jwt_payload):
    return {"code": "TOKEN_EXPIRED", "msg": "Token expired."}, 401
