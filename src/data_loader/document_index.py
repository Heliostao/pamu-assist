"""
向量入库 — 哈希去重，按 source 增量更新
"""
import hashlib
from typing import List

from langchain_core.documents import Document


def stable_id(chunk: Document) -> str:
    """生成文档 ID"""
    source = chunk.metadata.get("source", "")
    return hashlib.md5(f"{source}:{chunk.page_content}".encode()).hexdigest()


class DocumentIndex:

    def __init__(self, chunks: List[Document], vectorstore):
        self.chunks = chunks
        self.vectorstore = vectorstore

    def add_documents(self):
        sources = {c.metadata.get("source", "") for c in self.chunks}
        for source in sources:
            ids = self.vectorstore.get(where={"source": source})["ids"]
            if ids:
                self.vectorstore.delete(ids=ids)

        self.vectorstore.add_documents(
            self.chunks,
            ids=[stable_id(c) for c in self.chunks],
        )
