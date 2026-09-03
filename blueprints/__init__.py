"""DeriveSci-Backend/blueprints
Copyright (c) 2026 Zatursure  All rights reserved.

注册所有路由。
"""

from .auth import auth_bp


def register_all(app):
    """注册所有后端路由。"""
    app.register_blueprint(auth_bp)
