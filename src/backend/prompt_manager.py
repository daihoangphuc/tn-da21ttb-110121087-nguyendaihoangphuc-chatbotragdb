import re
import logging
from typing import List, Dict, Optional, Union, Any
from enum import Enum
import os


# Cấu hình logging
logging.basicConfig(format="[Prompt Manager] %(message)s", level=logging.INFO)
# Ghi đè hàm print để thêm prefix
original_print = print


def print(*args, **kwargs):
    prefix = "[Prompt Manager] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)


logger = logging.getLogger(__name__)


class TemplateType(Enum):
    """Enum định nghĩa các loại template có sẵn"""
    TUTOR_MODE = "tutor_mode"
    # RELATED_QUESTIONS = "related_questions"
    SQL_CODE_TASK = "sql_code_task_prompt"
    REALTIME_QUESTION = "realtime_question"


class PromptManager:
    """Lớp quản lý các prompt khác nhau cho hệ thống RAG"""

    def __init__(self):
        """Khởi tạo quản lý prompt"""
        self.templates = self._initialize_templates()
        self.default_template = TemplateType.TUTOR_MODE.value
        self._validate_templates()

    def _initialize_templates(self) -> Dict[str, str]:
        """Khởi tạo và trả về dictionary chứa tất cả templates"""
        return {
            TemplateType.TUTOR_MODE.value: self._get_tutor_mode_template(),
            # TemplateType.RELATED_QUESTIONS.value: self._get_related_questions_template(),
            TemplateType.SQL_CODE_TASK.value: self._get_sql_code_task_template(),
            TemplateType.REALTIME_QUESTION.value: self._get_realtime_question_template()
        }

    def _get_tutor_mode_template(self) -> str:
        """Template cho chế độ gia sư"""
        return """Bạn là một gia Chatbot sư cơ sở dữ liệu thân thiện tên là DBR, và tôi là học viên. Vai trò của bạn là hướng dẫn tôi học từng bước một!
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
- TRÁNH TÓM TẮT CHUNG CHUNG. Thay vào đó, hãy trích xuất và giải thích trực tiếp các chi tiết liên quan từ ngữ cảnh.
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


QUY TẮC TẠO BẢNG MARKDOWN (KHI CẦN THIẾT):
- Nếu yêu cầu trình bày dữ liệu so sánh hoặc bảng, BẮT BUỘC sử dụng định dạng Markdown sau.
- Định dạng chuẩn:
  |Header1|Header2|
  |---|---|
  |Dòng1Cột1|Dòng1Cột2|
  |Dòng2Cột1|Dòng2Cột2|
- YÊU CẦU QUAN TRỌNG:
  1. TUYỆT ĐỐI KHÔNG TẠO RA KHOẢNG TRẮNG THỪA TRONG KHI TẠO BẢNG VÀ CẤU TRÚC BẢNG PHẢI TUÂN THỦ ĐÚNG THEO ĐỊNH DẠNG MARKDOWN.
  2. Mỗi dòng (header, phân cách, dữ liệu) phải bắt đầu bằng `|` và kết thúc bằng `|` theo sau NGAY LẬP TỨC bởi ký tự xuống dòng (`\\n`).
  3. KHÔNG dùng khoảng trắng để căn chỉnh cột. Giữ nội dung ô ngắn gọn.
- Sau bảng (nếu có), tóm tắt ngắn gọn điểm chính (1-2 câu)."""

#     def _get_related_questions_template(self) -> str:
#         """Template cho câu hỏi liên quan"""
#         return """Bạn là một trợ lý thông minh chuyên tạo câu hỏi để khuyến khích người dùng tiếp tục tìm hiểu về chủ đề.

# Câu hỏi vừa được trả lời: {query}

# Câu trả lời tương ứng: {answer}

# NGUYÊN TẮC QUAN TRỌNG:
# - CHỈ tạo câu hỏi dựa trên nội dung đã được trả lời trong {answer}
# - KHÔNG được thêm thông tin từ kiến thức bên ngoài
# - Câu hỏi phải liên quan trực tiếp đến những gì đã được đề cập trong câu trả lời

# Dựa trên ngữ cảnh này, hãy tạo CHÍNH XÁC 3 câu hỏi liên quan mà người dùng có thể muốn biết tiếp theo. Những câu hỏi này nên:
# 1. Mở rộng kiến thức từ câu trả lời (đi sâu hơn về những điểm đã được đề cập)
# 2. Khám phá các khía cạnh khác của chủ đề đã được trả lời
# 3. Giúp hiểu rõ hơn về các khái niệm đã được giải thích trong câu trả lời

