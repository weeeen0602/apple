from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

import agent_core
from agent_core import Agent, get_token_budget


ORIGINAL_MEMORY_BLOCK_FOR_SYSTEM = agent_core.memory_block_for_system


def configure_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def load_environment() -> None:
    load_dotenv()

    if not os.getenv("OPENAI_MODEL") and os.getenv("MODEL_NAME"):
        os.environ["OPENAI_MODEL"] = os.environ["MODEL_NAME"]
    if not os.getenv("OPENAI_BASE_URL") and os.getenv("BASE_URL"):
        os.environ["OPENAI_BASE_URL"] = os.environ["BASE_URL"]


def new_session_path() -> str:
    session_dir = Path("session-records")
    session_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return str(session_dir / f"session-{stamp}.jsonl")


def set_memory_enabled(enabled: bool) -> None:
    if enabled:
        agent_core.memory_block_for_system = ORIGINAL_MEMORY_BLOCK_FOR_SYSTEM
    else:
        agent_core.memory_block_for_system = lambda: ""


def main() -> None:
    configure_stdio()
    load_environment()

    try:
        agent = Agent.from_env()
    except RuntimeError as e:
        print(e)
        return

    print("Agent CLI ready. Type quit, exit, or q to leave.")
    print("Images: use `/image relative/path.png` then type your prompt,")
    print("or use `/image relative/path.png your prompt` on one line.")
    print("Commands: `/new` starts a clean conversation; `/memory on|off` toggles long-term memory.")

    if agent.history:
        print(
            f"Loaded {len(agent.history)} messages from {agent.session_path!r}; "
            f"last_consolidated={agent.last_consolidated}."
        )
    else:
        print("Starting a new session.")

    print(
        f"TOKEN_BUDGET={get_token_budget()} "
        f"(memory consolidation target={get_token_budget() // 2})."
    )

    pending_image: str | None = None

    while True:
        try:
            user_line = input("\nYou: ").strip()
        except EOFError:
            print("\nBye.")
            break
        if user_line.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break
        if not user_line:
            continue
        if user_line == "/new":
            set_memory_enabled(False)
            try:
                agent = Agent.from_env(session_path=new_session_path())
            except RuntimeError as e:
                print(e)
                continue
            pending_image = None
            print(f"Started a clean session without long-term memory: {agent.session_path}")
            continue
        if user_line in ("/memory on", "/memory off"):
            enabled = user_line.endswith("on")
            set_memory_enabled(enabled)
            state = "enabled" if enabled else "disabled"
            print(f"Long-term memory {state}.")
            continue

        image_rel: str | None = None
        user_text = user_line

        if user_line.startswith("/image "):
            rest = user_line[len("/image ") :].strip()
            if not rest:
                print("Usage: /image relative/path.png [prompt]")
                continue

            parts = rest.split(maxsplit=1)
            image_rel = parts[0]
            if len(parts) > 1:
                user_text = parts[1].strip()
            else:
                pending_image = image_rel
                print(f"Selected image {image_rel!r}. Now type your prompt.")
                continue
        elif pending_image is not None:
            image_rel = pending_image
            pending_image = None
            user_text = user_line

        if not user_text and not image_rel:
            continue

        print("\nAssistant: ", end="", flush=True)
        try:
            agent.chat(user_text, image_path=image_rel)
        except KeyboardInterrupt:
            print("\nInterrupted.")
            break
        except Exception as e:
            print(f"\n[error] {e}")
            continue
        print()


if __name__ == "__main__":
    main()
