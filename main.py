import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

graph = None  # LangGraph 编译对象，lifespan 启动时注入


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    loop = asyncio.get_running_loop()
    print("正在加载知识库与模型...")
    graph = await loop.run_in_executor(None, _load_graph)
    print("启动完成 → http://localhost:426/static/index.html")
    yield


def _load_graph():
    from src.graph.Agentic_RAG import graph as g

    return g


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="src/static", html=True), name="static")


class QuestionRequest(BaseModel):
    question: str


@app.post("/chat")
async def chat(req: QuestionRequest):
    async def event_stream():
        try:
            async for event in graph.astream_events(  # type: ignore[union-attr]
                {"messages": [HumanMessage(content=req.question)]},
                version="v2",
            ):
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        yield f"data: {json.dumps({'t': chunk.content}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
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
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=426, reload=True)
