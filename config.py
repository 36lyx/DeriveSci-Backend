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
