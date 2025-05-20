from langchain_google_genai import ChatGoogleGenerativeAI
import logging

# Cấu hình logging
logging.basicConfig(format="[LLM] %(message)s", level=logging.INFO)
# Ghi đè hàm print để thêm prefix
original_print = print


def print(*args, **kwargs):
    prefix = "[LLM] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)


logger = logging.getLogger(__name__)
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import re
from typing import List, Optional

# Load biến môi trường từ .env
load_dotenv()


class GeminiLLM:
    """Lớp quản lý mô hình ngôn ngữ lớn Gemini"""

    def __init__(self, api_key=None):
        """Khởi tạo mô hình Gemini"""
        # Xử lý danh sách API keys
        self.api_keys = []
        self.current_key_index = 0

        if api_key:
            # Sử dụng key được truyền vào
            self.api_keys = [api_key]
        else:
            # Lấy và xử lý danh sách keys từ biến môi trường
            env_keys = os.getenv("GOOGLE_API_KEY", "")
            if "," in env_keys:
                # Nhiều keys được phân tách bằng dấu phẩy
                self.api_keys = [
                    key.strip() for key in env_keys.split(",") if key.strip()
                ]
            else:
                # Chỉ có một key
                self.api_keys = [env_keys] if env_keys else []

        if not self.api_keys:
            raise ValueError("GOOGLE_API_KEY không được cung cấp")

        print(f"Đã tải {len(self.api_keys)} API keys")

        # Cấu hình ban đầu với key đầu tiên
        self.api_key = self.api_keys[0]
        self._configure_api()

        # Lưu thông tin model
        self.model_name = os.getenv("LLM_MODEL_NAME", "gemini-2.0-flash")

    def _configure_api(self):
        """Cấu hình API với key hiện tại"""
        # Cấu hình google.generativeai
        genai.configure(api_key=self.api_key)

        # Khởi tạo LangChain wrapper
        self.model = ChatGoogleGenerativeAI(
            model=os.getenv("LLM_MODEL_NAME", "gemini-2.0-flash"),
            google_api_key=self.api_key,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
            top_p=float(os.getenv("LLM_TOP_P", "0.85")),
        )

    def _try_next_api_key(self) -> bool:
        """Thử chuyển sang API key tiếp theo. Trả về True nếu thành công, False nếu hết key."""
        if len(self.api_keys) <= 1:
            return False

        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self.api_key = self.api_keys[self.current_key_index]
        print(f"Chuyển sang API key mới (index: {self.current_key_index})")

        self._configure_api()
        return True

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

        max_retries = len(self.api_keys)
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Trả về response gốc từ LLM không qua xử lý
                return self.model.invoke(processed_prompt)
            except Exception as e:
                error_str = str(e).lower()
                retry_count += 1

                # Kiểm tra các lỗi liên quan đến quota hoặc rate limit
                if any(
                    err in error_str
                    for err in ["quota", "rate limit", "429", "exceeds", "limit"]
                ):
                    print(
                        f"API key hiện tại đã hết quota hoặc bị giới hạn: {error_str}"
                    )
                    if self._try_next_api_key() and retry_count < max_retries:
                        print(f"Thử lại với API key mới ({retry_count}/{max_retries})")
                        continue

                # Nếu đã thử tất cả các key hoặc lỗi không phải do quota
                print(f"Lỗi khi gọi LLM: {str(e)}")
                raise

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

        max_retries = len(self.api_keys)
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Sử dụng trực tiếp genai API thay vì langchain wrapper để streaming
                model = genai.GenerativeModel(self.model_name)

                # Chuẩn bị nội dung từ prompt (chuyển từ langchain format sang genai format)
                if hasattr(processed_prompt, "to_messages"):
                    # Là một chuỗi messages trong langchain
                    messages = processed_prompt.to_messages()
                    content = []

                    for message in messages:
                        role = "user" if message.type == "human" else "model"
                        content.append(
                            {"role": role, "parts": [{"text": message.content}]}
                        )
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

                # Nếu streaming hoàn thành mà không có lỗi, thoát khỏi vòng lặp
                break

            except Exception as e:
                error_str = str(e).lower()
                retry_count += 1

                # Kiểm tra các lỗi liên quan đến quota hoặc rate limit
                if any(
                    err in error_str
                    for err in ["quota", "rate limit", "429", "exceeds", "limit"]
                ):
                    print(
                        f"API key hiện tại đã hết quota hoặc bị giới hạn trong chế độ streaming: {error_str}"
                    )
                    if self._try_next_api_key() and retry_count < max_retries:
                        print(
                            f"Thử lại với API key mới cho streaming ({retry_count}/{max_retries})"
                        )
                        continue

                # Ném lỗi nếu đã thử hết tất cả key hoặc lỗi không phải do quota
                print(f"Lỗi khi gọi LLM streaming: {str(e)}")
                raise
