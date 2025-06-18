import logging
import json
import re
from typing import Tuple, Dict
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
    để giảm số lần gọi LLM. Bao gồm tính năng sửa lỗi chính tả và viết tắt.
    """

    def __init__(self):
        """Khởi tạo QueryHandler."""
        self.llm = GeminiLLM()

        # Dictionary các từ viết tắt và lỗi chính tả phổ biến trong lĩnh vực CSDL
        self.abbreviation_dict = {
            # Viết tắt tiếng Việt
            "cdld": "CSDL",
            "csdl": "CSDL", 
            "qtcsdl": "quản trị cơ sở dữ liệu",
            "qtcơ": "quản trị cơ",
            "hqtcsdl": "hệ quản trị cơ sở dữ liệu",
            "hệ qtcsdl": "hệ quản trị cơ sở dữ liệu",
            "hệ qt csdl": "hệ quản trị cơ sở dữ liệu",
            "dbms": "DBMS",
            "rdbms": "RDBMS",
            "nosql": "NoSQL",
            "mongodb": "MongoDB",
            "mysql": "MySQL",
            "postgresql": "PostgreSQL",
            "sqlite": "SQLite",
            "oracle": "Oracle",
            "sqlserver": "SQL Server",
            "ms sql": "SQL Server",
            
            # Lỗi chính tả phổ biến
            "co so du lieu": "cơ sở dữ liệu",
            "cơ sở dữ liệu": "cơ sở dữ liệu", # giữ nguyên nếu đúng
            "quan tri": "quản trị",
            "quản trị": "quản trị", # giữ nguyên nếu đúng
            "du lieu": "dữ liệu",
            "dữ liệu": "dữ liệu", # giữ nguyên nếu đúng
            "truy van": "truy vấn",
            "truy vấn": "truy vấn", # giữ nguyên nếu đúng
            "cau lenh": "câu lệnh",
            "câu lệnh": "câu lệnh", # giữ nguyên nếu đúng
            "bang": "bảng",
            "bảng": "bảng", # giữ nguyên nếu đúng
            "truong": "trường",
            "trường": "trường", # giữ nguyên nếu đúng
            "khoa chinh": "khóa chính",
            "khóa chính": "khóa chính", # giữ nguyên nếu đúng
            "khoa ngoai": "khóa ngoại",
            "khóa ngoại": "khóa ngoại", # giữ nguyên nếu đúng
            "chi muc": "chỉ mục",
            "chỉ mục": "chỉ mục", # giữ nguyên nếu đúng
            "backup": "sao lưu",
            "restore": "khôi phục",
            
            # Viết tắt SQL
            "select": "SELECT",
            "insert": "INSERT",
            "update": "UPDATE", 
            "delete": "DELETE",
            "create": "CREATE",
            "alter": "ALTER",
            "drop": "DROP",
            "join": "JOIN",
            "inner join": "INNER JOIN",
            "left join": "LEFT JOIN",
            "right join": "RIGHT JOIN",
            "full join": "FULL JOIN",
            "where": "WHERE",
            "group by": "GROUP BY",
            "order by": "ORDER BY",
            "having": "HAVING",
        }

    def _preprocess_query(self, query: str) -> str:
        """
        Tiền xử lý câu hỏi để sửa lỗi chính tả và viết tắt phổ biến.
        
        Args:
            query: Câu hỏi gốc từ người dùng
            
        Returns:
            Câu hỏi đã được sửa lỗi chính tả và viết tắt
        """
        processed_query = query.strip()
        
        # Sửa các từ viết tắt và lỗi chính tả
        for wrong_term, correct_term in self.abbreviation_dict.items():
            # Sử dụng regex để thay thế từ có ranh giới (word boundary)
            # Điều này tránh thay thế các từ con
            pattern = r'\b' + re.escape(wrong_term) + r'\b'
            processed_query = re.sub(pattern, correct_term, processed_query, flags=re.IGNORECASE)
        
        # Log nếu có thay đổi
        if processed_query != query:
            print(f"🔧 Đã sửa query: '{query}' → '{processed_query}'")
        
        return processed_query

    def _create_enhanced_prompt(self, query: str, conversation_history: str) -> str:
        """Tạo prompt được cải thiện cho việc mở rộng và phân loại câu hỏi."""
        # Cung cấp lịch sử hội thoại, nếu không có thì thông báo
        history_context = conversation_history if conversation_history and conversation_history.strip() else "Không có lịch sử hội thoại."

        # Xây dựng prompt chi tiết và tối ưu
        prompt = f"""
        Bạn là một chuyên gia xử lý ngôn ngữ tự nhiên chuyên về cơ sở dữ liệu. Nhiệm vụ của bạn là phân tích "Câu hỏi hiện tại" dựa trên "Lịch sử hội thoại" và trả về JSON với ba trường: "expanded_query", "query_type", và "corrections_made".

        **NHIỆM VỤ CHÍNH:**

        1. **`expanded_query`** (Mở rộng và làm rõ câu hỏi):
           • Viết lại câu hỏi thành dạng hoàn chỉnh, độc lập, rõ ràng
           • Giải quyết tất cả tham chiếu mơ hồ ("nó", "cái đó", "chúng", "như vậy")
           • Xử lý các phản hồi ngắn gọn ("ok", "được", "tiếp tục", "yes", "vâng"):
             - Nếu AI vừa đề xuất chủ đề → chuyển thành câu hỏi cụ thể về chủ đề đó
             - Nếu AI hỏi có muốn tiếp tục → chuyển thành yêu cầu tiếp tục rõ ràng
           • SỬA LỖI CHÍNH TẢ và CHUẨN HÓA thuật ngữ:
             - "cdld" → "CSDL"
             - "co so du lieu" → "cơ sở dữ liệu" 
             - "quan tri" → "quản trị"
             - "du lieu" → "dữ liệu"
             - Các lệnh SQL viết thường → VIẾT HOA (select → SELECT)
           • Bảo toàn và chuẩn hóa tất cả thuật ngữ kỹ thuật

        2. **`query_type`** (Phân loại chính xác):
           
           • **`question_from_document`**: Câu hỏi về kiến thức CSDL cơ bản/lý thuyết
             - Khái niệm, định nghĩa, nguyên lý
             - So sánh công nghệ (SQL vs NoSQL) 
             - Cú pháp, cấu trúc lệnh
             - Thiết kế CSDL, mô hình dữ liệu
             - Ví dụ: "CSDL là gì?", "Khóa chính và khóa ngoại khác nhau như thế nào?"

           • **`realtime_question`**: Câu hỏi về xu hướng/tin tức/thông tin cập nhật mới
             - Có từ khóa thời gian: "hiện tại", "mới nhất", "2024", "gần đây", "hiện nay"
             - KẾT HỢP với ý định tìm hiểu xu hướng/tin tức/cập nhật mới
             - Xu hướng công nghệ, phiên bản mới, thống kê thị trường
             - Ví dụ: "Xu hướng CSDL hiện tại", "PostgreSQL 16 có gì mới?", "CSDL nào phổ biến nhất hiện nay?"
             
             **CHÚ Ý**: Phân biệt với câu hỏi cơ bản:
             - "Các loại CSDL hiện nay" = question_from_document (hỏi phân loại cơ bản)
             - "CSDL nào đang thịnh hành hiện nay" = realtime_question (hỏi xu hướng)

           • **`sql_code_task`**: Yêu cầu trực tiếp về code SQL
             - Viết/tạo câu lệnh SQL
             - Giải thích/phân tích code SQL có sẵn
             - Debug/tối ưu hóa SQL
             - Ví dụ: "Viết SQL tạo bảng User", "Giải thích query này: SELECT..."

           • **`other_question`**: Không liên quan đến CSDL
             - CHỈ dùng khi hoàn toàn không liên quan sau khi mở rộng
             - Ví dụ: "Thời tiết", "Nấu ăn", "Thể thao"

        3. **`corrections_made`** (Danh sách sửa lỗi):
           • Mảng các thay đổi đã thực hiện
           • Format: ["cdld → CSDL", "co so → cơ sở"]
           • Để mảng rỗng [] nếu không có sửa đổi

        **VÍ DỤ THỰC TẾ:**

        Input: "Khái niệm hệ quản trị cdld là gì?"
        ```json
        {{
          "expanded_query": "Khái niệm hệ quản trị CSDL (Cơ sở dữ liệu) là gì?",
          "query_type": "question_from_document",
          "corrections_made": ["cdld → CSDL"]
        }}
        ```

        Input: "ok" (sau khi AI đề xuất tìm hiểu về Index)
        ```json
        {{
          "expanded_query": "Tôi muốn tìm hiểu về Index (chỉ mục) trong cơ sở dữ liệu",
          "query_type": "question_from_document", 
          "corrections_made": []
        }}
        ```

        **NGỮ CẢNH:**
        Lịch sử hội thoại:
        ---
        {history_context}
        ---

        Câu hỏi hiện tại: "{query}"

        **XUẤT KẾT QUẢ:**
        CHỈ trả về JSON hợp lệ, không có text khác:
        ```json
        {{
          "expanded_query": "...",
          "query_type": "...",
          "corrections_made": [...]
        }}
        ```
        """
        return prompt

    def expand_and_classify_query(self, query: str, conversation_history: str) -> Tuple[str, str]:
        """
        Xử lý câu hỏi của người dùng để mở rộng và phân loại trong một lệnh gọi LLM duy nhất.
        Bao gồm tính năng sửa lỗi chính tả và viết tắt.

        Args:
            query: Câu hỏi gốc từ người dùng
            conversation_history: Lịch sử hội thoại để hiểu ngữ cảnh

        Returns:
            Một tuple chứa (expanded_query, query_type).
        """
        # Bước 1: Tiền xử lý cơ bản (sửa lỗi chính tả phổ biến)
        preprocessed_query = self._preprocess_query(query)
        
        # Bước 2: Tạo prompt nâng cao
        prompt = self._create_enhanced_prompt(preprocessed_query, conversation_history)
        
        print(f"🤖 Gọi LLM với query: '{query}' → '{preprocessed_query}'")
        print(f"📜 History length: {len(conversation_history) if conversation_history else 0}")
        
        try:
            response = self.llm.invoke(prompt)
            response_text = response.content.strip()
            print(f"🤖 LLM response: {response_text[:300]}..." if len(response_text) > 300 else f"🤖 LLM response: {response_text}")

            # Trích xuất phần JSON từ phản hồi
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed_response = json.loads(json_str)
                
                expanded_query = parsed_response.get("expanded_query", "").strip()
                query_type = parsed_response.get("query_type", "").strip()
                corrections_made = parsed_response.get("corrections_made", [])

                # Xác thực và fallback
                if not expanded_query or not isinstance(expanded_query, str):
                    expanded_query = preprocessed_query
                    print(f"⚠️ Không có expanded_query hợp lệ, sử dụng preprocessed query")
                
                valid_types = ["question_from_document", "realtime_question", "sql_code_task", "other_question"]
                if query_type not in valid_types:
                    print(f"⚠️ Query type không hợp lệ '{query_type}', mặc định 'question_from_document'")
                    query_type = 'question_from_document'
                
                # Log kết quả
                print(f"✅ QueryHandler thành công:")
                print(f"   📝 Query gốc: '{query}'")
                if preprocessed_query != query:
                    print(f"   🔧 Tiền xử lý: '{preprocessed_query}'")
                print(f"   📈 Query mở rộng: '{expanded_query}'")
                print(f"   🏷️ Loại: '{query_type}'")
                if corrections_made:
                    print(f"   🔧 Sửa đổi: {corrections_made}")
                
                return expanded_query, query_type
            else:
                raise json.JSONDecodeError("Không tìm thấy JSON trong response", response_text, 0)

        except (json.JSONDecodeError, AttributeError, KeyError, TypeError) as e:
            print(f"❌ QueryHandler gặp lỗi: {type(e).__name__}: {e}")
            print(f"🔄 Fallback - Query: '{preprocessed_query}' | Type: 'question_from_document'")
            
            # Fallback nâng cao: ít nhất sử dụng preprocessed query
            return preprocessed_query, 'question_from_document'
        
        except Exception as e:
            print(f"❌ Lỗi không mong muốn: {type(e).__name__}: {e}")
            print(f"🔄 Emergency fallback - Query gốc: '{query}' | Type: 'question_from_document'")
            return query, 'question_from_document'
    
    def get_response_for_other_question(self, query: str) -> str:
        """
        Trả về phản hồi cho các câu hỏi không liên quan đến cơ sở dữ liệu

        Args:
            query: Câu hỏi cần phản hồi

        Returns:
            Phản hồi cố định cho câu hỏi không liên quan
        """
        return """Xin chào! 👋 

