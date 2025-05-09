from typing import Dict, List, Optional
import re
import os
import json
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()


class QueryProcessor:
    """Module xử lý truy vấn đơn giản sau khi loại bỏ tính năng query expansion"""

    def __init__(self, synonyms_file: str = None, use_model: bool = False):
        """Khởi tạo processor với cấu hình đơn giản"""
        # Giữ lại từ điển đồng nghĩa cơ bản
        self.synonyms = {}

        # Tạo synonyms mặc định
        self._create_default_synonyms()

        # Không sử dụng model
        self.use_model = False
        self.model = None

        # Cấu hình đơn giản
        self.use_query_compression = False
        self.max_query_length = int(os.getenv("MAX_QUERY_LENGTH", "250"))
        print("Đã khởi tạo QueryProcessor đơn giản (không dùng query expansion)")

    def _create_default_synonyms(self):
        """Tạo từ điển đồng nghĩa mặc định về CSDL và công nghệ liên quan"""
        self.synonyms = {
            # Một số từ đồng nghĩa cơ bản
            "csdl": ["cơ sở dữ liệu", "database", "db"],
            "database": ["cơ sở dữ liệu", "csdl", "db"],
            "sql": ["structured query language"],
            "nosql": ["not only sql", "phi quan hệ"],
        }

    def save_synonyms(self, file_path: str):
        """Lưu từ điển đồng nghĩa ra file"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.synonyms, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Lỗi khi lưu từ điển đồng nghĩa: {str(e)}")
            return False

    def add_synonym(self, term: str, synonyms: List[str]):
        """Thêm từ đồng nghĩa mới vào từ điển"""
        term = term.lower().strip()
        if term in self.synonyms:
            # Thêm vào danh sách đã có
            for syn in synonyms:
                if syn.lower().strip() not in self.synonyms[term]:
                    self.synonyms[term].append(syn.lower().strip())
        else:
            # Tạo danh sách mới
            self.synonyms[term] = [syn.lower().strip() for syn in synonyms]

    def compress_query(self, query: str) -> str:
        """Phiên bản đơn giản của phương thức nén query, không thực hiện nén thực sự"""
        return query

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Phiên bản đơn giản của phương thức trích xuất từ khóa"""
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

    def expand_query(self, query: str) -> List[str]:
        """Phiên bản đơn giản của phương thức mở rộng truy vấn, chỉ trả về truy vấn gốc"""
        return [query]  # Chỉ trả về truy vấn gốc, không mở rộng

    def hybrid_search_with_expansion(self, search_func, query: str, **kwargs) -> Dict:
        """Phiên bản đơn giản không mở rộng truy vấn, chỉ gọi hàm tìm kiếm với truy vấn gốc"""
        results = search_func(query, **kwargs)

        return {
            "results": results,
            "original_query": query,
            "compressed_query": None,
            "expanded_queries": [query],
            "queries_used": [query],
            "extracted_keywords": self.extract_keywords(query),
        }