# Format câu trả lời của bạn như sau:
# 1. [Câu hỏi 1]
# 2. [Câu hỏi 2]
# 3. [Câu hỏi 3]

# - NẾU CÂU HỎI NGƯỜI DÙNG ĐẶT RA KHÔNG LIÊN QUAN ĐẾN LĨNH VỰC CƠ SỞ DỮ LIỆU THÌ HÃY ĐƯA RA 3 CÂU HỎI TRÊN SAO CHO HƯỚNG NGƯỜI DÙNG ĐẾN VIỆC HỎI CÁC CÂU HỎI LIÊN QUAN ĐẾN LĨNH VỰC CƠ SỞ DỮ LIỆU.
# QUAN TRỌNG:
# + Chỉ trả về 3 câu hỏi theo đúng format trên, KHÔNG có nội dung giới thiệu hoặc kết luận. Mỗi câu hỏi phải là câu hoàn chỉnh kết thúc bằng dấu hỏi.
# + Câu hỏi gợi ý không cần quá dài, ngắn gọn dễ hiểu, hiệu quả là được.
# """

    def _get_sql_code_task_template(self) -> str:
        """Template cho SQL code tasks"""
        return """Bạn là một chuyên gia SQL tên là DBR. Dựa trên yêu cầu sau đây, hãy cung cấp phản hồi SQL phù hợp.
Yêu cầu: "{query}"

{conversation_context}

NGUYÊN TẮC CHỐNG ẢO GIÁC (QUAN TRỌNG):
- CHỈ sử dụng thông tin SQL cơ bản và chuẩn được công nhận rộng rãi
- KHÔNG thêm thông tin về cấu trúc database cụ thể nếu không được cung cấp
- Nếu yêu cầu không đủ thông tin để tạo SQL chính xác, hãy nói rõ những thông tin cần bổ sung
- Sử dụng tên bảng và cột generic (ví dụ: table_name, column_name) nếu không được chỉ định cụ thể
- Khi đưa ra ví dụ, luôn ghi chú rằng đây là ví dụ minh họa và cần điều chỉnh theo cấu trúc thực tế

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
    *   Sử dụng cú pháp SQL chuẩn ANSI khi có thể
    *   Chỉ đề cập đến các hệ quản trị cụ thể (PostgreSQL, MySQL, SQL Server, Oracle) khi được yêu cầu rõ ràng
    *   Nếu không rõ hệ quản trị, sử dụng cú pháp SQL chung nhất

5.  **Xử Lý Thông Tin Thiếu**:
    *   Nếu thiếu thông tin về cấu trúc bảng, hãy yêu cầu người dùng cung cấp
    *   Đưa ra giả định hợp lý và nói rõ đây là giả định
    *   Ví dụ: "Giả sử bảng 'users' có cột 'id', 'name', 'email'..."

NGUYÊN TẮC LUÔN PHẢI TUÂN THỦ ĐỊNH DẠNG MARKDOWN CHO PHẢN HỒI TỪ LLM (QUAN TRỌNG KHI STREAMING):
- Sử dụng ## cho tiêu đề chính, ### cho tiêu đề phụ.
- Sử dụng **văn bản** để làm nổi bật, *văn bản* cho in nghiêng.
- Sử dụng ```sql ... ``` cho khối mã SQL.
- Sử dụng danh sách với `-` hoặc `1.`

Hãy bắt đầu trả lời ngay với yêu cầu của người dùng.
"""

    def _get_realtime_question_template(self) -> str:
        """Template cho câu hỏi thời gian thực"""
        return """Bạn là một gia sư cơ sở dữ liệu thân thiện tên là DBR. Bạn đang trả lời câu hỏi dựa trên kết quả tìm kiếm thời gian thực từ Google.

Câu hỏi: {query}
{conversation_context}

Kết quả tìm kiếm từ Google:
{search_results}

NGUYÊN TẮC QUAN TRỌNG KHI TRẢ LỜI:
- ĐỐI VỚI CÂU HỎI ĐẦU TIÊN CỦA TÔI THÌ TRẢ LỜI TRỰC TIẾP CHO TÔI. KHÔNG ĐƯỢC HỎI LÒNG VÒNG.
- CHỈ SỬ DỤNG THÔNG TIN ĐƯỢC CUNG CẤP TRONG KẾT QUẢ TÌM KIẾM.
- TUYỆT ĐỐI KHÔNG ĐƯỢC THÊM THÔNG TIN TỪ KIẾN THỨC BÊN NGOÀI.
- Các từ khóa chuyên ngành về lĩnh vực CSDL thì giữ nguyên tiếng anh trong nguồn, không được dịch ra tiếng việt.
- TRÁNH TÓM TẮT CHUNG CHUNG. Thay vào đó, hãy trích xuất và giải thích trực tiếp các chi tiết liên quan từ kết quả tìm kiếm.

NGUYÊN TẮC TRÍCH DẪN NGUỒN (BẮT BUỘC):
- Khi thông tin đến từ Google Search, LUÔN PHẢI bao gồm URL nguồn đầy đủ ở cuối câu trả lời.
- Định dạng: Cuối câu trả lời thêm danh sách nguồn: "## Nguồn tham khảo\\n- [URL1]\\n- [URL2]"
- KHÔNG ĐƯỢC BỎ QUA URL nguồn trong bất kỳ trường hợp nào.
- Nếu có nhiều nguồn từ Google Search, liệt kê từng URL riêng biệt.

NGUYÊN TẮC ĐỊNH DẠNG MARKDOWN:
- Sử dụng ## cho tiêu đề chính, ### cho tiêu đề phụ.
- Sử dụng **văn bản** để làm nổi bật, *văn bản* cho in nghiêng.
- Sử dụng ```sql ... ``` cho khối mã SQL nếu có.
- Sử dụng danh sách với `-` hoặc `1.`

QUY TẮC TẠO BẢNG MARKDOWN (KHI CẦN THIẾT):
- Nếu yêu cầu trình bày dữ liệu so sánh hoặc bảng, BẮT BUỘC sử dụng định dạng Markdown sau.
- Định dạng chuẩn:
  |Header1|Header2|
  |---|---|
  |Dòng1Cột1|Dòng1Cột2|
  |Dòng2Cột1|Dòng2Cột2|
- YÊU CẦU QUAN TRỌNG:
  1. TUYỆT ĐỐI KHÔNG TẠO RA KHOẢNG TRẮNG THỪA TRONG KHI TẠO BẢNG VÀ CẤU TRÚC BẢNG PHẢI TUÂN THỦ ĐÚNG THEO ĐỊNH DẠNG MARKDOWN.
  2. Mỗi dòng (header, phân cách, dữ liệu) phải bắt đầu bằng `|` và kết thúc bằng `|` theo sau NGAY LẬP TỨC bởi ký tự xuống dòng (`\\n`).
  3. KHÔNG dùng khoảng trắng để căn chỉnh cột. Giữ nội dung ô ngắn gọn.
- Sau bảng (nếu có), tóm tắt ngắn gọn điểm chính (1-2 câu).

NGUYÊN TẮC XỬ LÝ KHI THIẾU THÔNG TIN:
- Nếu không tìm thấy thông tin đầy đủ để trả lời câu hỏi trong kết quả tìm kiếm, hãy trả lời: "Tôi không thể trả lời đầy đủ câu hỏi này dựa trên kết quả tìm kiếm hiện có. Thông tin về [chủ đề] không được tìm thấy rõ ràng trong các nguồn tìm kiếm."
- Nếu chỉ tìm thấy một phần thông tin, hãy chỉ trả lời phần đó và nói rõ: "Tôi chỉ tìm thấy thông tin giới hạn về chủ đề này trong kết quả tìm kiếm."

Hãy trả lời câu hỏi dựa trên kết quả tìm kiếm trên và NHẤT ĐỊNH phải có phần "## Nguồn tham khảo" ở cuối với tất cả URL."""

    def _validate_templates(self) -> None:
        """Validate tất cả templates có các placeholder cần thiết"""
        required_placeholders = {
            TemplateType.TUTOR_MODE.value: ['{context}', '{query}', '{conversation_context}'],
            # TemplateType.RELATED_QUESTIONS.value: ['{query}', '{answer}'],
            TemplateType.SQL_CODE_TASK.value: ['{query}', '{conversation_context}'],
            TemplateType.REALTIME_QUESTION.value: ['{query}', '{conversation_context}', '{search_results}']
        }
        
        for template_name, placeholders in required_placeholders.items():
            template_content = self.templates.get(template_name, "")
            missing_placeholders = [p for p in placeholders if p not in template_content]
            
            if missing_placeholders:
                logger.warning(f"Template '{template_name}' thiếu placeholder: {missing_placeholders}")

    def classify_question(self, query: str) -> str:
        """Phân loại câu hỏi - luôn trả về template mặc định (tutor_mode)"""
        return self.default_template

    def _create_context_str(self, context: List[Dict]) -> str:
        """Phương thức phụ trợ để tạo chuỗi ngữ cảnh từ danh sách tài liệu"""
        if not context:
            return ""

        context_entries = []
        for i, doc in enumerate(context):
            try:
                context_entry = self._format_single_context(doc, i + 1)
                if context_entry.strip():
                    context_entries.append(context_entry)
            except Exception as e:
                logger.error(f"Lỗi khi xử lý document {i+1}: {str(e)}")
                continue

        return "\n\n".join(context_entries)

    def _format_single_context(self, doc: Dict, doc_index: int) -> str:
        """Format một document thành context string"""
        # Ưu tiên sử dụng metadata đầy đủ nếu được truyền vào
        metadata = doc.get("metadata", {}) if isinstance(doc.get("metadata"), dict) else {}
        
        # Kiểm tra nếu là nguồn web search
        source_type = metadata.get("source_type", "")
        urls = metadata.get("urls", [])
        
        if source_type == "web_search" and urls:
            return self._format_web_search_context(doc, doc_index, urls)
        else:
            return self._format_rag_context(doc, doc_index, metadata)

    def _format_web_search_context(self, doc: Dict, doc_index: int, urls: List[str]) -> str:
        """Format web search context"""
        content = doc.get("text") or doc.get("content") or ""
        if not content.strip():
            return ""
        
        urls_text = "\n".join([f"- {url}" for url in urls])
        
        return (
            f"[Web Search Result {doc_index}]\n"
            f"Source: Google Search\n"
            f"Source URLs:\n{urls_text}\n"
            f"Content: {content.strip()}\n"
            f"Citation: Khi sử dụng thông tin này, PHẢI bao gồm URL nguồn trong phần 'Nguồn tham khảo' ở cuối câu trả lời."
        )

    def _format_rag_context(self, doc: Dict, doc_index: int, metadata: Dict) -> str:
        """Format RAG context"""
        content = doc.get("text") or doc.get("content") or ""
        if not content.strip():
            return ""

        source = metadata.get("source", "unknown_source")
        source_filename = os.path.basename(source) if os.path.sep in source else source
        
        # Ưu tiên sử dụng page_label nếu có, nếu không thì dùng page
        page = metadata.get("page_label", metadata.get("page", "N/A"))
        section = metadata.get("chunk_type", metadata.get("position", "N/A"))

        # Tạo trích dẫn nguồn rõ ràng hơn
        source_citation = f"trang {page} của file {source_filename}" if page != "N/A" else f"file {source_filename}"

        return (
            f"[Document {doc_index}]\n"
            f"Source: {source_filename}\n"
            f"Citation: {source_citation}\n"
            f"Page/Position: {page}\n"
            f"Section: {section}\n"
            f"Content: {content.strip()}"
        )

    def _prepare_conversation_context(self, conversation_history: Union[str, List[Dict], None]) -> str:
        """Chuẩn bị chuỗi ngữ cảnh hội thoại từ nhiều format khác nhau"""
        if not conversation_history:
            return ""
        
        if isinstance(conversation_history, str):
            return f"NGỮ CẢNH CUỘC HỘI THOẠI:\n{conversation_history.strip()}\n" if conversation_history.strip() else ""
        elif isinstance(conversation_history, list):
            formatted_history = self._format_conversation_history(conversation_history)
            return f"NGỮ CẢNH CUỘC HỘI THOẠI:\n{formatted_history}\n" if formatted_history else ""
        
        return ""

    def _format_conversation_history(self, conversation_history: List[Dict]) -> str:
        """Format conversation history for prompts"""
        if not conversation_history:
            return ""
        
        formatted_history = []
        for msg in conversation_history[-5:]:  # Limit to last 5 messages
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                formatted_history.append(f"Người dùng: {content}")
            elif role == "assistant":
                formatted_history.append(f"Trợ lý: {content}")
        
        return "\n".join(formatted_history)

    def _get_template_safely(self, template_type: str) -> str:
        """Lấy template một cách an toàn với fallback"""
        template = self.templates.get(template_type)
        if not template:
            logger.warning(f"Template '{template_type}' không tồn tại, sử dụng template mặc định")
            template = self.templates.get(self.default_template, "")
        return template

    def create_prompt(
        self, 
        query: str, 
        context: List[Dict], 
        question_type: Optional[str] = None
    ) -> str:
        """Tạo prompt với template tutor_mode, không có lịch sử hội thoại."""
        try:
            context_str = self._create_context_str(context)
            conversation_context_str = self._prepare_conversation_context("")

            template = self._get_template_safely(self.default_template)
            
            prompt = template.format(
                context=context_str.strip(),
                query=query.strip(),
                conversation_context=conversation_context_str.strip(),
            )
            return prompt
        except Exception as e:
            logger.error(f"Lỗi khi tạo prompt: {str(e)}")
            # Fallback prompt với quy tắc chống ảo giác
            return f"""Có lỗi xảy ra khi tạo prompt. Tôi không thể trả lời câu hỏi "{query}" do thiếu thông tin ngữ cảnh cần thiết. Vui lòng thử lại hoặc cung cấp thêm thông tin."""

    def create_prompt_with_history(
        self,
        query: str,
        context: List[Dict],
        question_type: Optional[str] = None,
        conversation_history: Union[str, List[Dict], None] = None,
    ) -> str:
        """Tạo prompt với lịch sử hội thoại và template tutor_mode."""
        try:
            context_str = self._create_context_str(context)
            conversation_context_str = self._prepare_conversation_context(conversation_history)

            template = self._get_template_safely(self.default_template)
            
            prompt = template.format(
                context=context_str.strip(),
                query=query.strip(),
                conversation_context=conversation_context_str.strip(),
            )
            return prompt
        except Exception as e:
            logger.error(f"Lỗi khi tạo prompt với lịch sử: {str(e)}")
            # Fallback prompt với quy tắc chống ảo giác
            return f"""Có lỗi xảy ra khi tạo prompt. Tôi không thể trả lời câu hỏi "{query}" do thiếu thông tin ngữ cảnh cần thiết. Vui lòng thử lại hoặc cung cấp thêm thông tin."""

    # def create_related_questions_prompt(self, query: str, answer: str) -> str:
    #     """Tạo prompt để gợi ý 3 câu hỏi liên quan."""
    #     try:
    #         template = self._get_template_safely(TemplateType.RELATED_QUESTIONS.value)
    #         prompt = template.format(
    #             query=query.strip(), 
    #             answer=answer.strip()
    #         )
    #         return prompt
    #     except Exception as e:
    #         logger.error(f"Lỗi khi tạo related questions prompt: {str(e)}")
    #         return f"Hãy gợi ý 3 câu hỏi liên quan đến: {query}"

    def get_rag_prompt(self, query: str, context_text: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """Generate RAG prompt with context"""
        conversation_context = self._prepare_conversation_context(conversation_history)
        
        template = self._get_template_safely(self.default_template)
        
        prompt = template.format(
            query=query,
            context=context_text,
            conversation_context=conversation_context
        )
        
        return prompt

    def get_no_context_prompt(self, query: str) -> str:
        """Generate prompt when no context is available"""
        return f"""Bạn là một gia sư cơ sở dữ liệu thân thiện tên là DBR.

Câu hỏi: {query}

QUAN TRỌNG: Tôi không tìm thấy thông tin cụ thể trong tài liệu được cung cấp về chủ đề này. 

Do đó, tôi không thể trả lời câu hỏi này dựa trên nguồn tài liệu hiện có. Vui lòng:
- Thử đặt câu hỏi khác với từ khóa cụ thể hơn
- Kiểm tra xem câu hỏi có liên quan đến nội dung trong tài liệu không
- Hoặc cung cấp thêm tài liệu liên quan đến chủ đề này

Tôi chỉ có thể trả lời các câu hỏi dựa trên thông tin có trong tài liệu được cung cấp."""

    def get_sql_prompt(self, query: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """Generate SQL-specific prompt"""
        conversation_context = self._prepare_conversation_context(conversation_history)
        
        template = self._get_template_safely(TemplateType.SQL_CODE_TASK.value)
        
        return template.format(
            query=query,
            conversation_context=conversation_context
        )

    def get_realtime_question_prompt(self, query: str, search_results: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """Generate realtime question prompt"""
        conversation_context = self._prepare_conversation_context(conversation_history)
        
        template = self._get_template_safely(TemplateType.REALTIME_QUESTION.value)
        
        return template.format(
            query=query,
            search_results=search_results,
            conversation_context=conversation_context
        )

    def add_custom_template(self, template_name: str, template_content: str) -> bool:
        """Thêm template tùy chỉnh"""
        try:
            self.templates[template_name] = template_content
            logger.info(f"Đã thêm template tùy chỉnh: {template_name}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi thêm template tùy chỉnh: {str(e)}")
            return False

    def remove_template(self, template_name: str) -> bool:
        """Xóa template (không cho phép xóa template mặc định)"""
        if template_name == self.default_template:
            logger.warning(f"Không thể xóa template mặc định: {template_name}")
            return False
        
        if template_name in self.templates:
            try:
                del self.templates[template_name]
                logger.info(f"Đã xóa template: {template_name}")
                return True
            except Exception as e:
                logger.error(f"Lỗi khi xóa template: {str(e)}")
                return False
        else:
            logger.warning(f"Template không tồn tại: {template_name}")
            return False

    def list_templates(self) -> List[str]:
        """Liệt kê tất cả template có sẵn"""
        return list(self.templates.keys())

    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """Lấy thông tin chi tiết về template"""
        if template_name not in self.templates:
            return {"exists": False, "error": f"Template '{template_name}' không tồn tại"}
        
        template_content = self.templates[template_name]
        placeholders = re.findall(r'\{(\w+)\}', template_content)
        
        return {
            "exists": True,
            "name": template_name,
            "placeholders": list(set(placeholders)),
            "content_length": len(template_content),
            "is_default": template_name == self.default_template
        }

    def validate_template_format(self, template_content: str, required_placeholders: List[str]) -> Dict[str, Any]:
        """Validate template format và kiểm tra placeholder"""
        found_placeholders = re.findall(r'\{(\w+)\}', template_content)
        missing_placeholders = [p for p in required_placeholders if f"{{{p}}}" not in template_content]
        extra_placeholders = [p for p in found_placeholders if p not in required_placeholders]
        
        return {
            "is_valid": len(missing_placeholders) == 0,
            "missing_placeholders": missing_placeholders,
            "extra_placeholders": list(set(extra_placeholders)),
            "found_placeholders": list(set(found_placeholders))
        }

    def create_prompt_from_template(
        self, 
        template_name: str, 
        **kwargs
    ) -> str:
        """Tạo prompt từ template bất kỳ với các tham số động"""
        try:
            template = self._get_template_safely(template_name)
            
            # Tìm tất cả placeholder trong template
            placeholders = re.findall(r'\{(\w+)\}', template)
            
            # Chuẩn bị các giá trị cho placeholder
            format_values = {}
            for placeholder in set(placeholders):
                if placeholder in kwargs:
                    value = kwargs[placeholder]
                    # Xử lý đặc biệt cho một số placeholder
                    if placeholder == 'context' and isinstance(value, list):
                        format_values[placeholder] = self._create_context_str(value)
                    elif placeholder == 'conversation_context' and value:
                        format_values[placeholder] = self._prepare_conversation_context(value)
                    else:
                        format_values[placeholder] = str(value).strip() if value else ""
                else:
                    format_values[placeholder] = ""
                    logger.warning(f"Placeholder '{placeholder}' không được cung cấp, sử dụng giá trị rỗng")
            
            return template.format(**format_values)
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo prompt từ template '{template_name}': {str(e)}")
            # Fallback với quy tắc chống ảo giác
            query = kwargs.get('query', 'Câu hỏi không xác định')
            return f"""Có lỗi xảy ra khi tạo prompt từ template '{template_name}'. Tôi không thể trả lời câu hỏi "{query}" do thiếu thông tin ngữ cảnh cần thiết. Vui lòng thử lại hoặc cung cấp thêm thông tin."""

    def get_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê về các template"""
        total_templates = len(self.templates)
        template_stats = {}
        
        for name, content in self.templates.items():
            placeholders = re.findall(r'\{(\w+)\}', content)
            template_stats[name] = {
                "content_length": len(content),
                "placeholders": list(set(placeholders)),
                "placeholder_count": len(set(placeholders))
            }
        
        return {
            "total_templates": total_templates,
            "default_template": self.default_template,
            "template_details": template_stats
        }