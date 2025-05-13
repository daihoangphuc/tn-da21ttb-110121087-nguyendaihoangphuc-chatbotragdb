import re
from typing import List, Dict
import os


class PromptManager:
    """Lớp quản lý các prompt khác nhau cho hệ thống RAG"""

    def __init__(self):
        """Khởi tạo quản lý prompt"""
        # Sử dụng tutor_mode làm template mặc định duy nhất
        self.templates = {
            "tutor_mode": """
            Bạn là một gia sư cơ sở dữ liệu thân thiện tên là PDB, và tôi là học viên. Vai trò của bạn là hướng dẫn tôi học từng bước một!

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
            Sử dụng ví dụ cụ thể, thực tế để minh họa khái niệm. Nếu phù hợp, hãy đề xuất các bài tập ngắn để tôi có thể thực hành.

            NGUYÊN TẮC TRÍCH DẪN:
            - Khi sử dụng thông tin từ tài liệu, đặt nguồn trong ngoặc đơn: (nguồn)
            - Nếu không có thông tin trong tài liệu, hãy nói rõ "Tôi không tìm thấy thông tin về [chủ đề] trong tài liệu được cung cấp."

            NGUYÊN TẮC ĐỊNH DẠNG MARKDOWN:
            - Sử dụng ## cho tiêu đề chính, ### cho tiêu đề phụ
            - Sử dụng **văn bản** để làm nổi bật nội dung quan trọng
            - Sử dụng ```sql và ``` cho khối mã SQL
            - Sử dụng danh sách có dấu gạch đầu dòng (-) và có số (1. 2. 3.)
            - KHÔNG sử dụng HTML, chỉ dùng Markdown
            - KHI CÂU TRẢ LỜI DẠNG BẢNG NHƯNG QUÁ DÀI THÌ HÃY TRẢ LỜI DẠNG LIỆT KÊ
            
            TRƯỜNG HỢP BẠN KHÔNG TRẢ LỜI ĐƯỢC:
            - Phân tích câu hỏi để xác định thiếu sót VÀ hãy hỏi lại người dùng để khai thác thêm thống tin
            """,
            # Giữ lại template gợi ý câu hỏi liên quan
            "related_questions": """
            Bạn là một trợ lý thông minh chuyên tạo câu hỏi để khuyến khích người dùng tiếp tục tìm hiểu về chủ đề.
            
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
            
            QUAN TRỌNG: Chỉ trả về 3 câu hỏi theo đúng format trên, KHÔNG có nội dung giới thiệu hoặc kết luận. Mỗi câu hỏi phải là câu hoàn chỉnh kết thúc bằng dấu hỏi.
            """,
        }

        # Sử dụng template tutor_mode làm mặc định
        self.default_template = "tutor_mode"

    def classify_question(self, query: str) -> str:
        """Phân loại câu hỏi - luôn trả về template mặc định (tutor_mode)"""
        # Để tương thích với code gọi phương thức này, chỉ trả về template mặc định
        return self.default_template

    def _create_context_str(self, context: List[Dict]) -> str:
        """Phương thức phụ trợ để tạo chuỗi ngữ cảnh từ danh sách tài liệu"""
        context_entries = []
        for i, doc in enumerate(context):
            metadata = doc.get("metadata", {})
            source = metadata.get("source", doc.get("source", "unknown"))
            page = metadata.get("page", "unknown")
            section = metadata.get("chunk_type", metadata.get("position", "unknown"))

            # Chuẩn bị tên nguồn tham khảo ngắn gọn
            source_ref = source
            if os.path.sep in source:  # Nếu là đường dẫn file
                source_ref = os.path.basename(source)  # Chỉ lấy tên file

            # Tạo tham chiếu ngắn gọn nếu có số trang
            if page != "unknown":
                source_citation = f"{source_ref}:{page}"
            else:
                source_citation = source_ref

            context_entry = (
                f"[Document {i+1}]\n"
                f"Source: {source}\n"
                f"Citation: {source_citation}\n"
                f"Page/Position: {page}\n"
                f"Section: {section}\n"
                f"Content: {doc['text']}"
            )
            context_entries.append(context_entry)

        return "\n\n".join(context_entries)

    def create_prompt(
        self, query: str, context: List[Dict], question_type: str = None
    ) -> str:
        """Tạo prompt với template tutor_mode"""
        # Tạo văn bản ngữ cảnh
        context_str = self._create_context_str(context)

        # Không có lịch sử hội thoại
        conversation_context = ""

        # Xử lý đặc biệt cho câu hỏi so sánh
        if "so sánh" in query.lower():
            special_instruction = """
            
            ĐÂY LÀ HƯỚNG DẪN CHO CÂU HỎI DẠNG SO SÁNH:
            
            Trong trường hợp câu hỏi so sánh, hãy sử dụng một trong hai cách sau:
            
            1. Bảng đơn giản (nếu có ít thông tin):
               | Tiêu chí | Khái niệm A | Khái niệm B |
               |----------|-------------|-------------|
               | Định nghĩa | ... | ... |
               
            2. Hoặc dùng danh sách (nếu thông tin dài):
               **Khái niệm A:**
               - Định nghĩa: ...
               - Đặc điểm: ...
               
               **Khái niệm B:**
               - Định nghĩa: ...
               - Đặc điểm: ...
            """

            # Thêm hướng dẫn đặc biệt vào đầu prompt
            prompt = self.templates[self.default_template].format(
                context=context_str,
                query=query + special_instruction,
                conversation_context=conversation_context,
            )
        else:
            prompt = self.templates[self.default_template].format(
                context=context_str,
                query=query,
                conversation_context=conversation_context,
            )
        return prompt

    def create_prompt_with_history(
        self,
        query: str,
        context: List[Dict],
        question_type: str = None,
        conversation_history: str = "",
    ) -> str:
        """Tạo prompt với lịch sử hội thoại và template tutor_mode"""
        # Tạo văn bản ngữ cảnh
        context_str = self._create_context_str(context)

        # Nếu có lịch sử hội thoại, thêm vào ngữ cảnh
        conversation_context = ""
        if conversation_history and len(conversation_history.strip()) > 0:
            conversation_context = f"""
            NGỮ CẢNH CUỘC HỘI THOẠI:
            {conversation_history}
            """

        # Xử lý đặc biệt cho câu hỏi so sánh
        if "so sánh" in query.lower():
            special_instruction = """

            ĐÂY LÀ HƯỚNG DẪN CHO CÂU HỎI DẠNG SO SÁNH:
            
            Trong trường hợp câu hỏi so sánh, hãy sử dụng một trong hai cách sau:
            
            1. Bảng đơn giản (nếu có ít thông tin):
               | Tiêu chí | Khái niệm A | Khái niệm B |
               |----------|-------------|-------------|
               | Định nghĩa | ... | ... |
               
            2. Hoặc dùng danh sách (nếu thông tin dài):
               **Khái niệm A:**
               - Định nghĩa: ...
               - Đặc điểm: ...
               
               **Khái niệm B:**
               - Định nghĩa: ...
               - Đặc điểm: ...
            """

            # Thêm hướng dẫn đặc biệt vào đầu prompt
            prompt = self.templates[self.default_template].format(
                context=context_str,
                query=query + special_instruction,
                conversation_context=conversation_context,
            )
        else:
            prompt = self.templates[self.default_template].format(
                context=context_str,
                query=query,
                conversation_context=conversation_context,
            )
        return prompt

    def create_related_questions_prompt(self, query: str, answer: str) -> str:
        """Tạo prompt để gợi ý 3 câu hỏi liên quan"""
        prompt = self.templates["related_questions"].format(query=query, answer=answer)
        return prompt
