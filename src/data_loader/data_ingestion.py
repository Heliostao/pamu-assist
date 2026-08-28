"""
数据入库入口（角色 + 术语）：加载 → 分割 → 向量化入库 Chroma
用法: python data_ingestion.py
"""
from pathlib import Path

from src.data_loader.document_loader import DocumentLoader
from src.data_loader.document_splitter import DocumentSplitter
from src.data_loader.document_index import DocumentIndex
from src.data_loader.term_loader import load_term_documents
from src.models.chroma import vectorstore
from src.util.config import PROJECT_ROOT

ROOT = Path(PROJECT_ROOT)
CHAR_DIR = str(ROOT / "data" / "character")
TERM_DIR = str(ROOT / "data" / "term")

# 全量清空
ids = vectorstore.get()["ids"]
if ids:
    vectorstore.delete(ids=ids)
    print(f"已清空旧数据 {len(ids)} 条")
else:
    print("数据库为空，跳过清空")

# 1. 加载角色 Markdown
loader = DocumentLoader(CHAR_DIR)
char_docs = loader.loader()

# 2. 加载术语表
term_docs = load_term_documents(TERM_DIR)

# 3. 合并 + 分割
all_docs = char_docs + term_docs
splitter = DocumentSplitter(docs=all_docs)
chunks = splitter.split()

# 4. 入库（Chroma）
index = DocumentIndex(chunks=chunks, vectorstore=vectorstore)
index.add_documents()
print(f"  Chroma 入库完成: {len(vectorstore.get()['ids'])} 条")
