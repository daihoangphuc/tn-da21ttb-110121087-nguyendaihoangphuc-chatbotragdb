from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

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

        # Lưu thông tin model
        self.model_name = os.getenv("LLM_MODEL_NAME", "gemini-2.0-flash")

    def invoke(self, prompt):
        """Gọi mô hình LLM với prompt"""
        return self.model.invoke(prompt)

    async def invoke_streaming(self, prompt):
        """Gọi mô hình LLM với prompt và trả về kết quả dạng streaming"""
        # Sử dụng trực tiếp genai API thay vì langchain wrapper để streaming
        model = genai.GenerativeModel(self.model_name)

        # Chuẩn bị nội dung từ prompt (chuyển từ langchain format sang genai format)
        if hasattr(prompt, "to_messages"):
            # Là một chuỗi messages trong langchain
            messages = prompt.to_messages()
            content = []

            for message in messages:
                role = "user" if message.type == "human" else "model"
                content.append({"role": role, "parts": [{"text": message.content}]})
        else:
            # Là text prompt đơn giản
            content = [{"role": "user", "parts": [{"text": prompt}]}]

        # Gọi model streaming
        stream = await model.generate_content_async(
            content,
            stream=True,
            generation_config={
                "temperature": float(os.getenv("LLM_TEMPERATURE", "0")),
                "top_p": float(os.getenv("LLM_TOP_P", "0.85")),
                "max_output_tokens": int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "2048")),
            },
        )

        # Trả về từng phần response qua generator
        async for chunk in stream:
            if hasattr(chunk, "candidates") and chunk.candidates:
                if (
                    hasattr(chunk.candidates[0], "content")
                    and chunk.candidates[0].content.parts
                ):
                    yield chunk.candidates[0].content.parts[0].text
