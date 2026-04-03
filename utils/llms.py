import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()


class LLMModel:
    def __init__(self, model_name="llama-3.3-70b-versatile"):
        """
        Initialize Groq LLM.
        model_name options:
          - llama-3.3-70b-versatile  (default, best for agentic tasks)
          - llama-3.1-8b-instant     (fast & cheap)
          - mixtral-8x7b-32768       (good context window)
          - gemma2-9b-it
        """
        if not model_name:
            raise ValueError("Model is not defined.")
        self.model_name = model_name
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment.")
        self.groq_model = ChatGroq(
            model=self.model_name,
            api_key=api_key,
            temperature=0,
        )

    def get_model(self):
        return self.groq_model


if __name__ == "__main__":
    llm_instance = LLMModel()
    llm_model = llm_instance.get_model()
    response = llm_model.invoke("hi")
    print(response)