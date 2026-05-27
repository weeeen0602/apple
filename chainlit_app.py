import os
from typing import List, Dict, Any

import chainlit as cl
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.callbacks.base import BaseCallbackHandler


load_dotenv()


SYSTEM_PROMPT = "你是友善且有幫助的 AI 助手，請使用繁體中文回覆。"


class ChainlitTokenHandler(BaseCallbackHandler):
    def __init__(self, msg: cl.Message):
        self.msg = msg

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        await self.msg.stream_token(token)


def build_messages(history: List[Dict[str, Any]], user_text: str) -> List[Any]:
    messages: List[Any] = [SystemMessage(content=SYSTEM_PROMPT)]

    for item in history:
        role = item.get("role")
        content = item.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=user_text))
    return messages


@cl.on_chat_start
async def on_chat_start() -> None:
    cl.user_session.set("history", [])
    await cl.Message(
        content="你好，我是你的 AI 助手。你可以直接輸入訊息，也可以上傳圖片與我一起討論。"
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    history = cl.user_session.get("history") or []

    user_parts: List[str] = []
    if message.content:
        user_parts.append(message.content)

    image_elements = []
    if message.elements:
        for element in message.elements:
            mime = getattr(element, "mime", "") or ""
            if mime.startswith("image/"):
                image_elements.append(element)

    if image_elements:
        user_parts.append("\n[使用者上傳了圖片]")
        for image in image_elements:
            name = getattr(image, "name", "未命名圖片")
            path = getattr(image, "path", "")
            user_parts.append(f"- 圖片檔名：{name}")
            if path:
                user_parts.append(f"- 圖片路徑：{path}")

    user_text = "\n".join(user_parts).strip()
    if not user_text:
        user_text = "請根據我上傳的圖片，描述你觀察到的內容。"

    history.append({"role": "user", "content": user_text})

    reply = cl.Message(content="")
    await reply.send()

    callback = ChainlitTokenHandler(reply)
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        streaming=True,
        callbacks=[callback],
    )

    messages = build_messages(history[:-1], user_text)
    result = await llm.ainvoke(messages)

    reply.content = result.content if isinstance(result.content, str) else str(result.content)
    await reply.update()

    history.append({"role": "assistant", "content": reply.content})
    cl.user_session.set("history", history)
