import unittest
import re
import sys
import os

# Import functions from app.py
sys.path.insert(0, os.path.dirname(__file__))
from app import sanitize_api_key, is_page_number_marker, render_wireframe, generate_ai_presentation_with_fallback

class TestInfoVisMasterDD(unittest.TestCase):
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
        success, diag_msg, used_model, fell_back = generate_ai_presentation_with_fallback(
            api_key="AIzaSy_fake_test_key_for_dd_verification",
            system_prompt="Test",
            user_content="Test",
            selected_model="gemini-2.5-flash"
        )
        self.assertFalse(success)
        self.assertIn("❌", diag_msg)
        self.assertIn("API_KEY_INVALID", diag_msg)

if __name__ == "__main__":
    unittest.main()
