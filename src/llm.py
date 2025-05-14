from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import re

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

    def preprocess_prompt(self, prompt):
        """Tiền xử lý prompt trước khi gửi đến LLM"""
        # Chỉ xử lý prompt dạng văn bản
        if isinstance(prompt, str):
            # Thêm nhắc nhở về định dạng Markdown và độ dài
            format_reminder = """
            LƯU Ý BỔ SUNG (QUAN TRỌNG):
            - Hãy trả lời ngắn gọn, tập trung vào trọng tâm
            - Sử dụng định dạng Markdown với ## cho tiêu đề chính
            - Đặt code SQL trong ```sql và ```
            - KHÔNG dùng HTML, chỉ dùng Markdown
            - Giới hạn độ dài trả lời không quá 4 đoạn văn
            - Nếu cần bảng so sánh, hãy tạo bảng đơn giản với tối đa 3 cột, nếu có nhiều cột quá thì trả lời dạng liệt kê
            """

            # Thêm hướng dẫn vào cuối prompt
            prompt += format_reminder

        return prompt

    def postprocess_response(self, response):
        """Hậu xử lý phản hồi từ LLM để đảm bảo định dạng nhất quán"""
        # Trả về response gốc mà không xử lý gì thêm
        return response

    def invoke(self, prompt):
        """Gọi mô hình LLM với prompt"""
        processed_prompt = self.preprocess_prompt(prompt)
        # Trả về response gốc từ LLM không qua xử lý
        return self.model.invoke(processed_prompt)

    async def stream(self, prompt):
        """Gọi mô hình LLM với prompt và trả về kết quả dạng streaming

        Phương thức này là wrapper của invoke_streaming để tương thích với
        phương thức query_with_sources_streaming trong rag.py
        """
        async for chunk in self.invoke_streaming(prompt):
            yield chunk

    async def invoke_streaming(self, prompt):
        """Gọi mô hình LLM với prompt và trả về kết quả dạng streaming"""
        processed_prompt = self.preprocess_prompt(prompt)

        # Sử dụng trực tiếp genai API thay vì langchain wrapper để streaming
        model = genai.GenerativeModel(self.model_name)

        # Chuẩn bị nội dung từ prompt (chuyển từ langchain format sang genai format)
        if hasattr(processed_prompt, "to_messages"):
            # Là một chuỗi messages trong langchain
            messages = processed_prompt.to_messages()
            content = []

            for message in messages:
                role = "user" if message.type == "human" else "model"
                content.append({"role": role, "parts": [{"text": message.content}]})
        else:
            # Là text prompt đơn giản
            content = [{"role": "user", "parts": [{"text": processed_prompt}]}]

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

        # Trả về từng phần response qua generator - không xử lý thêm
        async for chunk in stream:
            if hasattr(chunk, "candidates") and chunk.candidates:
                if (
                    hasattr(chunk.candidates[0], "content")
                    and chunk.candidates[0].content.parts
                ):
                    text_chunk = chunk.candidates[0].content.parts[0].text
                    yield text_chunk
