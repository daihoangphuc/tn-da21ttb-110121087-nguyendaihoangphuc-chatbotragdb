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
            - Bắt đầu bằng một định nghĩa ngắn gọn và rõ ràng, sử dụng **in đậm**
            - Sử dụng cấu trúc tiêu đề ## và ### để tổ chức nội dung
            - Nếu là một khái niệm phức tạp, hãy chia thành các phần nhỏ với tiêu đề rõ ràng
            - Liệt kê các khái niệm liên quan bằng danh sách có dấu gạch đầu dòng
            - Nếu có ví dụ sql, đặt trong khối ```sql và ```
            - Nếu cần so sánh, sử dụng bảng Markdown
            - Trích dẫn nguồn cho mỗi phần thông tin
            """,
            "comparison": """
            Bạn là chuyên gia Cơ sở dữ liệu. Hãy so sánh chi tiết các khái niệm được yêu cầu, 
            chỉ rõ sự giống và khác nhau, trường hợp sử dụng phù hợp cho từng loại.

            Ngữ cảnh:
            {context}

            Yêu cầu so sánh: {query}

            Yêu cầu:
            - Sử dụng cấu trúc tiêu đề ## và ### để tổ chức nội dung
            - Bắt đầu bằng giới thiệu ngắn về các khái niệm được so sánh
            - PHẢI sử dụng bảng Markdown cho phần so sánh chính như sau:
              | Đặc điểm | Khái niệm 1 | Khái niệm 2 |
              |----------|-------------|-------------|
              | Đặc điểm 1 | Mô tả 1 | Mô tả 2 |
            - Các ví dụ code PHẢI được đặt trong khối ```sql (hoặc ngôn ngữ khác) và ```
            - Trình bày điểm mạnh và điểm yếu của mỗi khái niệm bằng danh sách có dấu gạch đầu dòng
            - Có phần kết luận rõ ràng và khuyến nghị sử dụng
            - Trích dẫn nguồn cho mỗi phần thông tin
            """,
            "example": """
            Bạn là chuyên gia Cơ sở dữ liệu. Hãy cung cấp các ví dụ minh họa rõ ràng cho yêu cầu sau.
            Dựa vào ngữ cảnh được cung cấp, giải thích chi tiết từng ví dụ.

            Ngữ cảnh:
            {context}

            Yêu cầu ví dụ: {query}

            Yêu cầu:
            - Sử dụng tiêu đề ## cho tiêu đề chính và ### cho từng ví dụ
            - Mỗi ví dụ PHẢI có:
              1. Mô tả ngắn gọn về mục đích
              2. Mã code đặt trong khối ```sql (hoặc ngôn ngữ tương ứng) và ```
              3. Giải thích chi tiết từng dòng code hoặc mỗi phần của ví dụ
              4. Kết quả đầu ra hoặc hiệu ứng (nếu có thể)
            - Nếu có nhiều bước, sử dụng danh sách có số để liệt kê các bước
            - Sử dụng **in đậm** cho các thuật ngữ và điểm quan trọng
            - Đánh dấu các lưu ý quan trọng bằng > để nhấn mạnh
            - Trích dẫn nguồn cho mỗi phần thông tin
            """,
            "implementation": """
            Bạn là chuyên gia Cơ sở dữ liệu. Hãy hướng dẫn từng bước cách triển khai yêu cầu sau, 
            bao gồm cả mã SQL hoặc NoSQL nếu cần.

            Ngữ cảnh:
            {context}

            Yêu cầu triển khai: {query}

            Yêu cầu:
            - Sử dụng tiêu đề ## cho tiêu đề chính và ### cho mỗi phần/bước chính
            - Bắt đầu bằng tổng quan ngắn gọn về cách tiếp cận
            - Liệt kê các bước thực hiện bằng danh sách có số (1. 2. 3.)
            - Mỗi bước PHẢI:
              + Được giải thích rõ ràng
              + Có mã code mẫu nếu cần (đặt trong khối ```sql và ```)
              + Chú thích cho mã code phức tạp
            - Nếu có nhiều cách tiếp cận, sử dụng tiêu đề riêng cho mỗi cách và so sánh ưu/nhược điểm
            - Sử dụng > để đánh dấu các cảnh báo và lưu ý quan trọng
            - Trích dẫn nguồn cho mỗi phần thông tin
            """,
            "troubleshooting": """
            Bạn là chuyên gia Cơ sở dữ liệu. Hãy phân tích và giải quyết vấn đề được mô tả dưới đây,
            dựa trên ngữ cảnh được cung cấp.

            Ngữ cảnh:
            {context}

            Vấn đề cần giải quyết: {query}

            Yêu cầu:
            - Sử dụng tiêu đề ## cho tiêu đề chính và ### cho mỗi phần
            - Bắt đầu bằng phần **Phân tích vấn đề** để xác định nguyên nhân gốc rễ
            - Sử dụng phần **Giải pháp** với danh sách có số theo thứ tự ưu tiên
            - Mỗi giải pháp PHẢI có:
              1. Mô tả rõ ràng
              2. Mã code hoặc lệnh cụ thể (đặt trong khối ```sql và ```)
              3. Giải thích tại sao nó hoạt động
            - Thêm phần **Phòng ngừa** để giải thích cách ngăn chặn vấn đề tái diễn
            - Sử dụng bảng khi so sánh các giải pháp khác nhau
            - Trích dẫn nguồn cho mỗi phần thông tin
            """,
            "theory": """
            Bạn là chuyên gia Cơ sở dữ liệu. Hãy giải thích lý thuyết hoặc nguyên lý liên quan đến chủ đề sau,
            làm rõ các khái niệm cơ bản và nâng cao.

            Ngữ cảnh:
            {context}

            Chủ đề cần giải thích: {query}

            Yêu cầu:
            - Sử dụng cấu trúc tiêu đề ## cho tiêu đề chính và ### cho các khái niệm hoặc phần nhỏ
            - Bắt đầu bằng **tổng quan** ngắn gọn về lý thuyết/nguyên lý
            - Chia thành các phần rõ ràng với tiêu đề riêng (Khái niệm cơ bản, Cơ chế hoạt động, Ứng dụng...)
            - Sử dụng `định dạng code` cho thuật ngữ kỹ thuật và từ khóa
            - Sử dụng danh sách có dấu gạch đầu dòng để liệt kê các điểm chính
            - Đưa ra ví dụ minh họa cho các khái niệm phức tạp (đặt code trong khối ```sql và ```)
            - Sử dụng bảng Markdown để so sánh các khái niệm khi cần
            - Có phần tổng kết và liên hệ với các khái niệm khác
            - Trích dẫn nguồn cho mỗi phần thông tin
            """,
            "sql_analysis": """
            Bạn là chuyên gia tối ưu hóa SQL. Hãy phân tích và giải thích câu truy vấn SQL sau,
            chỉ ra cách nó hoạt động, hiệu suất, và đề xuất cải tiến nếu có thể.

            Ngữ cảnh:
            {context}

            Câu truy vấn SQL cần phân tích: {query}

            Yêu cầu:
            - Sử dụng tiêu đề ## cho tiêu đề chính và ### cho mỗi phần phân tích
            - Bắt đầu bằng khối code đầy đủ của truy vấn gốc đặt trong ```sql và ```
            - Phần **Phân tích cấu trúc**:
              + Chia truy vấn thành từng phần
              + Giải thích chi tiết mỗi mệnh đề (SELECT, FROM, JOIN, WHERE...) 
              + Chú thích rõ ràng từng phần
            - Phần **Phân tích hiệu suất**:
              + Xác định các điểm nghẽn cổ chai tiềm năng
              + Phân tích hiệu suất của mỗi phần
              + Sử dụng danh sách cho các vấn đề hiệu suất
            - Phần **Đề xuất tối ưu hóa**:
              + Liệt kê các đề xuất cụ thể
              + Cung cấp truy vấn đã tối ưu trong khối ```sql và ```
              + Giải thích lý do cho mỗi thay đổi
            - Sử dụng bảng để so sánh trước và sau khi tối ưu nếu cần
            - Trích dẫn nguồn cho mỗi phần thông tin
            """,
            "sql_generation": """
            Bạn là chuyên gia lập trình SQL. Hãy viết câu truy vấn SQL đáp ứng yêu cầu sau.

            Ngữ cảnh:
            {context}

            Yêu cầu truy vấn: {query}

            Yêu cầu:
            - Sử dụng tiêu đề ## cho tiêu đề chính
            - Bắt đầu bằng phần **Phân tích yêu cầu** ngắn gọn
            - Cung cấp câu truy vấn SQL trong khối ```sql và ```
            - Thêm chú thích cho mỗi phần quan trọng của truy vấn (sử dụng -- trong mã SQL)
            - Phần **Giải thích chi tiết**:
              + Giải thích từng mệnh đề và logic
              + Sử dụng danh sách có số cho các bước logic xử lý
            - Phần **Lưu ý về hiệu suất**:
              + Sử dụng danh sách có dấu gạch đầu dòng
              + Nhấn mạnh các điểm cần lưu ý
            - Nếu có thể, cung cấp ví dụ kết quả đầu ra dưới dạng bảng Markdown:
              | Cột 1 | Cột 2 | ... |
              |-------|-------|-----|
              | Giá trị | Giá trị | ... |
            - Trích dẫn nguồn cho mỗi phần thông tin
            """,
            "nosql_design": """
            Bạn là chuyên gia thiết kế NoSQL. Hãy tư vấn thiết kế NoSQL cho yêu cầu được mô tả.

            Ngữ cảnh:
            {context}

            Yêu cầu thiết kế: {query}

            Yêu cầu:
            - Sử dụng tiêu đề ## cho tiêu đề chính và ### cho mỗi phần thiết kế
            - Bắt đầu bằng phần **Phân tích yêu cầu** ngắn gọn
            - Phần **Đề xuất loại NoSQL**:
              + Xác định rõ loại NoSQL phù hợp nhất (document, key-value, column, graph)
              + Giải thích lý do lựa chọn
              + So sánh với các lựa chọn khác bằng bảng Markdown
            - Phần **Thiết kế cấu trúc dữ liệu**:
              + Mô tả chi tiết schema/cấu trúc
              + Cung cấp ví dụ JSON hoặc cấu trúc dữ liệu trong khối ```json và ```
            - Phần **Phân tích hiệu suất**:
              + Sử dụng danh sách có dấu gạch đầu dòng cho ưu điểm
              + Sử dụng danh sách có dấu gạch đầu dòng cho nhược điểm
            - Phần **Khả năng mở rộng**:
              + Giải thích chiến lược mở rộng
              + Lưu ý về các thách thức tiềm ẩn
            - Trích dẫn nguồn cho mỗi phần thông tin
            """,
            "general": """
            Bạn là chuyên gia trích xuất thông tin chính xác từ tài liệu về Cơ sở dữ liệu. Hãy trả lời câu hỏi sau dựa CHÍNH XÁC trên ngữ cảnh được cung cấp, không thêm bớt thông tin.

            Ngữ cảnh:
            {context}

            Câu hỏi: {query}

            Yêu cầu:
            - Sử dụng tiêu đề ## cho tiêu đề chính và ### cho các phần nhỏ nếu cần
            - PHẢI trung thành tuyệt đối với thông tin trong tài liệu ngữ cảnh
            - PHẢI trích dẫn nguồn cụ thể cho từng phần thông tin quan trọng
            - Tổ chức nội dung theo cấu trúc rõ ràng và logic:
              + Câu trả lời trực tiếp cho câu hỏi ở đầu tiên
              + Giải thích chi tiết với các tiêu đề phù hợp
              + Ví dụ minh họa nếu có (code trong khối ```sql và ```)
              + Thông tin bổ sung có liên quan
            - Sử dụng bảng Markdown cho dữ liệu có cấu trúc
            - Sử dụng danh sách cho các mục có liên quan
            - KHÔNG thêm thông tin từ kiến thức của riêng bạn
            - KHÔNG suy diễn quá mức từ ngữ cảnh được cung cấp
            - PHẢI thông báo rõ ràng nếu không có đủ thông tin để trả lời câu hỏi
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
        QUY ĐỊNH ĐỊNH DẠNG PHẢN HỒI (QUAN TRỌNG - PHẢI TUÂN THỦ):
        Bạn PHẢI định dạng câu trả lời theo các quy tắc sau:

        1. TIÊU ĐỀ VÀ CẤU TRÚC:
           - Sử dụng ## cho tiêu đề chính của câu trả lời
           - Sử dụng ### cho các phần, mục nhỏ
           - Mỗi phần phải có cấu trúc rõ ràng với tiêu đề riêng

        2. MÃ SQL VÀ MÃ LỆNH (QUAN TRỌNG):
           - LUÔN đặt mã SQL/code trong khối lệnh với 3 dấu backtick và chỉ định ngôn ngữ:
             ```sql
             SELECT * FROM customers WHERE customer_id = 1;
             ```
           - Đối với các truy vấn SQL phức tạp, PHẢI thêm chú thích vào các dòng quan trọng:
             ```sql
             SELECT c.customer_name, o.order_date
             FROM customers c         -- Bảng khách hàng
             JOIN orders o            -- Kết nối với bảng đơn hàng
             ON c.customer_id = o.customer_id
             WHERE o.order_amount > 1000;
             ```

        3. BẢNG (QUAN TRỌNG):
           - Khi cần trình bày dữ liệu dạng bảng, LUÔN sử dụng cú pháp bảng Markdown:
             | Cột 1 | Cột 2 | Cột 3 |
             |-------|-------|-------|
             | Dữ liệu 1 | Dữ liệu 2 | Dữ liệu 3 |
           - PHẢI căn chỉnh các cột cho dễ đọc
           - PHẢI có hàng ngăn cách tiêu đề và nội dung

        4. DANH SÁCH VÀ LIỆT KÊ (QUAN TRỌNG):
           - Sử dụng danh sách có số cho các bước tuần tự:
             1. Bước thứ nhất
             2. Bước thứ hai
           - Sử dụng danh sách có dấu gạch đầu dòng cho các mục không theo thứ tự:
             - Mục thứ nhất
             - Mục thứ hai
           - Sử dụng danh sách lồng nhau khi cần:
             - Mục chính
               - Mục con

        5. NHẤN MẠNH (QUAN TRỌNG):
           - Sử dụng **in đậm** cho các thuật ngữ quan trọng và điểm chính
           - Sử dụng *in nghiêng* cho các nhấn mạnh nhẹ hoặc thuật ngữ tiếng nước ngoài
           - Sử dụng `highlight` cho các tên biến, lệnh ngắn hoặc từ khóa SQL

        6. TRÍCH DẪN (BẮT BUỘC):
           - Khi trích dẫn thông tin PHẢI sử dụng định dạng: **[Nguồn: Tài liệu, Trang X, Phần Y]**
           - Sử dụng ký hiệu > cho các trích dẫn dài từ tài liệu:
             > Đây là đoạn trích dẫn từ tài liệu gốc...

        7. SO SÁNH VÀ ĐỐI CHIẾU (QUAN TRỌNG):
           - Khi so sánh hai hoặc nhiều đối tượng, PHẢI dùng bảng:
             | Đặc điểm | MySQL | PostgreSQL |
             |----------|-------|------------|
             | Hiệu suất | Tốt với ứng dụng đọc nhiều | Tốt với ứng dụng ghi nhiều |
           - Hoặc sử dụng danh sách có cấu trúc:
             - **MySQL**: 
               - Ưu điểm: dễ cài đặt, hiệu suất tốt với ứng dụng đọc nhiều
               - Nhược điểm: hỗ trợ hạn chế cho các tính năng nâng cao
        
        QUAN TRỌNG: Bạn PHẢI tuân theo các quy tắc định dạng trên trong MỌI câu trả lời. Hãy đảm bảo câu trả lời của bạn có cấu trúc rõ ràng, dễ đọc và chuyên nghiệp.
        """

        # Lấy template phù hợp hoặc sử dụng template chung
        template = self.templates.get(question_type, self.templates["general"])

        # Thêm hướng dẫn bổ sung cho các loại câu hỏi đặc biệt
        additional_instructions = ""

        # Thêm hướng dẫn bổ sung dựa trên loại câu hỏi
        if question_type == "sql_analysis" or question_type == "sql_generation":
            additional_instructions = """
            HƯỚNG DẪN BỔ SUNG CHO SQL:
            - PHẢI đặt tất cả mã SQL trong khối ```sql và ```
            - PHẢI chú thích từng phần của truy vấn phức tạp
            - PHẢI giải thích chi tiết cách hoạt động của mỗi mệnh đề SQL
            - Nếu có thể, hãy cung cấp ví dụ kết quả đầu ra dạng bảng
            """
        elif question_type == "comparison":
            additional_instructions = """
            HƯỚNG DẪN BỔ SUNG CHO SO SÁNH:
            - PHẢI trình bày phần so sánh dưới dạng bảng Markdown
            - PHẢI liệt kê rõ ràng các điểm giống và khác nhau
            - PHẢI tổng kết lại các điểm chính của so sánh
            """
        elif question_type == "example":
            additional_instructions = """
            HƯỚNG DẪN BỔ SUNG CHO VÍ DỤ:
            - PHẢI trình bày mã và lệnh trong khối ```
            - PHẢI giải thích chi tiết từng bước trong ví dụ
            - PHẢI sử dụng tiêu đề rõ ràng để phân biệt các ví dụ khác nhau
            """
        elif question_type == "definition" or question_type == "theory":
            additional_instructions = """
            HƯỚNG DẪN BỔ SUNG CHO ĐỊNH NGHĨA/LÝ THUYẾT:
            - PHẢI bắt đầu bằng định nghĩa ngắn gọn được in đậm
            - PHẢI tổ chức nội dung theo tiêu đề và danh mục
            - PHẢI sử dụng ví dụ để minh họa khi cần thiết
            """

        # Điền vào template và thêm các hướng dẫn
        prompt = template.format(context=context_str, query=query)
        prompt += strict_instruction
        prompt += markdown_instruction
        prompt += additional_instructions

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

    def create_prompt_with_history(
        self,
        query: str,
        context: List[Dict],
        question_type: str = None,
        conversation_history: str = "",
    ) -> str:
        """Tạo prompt phù hợp với loại câu hỏi, kèm theo lịch sử hội thoại"""
        # Nếu không có loại câu hỏi, hãy phân loại
        if question_type is None:
            question_type = self.classify_question(query)

        # Tạo văn bản ngữ cảnh từ các tài liệu đã truy xuất
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
        6. SỬ DỤNG NGỮ CẢNH CUỘC HỘI THOẠI để hiểu rõ hơn ý của người dùng, đặc biệt là các đại từ như "nó", "chúng", "chức năng này".
        """

        # Thêm hướng dẫn về định dạng Markdown
        markdown_instruction = """
        QUY ĐỊNH ĐỊNH DẠNG PHẢN HỒI (QUAN TRỌNG - PHẢI TUÂN THỦ):
        Bạn PHẢI định dạng câu trả lời theo các quy tắc sau:

        1. TIÊU ĐỀ VÀ CẤU TRÚC:
           - Sử dụng ## cho tiêu đề chính của câu trả lời
           - Sử dụng ### cho các phần, mục nhỏ
           - Mỗi phần phải có cấu trúc rõ ràng với tiêu đề riêng

        2. MÃ SQL VÀ MÃ LỆNH (QUAN TRỌNG):
           - LUÔN đặt mã SQL/code trong khối lệnh với 3 dấu backtick và chỉ định ngôn ngữ:
             ```sql
             SELECT * FROM customers WHERE customer_id = 1;
             ```
           - Đối với các truy vấn SQL phức tạp, PHẢI thêm chú thích vào các dòng quan trọng:
             ```sql
             SELECT c.customer_name, o.order_date
             FROM customers c         -- Bảng khách hàng
             JOIN orders o            -- Kết nối với bảng đơn hàng
             ON c.customer_id = o.customer_id
             WHERE o.order_amount > 1000;
             ```

        3. BẢNG (QUAN TRỌNG):
           - Khi cần trình bày dữ liệu dạng bảng, LUÔN sử dụng cú pháp bảng Markdown:
             | Cột 1 | Cột 2 | Cột 3 |
             |-------|-------|-------|
             | Dữ liệu 1 | Dữ liệu 2 | Dữ liệu 3 |
           - PHẢI căn chỉnh các cột cho dễ đọc
           - PHẢI có hàng ngăn cách tiêu đề và nội dung

        4. DANH SÁCH VÀ LIỆT KÊ (QUAN TRỌNG):
           - Sử dụng danh sách có số cho các bước tuần tự:
             1. Bước thứ nhất
             2. Bước thứ hai
           - Sử dụng danh sách có dấu gạch đầu dòng cho các mục không theo thứ tự:
             - Mục thứ nhất
             - Mục thứ hai
           - Sử dụng danh sách lồng nhau khi cần:
             - Mục chính
               - Mục con

        5. NHẤN MẠNH (QUAN TRỌNG):
           - Sử dụng **in đậm** cho các thuật ngữ quan trọng và điểm chính
           - Sử dụng *in nghiêng* cho các nhấn mạnh nhẹ hoặc thuật ngữ tiếng nước ngoài
           - Sử dụng `highlight` cho các tên biến, lệnh ngắn hoặc từ khóa SQL

        6. TRÍCH DẪN (BẮT BUỘC):
           - Khi trích dẫn thông tin PHẢI sử dụng định dạng: **[Nguồn: Tài liệu, Trang X, Phần Y]**
           - Sử dụng ký hiệu > cho các trích dẫn dài từ tài liệu:
             > Đây là đoạn trích dẫn từ tài liệu gốc...

        7. SO SÁNH VÀ ĐỐI CHIẾU (QUAN TRỌNG):
           - Khi so sánh hai hoặc nhiều đối tượng, PHẢI dùng bảng:
             | Đặc điểm | MySQL | PostgreSQL |
             |----------|-------|------------|
             | Hiệu suất | Tốt với ứng dụng đọc nhiều | Tốt với ứng dụng ghi nhiều |
           - Hoặc sử dụng danh sách có cấu trúc:
             - **MySQL**: 
               - Ưu điểm: dễ cài đặt, hiệu suất tốt với ứng dụng đọc nhiều
               - Nhược điểm: hỗ trợ hạn chế cho các tính năng nâng cao
        
        QUAN TRỌNG: Bạn PHẢI tuân theo các quy tắc định dạng trên trong MỌI câu trả lời. Hãy đảm bảo câu trả lời của bạn có cấu trúc rõ ràng, dễ đọc và chuyên nghiệp.
        """

        # Hướng dẫn về xử lý ngữ cảnh cuộc hội thoại
        context_instruction = f"""
        NGỮ CẢNH CUỘC HỘI THOẠI:
        Dưới đây là lịch sử cuộc hội thoại giữa người dùng và hệ thống trước câu hỏi hiện tại.
        Sử dụng ngữ cảnh này để hiểu rõ hơn ý định của người dùng, đặc biệt là các đại từ chỉ định.
        
        {conversation_history}
        
        Hãy trả lời câu hỏi hiện tại "{query}" dựa trên ngữ cảnh cuộc hội thoại ở trên và thông tin từ tài liệu.
        """

        # Lấy template phù hợp hoặc sử dụng template chung
        template = self.templates.get(question_type, self.templates["general"])

        # Thêm hướng dẫn bổ sung cho các loại câu hỏi đặc biệt
        additional_instructions = ""

        # Thêm hướng dẫn bổ sung dựa trên loại câu hỏi
        if question_type == "sql_analysis" or question_type == "sql_generation":
            additional_instructions = """
            HƯỚNG DẪN BỔ SUNG CHO SQL:
            - PHẢI đặt tất cả mã SQL trong khối ```sql và ```
            - PHẢI chú thích từng phần của truy vấn phức tạp
            - PHẢI giải thích chi tiết cách hoạt động của mỗi mệnh đề SQL
            - Nếu có thể, hãy cung cấp ví dụ kết quả đầu ra dạng bảng
            """
        elif question_type == "comparison":
            additional_instructions = """
            HƯỚNG DẪN BỔ SUNG CHO SO SÁNH:
            - PHẢI trình bày phần so sánh dưới dạng bảng Markdown
            - PHẢI liệt kê rõ ràng các điểm giống và khác nhau
            - PHẢI tổng kết lại các điểm chính của so sánh
            """
        elif question_type == "example":
            additional_instructions = """
            HƯỚNG DẪN BỔ SUNG CHO VÍ DỤ:
            - PHẢI trình bày mã và lệnh trong khối ```
            - PHẢI giải thích chi tiết từng bước trong ví dụ
            - PHẢI sử dụng tiêu đề rõ ràng để phân biệt các ví dụ khác nhau
            """
        elif question_type == "definition" or question_type == "theory":
            additional_instructions = """
            HƯỚNG DẪN BỔ SUNG CHO ĐỊNH NGHĨA/LÝ THUYẾT:
            - PHẢI bắt đầu bằng định nghĩa ngắn gọn được in đậm
            - PHẢI tổ chức nội dung theo tiêu đề và danh mục
            - PHẢI sử dụng ví dụ để minh họa khi cần thiết
            """

        # Điền vào template và thêm các hướng dẫn
        prompt = template.format(context=context_str, query=query)
        prompt += strict_instruction
        prompt += context_instruction
        prompt += markdown_instruction
        prompt += additional_instructions

        return prompt
