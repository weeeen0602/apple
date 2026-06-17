from pathlib import Path

app_path = Path("studio_shell/app.py")
text = app_path.read_text(encoding="utf-8")
old = '''pages = {
    "Studio": [
        st.Page(overview, title="總覽", default=True),
        st.Page(str(SHELL_ROOT / "pages" / "1_Home.py"), title="Home"),
        st.Page(str(SHELL_ROOT / "pages" / "2_Playground.py"), title="Playground"),
        st.Page(str(SHELL_ROOT / "pages" / "3_UI_Cheatsheet.py"), title="UI 元件詞彙表"),
        st.Page(str(SHELL_ROOT / "pages" / "6_UI_List_Helper.py"), title="清單元件助手"),
    ],
}
'''
new = '''pages = {
    "Studio": [
        st.Page(overview, title="總覽", default=True),
        st.Page(str(SHELL_ROOT / "pages" / "1_Home.py"), title="Home"),
        st.Page(str(SHELL_ROOT / "pages" / "2_Playground.py"), title="Playground"),
        st.Page(str(SHELL_ROOT / "pages" / "3_UI_Cheatsheet.py"), title="UI 元件詞彙表"),
        st.Page(str(SHELL_ROOT / "pages" / "6_UI_List_Helper.py"), title="清單元件助手"),
        st.Page(str(SHELL_ROOT / "pages" / "7_我還沒想好.py"), title="我還沒想好"),
    ],
}
'''
if old not in text:
    raise SystemExit("target block not found")
app_path.write_text(text.replace(old, new), encoding="utf-8")
print("updated app.py")
