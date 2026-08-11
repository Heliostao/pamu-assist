"""
角色文档加载器 — 使用 UnstructuredMarkdownLoader 解析 Markdown 文件
"""
from pathlib import Path

from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_core.documents import Document


class DocumentLoader:
    """批量加载 data/character/ 下全部角色 Markdown"""

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)

    def loader(self) -> list[Document]:
        docs: list[Document] = []
        for md_path in self.data_dir.glob("*.md"):
            loader = UnstructuredMarkdownLoader(
                file_path=str(md_path.resolve()),
                mode="single",         # 整篇加载，交给 RecursiveCharacterTextSplitter 按语义边界切分
            )
            loaded = loader.load()
            for doc in loaded:
                doc.metadata["source"] = md_path.name
                doc.metadata["doc_type"] = "角色数据"
            docs.extend(loaded)
        return docs
