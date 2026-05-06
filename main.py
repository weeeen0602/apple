import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
load_dotenv()



def main():
    if sys.platform == "win32":
        try:
            sys.stdin.reconfigure(encoding='utf-8')
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    api_key=os.getenv("OPENAI_API_KEY")
    base_url=os.getenv("BASE_URL")
    model=os.getenv("MODEL_NAME")
    
    ab="apple"
    print(f"歡迎使用{ab}")
    if api_key:
        print("API key is set")
    else:
        print("API key is not set")
        return 
    llm = ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=0.0,
    )

    history = []
    while True:
        user_message = input("使用者: ")
        if user_message.lower().strip() == "break":
            break
        
        history.append(HumanMessage(content=user_message))
        
        print("AI: ", end="", flush=True)
        full_response = ""
        for chunk in llm.stream(history):
            print(chunk.content, end="", flush=True)
            full_response += chunk.content
        print("\n")
        
        history.append(AIMessage(content=full_response))
    

    


if __name__ == "__main__":
    main()
