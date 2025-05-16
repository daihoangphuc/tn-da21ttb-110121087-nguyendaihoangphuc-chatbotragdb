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
        Bạn là một hệ thống phân loại câu hỏi cho ứng dụng cơ sở dữ liệu (database). 
        Xác định xem câu hỏi sau thuộc loại nào:
        
        Câu hỏi: "{query}"
        
        Phân loại thành một trong các loại sau:
        1. "question_from_document": Câu hỏi về kiến thức cơ sở dữ liệu cơ bản, các khái niệm, syntax SQL, thiết kế cơ sở dữ liệu, các nguyên lý, v.v. Những câu hỏi này không liên quan đến thời gian hiện tại hoặc xu hướng mới.
        
        2. "realtime_question": Câu hỏi liên quan đến cơ sở dữ liệu nhưng cần thông tin thời gian thực ở hiện tại. Câu hỏi thuộc loại này thường:
           - Có các từ khóa thời gian: "hiện nay", "hiện tại", "bây giờ", "thời điểm này", "lúc này", "gần đây", "năm nay", "đương đại", v.v.
           - Hỏi về xu hướng mới nhất, phiên bản mới nhất của các CSDL
           - Hỏi về sự so sánh công nghệ CSDL trong bối cảnh hiện tại
           - Hỏi về các công nghệ đang phát triển, đang phổ biến
           LƯU Ý QUAN TRỌNG: Ngay cả khi câu hỏi hỏi về khái niệm cơ bản nhưng có các từ khóa thời gian như "hiện nay", "hiện tại", v.v., vẫn phân loại là "realtime_question"
        
        3. "other_question": Câu hỏi không liên quan đến lĩnh vực cơ sở dữ liệu.
        
        Các ví dụ về question_from_document:
        - "SELECT là gì trong SQL?"
        - "Cách thiết kế khóa ngoại trong cơ sở dữ liệu?"
        - "Các loại JOIN trong SQL?"
        - "CSDL có những khái niệm gì?"
        
        Các ví dụ về realtime_question:
        - "PostgreSQL có gì mới trong phiên bản 15?"
        - "So sánh MongoDB và MySQL trong năm 2024?"
        - "Xu hướng cơ sở dữ liệu hiện nay?"
        - "Hiện nay CSDL có khái niệm gì?" (Chú ý từ "hiện nay")
        - "Các công nghệ CSDL đang phổ biến?"
        
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
        return f"Câu hỏi ({query}) thuộc về khoảng thời gian thực mình không đủ kiến thức đề trả lời cho bạn hiện tại."
