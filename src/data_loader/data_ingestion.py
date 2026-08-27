"""
数据入库入口（角色 + 术语）：加载 → 分割 → 向量化 → Chroma
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

# 0. 调试阶段全量清空
ids = vectorstore.get()["ids"]
if ids:
    vectorstore.delete(ids=ids)
    print(f"[0/4] 已清空旧数据 {len(ids)} 条")
else:
    print("[0/4] 数据库为空，跳过清空")

# 1. 加载角色 Markdown
print("[1/4] UnstructuredMarkdownLoader 加载角色 ")
loader = DocumentLoader(CHAR_DIR)
char_docs = loader.loader()
print(f"  角色文档: {len(char_docs)} 篇")

# 2. 加载术语表
print("[2/4] 加载术语表...")
term_docs = load_term_documents(TERM_DIR)
print(f"  术语条目: {len(term_docs)} 条")

# 3. 合并 + 分割
all_docs = char_docs + term_docs
print(f"[3/4] 递归分割（共 {len(all_docs)} 篇文档）...")
splitter = DocumentSplitter(docs=all_docs)
chunks = splitter.split()
print(f"  分割后: {len(chunks)} 个文本块")

# 4. 入库
print("[4/4] 向量化 & 写入 Chroma...")
index = DocumentIndex(chunks=chunks, vectorstore=vectorstore)
index.add_documents()
print(f"  入库完成: {len(vectorstore.get()['ids'])} 条")
