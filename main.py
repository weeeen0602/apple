from __future__ import annotations

from agent_core import Agent, get_token_budget


def main() -> None:
    try:
        agent = Agent.from_env()
    except RuntimeError as e:
        print(e)
        return

    print("Agent CLI ready. Type quit, exit, or q to leave.")
    print("Images: use `/image relative/path.png` then type your prompt,")
    print("or use `/image relative/path.png your prompt` on one line.")

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
        user_line = input("\nYou: ").strip()
        if user_line.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break
        if not user_line:
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
        agent.chat(user_text, image_path=image_rel)
        print()


if __name__ == "__main__":
    main()
