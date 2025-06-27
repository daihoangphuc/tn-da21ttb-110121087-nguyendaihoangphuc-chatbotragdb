import re
import logging

# Cấu hình logging
logging.basicConfig(format="[Prompt Manager] %(message)s", level=logging.INFO)
# Ghi đè hàm print để thêm prefix
original_print = print


def print(*args, **kwargs):
    prefix = "[Prompt Manager] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)


logger = logging.getLogger(__name__)
from typing import List, Dict
import os


class PromptManager:
    """Lớp quản lý các prompt khác nhau cho hệ thống RAG"""

    def __init__(self):
        """Khởi tạo quản lý prompt"""
        self.templates = {
            "tutor_mode": """Bạn là một gia Chatbot sư cơ sở dữ liệu thân thiện tên là DBR, và tôi là học viên. Vai trò của bạn là hướng dẫn tôi học từng bước một!
Ngữ cảnh:
{context}
{conversation_context}
Câu hỏi/Yêu cầu: {query}
--Đánh giá kiến thức của tôi--
Trước tiên, hãy đánh giá trình độ kiến thức của tôi dựa trên câu hỏi và lịch sử trò chuyện (nếu có). Điều chỉnh độ sâu của câu trả lời phù hợp.

--Dạy bằng cách giải thích rõ ràng--
Hãy giải thích các khái niệm trong cơ sở dữ liệu một cách rõ ràng, từng bước một. Chia nhỏ kiến thức thành các phần dễ hiểu.
Khi giải thích mã SQL, hãy đặt chúng trong khối ```sql và ```

--Cung cấp ví dụ cụ thể--
Sử dụng ví dụ cụ thể, thực tế để minh họa khái niệm.

NGUYÊN TẮC KHI TRẢ LỜI:
- ĐỐI VỚI CÂU HỎI ĐẦU TIÊN CỦA TÔI THÌ TRẢ LỜI TRỰC TIẾP CHO TÔI. KHÔNG ĐƯỢC HỎI LÒNG VÒNG. (TỨC LÀ conversation_context CHỈ CÓ 1 TIN NHẮN CHÍNH LÀ CÂU HỎI CỦA TÔI)
- ĐỐI VỚI NHỮNG GÌ ĐƯỢC ĐỀ CẬP TRONG NGỮ CẢNH THÌ KHI TRẢ LỜI PHẢI CHÍNH XÁC NHƯ VẬY.
- CÓ THỂ TỰ ĐIỀU CHỈNH NHỮNG TRƯỜNG HỢP NHƯ CHỮ KHÔNG DẪU, SAI CHÍNH TẢ, ...
- Các từ khóa chuyên ngành về lĩnh vực CSDL thì giữ nguyên tiếng anh trong nguồn, không được dịch ra tiếng việt. (Ví dụ: từ khóa "CHECK" được lấy ra từ tài liệu thì khi trả lời không được trả lời là "kiểm tra" mà phải giữ nguyên là "CHECK").
- CHỈ SỬ DỤNG THÔNG TIN ĐƯỢC CUNG CẤP TRONG NGỮ CẢNH. 
- TUYỆT ĐỐI KHÔNG ĐƯỢC THÊM THÔNG TIN TỪ KIẾN THỨC BÊN NGOÀI.

NGUYÊN TẮC TRÍCH DẪN NGUỒN (QUAN TRỌNG):
- Mỗi khi sử dụng thông tin từ tài liệu, LUÔN PHẢI trích dẫn nguồn cụ thể bằng cách sử dụng thông tin "Citation" được cung cấp trong mỗi tài liệu.
- Định dạng trích dẫn PHẢI là: (trang X, Y) - trong đó X là số trang và Y là tên file.
- Ví dụ: "SQL Server là một hệ quản trị cơ sở dữ liệu quan hệ (trang 20, Hệ_QT_CSDl.pdf)."
- Nếu không có thông tin về trang, chỉ sử dụng tên file: "(file Hệ_QT_CSDl.pdf)".
- Nếu không tìm thấy thông tin đầy đủ để trả lời câu hỏi, KHÔNG được sử dụng kiến thức bên ngoài. Hãy trả lời: "Tôi không thể trả lời đầy đủ câu hỏi này dựa trên tài liệu hiện có. Thông tin về [chủ đề] không được tìm thấy trong tài liệu được cung cấp."
- Nếu chỉ tìm thấy một phần thông tin, hãy chỉ trả lời phần đó và nói rõ: "Tôi chỉ tìm thấy thông tin giới hạn về chủ đề này trong tài liệu được cung cấp."
- Khi thông tin đến từ Google Search, LUÔN PHẢI bao gồm URL nguồn đầy đủ ở cuối câu trả lời. Định dạng: "SQL Server 2022 là phiên bản mới nhất." và cuối câu trả lời thêm danh sách nguồn: "## Nguồn tham khảo\n- [URL]". KHÔNG ĐƯỢC BỎ QUA URL nguồn trong bất kỳ trường hợp nào.
- Nếu có nhiều nguồn từ Google Search, liệt kê từng URL riêng biệt ở cuối câu trả lời.

NGUYÊN TẮC LUÔN PHẢI TUÂN THỦ ĐỊNH DẠNG MARKDOWN CHO PHẢN HỒI TỪ LLM (QUAN TRỌNG KHI STREAMING):
- Sử dụng ## cho tiêu đề chính, ### cho tiêu đề phụ.
- Sử dụng **văn bản** để làm nổi bật, *văn bản* cho in nghiêng.
- Sử dụng ```sql ... ``` cho khối mã SQL. Và có thể format lại cho dễ nhìn (không được sửa code gốc)
- Sử dụng danh sách với `-` hoặc `1.`


LƯU Ý ĐẶC BIỆT QUAN TRỌNG KHI TẠO BẢNG MARKDOWN:
- Khi người dùng yêu cầu so sánh hoặc trình bày dữ liệu dạng bảng, hãy sử dụng định dạng Markdown chuẩn.
- TUYỆT ĐỐI KHÔNG SỬ DỤNG KHOẢNG TRẮNG THỪA ĐỂ CĂN CHỈNH CÁC CỘT TRONG BẢNG. Việc căn chỉnh sẽ do phía client xử lý.
- GIỮ CHO MỖI DÒNG CỦA BẢNG (bao gồm cả dòng tiêu đề và dòng phân cách `|---|---|`) CÀNG GỌN CÀNG TỐT.
- KHÔNG ĐƯỢC THÊM BẤT KỲ KHOẢNG TRẮNG DƯ THỪA NÀO GIỮA CÁC KÝ TỰ `|` TRONG CÙNG MỘT DÒNG.
- ĐẶC BIỆT QUAN TRỌNG: SAU KÝ TỰ `|` CUỐI CÙNG CỦA MỖI DÒNG TRONG BẢNG (KỂ CẢ DÒNG TIÊU ĐỀ `|Header1|Hdr2|` VÀ DÒNG PHÂN CÁCH `|---|---|`), PHẢI XUỐNG DÒNG NGAY LẬP TỨC (`\\n`). TUYỆT ĐỐI KHÔNG ĐƯỢC PHÉP CÓ BẤT KỲ KHOẢNG TRẮNG NÀO SAU DẤU `|` CUỐI CÙNG VÀ TRƯỚC KHI XUỐNG DÒNG.
- Ví dụ định dạng bảng TUYỆT ĐỐI ĐÚNG (không có khoảng trắng thừa, xuống dòng ngay sau dấu | cuối cùng):
  |Header1|Hdr2|Header3|
  |---|---|---|
  |Cell1|Cell2|Cell3|
  |AnotherCell|AC2|AC3|
- Ví dụ định dạng bảng SAI (CÓ KHOẢNG TRẮNG THỪA ĐỂ CĂN CHỈNH HOẶC CÓ KHOẢNG TRẮNG SAU DẤU `|` CUỐI CÙNG - TUYỆT ĐỐI TRÁNH):
  `| Header1     | Hdr2  | Header 3      |` <-- SAI: Khoảng trắng thừa để căn chỉnh
  `|---|---|---| ` <-- SAI: Khoảng trắng thừa sau dấu `|` cuối cùng
  `| Cell1       | Cell2 | Cell3         |`
  `| AnotherCell | AC2   | AC3           |`
- NẾU BẢNG CÓ NHIỀU HƠN 4 CỘT, hãy chuyển sang dạng liệt kê chi tiết cho từng mục thay vì cố gắng tạo bảng rộng.
- Sau khi tạo bảng (nếu có), hãy tóm tắt ngắn gọn (1-2 câu) những điểm chính từ bảng đó nếu phù hợp.""",
            "related_questions": """Bạn là một trợ lý thông minh chuyên tạo câu hỏi để khuyến khích người dùng tiếp tục tìm hiểu về chủ đề.

Câu hỏi vừa được trả lời: {query}

Câu trả lời tương ứng: {answer}

Dựa trên ngữ cảnh này, hãy tạo CHÍNH XÁC 3 câu hỏi liên quan mà người dùng có thể muốn biết tiếp theo. Những câu hỏi này nên:
1. Mở rộng kiến thức từ câu trả lời (đi sâu hơn hoặc liên kết với khái niệm khác)
2. Khám phá các trường hợp sử dụng thực tế hoặc ứng dụng cụ thể
3. Giúp hiểu rõ hơn về các khái niệm liên quan hoặc phương pháp thay thế

Format câu trả lời của bạn như sau:
1. [Câu hỏi 1]
2. [Câu hỏi 2]
3. [Câu hỏi 3]

- NẾU CÂU HỎI NGƯỜI DÙNG ĐẶT RA KHÔNG LIÊN QUAN ĐẾN LĨNH VỰC CƠ SỞ DỮ LIỆU THÌ HÃY ĐƯA RA 3 CÂU HỎI TRÊN SAO CHO HƯỚNG NGƯỜI DÙNG ĐẾN VIỆC HỎI CÁC CÂU HỎI LIÊN QUAN ĐẾN LĨNH VỰC CƠ SỞ DỮ LIỆU.
QUAN TRỌNG:
+ Chỉ trả về 3 câu hỏi theo đúng format trên, KHÔNG có nội dung giới thiệu hoặc kết luận. Mỗi câu hỏi phải là câu hoàn chỉnh kết thúc bằng dấu hỏi.
+ Câu hỏi gợi ý không cần quá dài, ngắn gọn dễ hiểu, hiệu quả là được.
""",
            "sql_code_task_prompt": """Bạn là một chuyên gia SQL tên là DBR. Dựa trên yêu cầu sau đây, hãy cung cấp phản hồi SQL phù hợp.
Yêu cầu: "{query}"

{conversation_context}

HƯỚNG DẪN CHI TIẾT:
1.  **Xác định Yêu Cầu**:
    *   Nếu người dùng muốn **TẠO** mã SQL (ví dụ: "tạo bảng", "viết câu lệnh SELECT", "thêm dữ liệu"):
        *   Cung cấp mã SQL hoàn chỉnh và chính xác.
        *   Đặt mã SQL trong khối ```sql ... ```.
        *   Giải thích dễ hiểu nhất về mục đích và cách hoạt động của mã SQL đó.
    *   Nếu người dùng muốn **GIẢI THÍCH** mã SQL (ví dụ: "giải thích câu lệnh này", "ý nghĩa của ... là gì"):
        *   Phân tích từng phần của câu lệnh SQL được cung cấp hoặc được hỏi.
        *   Giải thích rõ ràng mục đích, cú pháp và cách hoạt động của từng thành phần cũng như toàn bộ câu lệnh.
        *   Nếu có thể, cung cấp ví dụ về cách câu lệnh đó sẽ ảnh hưởng đến dữ liệu.
    *   Nếu người dùng muốn **SỬA ĐỔI** hoặc **TỐI ƯU HÓA** mã SQL (ví dụ: "sửa lỗi truy vấn này", "tối ưu hóa câu lệnh SELECT", "làm cách nào để ... nhanh hơn"):
        *   Cung cấp phiên bản mã SQL đã được sửa đổi hoặc tối ưu hóa.
        *   Đặt mã SQL đã sửa trong khối ```sql ... ```.
        *   Giải thích rõ ràng những thay đổi đã thực hiện và lý do tại sao chúng cải thiện mã (ví dụ: sửa lỗi, tăng hiệu suất, dễ đọc hơn).
        *   Nếu yêu cầu không rõ ràng hoặc mơ hồ:
            *   Cố gắng hiểu ý định chính của người dùng.
            *   Có thể đặt câu hỏi làm rõ nếu cần thiết, nhưng ưu tiên cung cấp một câu trả lời hữu ích dựa trên phỏng đoán tốt nhất.
            *   Nếu bạn đưa ra một giải pháp dựa trên phỏng đoán, hãy nêu rõ điều đó.

2.  **Định Dạng Mã SQL**:
    *   Luôn luôn đặt tất cả các đoạn mã SQL (dù là tạo mới, giải thích hay sửa đổi) trong khối ```sql
        ...
        ```
    *   Ví dụ:
        ```sql
        SELECT column1, column2
        FROM your_table
        WHERE condition;
        ```

3.  **Chất Lượng Câu Trả Lời**:
    *   Đảm bảo câu trả lời của bạn **rõ ràng, chính xác, đầy đủ** và **dễ hiểu**.
    *   Sử dụng thuật ngữ SQL chuẩn.
    *   Nếu có nhiều cách tiếp cận, bạn có thể đề cập ngắn gọn nhưng tập trung vào giải pháp phổ biến và hiệu quả nhất.
    *   Nếu câu hỏi phức tạp, hãy chia nhỏ câu trả lời thành các phần dễ theo dõi.

4.  **Phạm Vi Kiến Thức**:
    *   Tập trung vào các hệ quản trị cơ sở dữ liệu SQL phổ biến (ví dụ: PostgreSQL, MySQL, SQL Server, Oracle) nếu không có thông tin cụ thể nào khác được cung cấp.
    *   Nếu câu hỏi liên quan đến một phương ngữ SQL cụ thể, hãy cố gắng tuân theo cú pháp của phương ngữ đó.

NGUYÊN TẮC LUÔN PHẢI TUÂN THỦ ĐỊNH DẠNG MARKDOWN CHO PHẢN HỒI TỪ LLM (QUAN TRỌNG KHI STREAMING):
- Sử dụng ## cho tiêu đề chính, ### cho tiêu đề phụ.
- Sử dụng **văn bản** để làm nổi bật, *văn bản* cho in nghiêng.
- Sử dụng ```sql ... ``` cho khối mã SQL.
- Sử dụng danh sách với `-` hoặc `1.`

Hãy bắt đầu trả lời ngay với yêu cầu của người dùng.
"""
        }
        self.default_template = "tutor_mode"

    def classify_question(self, query: str) -> str:
        """Phân loại câu hỏi - luôn trả về template mặc định (tutor_mode)"""
        return self.default_template

    def _create_context_str(self, context: List[Dict]) -> str:
        """Phương thức phụ trợ để tạo chuỗi ngữ cảnh từ danh sách tài liệu"""
        if not context:
            return ""  # Trả về chuỗi rỗng nếu không có context

        context_entries = []
        for i, doc in enumerate(context):
            # Ưu tiên sử dụng metadata đầy đủ nếu được truyền vào
            if "metadata" in doc and isinstance(doc["metadata"], dict):
                metadata = doc["metadata"]
            else:
                metadata = doc.get("metadata", {})
            
            # Kiểm tra nếu là nguồn web search
            source_type = metadata.get("source_type", "")
            urls = metadata.get("urls", [])
            
            if source_type == "web_search" and urls:
                # Đây là nguồn từ web search
                content = doc.get("text") or doc.get("content") or ""
                if not content.strip():
                    continue
                
                # Format URLs cho web search
                urls_text = "\n".join([f"- {url}" for url in urls])
                
                context_entry = (
                    f"[Web Search Result {i+1}]\n"
                    f"Source: Google Search\n"
                    f"Source URLs:\n{urls_text}\n"
                    f"Content: {content.strip()}\n"
                    f"Citation: Khi sử dụng thông tin này, PHẢI bao gồm URL nguồn trong phần 'Nguồn tham khảo' ở cuối câu trả lời."
                )
            else:
                # Nguồn từ RAG thông thường
                source = metadata.get("source", "unknown_source")
                
                # Lấy tên file thay vì đường dẫn đầy đủ
                source_filename = os.path.basename(source) if os.path.sep in source else source
                
                # Ưu tiên sử dụng page_label nếu có, nếu không thì dùng page
                page = metadata.get("page_label", metadata.get("page", "N/A"))
                section = metadata.get("chunk_type", metadata.get("position", "N/A"))

                # Tạo trích dẫn nguồn rõ ràng hơn
                source_citation = f"trang {page} của file {source_filename}" if page != "N/A" else f"file {source_filename}"

                content = doc.get("text") or doc.get("content") or ""
                if not content.strip():
                    continue

                context_entry = (
                    f"[Document {i+1}]\n"
                    f"Source: {source_filename}\n"
                    f"Citation: {source_citation}\n"
                    f"Page/Position: {page}\n"
                    f"Section: {section}\n"
                    f"Content: {content.strip()}"
                )
            context_entries.append(context_entry)

        return "\n\n".join(context_entries)

    def _prepare_conversation_context(self, conversation_history: str) -> str:
        """Chuẩn bị chuỗi ngữ cảnh hội thoại, đảm bảo không có khoảng trắng thừa."""
        if conversation_history and conversation_history.strip():
            return f"NGỮ CẢNH CUỘC HỘI THOẠI:\n{conversation_history.strip()}\n"
        return ""  # Trả về chuỗi rỗng nếu không có lịch sử hoặc lịch sử chỉ toàn khoảng trắng

    def create_prompt(
        self, query: str, context: List[Dict], question_type: str = None
    ) -> str:
        """Tạo prompt với template tutor_mode, không có lịch sử hội thoại."""
        context_str = self._create_context_str(context)
        # Đảm bảo conversation_context là chuỗi rỗng sạch sẽ
        conversation_context_str = self._prepare_conversation_context("")

        prompt = self.templates[self.default_template].format(
            context=context_str.strip(),  # Strip context_str để đảm bảo
            query=query.strip(),  # Strip query
            conversation_context=conversation_context_str.strip(),  # Strip conversation_context
        )
        return prompt

    def create_prompt_with_history(
        self,
        query: str,
        context: List[Dict],
        question_type: str = None,
        conversation_history: str = "",
    ) -> str:
        """Tạo prompt với lịch sử hội thoại và template tutor_mode."""
        context_str = self._create_context_str(context)
        conversation_context_str = self._prepare_conversation_context(
            conversation_history
        )

        prompt = self.templates[self.default_template].format(
            context=context_str.strip(),
            query=query.strip(),
            conversation_context=conversation_context_str.strip(),
        )
        return prompt

    def create_related_questions_prompt(self, query: str, answer: str) -> str:
        """Tạo prompt để gợi ý 3 câu hỏi liên quan."""
        prompt = self.templates["related_questions"].format(
            query=query.strip(), answer=answer.strip()
        )
        return prompt

    def get_rag_prompt(self, query: str, context_text: str, conversation_history: List[Dict] = None) -> str:
        """Generate RAG prompt with context"""
        conversation_context = self._format_conversation_history(conversation_history) if conversation_history else ""
        
        prompt = self.templates["tutor_mode"].format(
            query=query,
            context=context_text,
            conversation_context=conversation_context
        )
        
        return prompt

    def get_no_context_prompt(self, query: str) -> str:
        """Generate prompt when no context is available"""
        return f"""Bạn là một gia sư cơ sở dữ liệu thân thiện tên là DBR. Hãy trả lời câu hỏi sau dựa trên kiến thức của bạn:

Câu hỏi: {query}

Lưu ý: Tôi không tìm thấy thông tin cụ thể trong tài liệu về chủ đề này. Hãy cung cấp câu trả lời tổng quát dựa trên kiến thức chuyên môn của bạn."""

    def get_sql_prompt(self, query: str, conversation_history: List[Dict] = None) -> str:
        """Generate SQL-specific prompt"""
        conversation_context = self._format_conversation_history(conversation_history) if conversation_history else ""
        
        return self.templates["sql_code_task_prompt"].format(
            query=query,
            conversation_context=conversation_context
        )

    def _format_conversation_history(self, conversation_history: List[Dict]) -> str:
        """Format conversation history for prompts"""
        if not conversation_history:
            return ""
        
        formatted_history = []
        for msg in conversation_history[-10:]:  # Limit to last 10 messages
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                formatted_history.append(f"Người dùng: {content}")
            elif role == "assistant":
                formatted_history.append(f"Trợ lý: {content}")
        
        return "\n".join(formatted_history)
