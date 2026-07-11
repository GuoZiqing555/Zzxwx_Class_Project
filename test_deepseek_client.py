"""Tests for tolerant DeepSeek JSON handling."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from deepseek_client import (
    DeepSeekResponseError,
    DeepSeekSettings,
    call_deepseek_json,
    parse_json_object,
)


def response(content: str, finish_reason: str = "stop") -> SimpleNamespace:
    choice = SimpleNamespace(
        message=SimpleNamespace(content=content),
        finish_reason=finish_reason,
    )
    return SimpleNamespace(choices=[choice])


class ParseJsonObjectTests(unittest.TestCase):
    def test_parses_plain_object(self) -> None:
        self.assertEqual(parse_json_object('{"ok": true}'), {"ok": True})

    def test_parses_markdown_fence(self) -> None:
        self.assertEqual(parse_json_object('```json\n{"ok": true}\n```'), {"ok": True})

    def test_parses_object_surrounded_by_prose(self) -> None:
        self.assertEqual(parse_json_object('结果如下：\n{"ok": true}\n完成'), {"ok": True})

    def test_rejects_array(self) -> None:
        with self.assertRaises(DeepSeekResponseError):
            parse_json_object('[1, 2]')


class CallDeepSeekJsonTests(unittest.TestCase):
    @patch("deepseek_client.OpenAI")
    @patch("deepseek_client.get_settings")
    def test_corrects_invalid_first_response(self, get_settings: Mock, openai: Mock) -> None:
        get_settings.return_value = DeepSeekSettings("test-key")
        create = openai.return_value.chat.completions.create
        create.side_effect = [response('{"broken":'), response('{"ok": true}')]

        result = call_deepseek_json("system", "user")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(create.call_count, 2)
        second_call = create.call_args_list[1].kwargs
        self.assertEqual(second_call["temperature"], 0)
        self.assertEqual(second_call["messages"][-2]["role"], "assistant")

    @patch("deepseek_client.OpenAI")
    @patch("deepseek_client.get_settings")
    def test_corrects_object_missing_required_keys(
        self, get_settings: Mock, openai: Mock
    ) -> None:
        get_settings.return_value = DeepSeekSettings("test-key")
        create = openai.return_value.chat.completions.create
        create.side_effect = [response('{"error": "busy"}'), response('{"brief": "ok"}')]

        result = call_deepseek_json(
            "system", "user", required_keys={"brief"}
        )

        self.assertEqual(result, {"brief": "ok"})
        correction = create.call_args_list[1].kwargs["messages"][-1]["content"]
        self.assertIn("缺少必需的顶层字段：brief", correction)

    @patch("deepseek_client.OpenAI")
    @patch("deepseek_client.get_settings")
    def test_reports_missing_keys_after_final_attempt(
        self, get_settings: Mock, openai: Mock
    ) -> None:
        get_settings.return_value = DeepSeekSettings("test-key")
        openai.return_value.chat.completions.create.return_value = response("{}")

        with self.assertRaisesRegex(DeepSeekResponseError, "缺少必需.*brief"):
            call_deepseek_json(
                "system", "user", max_attempts=1, required_keys={"brief"}
            )

    @patch("deepseek_client.OpenAI")
    @patch("deepseek_client.get_settings")
    def test_reports_truncated_response(self, get_settings: Mock, openai: Mock) -> None:
        get_settings.return_value = DeepSeekSettings("test-key")
        openai.return_value.chat.completions.create.return_value = response(
            '{"broken":', finish_reason="length"
        )

        with self.assertRaisesRegex(DeepSeekResponseError, "被截断"):
            call_deepseek_json("system", "user", max_attempts=1)


if __name__ == "__main__":
    unittest.main()
