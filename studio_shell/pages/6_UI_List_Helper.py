from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from studio_shell.page_shell import page_shell
from studio_shell.shell_ui import inject_style


st.set_page_config(page_title="點餐介面範例", page_icon="🍽️", layout="wide")
inject_style()


def render_main() -> str:
    st.markdown("#### 點餐介面範例")
    st.info("使用三個 `st.selectbox` 製作簡單點餐介面，讓使用者選擇飲料、主菜與甜點，並查看目前點餐結果。")

    menu_col1, menu_col2, menu_col3 = st.columns(3)
    with menu_col1:
        drink = st.selectbox("飲料", ["紅茶", "綠茶", "奶茶", "可樂"], key="order_drink")
    with menu_col2:
        main_course = st.selectbox("主菜", ["牛肉麵", "雞腿飯", "咖哩飯", "鍋燒意麵"], key="order_main")
    with menu_col3:
        dessert = st.selectbox("甜點", ["布丁", "冰淇淋", "蛋糕", "仙草凍"], key="order_dessert")

    st.markdown("#### 目前點餐結果")
    order_summary = {
        "飲料": drink,
        "主菜": main_course,
        "甜點": dessert,
    }
    st.json(order_summary)

    submitted = st.button("送出訂單", type="primary")
    if submitted:
        st.success("訂單已送出")
        st.markdown("#### 訂單總結")
        st.write(f"你點了：飲料是 {drink}、主菜是 {main_course}、甜點是 {dessert}。")

    st.divider()
    st.markdown("#### 可直接貼給 Agent 的 Prompt")
    st.code(
        "請做一個點餐介面，使用三個 `st.selectbox`：\n"
        "- 飲料：紅茶、綠茶、奶茶、可樂\n"
        "- 主菜：牛肉麵、雞腿飯、咖哩飯、鍋燒意麵\n"
        "- 甜點：布丁、冰淇淋、蛋糕、仙草凍\n\n"
        "讓使用者在每個欄位各選一項，並在下方用 `st.write` 或 `st.json` 顯示目前點餐結果。\n"
        "再加入一個 `st.button` 當作送出訂單按鈕，按下後顯示訂單總結。\n"
        "請不要修改 `studio_shell/agent_panel.py` 或 `studio_shell/page_shell.py`。",
        language="text",
    )

    return (
        "【目前頁面】點餐介面範例\n"
        "【任務】示範使用三個 Streamlit `st.selectbox` 製作點餐介面。\n"
        f"【點餐結果】飲料：{drink}；主菜：{main_course}；甜點：{dessert}"
    )


page_shell(
    "點餐介面範例",
    "保留點餐 selectbox 範例，提供使用者選擇與送出訂單。",
    render_main,
    page_name="點餐介面範例",
)
