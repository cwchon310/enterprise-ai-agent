"""LLM provider abstraction. Swap providers without touching core logic.

- deepseek : DeepSeek Chat API (OpenAI-compatible)
- openai   : OpenAI Chat Completions
- ollama   : local Ollama server
- rule     : deterministic fallback that needs no key (great for demos/tests)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.config import Settings


@dataclass
class LLMResult:
    content: str
    provider: str
    model: str


class BaseLLM(ABC):
    provider = "base"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    def chat(self, messages: list[dict]) -> str:
        """messages: [{role, content}, ...]. Returns assistant text."""


class DeepSeekLLM(BaseLLM):
    provider = "deepseek"

    def chat(self, messages: list[dict]) -> str:
        if not self.settings.deepseek_api_key:
            return self._no_key_message()
        url = f"{self.settings.deepseek_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.settings.deepseek_model,
            "messages": messages,
            "temperature": 0.3,
        }
        headers = {"Authorization": f"Bearer {self.settings.deepseek_api_key}"}
        resp = httpx.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _no_key_message(self) -> str:
        return "（未設定 DEEPSEEK_API_KEY，請喺 .env 配置）"


class OpenAILLM(BaseLLM):
    provider = "openai"

    def chat(self, messages: list[dict]) -> str:
        if not self.settings.openai_api_key:
            return "（未設定 OPENAI_API_KEY，請喺 .env 配置）"
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": self.settings.openai_model,
            "messages": messages,
            "temperature": 0.3,
        }
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}"}
        resp = httpx.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


class OllamaLLM(BaseLLM):
    provider = "ollama"

    def chat(self, messages: list[dict]) -> str:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/chat"
        payload = {"model": self.settings.ollama_model, "messages": messages, "stream": False}
        resp = httpx.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["message"]["content"]


class RuleLLM(BaseLLM):
    """Deterministic 'LLM' — zero deps, zero cost. Used when no API key is set."""

    provider = "rule"

    def chat(self, messages: list[dict]) -> str:
        # Build an answer from evidence embedded in the system message.
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        evidence = _extract_evidence(system)
        if evidence:
            head = "\n\n".join(f"〔證據 {i + 1}〕{e[:400]}" for i, e in enumerate(evidence))
            return (
                f"[rule-engine] 根據檢索到嘅內容，答案如下：\n\n{head}\n\n"
                f"（提示：想攞真正 AI 生成答案，請喺 .env 設定 LLM_PROVIDER + API Key）\n\n"
                f"你嘅問題：{user[:200]}"
            )
        return f"[rule-engine] 冇檢索到相關證據。問題：{user[:200]}"


def _extract_evidence(system: str) -> list[str]:
    """Pull evidence lines we inject into the system prompt."""
    lines = [ln.strip() for ln in system.splitlines()]
    return [ln for ln in lines if ln.startswith("[[EV]]")]


def build_llm(settings: Settings) -> BaseLLM:
    factories = {
        "deepseek": DeepSeekLLM,
        "openai": OpenAILLM,
        "ollama": OllamaLLM,
        "rule": RuleLLM,
    }
    cls = factories.get(settings.llm_provider, RuleLLM)
    return cls(settings)