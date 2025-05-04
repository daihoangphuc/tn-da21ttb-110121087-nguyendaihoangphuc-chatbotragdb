from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()


class GeminiLLM:
    """Lớp quản lý mô hình ngôn ngữ lớn Gemini"""

    def __init__(self, api_key=None):
        """Khởi tạo mô hình Gemini"""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY không được cung cấp")

        # Cấu hình google.generativeai
        genai.configure(api_key=self.api_key)

        # Khởi tạo LangChain wrapper
        self.model = ChatGoogleGenerativeAI(
            model=os.getenv("LLM_MODEL_NAME", "gemini-2.0-flash"),
            google_api_key=self.api_key,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
            top_p=float(os.getenv("LLM_TOP_P", "0.85")),
            max_output_tokens=int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "2048")),
        )

    def invoke(self, prompt):
        """Gọi mô hình LLM với prompt"""
        return self.model.invoke(prompt)
