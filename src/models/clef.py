"""
Cloudflare Clef 决策模型客户端：对用户问题做「是否需要检索」的二分意图路由。

只暴露 needs_rag(state_text) -> float，返回「需要检索」的概率（0~1）。
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
        "type": "noul",
        "instructions": "用户是否在询问崩坏星穹铁道游戏角色或术语的具体内容，需要从游戏知识库检索准确信息才能回答？",
    }
}


def needs_rag(state_text: str) -> float:
    """返回「需要检索」的概率（0~1）。"""
    resp = httpx.post(
        _ENDPOINT,
        headers={"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"},
        json={"state": state_text, "questions": _QUESTIONS},
        timeout=10.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return float(data["result"]["answers"]["needs_rag"]["noul"])
