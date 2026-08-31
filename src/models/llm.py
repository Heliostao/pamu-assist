"""
DeepSeek LLM
"""
from langchain_openai import ChatOpenAI

from src.util import DEEPSEEK_MODEL_NAME, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

llm = ChatOpenAI(
    model=DEEPSEEK_MODEL_NAME,
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    temperature=0.2,
    streaming=True,
)
