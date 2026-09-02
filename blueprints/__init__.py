"""
Copyright (c) 2026 Zatursure  All rights reserved.
"""

from .auth import auth_bp


def register_all(app):
    app.register_blueprint(auth_bp)
