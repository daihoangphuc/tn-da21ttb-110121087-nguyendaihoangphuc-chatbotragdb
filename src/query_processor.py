from typing import Dict, List, Optional
import re
import os
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()


class QueryProcessor:
    """Module xử lý truy vấn cơ bản (không sử dụng query expansion)"""

    def __init__(self):
        """Khởi tạo processor với cấu hình đơn giản"""
        self.max_query_length = int(os.getenv("MAX_QUERY_LENGTH", "250"))
        print("Đã khởi tạo QueryProcessor đơn giản (không dùng query expansion)")

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Trích xuất từ khóa từ văn bản"""
        # Trích xuất đơn giản dựa trên tần suất từ
        words = re.findall(r"\b\w{3,}\b", text.lower())
        word_freq = {}
        for word in words:
            if word not in word_freq:
                word_freq[word] = 0
            word_freq[word] += 1

        # Loại bỏ các từ dừng phổ biến
        stop_words = {
            "và",
            "hoặc",
            "là",
            "của",
            "trong",
            "trên",
            "dưới",
            "có",
            "được",
            "cho",
            "này",
            "những",
        }
        word_freq = {k: v for k, v in word_freq.items() if k not in stop_words}

        # Sắp xếp theo tần suất
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:max_keywords]]
