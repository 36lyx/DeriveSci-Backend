"""DeriveSci-Backend/blueprints/probs.py
Copyright (c) 2026 Louis Liu  All rights reserved.
Copyright (c) 2026 Zatursure  All rights reserved.

题集题目相关的若干路由。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import User

from flask import Blueprint

from models import get_prob
from utils import optional_login

probs_bp = Blueprint("probs", __name__, url_prefix="/api/probs")


@probs_bp.get("/<probno>")
@optional_login
def probs_get(user: User | None, probno: str):
    prob = get_prob(probno)
    if prob is None:
        return {"code": "PAGE_NOT_FOUND", "msg": "Problem not found."}, 404
    if not prob.viewable_for(user):
        return {"code": "NO_ACCESS", "msg": "No access to the problem."}, 403
    return {"data": prob.to_dict()}
