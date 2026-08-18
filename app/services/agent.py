"""Agent loop: system prompt + tool calling + RAG evidence grounding."""

from __future__ import annotations

from datetime import datetime, timezone

from app.config import Settings
from app.services.llm import BaseLLM
from app.services.storage import DocumentStore

MAX_ITERATIONS = 3


def _render_evidence(rows: list[tuple[int, str, float]]) -> str:
    if not rows:
        return "（無相關資料）"
    # Collapse newlines so each [[EV]] block stays on one line for the rule engine.
    blocks = [content.replace("\n", " ").strip() for _, content, _ in rows]
    return "\n\n".join(f"[[EV]] {b}" for b in blocks)


def run_agent(
    llm: BaseLLM,
    store: DocumentStore,
    question: str,
    namespace: str,
    settings: Settings,
    use_tools: bool = True,
) -> tuple[str, list[tuple[int, str, float]], dict]:
    """Simple ReAct-ish loop: retrieve evidence -> ask LLM -> answer.

    Returns (answer, evidence_rows, trace_metadata).
    """
    evidence = store.search(question, namespace)

    system_prompt = (
        "你係一個企業級知識庫 AI 助手。回答必須基於以下「檢索證據」，唔可以作嘢；"
        "證據唔夠就要話「資料唔夠」。講嘢用繁體中文，簡潔準確。\n\n"
        "--- 檢索證據 ---\n"
        f"{_render_evidence(evidence)}"
    )

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    trace: dict = {"iterations": 0, "tools_used": []}

    if use_tools:
        messages, trace = _tool_round(messages, llm, trace)

    answer = llm.chat(messages)
    trace["iterations"] += 1
    trace["evidence_count"] = len(evidence)
    return answer, evidence, trace


def _tool_round(
    messages: list[dict], llm: BaseLLM, trace: dict
) -> tuple[list[dict], dict]:
    """Allow the LLM one tool pass (time/date) before final answer."""

    def tool_call(expr: str) -> str:
        if "date" in expr.lower() or "今日" in expr or "時間" in expr:
            trace["tools_used"].append("now")
            return datetime.now(timezone.utc).isoformat()
        if "time" in expr.lower():
            trace["tools_used"].append("now")
            return datetime.now(timezone.utc).isoformat()
        trace["tools_used"].append("unknown")
        return "唔識處理呢個工具"

    # Simple convention: if the question asks about time/date, append tool result.
    last_user = next(m["content"] for m in reversed(messages) if m["role"] == "user")
    if any(k in last_user.lower() for k in ("幾點", "時間", "今日", "date", "time")):
        messages.append(
            {
                "role": "user",
                "content": f"（工具結果：而家時間係 {tool_call('now')}）",
            }
        )
    return messages, trace