Mình là trợ lý AI chuyên về **Cơ sở dữ liệu** và **SQL**. Mình có thể giúp bạn:

🔹 **Học khái niệm**: CSDL, RDBMS, NoSQL, thiết kế cơ sở dữ liệu
🔹 **Viết SQL**: SELECT, INSERT, UPDATE, DELETE, JOIN, subquery
🔹 **Tối ưu hóa**: Index, query optimization, performance tuning  
🔹 **Giải thích**: Phân tích và debug câu lệnh SQL
🔹 **So sánh**: MySQL vs PostgreSQL, SQL vs NoSQL

Bạn có câu hỏi nào về cơ sở dữ liệu không? 😊"""

    def test_preprocessing(self, test_queries: list = None) -> None:
        """
        Hàm test để kiểm tra khả năng preprocessing của QueryHandler
        
        Args:
            test_queries: Danh sách câu hỏi test, nếu None sẽ dùng mặc định
        """
        if test_queries is None:
            test_queries = [
                "Khái niệm hệ quản trị cdld là gì?",
                "select * from bang user",
                "co so du lieu quan tri la gi?", 
                "Tạo bang với khoa chinh",
                "inner join va left join khac nhau nhu the nao?",
                "Backup va restore du lieu",
                "Cách tối ưu truy van sql"
            ]
        
        print("🧪 TESTING QUERY PREPROCESSING:")
        print("=" * 50)
        
        for i, query in enumerate(test_queries, 1):
            processed = self._preprocess_query(query)
            print(f"{i}. '{query}'")
            print(f"   → '{processed}'")
            print()