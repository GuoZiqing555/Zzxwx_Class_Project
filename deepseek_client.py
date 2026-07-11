"""DeepSeek API wrapper for the Streamlit demo."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from collections.abc import Collection
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from quota import reserve_api_call


load_dotenv()


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"


class DeepSeekConfigError(RuntimeError):
    """Raised when local API configuration is missing."""


class DeepSeekResponseError(RuntimeError):
    """Raised when the model response cannot be parsed."""


@dataclass(frozen=True)
class DeepSeekSettings:
    api_key: str
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL


def get_settings() -> DeepSeekSettings:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key or api_key in {"your_key_here", "replace_with_a_new_rotated_key"}:
        raise DeepSeekConfigError("请先在 .env 文件中填写 DEEPSEEK_API_KEY。")

    model = os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    base_url = os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    return DeepSeekSettings(api_key=api_key, model=model, base_url=base_url)


def parse_json_object(content: str) -> dict[str, Any]:
    """Parse a JSON object, tolerating code fences and surrounding prose."""
    text = content.lstrip("\ufeff").strip()
    candidates = [text]
    candidates.extend(
        match.strip()
        for match in re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    )

    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

        # raw_decode accepts a valid object followed by harmless explanatory text.
        for start, char in enumerate(candidate):
            if char != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(candidate, start)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

    raise DeepSeekResponseError("模型返回内容中没有可解析的 JSON 对象。")


def call_deepseek_json(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.35,
    max_tokens: int = 3000,
    max_attempts: int = 2,
    required_keys: Collection[str] = (),
) -> dict[str, Any]:
    """Call DeepSeek and return a valid JSON object with required top-level keys."""
    if max_attempts < 1:
        raise ValueError("max_attempts 必须大于等于 1。")

    settings = get_settings()
    # Disable SDK retries so every network request is explicitly reserved by
    # this module and the daily cap remains a hard upper bound.
    client = OpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
        max_retries=0,
        timeout=45.0,
    )
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    last_content = ""
    last_finish_reason: str | None = None
    last_error = ""
    required_key_set = set(required_keys)

    for attempt in range(max_attempts):
        # Reserve each provider request, including repair attempts. This is the
        # only point where an upstream API call can be made. It is deliberately
        # outside the API-error wrapper so callers can show the quota message.
        reserve_api_call()
        try:
            response = client.chat.completions.create(
                model=settings.model,
                messages=messages,
                temperature=temperature if attempt == 0 else 0,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # pragma: no cover - exact SDK exceptions vary.
            raise RuntimeError(f"DeepSeek API 调用失败：{exc}") from exc

        choice = response.choices[0]
        last_content = choice.message.content or ""
        last_finish_reason = getattr(choice, "finish_reason", None)
        try:
            parsed = parse_json_object(last_content)
            missing_keys = sorted(required_key_set - parsed.keys())
            if not missing_keys:
                return parsed
            last_error = f"缺少必需的顶层字段：{', '.join(missing_keys)}"
        except DeepSeekResponseError as exc:
            last_error = str(exc)

        if last_error:
            if attempt + 1 >= max_attempts:
                break

        messages.extend(
            [
                {"role": "assistant", "content": last_content},
                {
                    "role": "user",
                    "content": (
                        f"上一次输出不符合要求（{last_error}）。"
                        "请根据最初要求重新输出完整、合法的 JSON 对象；"
                        "不要使用 Markdown 代码块，不要添加任何解释文字，并确保所有字符串正确转义。"
                    ),
                },
            ]
        )

    if last_finish_reason == "length":
        raise DeepSeekResponseError(
            f"模型输出因达到 max_tokens={max_tokens} 被截断，无法解析 JSON；请提高 max_tokens。"
        )
    detail = f"最后一次问题：{last_error}" if last_error else ""
    raise DeepSeekResponseError(
        f"模型连续 {max_attempts} 次未返回可用的 JSON 对象。{detail}"
    )
