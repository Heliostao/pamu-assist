"""
Cloudflare Clef 决策模型客户端：一次调用返回三层意图决策。

三层：needs_rag（是否检索）/ needs_optimize（是否优化）/ how（怎么优化）。
state_text 由调用方（router 节点）拼装，包含游戏背景、锁定角色与用户最新问题。
"""
import httpx

from src.util.config import (
    CLOUDFLARE_ACCOUNT_ID,
    CLOUDFLARE_API_TOKEN,
    CLOUDFLARE_CLEF_MODEL,
)

_ENDPOINT = (
    "https://api.cloudflare.com/client/v4/accounts/"
    f"{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CLOUDFLARE_CLEF_MODEL}"
)

_QUESTIONS = {
    "needs_rag": {
        "type": "choice",
        "instructions": "用户是否需要从游戏知识库检索信息？",
        "criteria": {"chat": "打招呼、闲聊、与游戏无关，直接回复", "rag": "询问游戏角色或术语具体内容，需检索"},
    },
    "needs_optimize": {
        "type": "choice",
        "instructions": "该检索问题是否需要查询优化？",
        "criteria": {"direct": "问题规范、单一要点，可直接检索", "optimize": "口语化/含指代或含多要点，需改写或拆分"},
    },
    "how": {
        "type": "choice",
        "instructions": "该问题应如何优化？",
        "criteria": {"rewrite": "口语化或含指代，需改写", "split": "含多个独立要点，需拆分", "both": "既口语化又含多要点，改写并拆分"},
    },
}


def route_intent(state_text: str) -> dict:
    """一次调用返回三层决策，每层含 choice / confidence。"""
    resp = httpx.post(
        _ENDPOINT,
        headers={"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"},
        json={"state": state_text, "questions": _QUESTIONS},
        timeout=10.0,
    )
    resp.raise_for_status()
    answers = resp.json()["result"]["answers"]
    return {
        "needs_rag": answers["needs_rag"],
        "needs_optimize": answers["needs_optimize"],
        "how": answers["how"],
    }
