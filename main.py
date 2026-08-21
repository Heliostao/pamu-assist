import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from src.api import auth as auth_api
from src.api import conversations as conv_api
from src.auth.security import get_current_user
from src.database.db import get_db, init_db
from src.database.models import User

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

        def on_token(t: str):
            collected.append(t)

        try:
            async for chunk in graph.astream(  # type: ignore[union-attr]
                {"messages": [HumanMessage(content=req.question)]},
                stream_mode="custom",
            ):
                # stream_mode="custom" 只会收到节点中 writer 推送的 token
                if isinstance(chunk, dict) and chunk.get("t"):
                    on_token(chunk["t"])
                    yield f"data: {json.dumps({'t': chunk['t']}, ensure_ascii=False)}\n\n"
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
