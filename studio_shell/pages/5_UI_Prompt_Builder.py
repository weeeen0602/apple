from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from studio_shell.page_shell import page_shell
from studio_shell.shell_ui import inject_style


st.set_page_config(page_title="UI Prompt Builder", page_icon="🧩", layout="wide")
inject_style()


WIDGET_OPTIONS = {
    "文字輸入（一行）": "st.text_input",
    "文字輸入（多行）": "st.text_area",
    "數字輸入": "st.number_input",
    "下拉單選": "st.selectbox",
    "單選按鈕": "st.radio",
    "多選清單": "st.multiselect",
    "勾選框": "st.checkbox",
    "滑桿": "st.slider",
    "日期": "st.date_input",
    "時間": "st.time_input",
    "上傳檔案": "st.file_uploader",
    "按鈕": "st.button",
}


PROMPT_TEMPLATES = {
    "st.text_input": "請新增一個 `st.text_input`，讓使用者輸入{name}。",
    "st.text_area": "請新增一個 `st.text_area`，讓使用者輸入{name}。",
    "st.number_input": "請新增一個 `st.number_input`，讓使用者輸入{name}。",
    "st.selectbox": "請新增一個 `st.selectbox`，讓使用者從選項中選擇{name}。",
    "st.radio": "請新增一個 `st.radio`，讓使用者單選{name}。",
    "st.multiselect": "請新增一個 `st.multiselect`，讓使用者多選{name}。",
    "st.checkbox": "請新增一個 `st.checkbox`，讓使用者勾選{name}。",
    "st.slider": "請新增一個 `st.slider`，讓使用者調整{name}。",
    "st.date_input": "請新增一個 `st.date_input`，讓使用者選擇{name}。",
    "st.time_input": "請新增一個 `st.time_input`，讓使用者選擇{name}。",
    "st.file_uploader": "請新增一個 `st.file_uploader`，讓使用者上傳{name}。",
    "st.button": "請新增一個 `st.button`，按下後執行{name}。",
}


def build_prompt(widget_name: str, field_name: str, options_text: str, need_extra: bool) -> str:
    template = PROMPT_TEMPLATES[widget_name]
    prompt = template.format(name=field_name or "資料")

    if widget_name in {"st.selectbox", "st.radio", "st.multiselect"} and options_text.strip():
        prompt += f" 選項包含：{options_text.strip()}。"

    if need_extra:
        prompt += " 請把這個欄位的值整理進 Extra Context。"

    prompt += " 請不要修改 `studio_shell/agent_panel.py` 或 `studio_shell/page_shell.py`。"
    return prompt


def render_main() -> str:
    st.markdown("#### UI Prompt Builder")
    st.info("選擇你要的 UI 元件，系統會幫你組一段可直接貼給 Agent 的 Prompt。")

    left, right = st.columns([1, 1])

    with left:
        field_name = st.text_input("你想收集什麼資料？", placeholder="例如：姓名、主餐、是否同意")
        selected_label = st.selectbox("想用哪種元件？", list(WIDGET_OPTIONS.keys()))
        widget_name = WIDGET_OPTIONS[selected_label]
        options_text = st.text_area(
            "如果是選單／多選，請填選項（用頓號或逗號分隔）",
            placeholder="例如：牛肉麵、雞腿飯、滷肉飯",
            height=80,
        )
        need_extra = st.checkbox("要把結果放進 Extra Context", value=True)

    prompt = build_prompt(widget_name, field_name, options_text, need_extra)

    with right:
        st.markdown("#### 建議元件")
        st.success(widget_name)
        st.markdown("#### 可直接貼給 Agent 的 Prompt")
        st.code(prompt, language="text")

    st.divider()
    st.markdown("#### 常見快速選擇")
    quick1, quick2, quick3 = st.columns(3)
    quick1.info("清單單選 → `st.selectbox`")
    quick2.info("清單多選 → `st.multiselect`")
    quick3.info("勾選是／否 → `st.checkbox`")

    return "【目前頁面】UI Prompt Builder\n【任務】協助學生選擇適合的 Streamlit UI 元件，並把元件名稱寫進 Prompt。"


page_shell(
    "UI Prompt Builder",
    "用表單選出想要的元件，快速產生可以貼給 Agent 的 Prompt。",
    render_main,
    page_name="UI Prompt Builder",
)
