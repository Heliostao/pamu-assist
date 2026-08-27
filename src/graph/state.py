"""
RAG 工作流全局状态定义。
"""
from pydantic import Field
from langgraph.graph import MessagesState


class RagState(MessagesState):
    """Agentic RAG 工作流共享状态。

    messages: 对话消息序列（LangGraph 内建，追加式，多轮对话可携带历史）
    retrieval_query: 本次实际使用的检索词（工具参数拼装结果，兼作缓存 key；
                     优化路径为改写后的 query）
    retrieved_docs: 检索 + 重排后的文档列表（覆盖式写入，供 grade 节点与响应溯源使用）
    optimization_type: 查询优化类型（"rewrite" / "split" / "both" / None，优化路径专用）
    sub_queries: 拆分出的子问题列表（split / both 路径专用）
    """

    retrieval_query: str
    retrieved_docs: list[dict]
    optimization_type: str | None = None
    sub_queries: list[str] = Field(default_factory=list)
