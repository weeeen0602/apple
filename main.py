import base64
import copy
import json
import os
import platform
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    message_chunk_to_message,
)
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI


WORKSPACE = Path(__file__).resolve().parent
MEMORY_DIR = WORKSPACE / "memory"
MEMORY_PATH = MEMORY_DIR / "MEMORY.md"
MEMORY_HISTORY_PATH = MEMORY_DIR / "HISTORY.md"
MEMORY_MAX_CHARS = int(os.getenv("MEMORY_MAX_CHARS", "6000"))
TOKEN_BUDGET = int(os.getenv("TOKEN_BUDGET", "8000"))
CONSOLIDATION_MAX_RETRIES = int(os.getenv("CONSOLIDATION_MAX_RETRIES", "2"))
COMPACTABLE = {"read_file", "exec", "grep", "glob", "web_search", "web_fetch", "list_dir"}


def configure_stdio() -> None:
    if sys.platform == "win32":
        try:
            sys.stdin.reconfigure(encoding="utf-8")
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _runtime_env_note() -> str:
    system = platform.system()
    shell_note = (
        "exec 在 PowerShell / Windows shell 下執行；勿使用 <<、heredoc、bash -c。"
        if os.name == "nt"
        else "exec 在系統 shell 下執行；多行腳本仍請 write_file 後 uv run。"
    )
    return f"【執行環境】\n- platform.system(): {system}\n- os.name: {os.name}\n- {shell_note}"


def get_identity() -> str:
    system_text = (
        "你是課堂練習用的 Agent。請使用繁體中文回答，保持步驟清楚、可驗收，"
        "需要計算或存取工作區資料時應使用工具，不要假裝已經執行。"
    )
    nick = "法鬥超人"
    exec_note = (
        "【exec 注意】\n"
        "- 請依【執行環境】選擇相容 shell 寫法，勿假設 Linux Bash。\n"
        "- 若要執行 Python：先用 write_file 寫入 .py，再 exec「uv run python 相對路徑」。\n"
        "- 檔案讀寫請優先使用 read_file、write_file、edit_file、list_dir。"
    )
    tool_rule = "【工具規則】\n- 凡涉及兩個整數相加，必須呼叫 add_two，不可只靠心算。"
    return "\n\n".join([system_text, f"【顯示名稱】{nick}", _runtime_env_note(), exec_note, tool_rule])


def resolve_workspace_path(path: str) -> Path:
    raw = Path(path)
    full = raw if raw.is_absolute() else WORKSPACE / raw
    resolved = full.resolve()
    if resolved != WORKSPACE and WORKSPACE not in resolved.parents:
        raise ValueError(f"path escapes workspace: {path}")
    return resolved


@tool
def add_two(a: int, b: int) -> int:
    """凡涉及兩個整數相加必須呼叫此工具，回傳 a + b。"""
    return a + b


@tool("read_file")
def read_file(path: str, offset: int = 1, limit: int = 200) -> str:
    """Read a UTF-8 text file in the workspace with 1-based line numbers."""
    target = resolve_workspace_path(path)
    if not target.is_file():
        return f"[read_file] not a file: {path}"
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(offset, 1) - 1
    end = min(start + max(limit, 1), len(lines))
    return "\n".join(f"{i + 1}: {lines[i]}" for i in range(start, end))


@tool("write_file")
def write_file(path: str, content: str) -> str:
    """Write a UTF-8 text file in the workspace, replacing the whole file."""
    target = resolve_workspace_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"[write_file] wrote {target.relative_to(WORKSPACE)} ({len(content)} chars)"


@tool("edit_file")
def edit_file(path: str, old_text: str, new_text: str, replace_all: bool = False) -> str:
    """Replace text inside a UTF-8 workspace file."""
    target = resolve_workspace_path(path)
    if not target.is_file():
        return f"[edit_file] not a file: {path}"
    text = target.read_text(encoding="utf-8", errors="replace")
    count = text.count(old_text)
    if count == 0:
        return "[edit_file] old_text not found"
    updated = text.replace(old_text, new_text) if replace_all else text.replace(old_text, new_text, 1)
    target.write_text(updated, encoding="utf-8")
    changed = count if replace_all else 1
    return f"[edit_file] replaced {changed} occurrence(s)"


