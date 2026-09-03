"""DeriveSci-Backend/anschecker.py
Copyright (c) 2026 Louis Liu  All rights reserved.

判题引擎，用于判断用户提交的题目答案。
"""

import enum
from sympy import latex, Array, Expr
from func_timeout import func_timeout, FunctionTimedOut
from fpevaluator import fpparse, fpeval, ParseException

__all__ = [
    "TPStatus",
    "check_answer",
    "check_answers",
    "testpoints_passedlist",
    "latex",
]


class TPStatus(enum.Enum):

    CORRECT = 1
    INCORRECT = 2
    PARSEERR = 3
    EVALERR = 4
    TIMEOUT = 5
    ANSERR = 6


def _judge_equal(expr1, expr2):
    if isinstance(expr1, Array) and isinstance(expr2, Array):
        return expr1.shape == expr2.shape and all(
            _judge_equal(expr1[i], expr2[i]) for i in range(expr1.shape[0])
        )
    elif isinstance(expr1, Expr) and isinstance(expr2, Expr):
        return expr1.equals(expr2)
    return expr1 == expr2


def fpparse_with_timeout(answer):
    return func_timeout(0.1, fpparse, args=(answer,))


def fpeval_with_timeout(parsed_answer, context=None):
    return func_timeout(0.3, fpeval, args=(parsed_answer, context))


def check_answer(answer, userans_parsed, context=None):
    try:
        context_processed = {
            key: fpeval(fpparse(str(val))) for key, val in context.items()
        }
        answer_parsed = fpparse_with_timeout(answer)
        answer_eval = fpeval_with_timeout(answer_parsed, context_processed)
    except BaseException:
        return TPStatus.ANSERR
    try:
        userans_eval = fpeval_with_timeout(userans_parsed, context_processed)
        return (
            TPStatus.CORRECT
            if _judge_equal(answer_eval, userans_eval)
            else TPStatus.INCORRECT
        )
    except FunctionTimedOut:
        return TPStatus.TIMEOUT
    except ParseException:
        return TPStatus.PARSEERR
    except Exception:
        return TPStatus.EVALERR


def check_answers(answers, userans):
    try:
        userans_parsed = fpparse_with_timeout(userans)
        try:
            userans_nocontext = fpeval_with_timeout(userans_parsed)
        except BaseException:  # 直接求值的结果不参与答案检查，故不对其任何错误进行处理
            userans_nocontext = None
        return userans_nocontext, [
            check_answer(answer, userans_parsed, context) for context, answer in answers
        ]
    except FunctionTimedOut:
        return None, [TPStatus.TIMEOUT] * len(answers)
    except ParseException:
        return None, [TPStatus.PARSEERR] * len(answers)
    except BaseException:
        return None, [TPStatus.EVALERR] * len(answers)


def testpoints_passedlist(testpoints):
    return [testpoint == TPStatus.CORRECT for testpoint in testpoints]
