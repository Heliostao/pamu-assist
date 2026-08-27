"""
唯一的 FastAPI 应用入口，负责：
组装路由（挂载 auth、conversations 两个 router + 静态资源）、
定义核心的 POST /chat 流式接口（SSE）、
启动时经 lifespan 初始化数据库与编译 LangGraph。

/chat 里做三件事：
校验会话归属 →
从数据库加载最近 RAG_HISTORY_LIMIT 条历史拼成多轮消息（短期记忆）→
交给 graph.astream 流式生成，边收 token 边推给前端，结束后把问答写回数据库。
"""

import asyncio
import json
import random
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from src.api import auth as auth_api
from src.api import conversations as conv_api
from src.auth.security import get_current_user
from src.database.db import get_db, init_db
from src.database.models import Message as DbMessage
from src.database.models import User
from src.util.config import EVAL_LOG_ENABLED, EVAL_SAMPLE_RATE, RAG_HISTORY_LIMIT
from src.util.eval_log import write_eval_log

graph = None  # LangGraph 编译对象，lifespan 启动时注入


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    loop = asyncio.get_running_loop()
    print("正在初始化数据库...")
    await loop.run_in_executor(None, init_db)
    print("正在加载知识库与模型...")
    graph = await loop.run_in_executor(None, _load_graph)
    print("启动完成 → http://localhost:426/static/index.html")
    yield


def _load_graph():
    from src.graph.Agentic_RAG import graph as g

    return g


def _load_history(db, conversation_id: int) -> list:
    """短期记忆：加载会话最近的 N 条历史消息，构造为消息对象序列。"""
    rows = (
        db.query(DbMessage)
        .filter(DbMessage.conversation_id == conversation_id)
        .order_by(DbMessage.id.desc())
        .limit(RAG_HISTORY_LIMIT)
        .all()
    )
    rows.reverse()
    history = []
    for row in rows:
        if row.role == "user":
            history.append(HumanMessage(content=row.content))
        elif row.role == "assistant":
            history.append(AIMessage(content=row.content))
    return history


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="src/static", html=True), name="static")
app.include_router(auth_api.router)
app.include_router(conv_api.router)


@app.get("/")
async def index():
    """根路径直接返回前端页面（Vue 构建产物）。"""
    return FileResponse("src/static/index.html")


class QuestionRequest(BaseModel):
    question: str
    conversation_id: int | None = Field(default=None, description="会话 id，不传则创建新会话")


@app.post("/chat")
async def chat(
    req: QuestionRequest,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    # 未指定会话则自动创建
    if req.conversation_id is None:
        conv = conv_api.Conversation(user_id=user.id, title="新对话")
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conversation_id = conv.id
    else:
        conv = db.get(conv_api.Conversation, req.conversation_id)
        if conv is None or conv.user_id != user.id:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="会话不存在")
        conversation_id = conv.id

    async def event_stream():
        collected = []
        retrieved_docs: list[dict] = []

        def on_token(t: str):
            collected.append(t)

        # 短期记忆：注入该会话最近的历史消息（与当前问题组成多轮上下文）
        history = await asyncio.to_thread(_load_history, db, conversation_id)

        try:
            async for mode, chunk in graph.astream(  # type: ignore[union-attr]
                {"messages": history + [HumanMessage(content=req.question)]},
                stream_mode=["custom", "updates"],
            ):
                if mode == "custom":
                    # stream_mode="custom" 只会收到节点中 writer 推送的 token
                    if isinstance(chunk, dict) and chunk.get("t"):
                        on_token(chunk["t"])
                        yield f"data: {json.dumps({'t': chunk['t']}, ensure_ascii=False)}\n\n"
                elif mode == "updates":
                    # 从 format 节点输出中捕获本次检索结果（写评估日志用）
                    for node_name, output in chunk.items():
                        if node_name == "format" and isinstance(output, dict):
                            docs = output.get("retrieved_docs") or []
                            if docs:
                                retrieved_docs = docs
            yield "data: [DONE]\n\n"

            # 流结束后把问答写入数据库
            assistant_text = "".join(collected)
            if assistant_text.strip():
                await asyncio.to_thread(
                    conv_api.save_chat_messages,
                    db,
                    conversation_id,
                    user.id,
                    req.question,
                    assistant_text,
                )
                # 旁路写评估日志（采样率控制，用户无感知，失败静默）
                if EVAL_LOG_ENABLED and retrieved_docs and random.random() < EVAL_SAMPLE_RATE:
                    await asyncio.to_thread(
                        write_eval_log,
                        req.question,
                        assistant_text,
                        retrieved_docs,
                        conversation_id,
                    )
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import os

    import uvicorn

    # 生产默认关闭热重载（reload 会监听文件变更自动重启，消耗资源且有窗口期）
    # 本地开发需要热重载时：PAMU_RELOAD=1 python main.py
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=426,
        reload=os.getenv("PAMU_RELOAD", "0") == "1",
    )