@tool("list_dir")
def list_dir(path: str = ".", recursive: bool = False, max_entries: int = 200) -> str:
    """List files and folders inside the workspace."""
    target = resolve_workspace_path(path)
    if not target.is_dir():
        return f"[list_dir] not a directory: {path}"
    iterator = target.rglob("*") if recursive else target.iterdir()
    rows: list[str] = []
    for index, item in enumerate(iterator):
        if index >= max_entries:
            rows.append("[list_dir] truncated")
            break
        rel = item.relative_to(WORKSPACE)
        rows.append(("/ " if item.is_dir() else "- ") + str(rel))
    return "\n".join(rows) if rows else "[list_dir] empty"


@tool("exec")
def exec_workspace(command: str, timeout: int = 30) -> str:
    """Run a single shell command in the workspace and return exit code plus output."""
    lowered = command.lower()
    dangerous = ["rm -rf", "del /f", "rmdir /s", "format ", "shutdown", "git reset --hard"]
    if any(part in lowered for part in dangerous):
        return "[exec] refused dangerous command"
    if "<<" in command:
        return "[exec] refused heredoc; write a file first, then run it"
    try:
        completed = subprocess.run(
            command,
            cwd=WORKSPACE,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(1, min(timeout, 120)),
        )
    except subprocess.TimeoutExpired:
        return f"[exec] timeout after {timeout}s"
    output = ((completed.stdout or "") + (completed.stderr or "")).strip()
    if len(output) > 4000:
        output = output[:4000] + "\n\n[truncated]"
    return f"exit_code={completed.returncode}\n{output}"


TOOLS: list[BaseTool] = [add_two, read_file, write_file, edit_file, list_dir, exec_workspace]
TOOL_BY_NAME = {t.name: t for t in TOOLS}


def _default_metadata(created_at: str | None = None) -> dict[str, Any]:
    now = datetime.now().isoformat()
    return {
        "_type": "metadata",
        "key": "session",
        "created_at": created_at or now,
        "updated_at": now,
        "metadata": {},
        "last_consolidated": 0,
    }


def user_row_dict(text: str, image_rel: str | None, media_type: str | None) -> dict[str, Any]:
    row: dict[str, Any] = {"role": "user", "content": text, "timestamp": datetime.now().isoformat()}
    if image_rel:
        row["image_path"] = image_rel
        if media_type:
            row["media_type"] = media_type
    return row


def load_user_row_to_history_human(row: dict[str, Any]) -> HumanMessage:
    text = str(row.get("content", ""))
    rel = row.get("image_path")
    if not rel:
        return HumanMessage(content=text)
    media_type = row.get("media_type")
    placeholder = f"[此回合曾附圖，路徑：{rel}]"
    if media_type:
        placeholder += f" (media_type={media_type})"
    return HumanMessage(
        content=f"{text}\n\n{placeholder}",
        additional_kwargs={"image_path": rel, "media_type": media_type, "original_content": text},
    )


