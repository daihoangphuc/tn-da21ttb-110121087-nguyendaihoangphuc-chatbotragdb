import os
import json


class ConversationMemory:
    def clear_memory(self, conversation_id, user_id=None):
        """Xóa tất cả các tin nhắn trong một cuộc hội thoại nhưng giữ nguyên cuộc hội thoại đó"""
        try:
            # Nếu đang sử dụng Supabase, gọi phương thức clear_conversation_history
            if hasattr(self.database, "clear_conversation_history"):
                return self.database.clear_conversation_history(
                    conversation_id, user_id
                )

            # Còn không, xóa file history hiện tại và tạo mới một file rỗng
            file_path = os.path.join(
                self._get_user_history_dir(user_id), f"{conversation_id}.json"
            )

            # Nếu file không tồn tại, kiểm tra ở thư mục gốc
            if not os.path.exists(file_path):
                root_file_path = os.path.join(
                    self.history_dir, f"{conversation_id}.json"
                )
                if os.path.exists(root_file_path):
                    file_path = root_file_path

            # Nếu file tồn tại, xóa nội dung nhưng giữ lại file
            if os.path.exists(file_path):
                with open(file_path, "w") as f:
                    json.dump([], f)
                return True

            return False
        except Exception as e:
            print(f"Lỗi khi xóa bộ nhớ hội thoại: {str(e)}")
            return False

    def delete_conversation(self, conversation_id, user_id=None):
        """Xóa hoàn toàn một cuộc hội thoại"""
        try:
            # Nếu đang sử dụng Supabase, gọi phương thức delete_conversation
            if hasattr(self.database, "delete_conversation"):
                return self.database.delete_conversation(conversation_id, user_id)

            # Còn không, xóa file history
            user_dir = self._get_user_history_dir(user_id)
            file_path = os.path.join(user_dir, f"{conversation_id}.json")

            # Nếu file không tồn tại trong thư mục user, kiểm tra trong thư mục gốc
            if not os.path.exists(file_path):
                root_file_path = os.path.join(
                    self.history_dir, f"{conversation_id}.json"
                )
                if os.path.exists(root_file_path):
                    file_path = root_file_path

            # Nếu file tồn tại, xóa file
            if os.path.exists(file_path):
                os.remove(file_path)
            return True

            return False
        except Exception as e:
            print(f"Lỗi khi xóa cuộc hội thoại: {str(e)}")
            return False
