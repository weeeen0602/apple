import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
load_dotenv()



def main():
    api_key=os.getenv("OPENAI_API_KEY")
    print(api_key)
    ab="apple"
    print(f"歡迎使用{ab}")
    if api_key:
        print("API key is set")
        llm = ChatOpenAI(
            model="gemma4:26b",
            base_url="http://203.71.78.31:8000/v1",
            api_key=api_key,
            temperature=0.0,
        )
        print("LLM 已成功初始化")
    else:
        print("API key is not set")
        return 
    

if __name__ == "__main__":
    main()