def load_session_jsonl(path: str) -> tuple[list[BaseMessage], dict[str, Any] | None]:
    session_file = resolve_workspace_path(path)
    if not session_file.exists():
        return [], None
    messages: list[BaseMessage] = []
    meta: dict[str, Any] | None = None
    with session_file.open(encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            if obj.get("_type") == "metadata":
                meta = obj
                continue
            role = obj.get("role")
            if role == "user":
                messages.append(load_user_row_to_history_human(obj))
            elif role == "assistant":
                tool_calls = obj.get("tool_calls")
                if tool_calls:
                    messages.append(AIMessage(content=str(obj.get("content", "")), tool_calls=tool_calls))
                else:
                    messages.append(AIMessage(content=str(obj.get("content", ""))))
            elif role == "tool":
                messages.append(
                    ToolMessage(
                        content=str(obj.get("content", "")),
                        tool_call_id=str(obj.get("tool_call_id", "")),
                        name=obj.get("name"),
                    )
                )
    return messages, meta


def save_session_jsonl(
    path: str,
    messages: list[BaseMessage],
    existing_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    now = datetime.now().isoformat()
    meta = _default_metadata(now) if existing_meta is None else dict(existing_meta)
    meta["_type"] = "metadata"
    meta["key"] = meta.get("key", "session")
    meta.setdefault("created_at", now)
    meta.setdefault("metadata", {})
    meta.setdefault("last_consolidated", 0)
    meta["updated_at"] = now

    lines = [json.dumps(meta, ensure_ascii=False)]
    for message in messages:
        if isinstance(message, HumanMessage):
            image_rel = message.additional_kwargs.get("image_path")
            media_type = message.additional_kwargs.get("media_type")
            text = message.additional_kwargs.get("original_content")
            if text is None and isinstance(message.content, str):
                text = message.content
            row = user_row_dict(str(text or ""), image_rel, media_type)
        elif isinstance(message, AIMessage):
            row = {"role": "assistant", "content": message.content, "timestamp": datetime.now().isoformat()}
            if getattr(message, "tool_calls", None):
                row["tool_calls"] = message.tool_calls
        elif isinstance(message, ToolMessage):
            row = {
                "role": "tool",
                "content": message.content,
                "tool_call_id": message.tool_call_id,
                "name": getattr(message, "name", None),
                "timestamp": datetime.now().isoformat(),
            }
        else:
            continue
        lines.append(json.dumps(row, ensure_ascii=False))

    session_file = resolve_workspace_path(path)
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return meta


def estimate_message_tokens(message: BaseMessage) -> int:
    content = message.content
    cost = len(content) if isinstance(content, str) else len(json.dumps(content, ensure_ascii=False))
    if isinstance(message, AIMessage) and getattr(message, "tool_calls", None):
        cost += len(json.dumps(message.tool_calls, ensure_ascii=False))
    return cost


def pick_consolidation_boundary(
    messages: list[BaseMessage],
    last_consolidated: int,
    tokens_to_remove: int,
) -> tuple[int, int] | None:
    start = max(last_consolidated, 0)
    if start >= len(messages) or tokens_to_remove <= 0:
        return None
    removed_tokens = 0
    last_boundary: tuple[int, int] | None = None
    for idx in range(start, len(messages)):
        if idx > start and isinstance(messages[idx], HumanMessage):
            last_boundary = (idx, removed_tokens)
            if removed_tokens >= tokens_to_remove:
                return last_boundary
        removed_tokens += estimate_message_tokens(messages[idx])
    return last_boundary


def message_cost(system_str: str, messages: list[BaseMessage]) -> int:
    return len(system_str) + sum(estimate_message_tokens(m) for m in messages)


def memory_block_for_system() -> str:
    if not MEMORY_PATH.exists():
        return ""
    text = MEMORY_PATH.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return ""
    if len(text) > MEMORY_MAX_CHARS:
        text = text[-MEMORY_MAX_CHARS:]
    return f"## Long-term Memory\n\n{text}"


def append_memory_history(entry: str) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    one_line = " ".join(entry.split())
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with MEMORY_HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {one_line}\n")


def messages_to_plaintext(messages: list[BaseMessage]) -> str:
    rows: list[str] = []
    for msg in messages:
        role = msg.type
        content = msg.content if isinstance(msg.content, str) else json.dumps(msg.content, ensure_ascii=False)
        rows.append(f"{role}: {content}")
    return "\n".join(rows)


def parse_consolidation_response(text: str) -> dict[str, str] | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    if not isinstance(data, dict):
        return None
    history_entry = data.get("history_entry")
    memory_update = data.get("memory_update")
    if not isinstance(history_entry, str) or not isinstance(memory_update, str):
        return None
    return {"history_entry": history_entry, "memory_update": memory_update}


def consolidate_memory_if_needed(
    llm: ChatOpenAI,
    history: list[BaseMessage],
    session_meta: dict[str, Any],
    system_str: str,
    human_message: HumanMessage,
) -> dict[str, Any]:
    last = int(session_meta.get("last_consolidated", 0) or 0)
    past = history[last:]
    cost = message_cost(system_str, [*past, human_message])
    if cost <= TOKEN_BUDGET:
        return session_meta
    boundary = pick_consolidation_boundary(history, last, max(0, cost - TOKEN_BUDGET // 2))
    if boundary is None:
        return session_meta
    idx, _removed = boundary
    chunk = history[last:idx]
    if not chunk:
        return session_meta

    existing_memory = MEMORY_PATH.read_text(encoding="utf-8", errors="replace") if MEMORY_PATH.exists() else ""
    prompt = (
        "請把舊對話濃縮成長期記憶。只回傳 JSON 物件，且只能有兩個鍵："
        "history_entry（單行摘要）與 memory_update（完整取代 MEMORY.md 的 Markdown）。\n\n"
        f"現有 MEMORY.md:\n{existing_memory}\n\n待整併舊對話:\n{messages_to_plaintext(chunk)}"
    )
    for _ in range(CONSOLIDATION_MAX_RETRIES):
        response = llm.invoke([SystemMessage(content="你是長期記憶整併器。"), HumanMessage(content=prompt)])
        parsed = parse_consolidation_response(str(response.content))
        if parsed:
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            MEMORY_PATH.write_text(parsed["memory_update"].strip() + "\n", encoding="utf-8")
            append_memory_history(parsed["history_entry"])
            session_meta["last_consolidated"] = idx
            return session_meta
    append_memory_history("[CONSOLIDATION-FAILED] unable to parse model response")
    return session_meta


@dataclass
class SkillEntry:
    name: str
    path: Path
    source: str
    description: str
    always: bool
    body: str


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        return {}, text
    meta: dict[str, str] = {}
    for raw in lines[1:end]:
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, "\n".join(lines[end + 1 :]).strip()


class SkillsLoader:
    def __init__(self, workspace: Path, builtin_skills_dir: Path) -> None:
        self.workspace_skills = workspace / "skills"
        self.builtin_skills = builtin_skills_dir

    def _entries_from_dir(self, root: Path, source: str, skip: set[str]) -> list[SkillEntry]:
        if not root.exists():
            return []
        entries: list[SkillEntry] = []
        for skill_dir in sorted(root.iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if not skill_dir.is_dir() or not skill_file.exists() or skill_dir.name in skip:
                continue
            text = skill_file.read_text(encoding="utf-8", errors="replace")
            meta, body = split_frontmatter(text)
            name = meta.get("name") or skill_dir.name
            description = meta.get("description") or name
            always = meta.get("always", "false").lower() == "true"
            entries.append(SkillEntry(name, skill_file, source, description, always, body))
        return entries

    def list_skills(self) -> list[SkillEntry]:
        workspace_entries = self._entries_from_dir(self.workspace_skills, "workspace", set())
        workspace_names = {entry.name for entry in workspace_entries}
        builtin_entries = self._entries_from_dir(self.builtin_skills, "builtin", workspace_names)
        return workspace_entries + builtin_entries

    def load_skill(self, name: str) -> str | None:
        for root in (self.workspace_skills, self.builtin_skills):
            path = root / name / "SKILL.md"
            if path.exists():
                return path.read_text(encoding="utf-8", errors="replace")
        return None


def build_skills_summary(entries: list[SkillEntry]) -> str:
    summarized = [entry for entry in entries if not entry.always]
    if not summarized:
        return ""
    return "\n".join(f"- **{e.name}**: {e.description} `{e.path}`" for e in summarized)


def build_system_prompt(loader: SkillsLoader) -> str:
    parts: list[str] = [get_identity()]
    memory = memory_block_for_system()
    if memory:
        parts.append(memory)
    entries = loader.list_skills()
    active = [entry for entry in entries if entry.always]
    if active:
        body = "\n\n---\n\n".join(f"### Skill: {entry.name}\n\n{entry.body}" for entry in active)
        parts.append(f"# Active Skills\n\n{body}")
    summary = build_skills_summary(entries)
    if summary:
        intro = (
            "以下是可用技能摘要。需要使用某技能時，請先用 read_file 讀取其 SKILL.md 路徑，"
            "再依內容執行；若技能需要額外依賴，先說明並使用合適工具安裝或驗證。\n\n"
        )
        parts.append("# Skills\n\n" + intro + summary)
    return "\n\n---\n\n".join(parts)


def tool_json_schema(tool_obj: BaseTool) -> dict[str, Any]:
    schema_obj = getattr(tool_obj, "args_schema", None)
    if schema_obj is not None and hasattr(schema_obj, "model_json_schema"):
        return schema_obj.model_json_schema()
    return {"type": "object", "properties": {}, "required": []}


def cast_params(params: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    properties = schema.get("properties", {})
    casted = dict(params)
    for key, spec in properties.items():
        if key not in casted or not isinstance(spec, dict):
            continue
        expected = spec.get("type")
        value = casted[key]
        if expected == "integer" and isinstance(value, str):
            casted[key] = int(value)
        elif expected == "number" and isinstance(value, str):
            casted[key] = float(value)
        elif expected == "boolean" and isinstance(value, str):
            if value.lower() in ("true", "1", "yes", "y"):
                casted[key] = True
            elif value.lower() in ("false", "0", "no", "n"):
                casted[key] = False
    return casted


def validate_params(params: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    properties = schema.get("properties", {})
    for key in schema.get("required", []):
        if key not in params:
            errors.append(f"missing required parameter: {key}")
    type_map = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list, "object": dict}
    for key, value in params.items():
        spec = properties.get(key)
        if not isinstance(spec, dict):
            continue
        expected = spec.get("type")
        py_type = type_map.get(expected)
        if py_type is not None and not isinstance(value, py_type):
            errors.append(f"{key} should be {expected}")
    return errors


def prepare_tool_call(name: str, raw: Any) -> tuple[BaseTool | None, dict[str, Any], str | None]:
    tool_obj = TOOL_BY_NAME.get(name)
    if tool_obj is None:
        return None, {}, f"unknown tool: {name}"
    if isinstance(raw, str):
        try:
            params = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            return tool_obj, {}, "tool arguments must be a JSON object"
    elif isinstance(raw, dict):
        params = dict(raw)
    else:
        return tool_obj, {}, "tool arguments must be a dict or JSON object string"
    schema = tool_json_schema(tool_obj)
    try:
        params = cast_params(params, schema)
    except Exception as exc:
        return tool_obj, params, f"failed to cast tool arguments: {exc}"
    errors = validate_params(params, schema)
    if errors:
        return tool_obj, params, "; ".join(errors)
    return tool_obj, params, None


def image_bytes_to_data_url(data: bytes, media_type: str) -> str:
    return f"data:{media_type};base64,{base64.b64encode(data).decode('ascii')}"


def guess_media_type(path: Path, fallback: str = "image/png") -> str:
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    return fallback


def resolve_image_path(image_rel: str) -> Path:
    target = resolve_workspace_path(image_rel)
    if not target.is_file():
        raise FileNotFoundError(image_rel)
    return target


def build_human_message_for_current_turn(text: str, image_rel: str | None) -> HumanMessage:
    if not image_rel:
        return HumanMessage(content=text)
    try:
        full = resolve_image_path(image_rel)
    except Exception as exc:
        print(f"[warn] missing image for current turn: {image_rel} ({exc})")
        return HumanMessage(content=text)
    media_type = guess_media_type(full)
    url = image_bytes_to_data_url(full.read_bytes(), media_type)
    return HumanMessage(
        content=[
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": url}},
        ],
        additional_kwargs={"image_path": image_rel, "media_type": media_type, "original_content": text},
    )


def _human_to_text_only_placeholder(message: HumanMessage) -> HumanMessage:
    content = message.content
    if isinstance(content, str):
        return message
    text_parts: list[str] = []
    for block in content if isinstance(content, list) else []:
        if isinstance(block, dict) and block.get("type") == "text":
            text_parts.append(str(block.get("text", "")))
    body = "\n".join(part for part in text_parts if part).strip() or "[此回合含非文字內容]"
    rel = message.additional_kwargs.get("image_path")
    media_type = message.additional_kwargs.get("media_type")
    if rel:
        body += f"\n\n[此回合曾附圖，路徑：{rel}]"
        if media_type:
            body += f" (media_type={media_type})"
    return HumanMessage(content=body, additional_kwargs=copy.deepcopy(message.additional_kwargs))


def messages_for_model(
    system_message: BaseMessage,
    history: list[BaseMessage],
    human_message: HumanMessage,
) -> list[BaseMessage]:
    out: list[BaseMessage] = [copy.deepcopy(system_message)]
    for old in history:
        cloned = copy.deepcopy(old)
        if isinstance(cloned, HumanMessage) and not isinstance(cloned.content, str):
            cloned = _human_to_text_only_placeholder(cloned)
        out.append(cloned)
    out.append(copy.deepcopy(human_message))
    return out


def lc_message_to_row(message: BaseMessage) -> dict[str, Any]:
    if isinstance(message, SystemMessage):
        return {"role": "system", "content": str(message.content)}
    if isinstance(message, HumanMessage):
        return {"role": "user", "content": str(message.content)}
    if isinstance(message, AIMessage):
        row = {"role": "assistant", "content": str(message.content)}
        if getattr(message, "tool_calls", None):
            row["tool_calls"] = message.tool_calls
        return row
    if isinstance(message, ToolMessage):
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id,
            "name": getattr(message, "name", None),
            "content": str(message.content),
        }
    return {"role": message.type, "content": str(message.content)}


def build_messages_for_model(
    messages: list[dict[str, Any]],
    *,
    max_chars: int,
    max_tool_chars: int,
    keep_recent_tools: int,
) -> list[dict[str, Any]]:
    out = [dict(m) for m in messages]

    assistant_call_ids: set[str] = set()
    for row in out:
        if row.get("role") == "assistant":
            for call in row.get("tool_calls") or []:
                call_id = call.get("id")
                if call_id:
                    assistant_call_ids.add(call_id)
    out = [row for row in out if row.get("role") != "tool" or row.get("tool_call_id") in assistant_call_ids]

    tool_ids = {row.get("tool_call_id") for row in out if row.get("role") == "tool"}
    repaired: list[dict[str, Any]] = []
    for row in out:
        repaired.append(row)
        if row.get("role") == "assistant":
            for call in row.get("tool_calls") or []:
                call_id = call.get("id")
                if call_id and call_id not in tool_ids:
                    repaired.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": (call.get("name") or call.get("function", {}).get("name")),
                            "content": "[Tool result unavailable - call was interrupted or lost]",
                        }
                    )
    out = repaired

    for row in out:
        if row.get("role") == "tool":
            content = str(row.get("content", ""))
            if len(content) > max_tool_chars:
                row["content"] = content[:max_tool_chars] + "\n\n[truncated]"

    compactable_indexes = [
        i
        for i, row in enumerate(out)
        if row.get("role") == "tool"
        and row.get("name") in COMPACTABLE
        and len(str(row.get("content", ""))) >= 500
    ]
    for index in compactable_indexes[:-keep_recent_tools]:
        name = out[index].get("name") or "tool"
        out[index]["content"] = f"[{name} result omitted from context]"

    def total_cost(rows: list[dict[str, Any]]) -> int:
        return sum(len(str(row.get("content", ""))) for row in rows)

    while total_cost(out) > max_chars:
        user_indexes = [i for i, row in enumerate(out) if row.get("role") == "user"]
        if len(user_indexes) <= 1:
            break
        start = user_indexes[0]
        next_start = user_indexes[1]
        del out[start:next_start]
    return out


def parse_image_command(raw: str) -> tuple[str, str | None]:
    text = raw.strip()
    if not text.startswith("/image "):
        return text, None
    rest = text[len("/image ") :].strip()
    if not rest:
        return "", None
    try:
        parts = shlex.split(rest, posix=os.name != "nt")
    except ValueError:
        parts = rest.split(maxsplit=1)
    if not parts:
        return "", None
    image_rel = parts[0]
    prompt = rest[len(image_rel) :].strip()
    if not prompt:
        prompt = input("請輸入這張圖的問題：").strip()
    return prompt, image_rel


def visible_content(chunk: AIMessageChunk) -> str:
    content = chunk.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    return ""


def run_react_turn(
    llm_tools: Any,
    system_message: SystemMessage,
    past: list[BaseMessage],
    human_message: HumanMessage,
    *,
    stream_stdout: bool = True,
) -> tuple[str, list[BaseMessage]]:
    working = messages_for_model(system_message, past, human_message)
    turn_messages: list[BaseMessage] = [human_message]

    while True:
        acc: AIMessageChunk | None = None
        for chunk in llm_tools.stream(working):
            acc = chunk if acc is None else acc + chunk
            text = visible_content(chunk)
            if stream_stdout and text:
                print(text, end="", flush=True)
        if acc is None:
            raise RuntimeError("model returned no chunks")
        response = message_chunk_to_message(acc)

        if getattr(response, "tool_calls", None):
            if stream_stdout:
                print()
            working.append(response)
            turn_messages.append(response)
            for call in response.tool_calls:
                name = call.get("name", "")
                raw_args = call.get("args") or {}
                tool_obj, params, error = prepare_tool_call(name, raw_args)
                if error or tool_obj is None:
                    result = f"[tool error] {error}"
                else:
                    try:
                        result = tool_obj.invoke(params)
                    except Exception as exc:
                        result = f"[tool exception] {exc}"
                tool_message = ToolMessage(content=str(result), tool_call_id=call.get("id", ""), name=name)
                working.append(tool_message)
                turn_messages.append(tool_message)
            continue

        working.append(response)
        turn_messages.append(response)
        final = response.content if isinstance(response.content, str) else json.dumps(response.content, ensure_ascii=False)
        return final.strip(), turn_messages


def select_past_for_turn(
    history: list[BaseMessage],
    session_meta: dict[str, Any],
    system_str: str,
    human_message: HumanMessage,
) -> list[BaseMessage]:
    last = int(session_meta.get("last_consolidated", 0) or 0)
    past0 = history[last:]
    cost = message_cost(system_str, [*past0, human_message])
    if cost <= TOKEN_BUDGET:
        return past0
    boundary = pick_consolidation_boundary(history, last, max(0, cost - TOKEN_BUDGET // 2))
    return history[boundary[0] :] if boundary else past0


def main() -> None:
    configure_stdio()
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("找不到 OPENAI_API_KEY，請先在 .env 設定後再執行。")
        return

    session_path = os.getenv("SESSION_JSONL_PATH", "session.jsonl")
    model = os.getenv("MODEL_NAME", "gpt-4o-mini")
    base_url = os.getenv("BASE_URL") or None
    loader = SkillsLoader(WORKSPACE, WORKSPACE / "builtin_skills")
    history, session_meta = load_session_jsonl(session_path)
    session_meta = session_meta or _default_metadata()

    llm = ChatOpenAI(model=model, base_url=base_url, api_key=api_key, temperature=0.2)
    llm_tools = llm.bind_tools(TOOLS)

    print("已載入 Agent（WG-12~WG-21 合併版）。輸入 quit / exit / q 結束；可用 /image 相對路徑 問題 附圖。")
    while True:
        raw = input("你：").strip()
        if raw.lower() in ("quit", "exit", "q", "break"):
            print("再見。")
            break
        if not raw:
            continue

        user_text, image_rel = parse_image_command(raw)
        if not user_text:
            continue
        human_message = build_human_message_for_current_turn(user_text, image_rel)

        system_str = build_system_prompt(loader)
        session_meta = consolidate_memory_if_needed(llm, history, session_meta, system_str, human_message)
        system_str = build_system_prompt(loader)
        system_message = SystemMessage(content=system_str)
        past = select_past_for_turn(history, session_meta, system_str, human_message)

        print("AI：", end="", flush=True)
        _reply, turn_messages = run_react_turn(llm_tools, system_message, past, human_message)
        print()

        history.extend(turn_messages)
        session_meta = save_session_jsonl(session_path, history, session_meta)


if __name__ == "__main__":
    main()
