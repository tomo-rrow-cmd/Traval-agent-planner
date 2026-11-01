"""
LLM 抽象基类 - 定义统一的大模型调用接口
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional


class BaseLLM(ABC):
    """LLM 服务抽象基类"""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str:
        """同步对话：发送消息列表，返回完整回复"""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncIterator[str]:
        """流式对话：逐步返回回复片段"""
        ...

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        temperature: float = 0.7,
        **kwargs,
    ) -> dict:
        """带工具调用的对话：支持 Function Calling"""
        ...
