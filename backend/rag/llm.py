"""OpenAI 兼容接口的大模型客户端。

只要服务商提供 OpenAI 兼容的 /v1/chat/completions，都能直接用：
    通义千问 DashScope : LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1  LLM_MODEL=qwen-plus
    DeepSeek          : LLM_BASE_URL=https://api.deepseek.com/v1                        LLM_MODEL=deepseek-chat
    OpenAI            : LLM_BASE_URL 留空                                                LLM_MODEL=gpt-4o-mini
    本地 Ollama        : LLM_BASE_URL=http://localhost:11434/v1  LLM_API_KEY=ollama      LLM_MODEL=qwen2.5:7b
"""
from __future__ import annotations


class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 60.0):
        from openai import OpenAI

        self.model = model
        self.client = OpenAI(base_url=base_url or None, api_key=api_key or "EMPTY", timeout=timeout)

    def chat(self, messages: list[dict], temperature: float = 0.2, json_mode: bool = False) -> str:
        kwargs = {"model": self.model, "messages": messages, "temperature": temperature}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            resp = self.client.chat.completions.create(**kwargs)
        except Exception as e:  # 有些模型不支持 response_format，去掉再试一次
            if json_mode and "response_format" in str(e):
                kwargs.pop("response_format")
                resp = self.client.chat.completions.create(**kwargs)
            else:
                raise
        return resp.choices[0].message.content or ""
