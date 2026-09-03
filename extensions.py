"""DeriveSci-Backend/extensions.py
Copyright (c) 2026 Louis Liu  All rights reserved.

声明并实例化所需的第三方插件，包括：
- 全局 JWT 令牌管理器
- 全局 Redis 缓存客户端连接池
"""

from flask_jwt_extended import JWTManager
from flask_redis import FlaskRedis

jwt = JWTManager()
redis_client = FlaskRedis()
