from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import time

from src.config import (
    QUERY_EXPANSION_ENABLED,
    QUERY_EXPANSION_NUM_QUERIES,
    GEMINI_API_KEY,
)
from src.utils import measure_time


class QueryExpander(ABC):
    """Lớp trừu tượng cho query expansion"""

    @abstractmethod
    def expand_query(self, query: str) -> List[str]:
        """Mở rộng query thành danh sách các queries liên quan

        Args:
            query: Câu truy vấn gốc

        Returns:
            Danh sách các câu truy vấn mở rộng
        """
        pass


class LLMQueryExpander(QueryExpander):
    """Thực hiện query expansion bằng cách sử dụng LLM để tạo các truy vấn mở rộng"""

    def __init__(self, num_expansions: int = QUERY_EXPANSION_NUM_QUERIES):
        """Khởi tạo query expander sử dụng LLM

        Args:
            num_expansions: Số lượng truy vấn mở rộng cần tạo
        """
        self.num_expansions = num_expansions
        self._initialize_model()

    def _initialize_model(self):
        """Khởi tạo model LLM"""
        import google.generativeai as genai

        # Khởi tạo Gemini API
        genai.configure(api_key=GEMINI_API_KEY)

        # Sử dụng model nhỏ hơn và nhanh hơn cho query expansion
        self.model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")
        print("✅ Đã khởi tạo LLM cho query expansion")

    @measure_time
    def expand_query(self, query: str) -> List[str]:
        """Mở rộng query bằng cách sử dụng LLM

        Args:
            query: Câu truy vấn gốc

        Returns:
            Danh sách các câu truy vấn mở rộng
        """
        print(f"⏳ Đang thực hiện query expansion cho: '{query}'")
        expanded_queries = [query]  # Luôn giữ lại query gốc

        # Tạo prompt cho query expansion
        prompt = self._create_prompt(query)

        try:
            # Gửi prompt đến LLM
            response = self.model.generate_content(prompt)

            # Phân tích kết quả
            if response.text:
                result = self._parse_response(response.text)
                # Loại bỏ truy vấn trùng lặp hoặc rỗng
                for q in result:
                    if (
                        q
                        and q.strip()
                        and q.strip() != query
                        and q not in expanded_queries
                    ):
                        expanded_queries.append(q.strip())
                        # Dừng khi đủ số lượng truy vấn
                        if (
                            len(expanded_queries) >= self.num_expansions + 1
                        ):  # +1 vì có query gốc
                            break

            print(f"✅ Đã mở rộng thành {len(expanded_queries)} truy vấn")
            return expanded_queries

        except Exception as e:
            print(f"⚠️ Lỗi khi thực hiện query expansion: {str(e)}")
            # Nếu có lỗi, trả về query gốc
            return [query]

    def _create_prompt(self, query: str) -> str:
        """Tạo prompt cho LLM để thực hiện query expansion

        Args:
            query: Câu truy vấn gốc

        Returns:
            Prompt cho LLM
        """
        # Tùy chỉnh prompt cho domain cơ sở dữ liệu nếu query liên quan
        if any(
            kw in query.lower()
            for kw in [
                "database",
                "sql",
                "query",
                "table",
                "schema",
                "cơ sở dữ liệu",
                "csdl",
            ]
        ):
            return f"""Bạn là chuyên gia về cơ sở dữ liệu. Hãy mở rộng truy vấn sau thành {self.num_expansions} truy vấn khác nhau để tìm kiếm thông tin liên quan.

Truy vấn: {query}

Hãy trả về tập hợp các truy vấn khác có nội dung liên quan nhưng sử dụng từ ngữ, thuật ngữ kỹ thuật và góc nhìn khác nhau về cơ sở dữ liệu. 
Truy vấn nên bao gồm các khía cạnh kỹ thuật và các thuật ngữ chuyên ngành cơ sở dữ liệu như SQL, schema, normalization, index, transaction, v.v.

Trả về dưới dạng danh sách đánh số. Ví dụ:
1. Truy vấn mở rộng 1
2. Truy vấn mở rộng 2
...

Chỉ trả về danh sách truy vấn, không cần giải thích thêm."""
        else:
            # Prompt chung cho các truy vấn khác
            return f"""Hãy mở rộng truy vấn sau thành {self.num_expansions} truy vấn khác nhau để tìm kiếm thông tin liên quan.

Truy vấn: {query}

Trả về dưới dạng danh sách đánh số. Ví dụ:
1. Truy vấn mở rộng 1
2. Truy vấn mở rộng 2
...

Chỉ trả về danh sách truy vấn, không cần giải thích thêm."""

    def _parse_response(self, response: str) -> List[str]:
        """Phân tích kết quả từ LLM để lấy các truy vấn mở rộng

        Args:
            response: Kết quả từ LLM

        Returns:
            Danh sách các truy vấn mở rộng
        """
        queries = []

        # Chia các dòng
        lines = response.strip().split("\n")

        for line in lines:
            # Loại bỏ số thứ tự và khoảng trắng
            line = line.strip()
            if not line:
                continue

            # Kiểm tra xem có đánh số không
            if line[0].isdigit() and ". " in line:
                # Lấy phần sau của số và dấu chấm
                parts = line.split(". ", 1)
                if len(parts) > 1:
                    query = parts[1].strip()
                    queries.append(query)
            else:
                # Nếu không có số, thêm nguyên dòng
                queries.append(line)

        return queries
