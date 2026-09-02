from flask_jwt_extended import JWTManager
from flask_redis import FlaskRedis

jwt = JWTManager()
redis_client = FlaskRedis()
