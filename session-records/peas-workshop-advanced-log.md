# PEAS Workshop Advanced Log

## 2026-05-27 WG-22

- Created `agent_core.py` from the WG-22 reference core.
- Updated `main.py` to be a CLI wrapper around `Agent.from_env()` and `Agent.chat(...)`.
- Added required WG-19 assets: `prompts/memory_merge.md` and `templates/memory/MEMORY.md`.
- Verified syntax with `.venv\Scripts\python.exe -m py_compile .\agent_core.py .\main.py`.
- Verified imports with `.venv\Scripts\python.exe -c "import agent_core, main; ..."`.
