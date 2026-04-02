import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

class LLMModel:
    def __init__(self, model_name="llama-3.3-70b-versatile"):
        if not model_name:
            raise ValueError("Model is not defined.")
        self.model_name = model_name
        self.groq_model = ChatGroq(
            model=self.model_name,
            api_key=GROQ_API_KEY,
            temperature=0,        
            max_tokens=1024,      
        )

    def get_model(self):
        return self.groq_model


if __name__ == "__main__":
    llm_instance = LLMModel()
    llm_model = llm_instance.get_model()
    response = llm_model.invoke("hi")
    print(response)