"""Offline regression tests for the raw-text clear button.

These tests parse app.py instead of importing Streamlit, so they never start the
app, call Gemini, or require credentials.
"""

import ast
from pathlib import Path


APP_PATH = Path(__file__).with_name("app.py")


def _raw_text_area_call(tree: ast.AST) -> ast.Call:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "text_area"):
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant):
            continue
        if node.args[0].value == "在此貼上文稿或摘要 (建議 5,000 字內)：":
            return node
    raise AssertionError("raw text area not found")


def test_raw_text_area_uses_clearable_session_key() -> None:
    source = APP_PATH.read_text(encoding="utf-8")
    call = _raw_text_area_call(ast.parse(source))
    keywords = {keyword.arg: keyword.value for keyword in call.keywords}

    assert "value" not in keywords
    assert isinstance(keywords.get("key"), ast.Constant)
    assert keywords["key"].value == "raw_text_draft"


def test_clear_button_resets_the_bound_widget_key() -> None:
    source = APP_PATH.read_text(encoding="utf-8")
    expected = (
        'if st.button("💡 清空輸入內容", use_container_width=True):\n'
        '            st.session_state.raw_text_draft = ""\n'
        '            st.rerun()'
    )
    assert expected in source
