"""Thin Groq (OpenAI-compatible) client with JSON helper. Fails soft: callers decide the fallback."""
import json
import re
import httpx
from . import config


class LLMError(Exception):
    pass


def chat(messages, model, tools=None, temperature=0.2, timeout=20.0, max_tokens=1200):
    if config.MOCK_LLM:
        raise LLMError("mock mode")
    body = {"model": model, "messages": messages, "temperature": temperature,
            "max_tokens": max_tokens, "reasoning_effort": "low"}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    try:
        r = httpx.post(config.GROQ_URL, json=body, timeout=timeout,
                       headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"})
    except httpx.HTTPError as e:
        raise LLMError(str(e)) from e
    if r.status_code != 200:
        raise LLMError(f"{r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]


def parse_json(text):
    """Extract the first JSON object/array from model text."""
    if not text:
        raise LLMError("empty")
    m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
    if not m:
        raise LLMError("no json")
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError as e:
        raise LLMError("bad json") from e


def chat_json(messages, model, **kw):
    msg = chat(messages, model, **kw)
    return parse_json(msg.get("content") or "")
