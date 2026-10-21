"""DeriveSci-Backend/app.py
Copyright (c) 2026 Louis Liu  All rights reserved.
Copyright (c) 2026 Zatursure  All rights reserved.

后端核心入口文件。
"""

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from extensions import jwt, redis_client
from config import Config
from models import db, init_app
from blueprints import register_all

load_dotenv(override=True)
app = Flask(__name__)
app.config.from_object(Config)
CORS(app, supports_credentials=True)

init_app(app)
jwt.init_app(app)
redis_client.init_app(app)

register_all(app)


@app.errorhandler(404)
def page_not_found(error):
    return {"msg": str(error)}, 404


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, port=8080)
