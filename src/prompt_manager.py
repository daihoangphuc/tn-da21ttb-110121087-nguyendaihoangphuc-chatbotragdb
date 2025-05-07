import re
from typing import List, Dict


class PromptManager:
    """Lớp quản lý các prompt khác nhau cho hệ thống RAG"""

    def __init__(self):
        """Khởi tạo quản lý prompt"""
        self.templates = {
            "definition": """
            Bạn là chuyên gia Cơ sở dữ liệu. Hãy cung cấp định nghĩa chính xác và ngắn gọn cho thuật ngữ sau, 
            kèm theo các khái niệm liên quan nếu cần. Sử dụng ngữ cảnh dưới đây nhưng không trích dẫn trực tiếp.

            Ngữ cảnh:
            {context}

            Thuật ngữ/Câu hỏi: {query}

            Yêu cầu:
            - Định nghĩa rõ ràng, chính xác
            - Giải thích ngắn gọn bằng ví dụ nếu có
            - Liệt kê các khái niệm liên quan
            """,
            "comparison": """
            Bạn là chuyên gia Cơ sở dữ liệu. Hãy so sánh chi tiết các khái niệm được yêu cầu, 
            chỉ rõ sự giống và khác nhau, trường hợp sử dụng phù hợp cho từng loại.

            Ngữ cảnh:
            {context}

            Yêu cầu so sánh: {query}

            Yêu cầu:
            - Liệt kê ít nhất 3 điểm giống nhau
            - Liệt kê ít nhất 3 điểm khác nhau
            - Ví dụ minh họa cho từng trường hợp sử dụng
            - Khuyến nghị khi nào nên dùng cái nào
            """,
            "example": """
            Bạn là chuyên gia Cơ sở dữ liệu. Hãy cung cấp các ví dụ minh họa rõ ràng cho yêu cầu sau.
            Dựa vào ngữ cảnh được cung cấp, giải thích chi tiết từng ví dụ.

            Ngữ cảnh:
            {context}

            Yêu cầu ví dụ: {query}

            Yêu cầu:
            - Cung cấp ít nhất 2-3 ví dụ khác nhau
            - Mỗi ví dụ phải có code cụ thể
            - Giải thích chi tiết từng phần trong ví dụ
            - Nhấn mạnh các điểm quan trọng cần lưu ý
            """,
            "implementation": """
            Bạn là chuyên gia Cơ sở dữ liệu. Hãy hướng dẫn từng bước cách triển khai yêu cầu sau, 
            bao gồm cả mã SQL hoặc NoSQL nếu cần.

            Ngữ cảnh:
            {context}

            Yêu cầu triển khai: {query}

            Yêu cầu:
            - Trình bày từng bước rõ ràng
            - Cung cấp code mẫu nếu cần
            - Giải thích lý do từng bước
            - Cảnh báo các lỗi thường gặp
            """,
            "troubleshooting": """
            Bạn là chuyên gia Cơ sở dữ liệu. Hãy phân tích và giải quyết vấn đề được mô tả dưới đây,
            dựa trên ngữ cảnh được cung cấp.

            Ngữ cảnh:
            {context}

            Vấn đề cần giải quyết: {query}

            Yêu cầu:
            - Phân tích nguyên nhân gốc rễ của vấn đề
            - Đề xuất các giải pháp theo thứ tự ưu tiên
            - Cung cấp code hoặc lệnh để sửa lỗi
            - Giải thích cách ngăn chặn vấn đề tái diễn
            """,
            "theory": """
            Bạn là chuyên gia Cơ sở dữ liệu. Hãy giải thích lý thuyết hoặc nguyên lý liên quan đến chủ đề sau,
            làm rõ các khái niệm cơ bản và nâng cao.

            Ngữ cảnh:
            {context}

            Chủ đề cần giải thích: {query}

            Yêu cầu:
            - Giải thích rõ ràng từ cơ bản đến nâng cao
            - Làm rõ các thuật ngữ chuyên ngành
            - Liên hệ với các khái niệm khác trong CSDL
            - Đề cập đến các trường hợp thực tế
            """,
            "sql_analysis": """
            Bạn là chuyên gia tối ưu hóa SQL. Hãy phân tích và giải thích câu truy vấn SQL sau,
            chỉ ra cách nó hoạt động, hiệu suất, và đề xuất cải tiến nếu có thể.

            Ngữ cảnh:
            {context}

            Câu truy vấn SQL cần phân tích: {query}

            Yêu cầu:
            - Giải thích từng mệnh đề SQL trong truy vấn
            - Mô tả quy trình thực thi của cơ sở dữ liệu
            - Phân tích hiệu suất và điểm nghẽn cổ chai
            - Đề xuất tối ưu hóa cụ thể (index, viết lại truy vấn, v.v.)
            - Cung cấp truy vấn đã tối ưu nếu có thể
            """,
            "sql_generation": """
            Bạn là chuyên gia lập trình SQL. Hãy viết câu truy vấn SQL đáp ứng yêu cầu sau.

            Ngữ cảnh:
            {context}

            Yêu cầu truy vấn: {query}

            Yêu cầu:
            - Viết câu truy vấn SQL rõ ràng, hiệu quả
            - Giải thích logic của truy vấn 
            - Chỉ ra các điểm cần lưu ý (performance, edge cases)
            - Đảm bảo tuân thủ các chuẩn SQL
            """,
            "nosql_design": """
            Bạn là chuyên gia thiết kế NoSQL. Hãy tư vấn thiết kế NoSQL cho yêu cầu được mô tả.

            Ngữ cảnh:
            {context}

            Yêu cầu thiết kế: {query}

            Yêu cầu:
            - Đề xuất loại cơ sở dữ liệu NoSQL phù hợp (document, key-value, column, graph)
            - Mô tả cấu trúc dữ liệu chi tiết
            - Phân tích ưu/nhược điểm của thiết kế
            - Cung cấp ví dụ code hoặc mẫu dữ liệu
            - Lưu ý về khả năng mở rộng và hiệu suất
            """,
            "general": """
            Bạn là chuyên gia trích xuất thông tin chính xác từ tài liệu về Cơ sở dữ liệu. Hãy trả lời câu hỏi sau dựa CHÍNH XÁC trên ngữ cảnh được cung cấp, không thêm bớt thông tin.

            Ngữ cảnh:
            {context}

            Câu hỏi: {query}

            Yêu cầu:
            - PHẢI trung thành tuyệt đối với thông tin trong tài liệu ngữ cảnh
            - PHẢI trích dẫn nguồn cụ thể cho từng phần thông tin quan trọng
            - PHẢI thông báo rõ ràng nếu không có đủ thông tin để trả lời câu hỏi
            - KHÔNG thêm thông tin từ kiến thức của riêng bạn
            - KHÔNG suy diễn quá mức từ ngữ cảnh được cung cấp
            - Tổ chức nội dung rõ ràng, dễ hiểu
            """,
        }

        self.question_types = {
            "definition": r"(định nghĩa|khái niệm|là gì|what is|define)",
            "comparison": r"(so sánh|khác biệt|giống nhau|difference between|compare)",
            "example": r"(ví dụ|minh họa|example|demonstrate)",
            "implementation": r"(cách thức|cài đặt|triển khai|how to|implement|code)",
            "troubleshooting": r"(lỗi|sửa|fix|troubleshoot|error)",
            "theory": r"(nguyên lý|lý thuyết|theory|principle)",
            "sql_analysis": r"(phân tích|explain|analyze|tối ưu|optimize|hiệu suất|performance)[\s\w]+(query|truy vấn|sql)",
            "sql_generation": r"(viết|tạo|generate|write|code)[\s\w]+(query|truy vấn|sql)",
            "nosql_design": r"(thiết kế|design)[\s\w]+(nosql|mongodb|redis|cassandra)",
        }

    def classify_question(self, query: str) -> str:
        """Phân loại câu hỏi"""
        query_lower = query.lower()

        # Kiểm tra xem có chứa mã SQL không
        if re.search(r"SELECT\s+.*\s+FROM\s+.*", query, re.IGNORECASE):
            return "sql_analysis"

        # Phân loại dựa trên pattern
        for q_type, pattern in self.question_types.items():
            if re.search(pattern, query_lower):
                return q_type

        return "general"

    def create_prompt(
        self, query: str, context: List[Dict], question_type: str = None
    ) -> str:
        """Tạo prompt phù hợp với loại câu hỏi"""
        # Nếu không có loại câu hỏi, hãy phân loại
        if question_type is None:
            question_type = self.classify_question(query)

        # Tạo văn bản ngữ cảnh từ các tài liệu đã truy xuất - sử dụng tất cả kết quả được cung cấp
        context_str = "\n\n".join(
            [
                f"Source: {doc['metadata'].get('source', 'unknown')}\n"
                + f"Page/Position: {doc['metadata'].get('page', 'unknown')}\n"
                + f"Section: {doc['metadata'].get('chunk_type', 'unknown')}\n"
                + f"Category: {doc['metadata'].get('category', 'general')}\n"
                + f"Content: {doc['text']}"
                for doc in context
            ]
        )

        # Thêm hướng dẫn chặt chẽ để đảm bảo độ trung thực
        strict_instruction = """
        HƯỚNG DẪN NGHIÊM NGẶT:
        1. CHỈ sử dụng thông tin từ các tài liệu được cung cấp ở trên để trả lời.
        2. KHÔNG được thêm vào bất kỳ thông tin nào từ kiến thức cá nhân, trừ khi để giải thích bối cảnh hoặc đơn giản hóa.
        3. Nếu tài liệu không chứa đủ thông tin để trả lời đầy đủ, hãy chỉ trả lời phần bạn CÓ THỂ trả lời từ tài liệu và nêu rõ phần nào chưa được đề cập.
        4. Nếu tài liệu không chứa THÔNG TIN NÀO liên quan đến câu hỏi, hãy nói rõ "Tài liệu không chứa thông tin về chủ đề này."
        5. Nêu rõ nguồn của từng phần thông tin trong câu trả lời bằng cách đề cập đến tên tài liệu, trang/vị trí, và phần cụ thể, ví dụ: [Tài liệu.pdf, Trang 5, Phần Table].
        """

        # Thêm hướng dẫn về định dạng Markdown
        markdown_instruction = """
        ĐỊNH DẠNG MARKDOWN:
        Hãy định dạng câu trả lời của bạn bằng Markdown để dễ hiển thị ở frontend:
        - Sử dụng **in đậm** cho các thuật ngữ và điểm quan trọng
        - Sử dụng *in nghiêng* cho các nhấn mạnh
        - Sử dụng ## cho tiêu đề cấp 2, ### cho tiêu đề cấp 3
        - Sử dụng danh sách có dấu gạch đầu dòng (- item) hoặc số (1. item)
        - Sử dụng ```code``` cho các đoạn mã, lệnh SQL, cú pháp
        - Sử dụng bảng Markdown khi cần so sánh thông tin
        - Sử dụng > cho các trích dẫn
        - Khi trích dẫn thông tin, hãy sử dụng định dạng: **[Nguồn: Tài liệu, Trang X, Phần Y]**
        
        Đảm bảo câu trả lời có cấu trúc rõ ràng, dễ đọc và trực quan.
        """

        # Lấy template phù hợp hoặc sử dụng template chung
        template = self.templates.get(question_type, self.templates["general"])

        # Điền vào template và thêm các hướng dẫn
        prompt = template.format(context=context_str, query=query)
        prompt += strict_instruction
        prompt += markdown_instruction

        return prompt

    def detect_sql_query(self, text: str) -> bool:
        """Phát hiện xem văn bản có chứa câu truy vấn SQL không"""
        # Pattern cơ bản cho SELECT, INSERT, UPDATE, DELETE query
        sql_patterns = [
            r"SELECT\s+.+\s+FROM\s+.+",
            r"INSERT\s+INTO\s+.+\s+VALUES\s*\(.+\)",
            r"UPDATE\s+.+\s+SET\s+.+",
            r"DELETE\s+FROM\s+.+",
            r"CREATE\s+TABLE\s+.+",
            r"ALTER\s+TABLE\s+.+",
        ]

        for pattern in sql_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def extract_sql_query(self, text: str) -> str:
        """Trích xuất câu truy vấn SQL từ văn bản"""
        # Tìm đoạn mã SQL trong văn bản
        sql_blocks = re.findall(r"```sql\s*([\s\S]*?)\s*```", text, re.IGNORECASE)

        if sql_blocks:
            return sql_blocks[0].strip()

        # Thử tìm kiểu khác
        for pattern in [
            r"SELECT\s+.+\s+FROM.+?;",
            r"INSERT\s+INTO\s+.+?;",
            r"UPDATE\s+.+?;",
            r"DELETE\s+FROM\s+.+?;",
        ]:
            matches = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if matches:
                return matches.group(0).strip()

        return ""
