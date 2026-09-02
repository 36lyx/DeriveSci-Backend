"""
Copyright (c) 2026 Louis Liu  All rights reserved.
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

REFRESH_KEY = "jwt:refresh:{}"
BLACKLIST_KEY = "jwt:blacklist:{}"


def get_current_user():
    uid = get_jwt_identity()
    return None if uid is None else find_user(uid)


def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return {"msg": "请先登录"}, 401

        uid = get_jwt_identity()
        if not uid:
            return {"msg": "无效的 Token"}, 401

        try:
            uid = int(uid)
        except ValueError:
            return {"msg": "无效用户"}, 401

        user = find_user(int(uid))
        if not user:
            return {"msg": "用户不存在"}, 404

        return f(user, *args, **kwargs)

    return decorated_function


def create_tokens(user):
    access_token = create_access_token(
        identity=str(user.uid),
        additional_claims={"userName": user.name, "isAdmin": user.isadmin},
    )
    refresh_token = create_refresh_token(identity=str(user.uid))
    save_refresh_token(refresh_token, user.uid)
    return access_token, refresh_token


def save_refresh_token(refresh_token, user_id):
    payload = decode_token(refresh_token)
    jti, exp = payload["jti"], payload["exp"]
    ttl = exp - int(time.time())
    if ttl > 0:
        redis_client.setex(REFRESH_KEY.format(jti), ttl, str(user_id))


def revoke_refresh_token(refresh_token):
    if not refresh_token:
        return
    try:
        payload = decode_token(refresh_token)
        jti = payload["jti"]
        redis_client.delete(REFRESH_KEY.format(jti))
    except Exception:
        pass


def validate_refresh_token(refresh_token):
    payload = decode_token(refresh_token)
    jti = payload["jti"]
    return redis_client.exists(REFRESH_KEY.format(jti))


def rotate_refresh_token(old_refresh_token):
    payload = decode_token(old_refresh_token)
    uid = payload["sub"]
    user = find_user(int(uid))
    revoke_refresh_token(old_refresh_token)
    return create_tokens(user)


def blacklist_access_token(jwt_payload):
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
    return {"code": "TOKEN_EXPIRED", "msg": "token expired"}, 401
