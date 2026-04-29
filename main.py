import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
load_dotenv()


def main():
    api_key=os.getenv("OPENAI_API_KEY")
    print(api_key)
    ab="apple"
    print(f"歡迎使用{ab}")
    if  api_key:
        print("API key is  set")
    else:
        print("API key is not set")
        return 
    

if __name__ == "__main__":
    main()
