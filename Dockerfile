# ── 阶段一：构建前端（Vue3 + Vite）──
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── 阶段二：后端运行镜像 ──
FROM python:3.10-slim

WORKDIR /app

# ── 系统依赖（sentence-transformers / unstructured 编译需要）──
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ build-essential \
    && rm -rf /var/lib/apt/lists/*

# ── Python 依赖（利用 Docker 层缓存，代码改动不会重装）──
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── 预下载 ML 模型（检索阶段必需：embedding 向量化用户问题 + reranker 重排）──
# HuggingFace 下载慢的话在 Railway Variables 加 HF_ENDPOINT=https://hf-mirror.com
RUN python -c "\
from langchain_huggingface import HuggingFaceEmbeddings; \
HuggingFaceEmbeddings(model_name='BAAI/bge-base-zh-v1.5', model_kwargs={'device': 'cpu'})"

RUN python -c "\
from langchain_community.cross_encoders import HuggingFaceCrossEncoder; \
HuggingFaceCrossEncoder(model_name='BAAI/bge-reranker-base', model_kwargs={'device': 'cpu'})"

# ── 拷贝项目（含本地预构建的 chroma_data/ 向量库）──
COPY . .

# ── 覆盖为 Docker 内构建的前端产物 ──
COPY --from=frontend /frontend/src/static/ ./src/static/

# ── 环境变量 ──
ENV PYTHONPATH=/app
ENV CHROMA_PERSIST_DIR=/app/chroma_data

EXPOSE 426

CMD ["python", "main.py"]
