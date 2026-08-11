"""
文档分割 — 按中文语义边界递归分割
"""
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentSplitter:
    """递归分割：优先按段落/换行/句号级别切分，chunk 512 重叠 64"""

    def __init__(self, docs: List[Document]):
        self.docs = docs

    def split(self) -> List[Document]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=64,
            separators=["\n\n", "\n", "。", ""],
        )
        return splitter.split_documents(self.docs)
