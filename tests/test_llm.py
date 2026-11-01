"""
LLM 服务测试
"""

import pytest
from unittest.mock import MagicMock

from app.services.llm.base import BaseLLM


class MockLLM(BaseLLM):
    """用于测试的 Mock LLM"""

    async def chat(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
        return "Mock response"

    async def chat_stream(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
        yield "Mock "
        yield "stream "
        yield "response"

    async def chat_with_tools(self, messages, tools, temperature=0.7, **kwargs):
        return {"content": "Mock tool response", "tool_calls": []}


@pytest.mark.asyncio
async def test_mock_llm_chat():
    llm = MockLLM(api_key="test", base_url="http://test", model="test")
    response = await llm.chat([{"role": "user", "content": "Hello"}])
    assert response == "Mock response"


@pytest.mark.asyncio
async def test_mock_llm_stream():
    llm = MockLLM(api_key="test", base_url="http://test", model="test")
    chunks = []
    async for chunk in llm.chat_stream([{"role": "user", "content": "Hello"}]):
        chunks.append(chunk)
    assert "".join(chunks) == "Mock stream response"


@pytest.mark.asyncio
async def test_mock_llm_with_tools():
    llm = MockLLM(api_key="test", base_url="http://test", model="test")
    response = await llm.chat_with_tools(
        [{"role": "user", "content": "Hello"}],
        tools=[],
    )
    assert response["content"] == "Mock tool response"


def test_deepseek_client_uses_bounded_timeout_and_sdk_retries(monkeypatch):
    from app.services.llm import deepseek as deepseek_module

    client_factory = MagicMock()
    monkeypatch.setattr(deepseek_module, "AsyncOpenAI", client_factory)
    monkeypatch.setattr(deepseek_module.settings, "LLM_REQUEST_TIMEOUT_SECONDS", 60.0)
    monkeypatch.setattr(deepseek_module.settings, "LLM_SDK_MAX_RETRIES", 0)

    deepseek_module.DeepSeekLLM()

    client_factory.assert_called_once_with(
        api_key=deepseek_module.settings.DEEPSEEK_API_KEY,
        base_url=deepseek_module.settings.DEEPSEEK_BASE_URL,
        timeout=60.0,
        max_retries=0,
    )
