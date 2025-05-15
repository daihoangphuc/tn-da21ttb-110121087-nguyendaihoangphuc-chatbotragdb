from typing import Dict, List, Optional
import logging

# Cấu hình logging
logging.basicConfig(format="[Query Processor] %(message)s", level=logging.INFO)
# Ghi đè hàm print để thêm prefix
original_print = print


def print(*args, **kwargs):
    prefix = "[Query Processor] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)


logger = logging.getLogger(__name__)
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
            print("Không có lịch sử hội thoại, giữ nguyên câu hỏi gốc")
            return query

        # Tách lịch sử thành các cặp câu hỏi-trả lời
        messages = conversation_history.split("\n")
        context = []
        for msg in messages:
            if msg.startswith("Người dùng: ") or msg.startswith("Trợ lý: "):
                context.append(msg)

        print(f"Phân tích {len(context)} tin nhắn trong lịch sử")

        prompt = f"""
        Lịch sử hội thoại:
        {conversation_history}
        
        Câu hỏi hiện tại: "{query}"
        
        Nhiệm vụ: Phân tích lịch sử trò chuyện và viết lại câu hỏi để nó rõ ràng, hoàn chỉnh.
        
        Quy tắc:
        1. Thay thế các đại từ (nó, chúng, này, đó, đấy, kia, ...) bằng từ tham chiếu cụ thể từ các câu trước
        2. Giữ nguyên các thuật ngữ chuyên môn và tên riêng
        3. Bảo toàn ý nghĩa gốc của câu hỏi
        4. Nếu câu hỏi đã rõ ràng và không có đại từ cần thay thế, giữ nguyên câu hỏi
        5. Đảm bảo câu hỏi mở rộng vẫn giữ được ngữ cảnh của cuộc trò chuyện
        6. Nếu không thể xác định được đối tượng tham chiếu, giữ nguyên câu hỏi gốc
        
        Chỉ trả về câu hỏi đã viết lại, không thêm giải thích hay bất kỳ nội dung nào khác.
        """

        try:
            response = self.llm.invoke(prompt)
            expanded_query = response.content.strip()

            # Ghi log để debug
            print(f"Câu hỏi gốc: '{query}'")
            print(f"Câu hỏi mở rộng: '{expanded_query}'")
            print(f"Dựa trên lịch sử: {conversation_history[:200]}...")

            # Kiểm tra tính hợp lệ của câu mở rộng
            if not expanded_query or len(expanded_query) < len(query) / 2:
                print("Câu mở rộng không hợp lệ, giữ nguyên câu gốc")
                return query

            # Loại bỏ các prefix không cần thiết
            expanded_query = expanded_query.replace(
                "## Câu hỏi đã viết lại:", ""
            ).strip()
            expanded_query = expanded_query.replace("Câu hỏi đã viết lại:", "").strip()

            return expanded_query
        except Exception as e:
            print(f"Lỗi khi mở rộng câu hỏi: {str(e)}")
            return query
