"""DeriveSci-Backend/blueprints/auth.py
Copyright (c) 2026 Louis Liu  All rights reserved.
Copyright (c) 2026 Zatursure  All rights reserved.

用于用户登录态管理的若干路由。
"""

import datetime
import hashlib

from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import (
    get_jwt,
    jwt_required,
    set_refresh_cookies,
    unset_jwt_cookies,
)

from models import db, find_user, register_user, unregister_user
from utils import (
    create_tokens,
    blacklist_access_token,
    validate_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
    login_required,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/login")
def auth_login():
    data = request.json
    username = data.get("userName")
    password = data.get("password")

    if not username or not password:
        return {"code": "INVALID_INPUT", "msg": "用户名和密码不能为空。"}, 400

    user = find_user(username, "name")
    if not user or not user.verify_password(password):
        return {"code": "INVALID_CREDENTIALS", "msg": "用户名或密码错误。"}, 401

    access_token, refresh_token = create_tokens(user)
    response = jsonify(
        {
            "msg": "登录成功",
            "data": {
                "token": access_token,
                "user": user.to_dict(),
            },
        }
    )
    set_refresh_cookies(response, refresh_token)
    return response


@auth_bp.post("/register")
def auth_register():
    data = request.form
    username = data.get("userName")
    gender = data.get("gender")
    password = data.get("password")
    avatar = request.files.get("avatar")

    if not username or not password:
        return {"code": "INVALID_INPUT", "msg": "用户名和密码不能为空。"}, 400

    try:
        gender = int(gender) if gender else 0
    except (ValueError, TypeError):
        return {"code": "INVALID_INPUT", "msg": "性别字段非法。"}, 400

    status, user = register_user(username, gender, password, avatar)
    if not status:
        return {"code": "REGISTRATION_FAILED", "msg": str(user)}, 400

    access_token, refresh_token = create_tokens(user)
    response = jsonify(
        {
            "msg": "注册成功",
            "data": {
                "token": access_token,
                "user": user.to_dict(),
            },
        }
    )
    set_refresh_cookies(response, refresh_token)
    return response


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def auth_refresh():
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        return {"code": "REFRESH_TOKEN_NOT_FOUND", "msg": "refresh token 不存在"}, 401
    if not validate_refresh_token(refresh_token):
        return {"code": "REFRESH_TOKEN_INVALID", "msg": "refresh token 已失效"}, 401
    new_access_token, new_refresh_token = rotate_refresh_token(refresh_token)
    response = jsonify({"data": {"token": new_access_token}})
    set_refresh_cookies(response, new_refresh_token)
    return response


@auth_bp.post("/logout")
@jwt_required()
def auth_logout():
    blacklist_access_token(get_jwt())
    revoke_refresh_token(request.cookies.get("refresh_token"))
    response = jsonify({"msg": "登出成功"})
    unset_jwt_cookies(response)
    return response


@auth_bp.post("/unregister")
@login_required
def auth_unregister(user):
    try:
        blacklist_access_token(get_jwt())
        revoke_refresh_token(request.cookies.get("refresh_token"))
        unregister_user(user)
        response = jsonify({"msg": "注销成功"})
        unset_jwt_cookies(response)
        return response
    except Exception as err:
        return {"code": "UNREGISTER_FAILED", "msg": str(err)}, 500


@auth_bp.get("/me")
@login_required
def auth_me(user):
    return {"data": user.to_dict()}


@auth_bp.get("/avatar/<int:uid>")
def avatar(uid):
    user = find_user(uid)
    if not user or not user.avatar:
        return "", 404
    if not user.avlastmodified:
        user.avlastmodified = datetime.datetime.min
        db.session.commit()

    etag = hashlib.md5(user.avatar).hexdigest()
    if_none_match = request.headers.get("If-None-Match")
    if_modified_since = request.headers.get("If-Modified-Since")
    if if_none_match and if_none_match == etag:
        return "", 304
    if if_modified_since:
        try:
            client_time = datetime.datetime.strptime(
                if_modified_since, "%a, %d %b %Y %H:%M:%S GMT"
            )
            if client_time >= user.avlastmodified.replace(microsecond=0):
                return "", 304
        except ValueError:
            return "", 400

    response = make_response(user.avatar)
    response.headers["Content-Type"] = user.avmimetype or "image/jpeg"
    response.headers["ETag"] = etag
    response.headers["Last-Modified"] = user.avlastmodified.strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )
    response.headers["Cache-Control"] = "public, max-age=600"
    return response
