"""
RAG 评估日志写入模块（在线侧旁路）。

职责：/chat 流结束后，把本次问答的 question / answer / contexts 追加写入
eval_data/ 目录下的 JSONL 文件（按天分文件），供离线 RAGAS 评估脚本消费。

原则：与用户请求链路完全解耦——只多一条文件写入，不改变任何返回内容；
任何失败都静默吞掉，绝不干扰主链路。
"""
import json
import os
import uuid
from datetime import datetime

from src.util.config import EVAL_LOG_DIR


def _log_path(date_str: str) -> str:
    return os.path.join(EVAL_LOG_DIR, f"{date_str}.jsonl")


def write_eval_log(
    question: str,
    answer: str,
    docs: list[dict],
    conversation_id: int | None = None,
) -> str | None:
    """追加写入一条评估日志，返回记录 id；失败时返回 None（不抛异常）。"""
    try:
        os.makedirs(EVAL_LOG_DIR, exist_ok=True)
        now = datetime.now().astimezone()
        record = {
            "id": str(uuid.uuid4()),
            "timestamp": now.isoformat(),
            "conversation_id": conversation_id,
            "question": question,
            "answer": answer,
            "contexts": [d.get("content", "") for d in docs],
            "ground_truth": None,
        }
        path = _log_path(now.strftime("%Y-%m-%d"))
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record["id"]
    except Exception:
        # 评估日志属于旁路，失败绝不干扰主链路
        return None
