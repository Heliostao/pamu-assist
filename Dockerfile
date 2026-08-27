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
# 国内网络下 deb.debian.org 频繁中断（unexpected EOF），切阿里云镜像并启用下载重试
RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list; \
    apt-get update -o Acquire::Retries=5 && \
    apt-get install -y --no-install-recommends \
    gcc g++ build-essential \
    && rm -rf /var/lib/apt/lists/*

# ── Python 依赖（利用 Docker 层缓存，代码改动不会重装）──
COPY requirements.txt .
# 国内网络下 PyPI 直连较慢，改用阿里云镜像源
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# ── 本地推理依赖（HuggingFaceEmbeddings / HuggingFaceCrossEncoder 必需）──
# langchain-huggingface 1.x 把 sentence-transformers/transformers 放在 [full] extra 里默认不装，
# langchain-community 0.4.x 也不声明。容器纯 CPU 运行，故装 CPU-only torch（约 800MB，避免 PyPI 默认
# CUDA 版附带 4GB nvidia 库）；CPU wheel 不在 PyPI，用上海交大 pytorch 镜像（国内源，无需代理）。
# 先装 CPU torch 占住依赖，再装 sentence-transformers 时 pip 检测到已满足，不会再拉 CUDA 版。
# 独立成层以保留上面 pip 层的构建缓存
RUN pip install --no-cache-dir torch --index-url https://mirror.sjtu.edu.cn/pytorch-wheels/cpu && \
    pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ "sentence-transformers>=5.2.0,<6.0.0"

# ── 预下载 ML 模型（检索阶段必需：embedding 向量化用户问题 + reranker 重排）──
# HuggingFace 下载慢的话在 Railway Variables 加 HF_ENDPOINT=https://hf-mirror.com
# 构建期模型下载同样走 hf-mirror 加速（如本机已配代理可删除该行）
ENV HF_ENDPOINT=https://hf-mirror.com
RUN python -c "\
from langchain_huggingface import HuggingFaceEmbeddings; \
HuggingFaceEmbeddings(model_name='BAAI/bge-base-zh-v1.5', model_kwargs={'device': 'cpu'})"

RUN python -c "\
from langchain_community.cross_encoders import HuggingFaceCrossEncoder; \
HuggingFaceCrossEncoder(model_name='BAAI/bge-reranker-base', model_kwargs={'device': 'cpu'})"

# ── 拷贝项目（chroma_data/ 已被 .dockerignore 排除，向量库由 Docker 中的 Chroma 服务提供）──
COPY . .

# ── 覆盖为 Docker 内构建的前端产物 ──
# vite.config.js 的 outDir: '../src/static' 相对 frontend 阶段的 /frontend 解析，实际输出到容器根 /src/static
COPY --from=frontend /src/static/ ./src/static/

# ── 环境变量 ──
ENV PYTHONPATH=/app

EXPOSE 426

CMD ["python", "main.py"]
