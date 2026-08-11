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

# ── 环境变量 ──
ENV PYTHONPATH=/app
ENV CHROMA_PERSIST_DIR=/app/chroma_data

EXPOSE 426

CMD ["python", "main.py"]
