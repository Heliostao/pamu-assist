"""检索层统一出口：tools 包只需 import 本包导出的 compression_retriever。"""
from src.retriever.compression_retriever import compression_retriever

__all__ = ["compression_retriever"]
