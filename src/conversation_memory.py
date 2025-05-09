from langchain.memory import ConversationBufferMemory
from typing import Dict, List, Optional
import datetime
import os
import json


class ConversationManager:
    """Lớp quản lý bộ nhớ hội thoại dựa trên ConversationBufferMemory"""

    def __init__(
        self, memory_key="chat_history", return_messages=True, output_key="answer"
    ):
        """Khởi tạo trình quản lý bộ nhớ hội thoại"""
        self.memories = {}  # Dictionary để lưu trữ bộ nhớ theo session_id
        self.memory_key = memory_key
        self.return_messages = return_messages
        self.output_key = output_key

        # Thư mục lưu trữ lịch sử hội thoại
        self.history_dir = os.path.join("src", "conversation_history")
        os.makedirs(self.history_dir, exist_ok=True)

    def get_memory(self, session_id: str) -> ConversationBufferMemory:
        """Lấy hoặc tạo bộ nhớ cho một phiên hội thoại cụ thể"""
        if session_id not in self.memories:
            # Tạo bộ nhớ mới nếu chưa tồn tại
            self.memories[session_id] = ConversationBufferMemory(
                memory_key=self.memory_key,
                return_messages=self.return_messages,
                output_key=self.output_key,
            )
        return self.memories[session_id]

    def add_user_message(self, session_id: str, message: str) -> None:
        """Thêm tin nhắn người dùng vào bộ nhớ"""
        memory = self.get_memory(session_id)
        memory.chat_memory.add_user_message(message)
        self._save_history(session_id)

    def add_ai_message(self, session_id: str, message: str) -> None:
        """Thêm tin nhắn AI vào bộ nhớ"""
        memory = self.get_memory(session_id)
        memory.chat_memory.add_ai_message(message)
        self._save_history(session_id)

    def get_conversation_history(self, session_id: str) -> str:
        """Lấy lịch sử cuộc hội thoại dưới dạng chuỗi văn bản"""
        memory = self.get_memory(session_id)
        return memory.load_memory_variables({})[self.memory_key]

    def get_messages(self, session_id: str) -> List[Dict]:
        """Lấy danh sách các tin nhắn trong hội thoại"""
        memory = self.get_memory(session_id)
        messages = []

        # Chuyển đổi từ dạng lưu trữ nội bộ sang danh sách tin nhắn
        for message in memory.chat_memory.messages:
            messages.append(
                {
                    "role": "user" if message.type == "human" else "assistant",
                    "content": message.content,
                }
            )

        return messages

    def clear_memory(self, session_id: str) -> None:
        """Xóa bộ nhớ cho một phiên hội thoại cụ thể"""
        if session_id in self.memories:
            self.memories[session_id].clear()
            self._save_history(session_id, is_cleared=True)

    def _save_history(self, session_id: str, is_cleared: bool = False) -> None:
        """Lưu lịch sử hội thoại ra file"""
        try:
            file_path = os.path.join(self.history_dir, f"{session_id}.json")

            if is_cleared:
                # Nếu đã xóa bộ nhớ, tạo dữ liệu trống
                history_data = {
                    "session_id": session_id,
                    "last_updated": datetime.datetime.now().isoformat(),
                    "messages": [],
                }
            else:
                # Lấy tin nhắn từ bộ nhớ
                messages = self.get_messages(session_id)
                history_data = {
                    "session_id": session_id,
                    "last_updated": datetime.datetime.now().isoformat(),
                    "messages": messages,
                }

            # Lưu ra file JSON
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"Lỗi khi lưu lịch sử hội thoại: {str(e)}")

    def load_history(self, session_id: str) -> bool:
        """Tải lịch sử hội thoại từ file"""
        try:
            file_path = os.path.join(self.history_dir, f"{session_id}.json")

            if not os.path.exists(file_path):
                return False

            with open(file_path, "r", encoding="utf-8") as f:
                history_data = json.load(f)

            # Xóa bộ nhớ hiện tại
            if session_id in self.memories:
                self.memories[session_id].clear()
            else:
                self.memories[session_id] = ConversationBufferMemory(
                    memory_key=self.memory_key,
                    return_messages=self.return_messages,
                    output_key=self.output_key,
                )

            # Thêm tin nhắn từ lịch sử
            memory = self.get_memory(session_id)
            for message in history_data.get("messages", []):
                if message["role"] == "user":
                    memory.chat_memory.add_user_message(message["content"])
                else:
                    memory.chat_memory.add_ai_message(message["content"])

            return True

        except Exception as e:
            print(f"Lỗi khi tải lịch sử hội thoại: {str(e)}")
            return False

    def format_for_prompt(self, session_id: str) -> str:
        """Định dạng lịch sử hội thoại để sử dụng trong prompt"""
        messages = self.get_messages(session_id)
        if not messages:
            return ""

        formatted_history = "LỊCH SỬ CUỘC HỘI THOẠI:\n"
        for i, message in enumerate(messages):
            if message["role"] == "user":
                formatted_history += f"Người dùng: {message['content']}\n"
            else:
                formatted_history += f"Trợ lý: {message['content']}\n"

        return formatted_history
