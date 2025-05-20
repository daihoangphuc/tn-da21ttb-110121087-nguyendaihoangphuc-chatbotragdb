from typing import Dict, List, Optional, Tuple
import logging

# Cấu hình logging
logging.basicConfig(format="[Query Router] %(message)s", level=logging.INFO)
# Ghi đè hàm print để thêm prefix
original_print = print


def print(*args, **kwargs):
    prefix = "[Query Router] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)


logger = logging.getLogger(__name__)
import os
from dotenv import load_dotenv
from src.llm import GeminiLLM

# Load biến môi trường từ .env
load_dotenv()


class QueryRouter:
    """
    Module phân loại câu hỏi thành 3 loại:
    1. "question_from_document": Câu hỏi thuộc lĩnh vực cơ sở dữ liệu có trong tài liệu
    2. "realtime_question": Câu hỏi liên quan đến cơ sở dữ liệu nhưng cần thông tin thời gian thực hiện tại (và có các từ khóa hiện thời gian hiện tại)
    3. "other_question": Câu hỏi không liên quan đến lĩnh vực cơ sở dữ liệu
    """

    def __init__(self):
        """Khởi tạo bộ phân loại câu hỏi"""
        self.llm = GeminiLLM()  # Sử dụng LLM để phân loại câu hỏi

    def classify_query(self, query: str, vector_store_has_results: bool = None) -> str:
        """
        Phân loại câu hỏi thành một trong ba loại, sử dụng hoàn toàn LLM

        Args:
            query: Câu hỏi cần phân loại
            vector_store_has_results: Tham số này giữ lại để tương thích với code cũ nhưng không sử dụng

        Returns:
            Loại câu hỏi: "question_from_document", "realtime_question", hoặc "other_question"
        """
        # Sử dụng hoàn toàn LLM để phân loại câu hỏi
        classification = self._classify_with_llm(query)
        print(f"LLM đã phân loại câu hỏi '{query}' thành: {classification}")
        return classification

    def _classify_with_llm(self, query: str) -> str:
        """
        Sử dụng LLM để phân loại câu hỏi

        Args:
            query: Câu hỏi cần phân loại

        Returns:
            Loại câu hỏi: "question_from_document", "realtime_question", hoặc "other_question"
        """
        prompt = f"""
        Phân loại câu hỏi sau vào một trong ba loại:
        
        Câu hỏi: "{query}"
        
        1. "question_from_document": Câu hỏi về kiến thức cơ sở dữ liệu cơ bản, khái niệm, cú pháp, thiết kế, hoặc so sánh công nghệ CSDL không đề cập đến thời gian hiện tại.
            Ví dụ:
            - "Cơ sở dữ liệu là gì?"
            - "So sánh SQL và NoSQL?"
            - "Cú pháp INSERT INTO trong SQL như thế nào?"
            - Lấy danh sách các bảng trong cơ sở dữ liệu ...
        
        2. "realtime_question": Câu hỏi về CSDL có đề cập đến thời gian hiện tại, xu hướng mới nhất, phiên bản mới nhất, hoặc công nghệ đang phát triển. Câu hỏi này PHẢI có từ khóa thời gian như "hiện nay", "hiện tại", "bây giờ", "năm 2023", "năm 2024", v.v.
            Ví dụ:
            - "Xu hướng cơ sở dữ liệu mới nhất hiện nay là gì?"
            - "Phiên bản PostgreSQL 16 hiện tại có gì mới?"
            - "Công nghệ cơ sở dữ liệu nào đang phát triển mạnh mẽ vào năm 2024?"
        
        3. "other_question": Câu hỏi không liên quan đến lĩnh vực cơ sở dữ liệu.
            Ví dụ:
            - "Thời tiết hôm nay thế nào?"
            - "Cách làm món phở bò?"
        
        LƯU Ý: Câu hỏi so sánh giữa các công nghệ CSDL mà KHÔNG có từ khóa thời gian thuộc loại "question_from_document".
        
        Chỉ trả về một trong ba giá trị: "question_from_document", "realtime_question", hoặc "other_question" mà không có thêm bất kỳ giải thích nào.
        """

        response = self.llm.invoke(prompt)
        classification = response.content.strip().lower()

        # Chuẩn hóa kết quả
        if "question_from_document" in classification:
            return "question_from_document"
        elif "realtime_question" in classification:
            return "realtime_question"
        else:
            return "other_question"

    def get_response_for_other_question(self, query: str) -> str:
        """
        Trả về phản hồi cho các câu hỏi không liên quan đến cơ sở dữ liệu

        Args:
            query: Câu hỏi cần phản hồi

        Returns:
            Phản hồi cố định cho câu hỏi không liên quan
        """
        return "Vì mình là Chatbot chỉ hỗ trợ và phản hồi trong lĩnh vực cơ sở dữ liệu thôi."

    def prepare_realtime_response(self, query: str) -> str:
        """
        Trả về phản hồi cho các câu hỏi thời gian thực về cơ sở dữ liệu

        Args:
            query: Câu hỏi cần phản hồi

        Returns:
            Phản hồi cố định cho câu hỏi thời gian thực
        """
        return f"Câu hỏi ({query}) thuộc về khoảng thời gian thực mình không đủ kiến thức đề trả lời cho bạn hiện tại."
