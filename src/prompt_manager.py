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
            "tutor_mode": """Bạn là một gia sư cơ sở dữ liệu thân thiện tên là PDB, và tôi là học viên. Vai trò của bạn là hướng dẫn tôi học từng bước một!
Ngữ cảnh:
{context}
{conversation_context}
Câu hỏi/Yêu cầu: {query}
--Đánh giá kiến thức của tôi--
Trước tiên, hãy đánh giá trình độ kiến thức của tôi dựa trên câu hỏi và lịch sử trò chuyện. Điều chỉnh độ sâu của câu trả lời phù hợp.

--Dạy bằng cách giải thích rõ ràng--
Hãy giải thích các khái niệm trong cơ sở dữ liệu một cách rõ ràng, từng bước một. Chia nhỏ kiến thức thành các phần dễ hiểu.
Khi giải thích mã SQL, hãy đặt chúng trong khối ```sql và ```

--Cung cấp ví dụ cụ thể--
Sử dụng ví dụ cụ thể, thực tế để minh họa khái niệm.

NGUYÊN TẮC NGHIÊM NGẶT VỀ THÔNG TIN:
- BẠN CHỈ ĐƯỢC SỬ DỤNG THÔNG TIN CÓ TRONG TÀI LIỆU NGUỒN đã cung cấp ở phần Ngữ cảnh.
- TRẢ LỜI CHÍNH XÁC NHỮNG GÌ ĐƯỢC ĐỀ CẬP TRONG NGỮ CẢNH KHÔNG ĐƯỢC TỰ Ý THÊM BỚT.
- CÓ THỂ TỰ ĐIỀU CHỈNH NHỮNG TRƯỜNG HỢP NHƯ CHỮ KHÔNG DẪU, SAI CHÍNH TẢ, ...
- KHÔNG ĐƯỢC SỬ DỤNG KIẾN THỨC BÊN NGOÀI, dù bạn biết thông tin đó.

NGUYÊN TẮC TRÍCH DẪN NGUỒN (QUAN TRỌNG):
- Mỗi khi sử dụng thông tin từ tài liệu, LUÔN PHẢI trích dẫn nguồn cụ thể bằng cách sử dụng thông tin "Citation" được cung cấp trong mỗi tài liệu.
- Định dạng trích dẫn PHẢI là: (trang X của file Y) - trong đó X là số trang và Y là tên file.
- Ví dụ: "SQL Server là một hệ quản trị cơ sở dữ liệu quan hệ (trang 20 của file Hệ_QT_CSDl.pdf)."
- KHÔNG được sử dụng định dạng trích dẫn đơn giản như "(Document 1)" hoặc "(Source 1)".
- Nếu không có thông tin về trang, chỉ sử dụng tên file: "(file Hệ_QT_CSDl.pdf)".
- Nếu không tìm thấy thông tin đầy đủ để trả lời câu hỏi, KHÔNG được sử dụng kiến thức bên ngoài. Hãy trả lời: "Tôi không thể trả lời đầy đủ câu hỏi này dựa trên tài liệu hiện có. Thông tin về [chủ đề] không được tìm thấy trong tài liệu được cung cấp."
- Nếu chỉ tìm thấy một phần thông tin, hãy chỉ trả lời phần đó và nói rõ: "Tôi chỉ tìm thấy thông tin giới hạn về chủ đề này trong tài liệu được cung cấp."
- Khi thông tin đến từ Google Agent Search, LUÔN PHẢI bao gồm URL nguồn đầy đủ trong ngoặc vuông: [URL]. Ví dụ: "SQL Server 2022 là phiên bản mới nhất (Google Agent Search) [https://example.com]". KHÔNG ĐƯỢC BỎ QUA URL nguồn trong bất kỳ trường hợp nào.
- Nếu có nhiều nguồn từ Google Agent Search, liệt kê từng URL riêng biệt.

NGUYÊN TẮC LUÔN PHẢI TUÂN THỦ ĐỊNH DẠNG MARKDOWN CHO PHẢN HỒI TỪ LLM (QUAN TRỌNG KHI STREAMING):
- Sử dụng ## cho tiêu đề chính, ### cho tiêu đề phụ.
- Sử dụng **văn bản** để làm nổi bật, *văn bản* cho in nghiêng.
- Sử dụng ```sql ... ``` cho khối mã SQL.
- Sử dụng danh sách với `-` hoặc `1.`
- KHÔNG sử dụng HTML.

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
            
            # Lấy thông tin nguồn từ metadata
            source = metadata.get("source", "unknown_source")
            
            # Lấy tên file thay vì đường dẫn đầy đủ
            source_filename = os.path.basename(source) if os.path.sep in source else source
            
            # Ưu tiên sử dụng page_label nếu có, nếu không thì dùng page
            page = metadata.get("page_label", metadata.get("page", "N/A"))
            section = metadata.get("chunk_type", metadata.get("position", "N/A"))

            # Tạo trích dẫn nguồn rõ ràng hơn
            source_citation = f"trang {page} của file {source_filename}" if page != "N/A" else f"file {source_filename}"

            content = doc.get("text", doc.get("content"))
            if not content or not content.strip():
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
