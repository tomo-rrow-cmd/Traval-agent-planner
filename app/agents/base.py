"""
Agent 基类定义 - 所有智能体的抽象基类
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from app.services.llm.base import BaseLLM


class BaseAgent(ABC):
    """
    智能体基类。

    每个 Agent 负责旅行规划中的一个特定领域，
    拥有自己的 LLM 实例、工具集和系统提示词。
    """

    # 子类需覆盖的属性
    name: str = "base"
    description: str = "Base agent"

    def __init__(self, llm: BaseLLM):
        self.llm = llm
        self.tools: list[dict] = []
        self._context: dict[str, Any] = {}

    @property
    def context(self) -> dict[str, Any]:
        return self._context

    @context.setter
    def context(self, value: dict[str, Any]):
        self._context = value

    @abstractmethod
    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        执行智能体的核心逻辑。

        Args:
            input_data: 输入数据

        Returns:
            处理结果
        """
        ...

    async def run_stream(
        self,
        input_data: dict[str, Any],
    ) -> AsyncIterator[str]:
        """
        流式执行（可选覆盖）。
        """
        result = await self.run(input_data)
        yield str(result)

    def get_system_prompt(self) -> str:
        """获取该 Agent 的系统提示词"""
        from app.services.llm.prompt_manager import prompt_manager

        return prompt_manager.get_system_prompt(self.name)

    def register_tool(self, tool_def: dict):
        """注册一个工具定义"""
        self.tools.append(tool_def)

    def register_tools_from_registry(self, tool_names: list[str]):
        """从全局工具注册表注册工具（tool_registry.py）"""
        from app.agents.tools.tool_registry import get_tool_defs, get_handler
        all_defs = get_tool_defs()
        for name in tool_names:
            for d in all_defs:
                if d["function"]["name"] == name:
                    self.tools.append(d)
                    setattr(self, f"_handler_{name}", get_handler(name))
                    break

    async def execute_tools(self, messages: list[dict], temperature: float = 0.7,
                             max_turns: int = 3) -> str:
        """
        工具调用循环：LLM → 工具执行 → 结果回传 → LLM 再处理。

        最多 max_turns 轮，防止无限循环。
        """
        import json
        from app.agents.tools.tool_registry import get_handler

        current_msgs = list(messages)
        for turn in range(max_turns):
            response = await self.llm.chat_with_tools(
                messages=current_msgs, tools=self.tools, temperature=temperature,
            )

            tool_calls = response.get("tool_calls") or []
            if not tool_calls:
                # 没有工具调用，返回纯文本回复
                return response.get("content", "")

            # 追加 assistant 的 tool_call 消息
            current_msgs.append({
                "role": "assistant",
                "content": response.get("content") or "",
                "tool_calls": tool_calls,
            })

            # 执行每个工具调用
            for tc in tool_calls:
                func = tc.get("function", {})
                name = func.get("name", "")
                args = json.loads(func.get("arguments", "{}"))
                handler = get_handler(name)

                if handler:
                    try:
                        result = await handler(**args)
                    except Exception as e:
                        result = {"error": str(e)}
                else:
                    result = {"error": f"未知工具: {name}"}

                # tool 结果回传
                current_msgs.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", f"call_{turn}"),
                    "content": json.dumps(result, ensure_ascii=False),
                })

        # 最后一轮用纯 chat 获取最终回复
        final = await self.llm.chat(current_msgs, temperature=temperature)
        return final

    def validate_output(self, data: dict, schema_class) -> dict:
        """Pydantic 校验输出，字段缺失时补默认值并告警"""
        try:
            validated = schema_class(**data)
            return validated.model_dump()
        except Exception as e:
            import json
            print(f"  [{self.name}] 输出校验失败: {e}")
            # 尽力修复：合并默认值
            try:
                default = schema_class()
                merged = json.loads(json.dumps(default.model_dump()))
                merged.update({k: v for k, v in data.items() if k in merged})
                return merged
            except Exception:
                return data

    async def call_llm_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> AsyncIterator[str]:
        """流式调用 LLM，逐 chunk 产出文本（自动重试）"""
        import asyncio
        last_err = None
        for attempt in range(max_retries):
            try:
                async for chunk in self.llm.chat_stream(messages, temperature=temperature):
                    yield chunk
                return
            except Exception as e:
                last_err = e
                if attempt < max_retries - 1:
                    delay = 1.5 ** attempt
                    print(f"  [LLM] stream 重试 {attempt+1}/{max_retries} (等{delay:.1f}s): {str(e)[:60]}")
                    await asyncio.sleep(delay)
        raise last_err  # type: ignore

    async def call_llm(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> str:
        """调用 LLM（自动重试 3 次）"""
        import asyncio
        last_err = None
        for attempt in range(max_retries):
            try:
                return await self.llm.chat(messages, temperature=temperature)
            except Exception as e:
                last_err = e
                if attempt < max_retries - 1:
                    delay = 1.5 ** attempt
                    print(f"  [LLM] 重试 {attempt+1}/{max_retries} (等{delay:.1f}s): {str(e)[:60]}")
                    await asyncio.sleep(delay)
        raise last_err

    async def call_llm_with_tools(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> dict:
        """调用 LLM（带工具，自动重试）"""
        import asyncio
        last_err = None
        for attempt in range(max_retries):
            try:
                return await self.llm.chat_with_tools(
                    messages=messages, tools=self.tools, temperature=temperature,
                )
            except Exception as e:
                last_err = e
                if attempt < max_retries - 1:
                    delay = 1.5 ** attempt
                    print(f"  [LLM] 重试 {attempt+1}/{max_retries} (等{delay:.1f}s): {str(e)[:60]}")
                    await asyncio.sleep(delay)
        raise last_err
