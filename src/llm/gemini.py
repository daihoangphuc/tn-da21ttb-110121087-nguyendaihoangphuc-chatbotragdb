from typing import List, Dict, Any, Optional, Callable
import google.generativeai as genai
from google.generativeai import GenerationConfig
from langchain.schema import Document

from src.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_TOP_P,
    GEMINI_TOP_K,
)
from src.utils import format_context_for_llm, measure_time, extract_source_info
from src.templates import get_database_query_prompt


class GeminiLLM:
    """Lớp quản lý việc giao tiếp với Gemini LLM"""

    def __init__(self):
        """Khởi tạo kết nối đến Gemini"""
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(model_name=GEMINI_MODEL)
        self.generation_config = GenerationConfig(
            temperature=GEMINI_TEMPERATURE, top_p=GEMINI_TOP_P, top_k=GEMINI_TOP_K
        )

    @measure_time
    def generate_response(
        self,
        query: str,
        docs: List[Document],
        prompt_template: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Tạo câu trả lời với Gemini dựa trên context và câu truy vấn

        Args:
            query: Câu truy vấn
            docs: Danh sách tài liệu liên quan
            prompt_template: Hàm tạo prompt template, nếu None sẽ dùng mặc định

        Returns:
            Dict chứa câu trả lời và thông tin bổ sung như prompt, nguồn,...
        """
        # Kiểm tra số lượng tài liệu
        if not docs or len(docs) == 0:
            print("⚠️ Không có tài liệu nào trong context")
            return {
                "text": "Không tìm thấy thông tin liên quan trong cơ sở dữ liệu. Vui lòng index dữ liệu trước khi truy vấn hoặc thử lại với câu hỏi khác.",
                "sources": [],
                "prompt": "",
                "model": GEMINI_MODEL,
                "temperature": GEMINI_TEMPERATURE,
            }

        # Format context từ tài liệu
        context = format_context_for_llm(docs)

        # Trích xuất thông tin về nguồn
        sources = extract_source_info(docs)

        # Sử dụng prompt template nếu được cung cấp, nếu không dùng mặc định
        if prompt_template is None:
            prompt_template = get_database_query_prompt

        prompt = prompt_template(context, query)

        print(f"⏳ Đang tạo câu trả lời từ Gemini...")
        response = self.model.generate_content(
            prompt, generation_config=self.generation_config
        )

        # Trả về kết quả dưới dạng dict để có thể bổ sung thông tin
        return {
            "text": response.text,
            "sources": sources,
            "prompt": prompt,
            "model": GEMINI_MODEL,
            "temperature": GEMINI_TEMPERATURE,
            "total_sources": len(docs),
        }
