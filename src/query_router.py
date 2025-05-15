from typing import Dict, List, Optional, Tuple
import logging

# Cấu hình logging
logging.basicConfig(
    format='[Query Router] %(message)s',
    level=logging.INFO
)
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
    2. "realtime_question": Câu hỏi liên quan đến cơ sở dữ liệu nhưng cần thông tin thời gian thực
    3. "other_question": Câu hỏi không liên quan đến lĩnh vực cơ sở dữ liệu
    """

    def __init__(self):
        """Khởi tạo bộ phân loại câu hỏi"""
        self.llm = GeminiLLM()  # Sử dụng LLM để phân loại câu hỏi

    def classify_query(self, query: str, vector_store_has_results: bool = None) -> str:
        """
        Phân loại câu hỏi thành một trong ba loại, sử dụng LLM

        Args:
            query: Câu hỏi cần phân loại
            vector_store_has_results: True nếu vector store có kết quả cho câu hỏi này

        Returns:
            Loại câu hỏi: "question_from_document", "realtime_question", hoặc "other_question"
        """
        # Nếu vector store có kết quả và đó là câu hỏi liên quan đến CSDL,
        # thì đó là question_from_document
        initial_classification = self._classify_with_llm(query)

        # Logic dựa trên kết quả vector store
        if (
            vector_store_has_results is True
            and initial_classification != "other_question"
        ):
            return "question_from_document"

        # Nếu không có kết quả từ vector store nhưng là câu hỏi về CSDL,
        # thì đó là realtime_question
        if (
            vector_store_has_results is False
            and initial_classification != "other_question"
        ):
            return "realtime_question"

        # Trả về kết quả phân loại từ LLM trong các trường hợp còn lại
        return initial_classification

    def _classify_with_llm(self, query: str) -> str:
        """
        Sử dụng LLM để phân loại câu hỏi

        Args:
            query: Câu hỏi cần phân loại

        Returns:
            Loại câu hỏi: "question_from_document", "realtime_question", hoặc "other_question"
        """
        prompt = f"""
        Bạn là một hệ thống phân loại câu hỏi cho ứng dụng cơ sở dữ liệu (database). 
        Xác định xem câu hỏi sau thuộc loại nào:
        
        Câu hỏi: "{query}"
        
        Phân loại thành một trong các loại sau:
        1. "question_from_document": Câu hỏi về kiến thức cơ sở dữ liệu cơ bản, các khái niệm, syntax SQL, thiết kế cơ sở dữ liệu, các nguyên lý, v.v.
        2. "realtime_question": Câu hỏi liên quan đến cơ sở dữ liệu nhưng yêu cầu thông tin thời gian thực, so sánh các công nghệ mới, xu hướng hiện tại, phiên bản mới nhất, v.v.
        3. "other_question": Câu hỏi không liên quan đến lĩnh vực cơ sở dữ liệu.
        
        Các ví dụ về question_from_document:
        - "SELECT là gì trong SQL?"
        - "Cách thiết kế khóa ngoại trong cơ sở dữ liệu?"
        - "Các loại JOIN trong SQL?"
        
        Các ví dụ về realtime_question:
        - "PostgreSQL có gì mới trong phiên bản 15?"
        - "So sánh MongoDB và MySQL trong năm 2024?"
        - "Xu hướng cơ sở dữ liệu hiện nay?"
        
        Các ví dụ về other_question:
        - "Thời tiết ở Hà Nội hôm nay thế nào?"
        - "Làm sao để nấu bún bò Huế?"
        - "Tôi nên học tiếng Anh như thế nào?"
        
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
        return "Đây là câu hỏi thời gian thực mình không đủ kiến thức đề trả lời cho bạn hiện tại."
