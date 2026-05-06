import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
load_dotenv()



def main():
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

    while True:
        user_message = input("使用者: ")
        if user_message.lower() == " break":
            break
        
        response = llm.invoke(user_message) 
        print(f"AI\n {response.content}\n")
    

    


if __name__ == "__main__":
    main()
