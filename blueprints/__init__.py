"""DeriveSci-Backend/blueprints
Copyright (c) 2026 Zatursure  All rights reserved.

注册所有路由。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask

from .auth import auth_bp
from .probs import probs_bp


def register_all(app: Flask):
    """注册所有后端路由。"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(probs_bp)
