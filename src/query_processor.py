from typing import Dict, List, Optional
import re
import os
from dotenv import load_dotenv
from src.llm import GeminiLLM

# Load biến môi trường từ .env
load_dotenv()


class QueryProcessor:
    """Xử lý mở rộng truy vấn và giải quyết đồng tham chiếu"""

    def __init__(self):
        """Khởi tạo bộ xử lý truy vấn"""
        self.llm = GeminiLLM()  # Hoặc một LLM nhẹ hơn dành riêng cho nhiệm vụ này

    def expand_query(self, query: str, conversation_history: str) -> str:
        """Mở rộng truy vấn bằng cách giải quyết đồng tham chiếu từ lịch sử hội thoại"""
        if not conversation_history or len(conversation_history.strip()) == 0:
            return query  # Không cần mở rộng nếu không có lịch sử

        prompt = f"""
        Dưới đây là lịch sử cuộc trò chuyện:
        
        {conversation_history}
        
        Câu hỏi tiếp theo: "{query}"
        
        Nhiệm vụ: Xem xét lịch sử trò chuyện và viết lại câu hỏi để nó rõ ràng, hoàn chỉnh và có thể hiểu độc lập, không phụ thuộc vào ngữ cảnh. 
        Thay thế các đại từ (như "nó", "chúng") bằng các từ tham chiếu cụ thể. Viết lại câu hỏi một cách tự nhiên.
        
        Chỉ trả về câu hỏi đã viết lại, không thêm giải thích hay bất kỳ nội dung nào khác.
        """

        response = self.llm.invoke(prompt)
        expanded_query = response.content.strip()

        # Ghi log để debug
        print(f"Câu hỏi gốc: '{query}'")
        print(f"Câu hỏi mở rộng: '{expanded_query}'")

        return expanded_query
