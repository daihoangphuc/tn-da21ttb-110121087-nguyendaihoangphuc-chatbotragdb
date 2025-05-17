import logging
from typing import List, Dict
from src.llm import GeminiLLM

# Cấu hình logging
logging.basicConfig(format="[Suggestion Manager] %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Ghi đè hàm print để thêm prefix
original_print = print


def print(*args, **kwargs):
    prefix = "[Suggestion Manager] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)


class SuggestionManager:
    """
    Lớp quản lý việc đề xuất câu hỏi dựa trên lịch sử hội thoại
    """

    def __init__(self, llm=None):
        """
        Khởi tạo SuggestionManager với LLM

        Args:
            llm: Model ngôn ngữ để tạo đề xuất, nếu None sẽ tạo mới
        """
        self.llm = llm if llm else GeminiLLM()
        print("Đã khởi tạo SuggestionManager")

    def generate_question_suggestions(
        self, conversation_history: str, num_suggestions: int = 3
    ) -> List[str]:
        """
        Tạo đề xuất câu hỏi dựa trên lịch sử hội thoại

        Args:
            conversation_history: Chuỗi chứa lịch sử hội thoại
            num_suggestions: Số lượng câu hỏi đề xuất (mặc định: 3)

        Returns:
            Danh sách các câu hỏi đề xuất
        """
        # Nếu không có lịch sử hội thoại
        if not conversation_history or len(conversation_history.strip()) < 10:
            print("Lịch sử hội thoại quá ngắn hoặc trống, sử dụng đề xuất mặc định")
            return self._get_default_suggestions()

        print(f"Đang tạo {num_suggestions} đề xuất câu hỏi từ lịch sử hội thoại")

        # Tạo prompt để sinh đề xuất câu hỏi
        prompt = f"""
        Dưới đây là lịch sử hội thoại gần đây giữa người dùng và chatbot về cơ sở dữ liệu:
        
        {conversation_history}
        
        Dựa trên nội dung hội thoại trên, hãy tạo {num_suggestions} câu hỏi mới mà người dùng có thể quan tâm để tìm hiểu sâu hơn hoặc mở rộng kiến thức về chủ đề họ đang thảo luận. 
        
        Yêu cầu:
        1. Câu hỏi phải có liên quan mật thiết đến chủ đề trong lịch sử hội thoại
        2. Câu hỏi không được trùng lặp với những gì đã thảo luận
        3. Câu hỏi nên giúp người dùng khám phá sâu hơn, mở rộng kiến thức
        4. Câu hỏi nên phù hợp cho một người đang tìm hiểu về cơ sở dữ liệu
        5. Câu hỏi phải viết bằng tiếng Việt và phải có dấu câu hỏi ở cuối
        
        Chỉ trả về {num_suggestions} câu hỏi, mỗi câu hỏi trên một dòng, với định dạng:
        1. [Câu hỏi 1]
        2. [Câu hỏi 2]
        3. [Câu hỏi 3]
        
        Không cần thêm bất kỳ văn bản giải thích nào khác.
        """

        try:
            # Gọi LLM để sinh đề xuất
            response = self.llm.invoke(prompt)
            suggestions_text = response.content.strip()

            # Xử lý kết quả để trích xuất từng câu hỏi
            suggestions = []
            for line in suggestions_text.split("\n"):
                # Loại bỏ số thứ tự và khoảng trắng
                line = line.strip()
                if line and any(
                    line.startswith(f"{i}.") for i in range(1, num_suggestions + 1)
                ):
                    # Cắt bỏ số thứ tự và khoảng trắng
                    question = line.split(".", 1)[1].strip()
                    suggestions.append(question)

            # Đảm bảo đủ số lượng câu hỏi
            while len(suggestions) < num_suggestions:
                default_questions = self._get_default_suggestions()
                for q in default_questions:
                    if q not in suggestions:
                        suggestions.append(q)
                        if len(suggestions) >= num_suggestions:
                            break

            # Giới hạn số lượng câu hỏi
            suggestions = suggestions[:num_suggestions]
            print(f"Đã tạo {len(suggestions)} đề xuất câu hỏi")
            return suggestions

        except Exception as e:
            print(f"Lỗi khi tạo đề xuất câu hỏi: {str(e)}")
            return self._get_default_suggestions()

    def _get_default_suggestions(self) -> List[str]:
        """
        Trả về các câu hỏi đề xuất mặc định khi không có đủ thông tin

        Returns:
            Danh sách các câu hỏi đề xuất mặc định
        """
        return [
            "Các loại cơ sở dữ liệu phổ biến hiện nay là gì?",
            "Sự khác biệt giữa cơ sở dữ liệu quan hệ và NoSQL là gì?",
            "Làm thế nào để tối ưu hóa truy vấn SQL trong ứng dụng?",
            "Các mô hình dữ liệu cơ bản trong thiết kế cơ sở dữ liệu?",
            "Cách thiết kế schema cơ sở dữ liệu hiệu quả?",
            "Các cấp độ chuẩn hóa trong cơ sở dữ liệu quan hệ?",
            "Khi nào nên sử dụng index trong cơ sở dữ liệu?",
            "Các phương pháp backup và khôi phục cơ sở dữ liệu?",
        ]

    def extract_recent_conversation(
        self, full_history: List[Dict], max_messages: int = 10
    ) -> str:
        """
        Trích xuất đoạn hội thoại gần đây nhất từ lịch sử đầy đủ

        Args:
            full_history: Danh sách các tin nhắn trong lịch sử hội thoại
            max_messages: Số lượng tin nhắn tối đa để trích xuất

        Returns:
            Chuỗi chứa lịch sử hội thoại gần đây
        """
        if not full_history:
            return ""

        # Lấy max_messages tin nhắn gần nhất
        recent_messages = (
            full_history[-max_messages:]
            if len(full_history) > max_messages
            else full_history
        )

        # Định dạng thành chuỗi hội thoại
        conversation = ""
        for msg in recent_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role.lower() == "user":
                conversation += f"Người dùng: {content}\n\n"
            elif role.lower() in ["assistant", "bot", "ai"]:
                conversation += f"Chatbot: {content}\n\n"

        return conversation.strip()

    def get_suggestions_from_latest_conversation(
        self, user_id: str, conversation_manager, num_suggestions: int = 3
    ) -> List[str]:
        """
        Lấy đề xuất câu hỏi dựa trên cuộc hội thoại gần đây nhất có tin nhắn

        Args:
            user_id: ID người dùng
            conversation_manager: Đối tượng quản lý hội thoại (SupabaseConversationManager)
            num_suggestions: Số lượng câu hỏi đề xuất (mặc định: 3)

        Returns:
            Danh sách các câu hỏi đề xuất dựa trên hội thoại gần đây nhất
        """
        try:
            # Lấy cuộc hội thoại gần đây nhất có tin nhắn
            conversation_data = (
                conversation_manager.get_latest_conversation_with_messages(user_id)
            )

            if not conversation_data or "messages" not in conversation_data:
                print("Không tìm thấy cuộc hội thoại gần đây có tin nhắn")
                return self._get_default_suggestions()[:num_suggestions]

            # Trích xuất đoạn hội thoại gần đây từ danh sách tin nhắn
            messages = conversation_data["messages"]
            formatted_conversation = self.extract_recent_conversation(messages)

            if not formatted_conversation:
                print("Không thể định dạng hội thoại từ tin nhắn")
                return self._get_default_suggestions()[:num_suggestions]

            print(f"Đã tìm thấy cuộc hội thoại gần đây có {len(messages)} tin nhắn")

            # Tạo đề xuất từ lịch sử hội thoại đã định dạng
            suggestions = self.generate_question_suggestions(
                formatted_conversation, num_suggestions
            )
            return suggestions

        except Exception as e:
            print(f"Lỗi khi tạo đề xuất từ cuộc hội thoại gần đây: {str(e)}")
            return self._get_default_suggestions()[:num_suggestions]
