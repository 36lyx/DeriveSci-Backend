"""DeriveSci-Backend/config.py
Copyright (c) 2026 Louis Liu  All rights reserved.

后端运行所需配置。实际配置全部定义在 `.env` 文件中。`.env` 文件的模板如下：
```
APP_ENV='development'                  # 运行环境，允许 development 或 production

# Flask
SECRET_KEY='FlaskSecretKey'            # Flask 密钥

# Database
DATABASE_URL='mysql+pymysql://UserName:Password@localhost/DatabaseName'  # MySQL 数据库 URL

# JWT
JWT_SECRET_KEY='JWTSecretKey'          # JWT 密钥

JWT_ACCESS_EXPIRES=900                 # Access Token 有效期（秒）
JWT_REFRESH_EXPIRES=2592000            # Refresh Token 有效期（秒）

# Redis
REDIS_URL='redis://localhost:6379/0'   # Redis 服务器 URL
```
"""

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv(override=True)


class Config:

    APP_ENV = os.getenv("APP_ENV", "development")
    IS_PRODUCTION = APP_ENV == "production"

    SECRET_KEY = os.getenv("SECRET_KEY")

    # JWT

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv("JWT_ACCESS_EXPIRES", 900))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv("JWT_REFRESH_EXPIRES", 2592000))
    )

    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_REFRESH_COOKIE_NAME = "refresh_token"
    JWT_COOKIE_SECURE = IS_PRODUCTION
    JWT_COOKIE_CSRF_PROTECT = IS_PRODUCTION
    JWT_COOKIE_HTTPONLY = True
    JWT_COOKIE_SAMESITE = "Lax"

    # Redis

    REDIS_URL = os.getenv("REDIS_URL")

    # Database

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
