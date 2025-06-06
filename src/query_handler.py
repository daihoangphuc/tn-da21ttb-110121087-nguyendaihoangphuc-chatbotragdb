import logging
import json
import re
from typing import Tuple
from src.llm import GeminiLLM

# Cấu hình logging
logging.basicConfig(format="[QueryHandler] %(message)s", level=logging.INFO)
original_print = print

def print(*args, **kwargs):
    prefix = "[QueryHandler] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)

logger = logging.getLogger(__name__)

class QueryHandler:
    """
    Module hợp nhất xử lý và phân loại câu hỏi của người dùng trong một bước duy nhất
    để giảm số lần gọi LLM.
    """

    def __init__(self):
        """Khởi tạo QueryHandler."""
        self.llm = GeminiLLM()

    def _create_combined_prompt(self, query: str, conversation_history: str) -> str:
        """Tạo prompt kết hợp cho việc mở rộng và phân loại câu hỏi."""
        # Cung cấp lịch sử hội thoại, nếu không có thì thông báo
        history_context = conversation_history if conversation_history and conversation_history.strip() else "Không có lịch sử hội thoại."

        # Xây dựng prompt chi tiết
        prompt = f"""
        Bạn là một trợ lý chuyên gia xử lý và phân loại các câu hỏi của người dùng về cơ sở dữ liệu.
        Dựa vào "Lịch sử hội thoại" được cung cấp, nhiệm vụ của bạn là phân tích "Câu hỏi hiện tại" và trả về một đối tượng JSON với hai trường: "expanded_query" và "query_type".

        **Hướng dẫn:**

        1.  **`expanded_query`**:
            *   Viết lại "Câu hỏi hiện tại" thành một câu hỏi hoàn chỉnh, độc lập bằng cách giải quyết mọi tham chiếu (như "nó", "cái đó", "chúng") bằng cách sử dụng ngữ cảnh từ "Lịch sử hội thoại".
            *   Nếu "Câu hỏi hiện tại" đã rõ ràng, là một câu hỏi độc lập hoặc không liên quan đến lịch sử, hãy sử dụng câu hỏi gốc làm `expanded_query`.
            *   Bảo toàn tất cả các thuật ngữ kỹ thuật và tên riêng.

        2.  **`query_type`**:
            *   Phân loại `expanded_query` vào MỘT trong bốn loại sau:

            *   `question_from_document`: Câu hỏi về kiến thức cơ sở dữ liệu, khái niệm, cú pháp, thiết kế hoặc so sánh không nhạy cảm về thời gian và không yêu cầu trực tiếp tạo/giải thích mã SQL.
                *   Ví dụ: "Cơ sở dữ liệu là gì?", "So sánh SQL và NoSQL.", "Cú pháp của INSERT INTO trong SQL là gì?"

            *   `realtime_question`: Câu hỏi về cơ sở dữ liệu đề cập đến thời gian hiện tại, xu hướng mới nhất hoặc các phiên bản mới nhất. PHẢI chứa các từ khóa liên quan đến thời gian như "hiện tại", "mới nhất", "năm 2024".
                *   Ví dụ: "Xu hướng cơ sở dữ liệu mới nhất hiện nay là gì?", "Có gì mới trong PostgreSQL 16?", "Công nghệ cơ sở dữ liệu nào đang phát triển nhanh trong năm 2024?"

            *   `sql_code_task`: Yêu cầu trực tiếp để tạo, giải thích, sửa đổi hoặc tối ưu hóa một đoạn mã SQL cụ thể.
                *   Ví dụ: "Viết câu lệnh SQL để tạo bảng Users.", "Giải thích truy vấn này: SELECT * FROM Products WHERE Price > 100.", "Làm thế nào để tối ưu hóa truy vấn SQL này: SELECT ...?"

            *   `other_question`: Câu hỏi hoàn toàn không liên quan đến cơ sở dữ liệu hoặc SQL.
                *   Ví dụ: "Thời tiết hôm nay thế nào?", "Cách nấu phở?"

        **Lịch sử hội thoại:**
        ---
        {history_context}
        ---

        **Câu hỏi hiện tại:** "{query}"

        **Định dạng đầu ra:**
        CHỈ trả lời bằng một đối tượng JSON hợp lệ theo định dạng sau, không có bất kỳ giải thích hay văn bản nào khác.
        ```json
        {{
          "expanded_query": "...",
          "query_type": "..."
        }}
        ```
        """
        return prompt

    def expand_and_classify_query(self, query: str, conversation_history: str) -> Tuple[str, str]:
        """
        Xử lý câu hỏi của người dùng để mở rộng và phân loại trong một lệnh gọi LLM duy nhất.

        Trả về:
            Một tuple chứa (expanded_query, query_type).
        """
        prompt = self._create_combined_prompt(query, conversation_history)
        
        try:
            response = self.llm.invoke(prompt)
            response_text = response.content.strip()

            # Trích xuất phần JSON từ phản hồi, có thể nằm trong markdown block
            match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if match:
                json_str = match.group(0)
                parsed_response = json.loads(json_str)
                
                expanded_query = parsed_response.get("expanded_query")
                query_type = parsed_response.get("query_type")

                # Xác thực kết quả
                if not expanded_query or not isinstance(expanded_query, str):
                    expanded_query = query
                
                valid_types = ["question_from_document", "realtime_question", "sql_code_task", "other_question"]
                if query_type not in valid_types:
                    print(f"Loại truy vấn không hợp lệ '{query_type}' nhận được. Mặc định là 'question_from_document'.")
                    query_type = 'question_from_document'
                
                print(f"Truy vấn đã xử lý. Mở rộng: '{expanded_query}', Loại: '{query_type}'")
                return expanded_query, query_type
            else:
                # Nếu không tìm thấy JSON, đưa ra lỗi để chuyển sang fallback
                raise json.JSONDecodeError("Không tìm thấy đối tượng JSON trong phản hồi", response_text, 0)

        except (json.JSONDecodeError, AttributeError, KeyError, TypeError) as e:
            print(f"Không thể xử lý và phân loại truy vấn bằng prompt kết hợp: {e}")
            print("Chuyển sang phương án dự phòng: chỉ phân loại câu hỏi gốc.")
            # Đây là một phương án dự phòng đơn giản nếu LLM không trả về đúng định dạng
            # Chúng ta có thể tạo một QueryRouter dự phòng hoặc chỉ mặc định
            return query, 'question_from_document' # Giá trị mặc định an toàn