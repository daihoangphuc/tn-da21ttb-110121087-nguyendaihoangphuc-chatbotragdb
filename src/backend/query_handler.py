import logging
import json
import re
from typing import Tuple, Dict
from backend.llm import GeminiLLM
import asyncio

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
    Hỗ trợ async đầy đủ.
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
             - Cú pháp, cấu trúc lệnh SQL (ý nghĩa, mục đích, quy tắc)
             - Thiết kế CSDL, mô hình dữ liệu
             - Giải thích lý thuyết về lệnh SQL (không có code cụ thể)
             - Ví dụ: "CSDL là gì?", "Khóa chính và khóa ngoại khác nhau như thế nào?", "Cú pháp lệnh SELECT là gì?"

           • **`realtime_question`**: Câu hỏi về xu hướng/tin tức/thông tin cập nhật mới
             - Có từ khóa thời gian: "hiện tại", "mới nhất", "2024", "gần đây", "hiện nay"
             - KẾT HỢP với ý định tìm hiểu xu hướng/tin tức/cập nhật mới
             - Xu hướng công nghệ, phiên bản mới, thống kê thị trường
             - Ví dụ: "Xu hướng CSDL hiện tại", "PostgreSQL 16 có gì mới?", "CSDL nào phổ biến nhất hiện nay?"
             
             **CHÚ Ý**: Phân biệt với câu hỏi cơ bản:
             - "Các loại CSDL" = question_from_document (hỏi phân loại cơ bản)
             - "CSDL nào đang thịnh hành hiện nay" = realtime_question (hỏi xu hướng)

        **QUAN TRỌNG - PHÂN BIỆT question_from_document vs sql_code_task:**
        - "Cú pháp lệnh SELECT là gì?" = question_from_document (hỏi lý thuyết)
        - "Viết lệnh SELECT lấy dữ liệu" = sql_code_task (yêu cầu code)
        - "Các mệnh đề của SELECT" = question_from_document (hỏi kiến thức)  
        - "SELECT * FROM table WHERE..." = sql_code_task (có code cụ thể)

           • **`sql_code_task`**: Yêu cầu trực tiếp về code SQL CỤ THỂ
             - Viết/tạo câu lệnh SQL hoàn chỉnh
             - Giải thích/phân tích code SQL CÓ SẴN (có đoạn code cụ thể)
             - Debug/tối ưu hóa SQL với code thực tế
             - Tạo ví dụ code SQL minh họa
             - **GIẢI BÀI TẬP CSDL** (dạng chuẩn, phụ thuộc hàm, thiết kế ER...)
             - **PHÂN TÍCH TỪNG BƯỚC** các bài toán CSDL cụ thể
             - Ví dụ: "Viết SQL tạo bảng User", "Giải bài tập xác định dạng chuẩn", "Tìm khóa chính cho lược đồ này"

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

        Input: "Cú pháp lệnh SELECT là gì?"
        ```json
        {{
          "expanded_query": "Cú pháp và chức năng của lệnh SELECT trong SQL là gì?",
          "query_type": "question_from_document",
          "corrections_made": []
        }}
        ```

        Input: "Viết lệnh SELECT lấy tất cả user"
        ```json
        {{
          "expanded_query": "Viết câu lệnh SQL SELECT để lấy tất cả thông tin người dùng",
          "query_type": "sql_code_task",
          "corrections_made": []
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

        **CÂU HỎI HIỆN TẠI:** {query}

        Hãy trả về JSON chính xác với 3 trường như mô tả trên:
        """

        return prompt

    async def expand_and_classify_query(self, query: str, conversation_history: str) -> Tuple[str, str]:
        """
        Mở rộng và phân loại câu hỏi bằng LLM một lần duy nhất (bất đồng bộ)
        
        Args:
            query: Câu hỏi gốc từ người dùng
            conversation_history: Lịch sử hội thoại để cung cấp ngữ cảnh
            
        Returns:
            Tuple của (expanded_query, query_type)
        """
        print(f"🔄 Bắt đầu xử lý và phân loại query: '{query[:50]}...'")
        
        # Bước 1: Tiền xử lý cơ bản
        preprocessed_query = self._preprocess_query(query)
        
        # Bước 2: Tạo prompt và gọi LLM
        enhanced_prompt = self._create_enhanced_prompt(preprocessed_query, conversation_history)
        
        try:
            # Gọi LLM bất đồng bộ
            response = await self.llm.invoke(enhanced_prompt)
            response_text = response.content.strip()
            print(f"📝 Raw LLM response: {response_text[:200]}...")
            
            # Bước 3: Parse JSON response
            # Tìm JSON trong response (có thể có text phụ xung quanh)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                expanded_query = result.get("expanded_query", preprocessed_query)
                query_type = result.get("query_type", "question_from_document")
                corrections_made = result.get("corrections_made", [])
                
                print(f"✅ Expanded query: '{expanded_query}'")
                print(f"🏷️ Query type: {query_type}")
                if corrections_made:
                    print(f"🔧 Corrections made: {corrections_made}")
                
                return expanded_query, query_type
                
            else:
                print("⚠️ Không tìm thấy JSON trong response, sử dụng giá trị mặc định")
                return preprocessed_query, "question_from_document"
                
        except json.JSONDecodeError as e:
            print(f"⚠️ Lỗi parse JSON: {e}, sử dụng giá trị mặc định")
            return preprocessed_query, "question_from_document"
            
        except Exception as e:
            print(f"⚠️ Lỗi khi gọi LLM: {e}, sử dụng giá trị mặc định")
            return preprocessed_query, "question_from_document"

    def expand_and_classify_query_sync(self, query: str, conversation_history: str) -> Tuple[str, str]:
        """
        Mở rộng và phân loại câu hỏi bằng LLM một lần duy nhất (đồng bộ - để tương thích ngược)
        
        Args:
            query: Câu hỏi gốc từ người dùng
            conversation_history: Lịch sử hội thoại để cung cấp ngữ cảnh
            
        Returns:
            Tuple của (expanded_query, query_type)
        """
        print(f"🔄 Bắt đầu xử lý và phân loại query: '{query[:50]}...'")
        
        # Bước 1: Tiền xử lý cơ bản
        preprocessed_query = self._preprocess_query(query)
        
        # Bước 2: Tạo prompt và gọi LLM
        enhanced_prompt = self._create_enhanced_prompt(preprocessed_query, conversation_history)
        
        try:
            # Gọi LLM đồng bộ
            response = self.llm.invoke_sync(enhanced_prompt)
            response_text = response.content.strip()
            print(f"📝 Raw LLM response: {response_text[:200]}...")
            
            # Bước 3: Parse JSON response
            # Tìm JSON trong response (có thể có text phụ xung quanh)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                expanded_query = result.get("expanded_query", preprocessed_query)
                query_type = result.get("query_type", "question_from_document")
                corrections_made = result.get("corrections_made", [])
                
                print(f"✅ Expanded query: '{expanded_query}'")
                print(f"🏷️ Query type: {query_type}")
                if corrections_made:
                    print(f"🔧 Corrections made: {corrections_made}")
                
                return expanded_query, query_type
                
            else:
                print("⚠️ Không tìm thấy JSON trong response, sử dụng giá trị mặc định")
                return preprocessed_query, "question_from_document"
                
        except json.JSONDecodeError as e:
            print(f"⚠️ Lỗi parse JSON: {e}, sử dụng giá trị mặc định")
            return preprocessed_query, "question_from_document"
            
        except Exception as e:
            print(f"⚠️ Lỗi khi gọi LLM: {e}, sử dụng giá trị mặc định")
            return preprocessed_query, "question_from_document"

    async def get_response_for_other_question(self, query: str) -> str:
        """
        Tạo phản hồi lịch sự cho những câu hỏi không liên quan đến lĩnh vực CSDL (bất đồng bộ)
        
        Args:
            query: Câu hỏi của người dùng
            
        Returns:
            Phản hồi lịch sự hướng dẫn người dùng quay lại chủ đề CSDL
        """
        default_response = f"""
        Xin chào! Tôi là DBR - chatbot chuyên về cơ sở dữ liệu. 

        Câu hỏi của bạn: "{query}" có vẻ không liên quan đến lĩnh vực cơ sở dữ liệu mà tôi được đào tạo để hỗ trợ.

        Tôi có thể giúp bạn với:
        • Các khái niệm về cơ sở dữ liệu
        • Thiết kế và chuẩn hóa CSDL  
        • Ngôn ngữ SQL và các truy vấn
        • Hệ quản trị CSDL (MySQL, PostgreSQL, MongoDB...)
        • Tối ưu hóa hiệu suất và bảo mật

        Bạn có muốn hỏi gì về cơ sở dữ liệu không? Tôi sẽ rất vui được hỗ trợ! 😊
        """
        return default_response

    def get_response_for_other_question_sync(self, query: str) -> str:
        """
        Tạo phản hồi lịch sự cho những câu hỏi không liên quan đến lĩnh vực CSDL (đồng bộ)
        
        Args:
            query: Câu hỏi của người dùng
            
        Returns:
            Phản hồi lịch sự hướng dẫn người dùng quay lại chủ đề CSDL
        """
        default_response = f"""
        Xin chào! Tôi là DBR - chatbot chuyên về cơ sở dữ liệu. 

        Câu hỏi của bạn: "{query}" có vẻ không liên quan đến lĩnh vực cơ sở dữ liệu mà tôi được đào tạo để hỗ trợ.

        Tôi có thể giúp bạn với:
        • Các khái niệm về cơ sở dữ liệu
        • Thiết kế và chuẩn hóa CSDL  
        • Ngôn ngữ SQL và các truy vấn
        • Hệ quản trị CSDL (MySQL, PostgreSQL, MongoDB...)
        • Tối ưu hóa hiệu suất và bảo mật

        Bạn có muốn hỏi gì về cơ sở dữ liệu không? Tôi sẽ rất vui được hỗ trợ! 😊
        """
        return default_response

    def test_preprocessing(self, test_queries=None) -> None:
        """
        Test phương thức tiền xử lý với một số câu hỏi mẫu
        
        Args:
            test_queries: Danh sách câu hỏi để test, nếu None sẽ dùng mẫu có sẵn
        """
        if test_queries is None:
            test_queries = [
                "Làm thế nào để tạo bảng trong mysql?",
                "Cách tạo cdld mới",
                "co so du lieu la gi?",
                "quan tri csdl khac gi voi DBMS?",
                "select * from bang nao do",
                "inner join vs left join",
            ]
            
        print("🧪 Testing query preprocessing:")
        print("=" * 50)
        
        for query in test_queries:
            processed = self._preprocess_query(query)
            print(f"Original:  {query}")
            print(f"Processed: {processed}")
            print("-" * 30)

    def test_classification(self, test_queries=None) -> float:
        """
        Test phương thức phân loại với các câu hỏi mẫu để kiểm tra độ chính xác
        
        Args:
            test_queries: Danh sách tuple (query, expected_type), nếu None sẽ dùng mẫu có sẵn
        """
        if test_queries is None:
            test_queries = [
                # question_from_document
                ("CSDL là gì?", "question_from_document"),
                ("Cú pháp lệnh SELECT là gì?", "question_from_document"),
                ("Khóa chính và khóa ngoại khác nhau như thế nào?", "question_from_document"),
                ("Các mệnh đề thường dùng với SELECT", "question_from_document"),
                ("Mô hình quan hệ có ưu nhược điểm gì?", "question_from_document"),
                
                # sql_code_task
                ("Viết lệnh SELECT lấy tất cả user", "sql_code_task"),
                ("Tạo bảng sinh viên với SQL", "sql_code_task"),
                ("Giải thích query này: SELECT * FROM users WHERE age > 18", "sql_code_task"),
                ("Tối ưu hóa câu lệnh SQL này", "sql_code_task"),
                
                # realtime_question
                ("Xu hướng CSDL hiện tại là gì?", "realtime_question"),
                ("PostgreSQL 16 có gì mới?", "realtime_question"),
                ("CSDL nào phổ biến nhất 2024?", "realtime_question"),
                ("Công nghệ database nào đang hot hiện nay?", "realtime_question"),
                
                # other_question
                ("Thời tiết hôm nay thế nào?", "other_question"),
                ("Cách nấu phở", "other_question"),
                ("Kết quả bóng đá", "other_question"),
            ]
            
        print("🧪 Testing query classification:")
        print("=" * 80)
        
        correct_predictions = 0
        total_predictions = len(test_queries)
        
        for query, expected_type in test_queries:
            try:
                expanded_query, predicted_type = self.expand_and_classify_query_sync(query, "")
                
                is_correct = predicted_type == expected_type
                if is_correct:
                    correct_predictions += 1
                    status = "✅ ĐÚNG"
                else:
                    status = "❌ SAI"
                
                print(f"{status} | Query: {query}")
                print(f"      | Expected: {expected_type}")
                print(f"      | Predicted: {predicted_type}")
                print(f"      | Expanded: {expanded_query}")
                print("-" * 60)
                
            except Exception as e:
                print(f"❌ LỖI | Query: {query}")
                print(f"      | Error: {e}")
                print("-" * 60)
        
        accuracy = (correct_predictions / total_predictions) * 100
        print(f"\n📊 KẾT QUẢ TỔNG KẾT:")
        print(f"   Độ chính xác: {correct_predictions}/{total_predictions} ({accuracy:.1f}%)")
        
        if accuracy >= 90:
            print("   🎉 Excellent! Classification working very well")
        elif accuracy >= 75:
            print("   👍 Good! Some edge cases need improvement")
        elif accuracy >= 60:
            print("   ⚠️  Fair! Significant improvements needed")
        else:
            print("   🚨 Poor! Major issues with classification")
        
        return accuracy