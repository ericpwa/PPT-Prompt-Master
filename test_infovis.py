import unittest
import re
import sys
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Exercise the actual UI declarations without Streamlit or network dependencies.
class SessionState(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

ui = MagicMock()
ui.session_state = SessionState()
ui.text_input.return_value = "offline-test-key"
ui.text_area.return_value = ""
ui.button.return_value = False
ui.selectbox.side_effect = lambda label, options, index=0, **kwargs: options[index]
ui.number_input.side_effect = lambda label, minimum, maximum, value: value
ui.columns.side_effect = lambda spec: [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
ui.tabs.side_effect = lambda labels: [MagicMock() for _ in labels]

sys.path.insert(0, os.path.dirname(__file__))
with patch.dict(sys.modules, {"streamlit": ui}):
    import app
    from app import sanitize_api_key, is_page_number_marker, render_wireframe, generate_ai_presentation_with_fallback


class APIError(Exception):
    """Offline SDK-shaped error with a numeric HTTP code."""
    def __init__(self, code, message="mock API error"):
        super().__init__(message)
        self.code = code


class OfflineAPITest(unittest.TestCase):
    def setUp(self):
        # Fail closed if a future test accidentally tries to open a live socket.
        self.start_patch(patch("socket.socket.connect", side_effect=AssertionError("Live API calls forbidden")))
        self.client = MagicMock()
        self.client.models.generate_content.return_value = SimpleNamespace(text="mock presentation")
        self.sdk = SimpleNamespace(Client=MagicMock(return_value=self.client))
        self.start_patch(patch.object(app, "GENAI_SDK_AVAILABLE", True))
        self.start_patch(patch.object(app, "genai", self.sdk, create=True))

    def start_patch(self, patcher):
        self.addCleanup(patcher.stop)
        return patcher.start()

    def generate(self, model=app.DEFAULT_MODEL, api_key="offline-test-key"):
        return generate_ai_presentation_with_fallback(api_key, "system", "content", model)

    def called_models(self):
        return [call.kwargs["model"] for call in self.client.models.generate_content.call_args_list]

class TestInfoVisMasterDD(OfflineAPITest):
    def test_api_key_sanitization(self):
        """Test BYOK sanitization of spaces, quotes, and backticks"""
        raw_keys = [
            "  AIzaSyTest123  ",
            "'AIzaSyTest123'",
            '"AIzaSyTest123"',
            "`AIzaSyTest123`",
            " \n `AIzaSyTest123` \t \n "
        ]
        for rk in raw_keys:
            self.assertEqual(sanitize_api_key(rk), "AIzaSyTest123")
        self.assertEqual(sanitize_api_key(""), "")
        self.assertEqual(sanitize_api_key(None), "")

    def test_page_number_marker_regex(self):
        """Ensure page markers are detected and legitimate content containing '第' or '頁' is NOT stripped"""
        markers = ["第 1 頁", "第10頁", "Slide 1", "slide 25", "Page 3", "page 4", "1/10", "  第 2 頁  "]
        for m in markers:
            self.assertTrue(is_page_number_marker(m), f"Failed to identify marker: {m}")

        legitimate_lines = [
            "第一階段數位轉型成效總覽",
            "第三季營業額突破五千萬元",
            "首頁設計風格與視覺規範",
            "本頁核心觀點：降低認知負荷",
            "市場痛點與頁面轉換率分析"
        ]
        for l in legitimate_lines:
            self.assertFalse(is_page_number_marker(l), f"False positive on legitimate line: {l}")

    def test_wireframe_rendering(self):
        """Ensure wireframe HTML renders without crash for all IP positions"""
        positions = ["右側 (Right)", "左側 (Left)", "置中 (Center)", "底部 (Bottom)", "無"]
        for pos in positions:
            html = render_wireframe("測試標題", "測試內文", pos)
            self.assertIn("wireframe-slide", html)
            self.assertIn("測試標題", html)
            self.assertIn("測試內文", html)

    def test_fallback_diagnosis(self):
        """Ensure invalid key returns clear diagnostic message instead of misleading model switch"""
        self.client.models.generate_content.side_effect = APIError(400, "API_KEY_INVALID: API key not valid")
        success, diag_msg, used_model, fell_back = generate_ai_presentation_with_fallback(
            api_key="AIzaSy_fake_test_key_for_dd_verification",
            system_prompt="Test",
            user_content="Test",
            selected_model="gemini-2.5-flash"
        )
        self.assertFalse(success)
        self.assertIn("❌", diag_msg)
        self.assertIn("API_KEY_INVALID", diag_msg)
        self.assertEqual(self.called_models(), ["gemini-2.5-flash"])
        self.assertIsNone(used_model)
        self.assertFalse(fell_back)


class TestSupportedModelRouting(OfflineAPITest):
    def test_selected_models_succeed_without_fallback(self):
        for model in app.SUPPORTED_MODELS:
            with self.subTest(model=model):
                self.client.models.generate_content.reset_mock()
                self.assertEqual(self.generate(model), (True, "mock presentation", model, False))
                self.assertEqual(self.called_models(), [model])

    def test_fallback_order_and_deduplication(self):
        expected_chains = {
            "gemini-3.8-flash": ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"],
            "gemini-3.5-flash-lite": ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.5-flash"],
            "gemini-2.5-flash": ["gemini-2.5-flash", "gemini-3.8-flash", "gemini-3.5-flash-lite"],
        }
        for selected, expected in expected_chains.items():
            with self.subTest(selected=selected):
                self.client.models.generate_content.reset_mock()
                self.client.models.generate_content.side_effect = APIError(404)
                success, diagnosis, used_model, fell_back = self.generate(selected)
                self.assertEqual(self.called_models(), expected)
                self.assertFalse(success)
                self.assertIn("404", diagnosis)
                self.assertIsNone(used_model)
                self.assertFalse(fell_back)

    def test_404_fallback_succeeds_for_new_and_legacy_projects(self):
        for selected, fallback in (("gemini-3.8-flash", "gemini-3.5-flash-lite"),
                                   ("gemini-2.5-flash", "gemini-3.8-flash")):
            with self.subTest(selected=selected):
                self.client.models.generate_content.reset_mock()
                self.client.models.generate_content.side_effect = [APIError(404), SimpleNamespace(text="ok")]
                self.assertEqual(self.generate(selected), (True, "ok", fallback, True))
                self.assertEqual(self.called_models(), [selected, fallback])

    def test_legacy_key_can_reach_25_after_3x_404s(self):
        self.client.models.generate_content.side_effect = [APIError(404), APIError(404), SimpleNamespace(text="ok")]
        self.assertEqual(self.generate(), (True, "ok", "gemini-2.5-flash", True))
        self.assertEqual(self.called_models(), ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"])

    def test_quota_auth_and_permission_errors_stop(self):
        for code, diagnostic in ((429, "429"), (403, "403"), (401, "401"), (400, "呼叫失敗"), (402, "呼叫失敗")):
            with self.subTest(code=code):
                self.client.models.generate_content.reset_mock()
                self.client.models.generate_content.side_effect = APIError(code)
                success, diagnosis, used_model, fell_back = self.generate()
                self.assertFalse(success)
                self.assertIn(diagnostic, diagnosis)
                self.assertEqual(self.called_models(), [app.DEFAULT_MODEL])
                self.assertIsNone(used_model)
                self.assertFalse(fell_back)
                if code == 429:
                    self.assertNotIn("免費", diagnosis)
                    self.assertNotIn("1 分鐘", diagnosis)

    def test_stop_errors_after_404_do_not_try_remaining_models(self):
        for code in (429, 403, 401):
            with self.subTest(code=code):
                self.client.models.generate_content.reset_mock()
                self.client.models.generate_content.side_effect = [APIError(404), APIError(code)]
                success, diagnosis, used_model, fell_back = self.generate("gemini-2.5-flash")
                self.assertFalse(success)
                self.assertIn(str(code), diagnosis)
                self.assertEqual(self.called_models(), ["gemini-2.5-flash", "gemini-3.8-flash"])
                self.assertIsNone(used_model)
                self.assertFalse(fell_back)

    def test_untyped_errors_use_status_markers(self):
        for message, expected_code in (("404 model not available", 404), ("NOT_FOUND", 404),
                                       ("no longer available", 404), ("RESOURCE_EXHAUSTED", 429),
                                       ("PERMISSION_DENIED", 403), ("Forbidden", 403),
                                       ("UNAUTHENTICATED", 401), ("API_KEY_INVALID", 401)):
            with self.subTest(message=message):
                self.client.models.generate_content.reset_mock()
                error = RuntimeError(message)
                self.assertEqual(app.get_api_error_code(error), expected_code)
                self.client.models.generate_content.side_effect = [error, SimpleNamespace(text="ok")]
                success, diagnosis, used_model, fell_back = self.generate()
                self.assertEqual(success, expected_code == 404)
                self.assertEqual(len(self.called_models()), 2 if expected_code == 404 else 1)

    def test_structured_code_takes_precedence_over_message_numbers(self):
        error = APIError(403, "Permission denied for resource 404")
        self.assertEqual(app.get_api_error_code(error), 403)
        self.client.models.generate_content.side_effect = error
        self.assertFalse(self.generate()[0])
        self.assertEqual(self.called_models(), [app.DEFAULT_MODEL])
        self.assertEqual(app.get_api_error_code(APIError("404")), 404)

    def test_unknown_errors_stop_without_fallback(self):
        self.client.models.generate_content.side_effect = RuntimeError("unexpected payload error")
        self.assertFalse(self.generate()[0])
        self.assertEqual(self.called_models(), [app.DEFAULT_MODEL])

    def test_unsupported_models_never_reach_sdk(self):
        for model in ("gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "unknown", "", None):
            with self.subTest(model=model):
                success, diagnosis, used_model, fell_back = self.generate(model)
                self.assertFalse(success)
                self.assertIn("不支援", diagnosis)
                self.assertIsNone(used_model)
                self.assertFalse(fell_back)
        self.sdk.Client.assert_not_called()

    def test_ui_options_and_default_match_routing_registry(self):
        model_menu = [call for call in ui.selectbox.call_args_list if call.args[0].startswith("AI 引擎選擇")]
        self.assertEqual(len(model_menu), 1)
        menu = model_menu[0]
        self.assertEqual(menu.args[1], ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"])
        self.assertEqual(menu.args[1], list(app.SUPPORTED_MODELS))
        self.assertEqual(menu.args[1][menu.kwargs["index"]], app.DEFAULT_MODEL)
        self.assertEqual(app.selected_model_engine, app.DEFAULT_MODEL)
        self.assertIn("新專案", menu.kwargs["format_func"](app.DEFAULT_MODEL))
        self.assertIn("已有 2.5 存取權限", menu.kwargs["format_func"]("gemini-2.5-flash"))
        self.sdk.Client.assert_not_called()

    def test_empty_key_and_missing_sdk_never_construct_client(self):
        self.assertFalse(self.generate(api_key="")[0])
        with patch.object(app, "GENAI_SDK_AVAILABLE", False):
            self.assertIn("google-genai", self.generate()[1])
        self.sdk.Client.assert_not_called()

    def test_sanitized_key_and_prompt_are_preserved(self):
        self.generate(api_key=" `offline-test-key` ")
        self.sdk.Client.assert_called_once_with(api_key="offline-test-key")
        self.client.models.generate_content.assert_called_once_with(
            model=app.DEFAULT_MODEL, contents="system\n\n=== 原始資料文稿 ===\ncontent")

if __name__ == "__main__":
    unittest.main()
