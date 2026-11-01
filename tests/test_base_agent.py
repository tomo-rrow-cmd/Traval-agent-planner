"""测试 app/agents/base.py — BaseAgent 基类"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.base import BaseAgent


class ConcreteAgent(BaseAgent):
    """用于测试 BaseAgent 非抽象方法的最小实现"""
    name = "test_agent"

    async def run(self, input_data: dict) -> dict:
        return {"result": "ok", **input_data}


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value="mock response")
    llm.chat_stream = AsyncMock()
    llm.chat_with_tools = AsyncMock(return_value={"content": "tool response", "tool_calls": []})
    llm.api_key = "test"
    llm.base_url = "http://test"
    llm.model = "test"
    return llm


@pytest.fixture
def agent(mock_llm):
    return ConcreteAgent(mock_llm)


# ═══════════════════════════════════════════════════════
# 基础属性
# ═══════════════════════════════════════════════════════

class TestBaseAgentInit:
    def test_init_stores_llm(self, mock_llm):
        agent = ConcreteAgent(mock_llm)
        assert agent.llm is mock_llm

    def test_init_has_empty_tools(self, mock_llm):
        agent = ConcreteAgent(mock_llm)
        assert agent.tools == []

    def test_init_has_empty_context(self, mock_llm):
        agent = ConcreteAgent(mock_llm)
        assert agent._context == {}


class TestBaseAgentContext:
    def test_context_getter_setter(self, agent):
        agent.context = {"key": "value"}
        assert agent.context == {"key": "value"}

    def test_context_default_empty_dict(self, agent):
        assert agent.context == {}


# ═══════════════════════════════════════════════════════
# call_llm
# ═══════════════════════════════════════════════════════

class TestCallLLM:
    @pytest.mark.asyncio
    async def test_returns_llm_chat_result(self, agent):
        agent.llm.chat = AsyncMock(return_value="hello from LLM")
        result = await agent.call_llm([{"role": "user", "content": "hi"}])
        assert result == "hello from LLM"

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self, agent):
        call_count = [0]

        async def flaky_chat(messages, temperature=0.7, max_tokens=4096, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise RuntimeError("temporary failure")
            return "finally worked"

        agent.llm.chat = flaky_chat
        result = await agent.call_llm([{"role": "user", "content": "hi"}])
        assert result == "finally worked"
        assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self, agent):
        async def always_fails(messages, temperature=0.7, max_tokens=4096, **kwargs):
            raise RuntimeError("always fail")

        agent.llm.chat = always_fails
        with pytest.raises(RuntimeError, match="always fail"):
            await agent.call_llm([{"role": "user", "content": "hi"}])


# ═══════════════════════════════════════════════════════
# call_llm_with_tools
# ═══════════════════════════════════════════════════════

class TestCallLLMWithTools:
    @pytest.mark.asyncio
    async def test_returns_chat_with_tools_result(self, agent):
        expected = {"content": "tool result", "tool_calls": [{"id": "t1"}]}
        agent.llm.chat_with_tools = AsyncMock(return_value=expected)
        result = await agent.call_llm_with_tools([{"role": "user", "content": "hi"}])
        assert result == expected

    @pytest.mark.asyncio
    async def test_retries_and_raises(self, agent):
        async def always_fails(messages, tools, temperature=0.7, **kwargs):
            raise RuntimeError("tool failure")

        agent.llm.chat_with_tools = always_fails
        with pytest.raises(RuntimeError):
            await agent.call_llm_with_tools([{"role": "user", "content": "hi"}])


# ═══════════════════════════════════════════════════════
# execute_tools
# ═══════════════════════════════════════════════════════

class TestExecuteTools:
    @pytest.mark.asyncio
    async def test_no_tool_calls_returns_content(self, agent):
        agent.llm.chat_with_tools = AsyncMock(return_value={
            "content": "no tools needed", "tool_calls": []
        })
        result = await agent.execute_tools([{"role": "user", "content": "hello"}])
        assert result == "no tools needed"

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error_recovery(self, agent):
        agent.llm.chat_with_tools = AsyncMock(return_value={
            "content": "calling",
            "tool_calls": [
                {"id": "call_1", "function": {"name": "unknown_tool", "arguments": "{}"}}
            ]
        })
        agent.llm.chat = AsyncMock(return_value="final response after tool failure")

        result = await agent.execute_tools([{"role": "user", "content": "hi"}])
        assert result == "final response after tool failure"


# ═══════════════════════════════════════════════════════
# validate_output
# ═══════════════════════════════════════════════════════

class TestValidateOutput:
    def test_valid_data_passes(self, agent):
        from pydantic import BaseModel

        class TestSchema(BaseModel):
            name: str = "default"
            age: int = 0

        result = agent.validate_output({"name": "Alice", "age": 30}, TestSchema)
        assert result["name"] == "Alice"
        assert result["age"] == 30

    def test_invalid_data_merges_defaults(self, agent):
        from pydantic import BaseModel

        class TestSchema(BaseModel):
            name: str = "default"
            age: int = 0

        result = agent.validate_output({"extra": "field"}, TestSchema)
        assert "name" in result  # 合并了默认值

    def test_extreme_corruption_returns_original(self, agent):
        from pydantic import BaseModel

        class TestSchema(BaseModel):
            version: int

        data = {"completely": "wrong"}
        result = agent.validate_output(data, TestSchema)
        assert result == data


# ═══════════════════════════════════════════════════════
# register_tool / run_stream
# ═══════════════════════════════════════════════════════

class TestRegisterTool:
    def test_register_tool_appends(self, agent):
        tool_def = {"name": "search", "description": "search tool"}
        agent.register_tool(tool_def)
        assert len(agent.tools) == 1
        assert agent.tools[0]["name"] == "search"


class TestRunStream:
    @pytest.mark.asyncio
    async def test_run_stream_yields_json(self, agent):
        chunks = []
        async for chunk in agent.run_stream({"input": "test"}):
            chunks.append(chunk)
        result = "".join(chunks)
        assert "ok" in result
        assert "test" in result
