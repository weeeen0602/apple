import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
load_dotenv()
print(os.getenv("OPENAI_API_KEY"))

def main():
    ab="apple"
    print(f"歡迎使用{ab}")

load_dotenv()
print(os.getenv("OPENAI_API_KEY"))


if __name__ == "__main__":
    main()
