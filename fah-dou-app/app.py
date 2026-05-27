from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import chainlit as cl
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_core import Agent


def load_environment() -> None:
    load_dotenv(ROOT / ".env", override=True)

    if not os.getenv("OPENAI_MODEL") and os.getenv("MODEL_NAME"):
        os.environ["OPENAI_MODEL"] = os.environ["MODEL_NAME"]
    if not os.getenv("OPENAI_BASE_URL") and os.getenv("BASE_URL"):
        os.environ["OPENAI_BASE_URL"] = os.environ["BASE_URL"]


@cl.on_chat_start
async def start() -> None:
    load_environment()

    try:
        agent = Agent.from_env()
    except RuntimeError as e:
        await cl.Message(content=f"Startup failed: {e}").send()
        return
    except Exception as e:
        await cl.Message(content=f"Startup error: {e}").send()
        return

    cl.user_session.set("agent", agent)
    await cl.Message(content="Agent UI is ready. Send a message to chat.").send()


@cl.on_message
async def main(message: cl.Message) -> None:
    agent = cl.user_session.get("agent")
    if agent is None:
        load_environment()
        agent = Agent.from_env()
        cl.user_session.set("agent", agent)

    reply = cl.Message(content="")
    await reply.send()

    token_queue: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    errors: list[Exception] = []

    def on_token(token: str) -> None:
        loop.call_soon_threadsafe(token_queue.put_nowait, token)

    def chat() -> None:
        try:
            agent.chat(message.content, on_token=on_token)
        except Exception as e:
            errors.append(e)
        finally:
            loop.call_soon_threadsafe(token_queue.put_nowait, None)

    worker = asyncio.create_task(asyncio.to_thread(chat))

    while True:
        token = await token_queue.get()
        if token is None:
            break
        await reply.stream_token(token)

    await worker

    if errors:
        await reply.stream_token(f"\n\n[error] {errors[0]}")

    await reply.update()
