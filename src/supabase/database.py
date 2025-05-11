"""
Supabase Database module for database operations.
"""

from typing import Dict, List, Optional, Any, Union
from .client import SupabaseClient


class SupabaseDatabase:
    """Class for managing database operations with Supabase"""

    def __init__(self, client=None):
        """Initialize the database module with a Supabase client"""
        if client:
            self.client = client
        else:
            self.client = SupabaseClient().get_client()

    def from_table(self, table_name: str):
        """Get a query builder for a specific table"""
        return self.client.table(table_name)

    def query(self, sql_query: str, params: Optional[Dict] = None):
        """Execute a raw SQL query"""
        return self.client.rpc("exec_sql", {"query": sql_query, "params": params or {}})

    # Conversation History Management

    def create_conversation_history_table(self):
        """Create the conversation and messages tables if they don't exist"""
        print("Đang cố gắng tạo bảng conversations và messages...")
        try:
            # Phương pháp 1: Sử dụng SQL trực tiếp qua REST API
            direct_sql = """
            -- 1. Bảng conversations lưu thông tin phiên
            CREATE TABLE IF NOT EXISTS conversations (
              id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
              session_id TEXT NOT NULL UNIQUE,
              user_id TEXT,
              last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              metadata JSONB
            );

            CREATE INDEX IF NOT EXISTS idx_conversations_user_id
              ON conversations(user_id);

            CREATE INDEX IF NOT EXISTS idx_conversations_last_updated
              ON conversations(last_updated);

            -- 2. Bảng messages lưu nội dung từng message
            CREATE TABLE IF NOT EXISTS messages (
              id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
              conversation_id UUID NOT NULL
                REFERENCES conversations(id) ON DELETE CASCADE,
              role TEXT NOT NULL CHECK (role IN ('user','assistant')),
              content TEXT NOT NULL,
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              metadata JSONB
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
              ON messages(conversation_id);

            CREATE INDEX IF NOT EXISTS idx_messages_created_at
              ON messages(created_at);
            """

            print("Thực thi SQL trực tiếp để tạo bảng...")
            # Phương pháp 1: Dùng SQL trực tiếp
            result = self.client.postgrest.rpc(
                "exec_sql", {"query": direct_sql}
            ).execute()
            print(f"Kết quả tạo bảng: {result}")
            return result

        except Exception as e:
            print(f"Lỗi khi tạo bảng qua SQL trực tiếp: {str(e)}")
            import traceback

            print(f"Chi tiết: {traceback.format_exc()}")

            # Phương pháp 2: Thử insert để xem bảng đã tồn tại chưa
            try:
                print("Thử phương pháp insert để tạo bảng...")
                # Tạo một conversation trước
                import uuid

                session_id = f"test_session_init_{uuid.uuid4().hex[:8]}"
                conversation_data = {
                    "session_id": session_id,
                    "last_updated": "NOW()",
                }
                conversation_result = (
                    self.client.table("conversations")
                    .insert(conversation_data)
                    .execute()
                )

                # Sau đó tạo một message
                if hasattr(conversation_result, "data") and conversation_result.data:
                    conversation_id = conversation_result.data[0].get("id")
                    message_data = {
                        "conversation_id": conversation_id,
                        "role": "system",
                        "content": "Khởi tạo bảng dữ liệu",
                    }
                    message_result = (
                        self.client.table("messages").insert(message_data).execute()
                    )
                    print(
                        f"Đã tạo bản ghi test thành công: {message_result.data if hasattr(message_result, 'data') else 'No data'}"
                    )

                return conversation_result
            except Exception as e2:
                print(f"Lỗi khi insert dữ liệu mẫu: {str(e2)}")

                # Phương pháp 3: Dùng RPC
                try:
                    print("Thử phương pháp RPC exec_sql...")
                    # Phương pháp gốc: RPC
                    sql = """
                    -- 1. Bảng conversations lưu thông tin phiên
                    CREATE TABLE IF NOT EXISTS conversations (
                      id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                      session_id TEXT NOT NULL UNIQUE,
                      user_id TEXT,
                      last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                      metadata JSONB
                    );

                    CREATE INDEX IF NOT EXISTS idx_conversations_user_id
                      ON conversations(user_id);

                    CREATE INDEX IF NOT EXISTS idx_conversations_last_updated
                      ON conversations(last_updated);

                    -- 2. Bảng messages lưu nội dung từng message
                    CREATE TABLE IF NOT EXISTS messages (
                      id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                      conversation_id UUID NOT NULL
                        REFERENCES conversations(id) ON DELETE CASCADE,
                      role TEXT NOT NULL CHECK (role IN ('user','assistant')),
                      content TEXT NOT NULL,
                      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                      metadata JSONB
                    );

                    CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
                      ON messages(conversation_id);

                    CREATE INDEX IF NOT EXISTS idx_messages_created_at
                      ON messages(created_at);
                    """
                    return self.query(sql)
                except Exception as e3:
                    print(f"Tất cả các phương pháp tạo bảng thất bại: {str(e3)}")
                    raise Exception(
                        "Không thể tạo bảng conversations và messages bằng bất kỳ phương pháp nào"
                    )

    def save_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Lưu tin nhắn vào cơ sở dữ liệu với cấu trúc bảng mới

        Args:
            session_id: ID phiên hội thoại
            role: Vai trò ('user' hoặc 'assistant')
            content: Nội dung tin nhắn
            user_id: ID người dùng (nếu có)
            metadata: Metadata bổ sung (nếu có)

        Returns:
            Bản ghi đã tạo
        """
        print(
            f"Lưu tin nhắn: session_id={session_id}, role={role}, content={content[:30]}..."
        )

        # Đảm bảo dữ liệu đúng định dạng
        if role not in ["user", "assistant", "system"]:
            print(f"Warning: Role '{role}' không hợp lệ, đang sử dụng 'user' thay thế")
            role = "user"

        # Kiểm tra session_id không được để trống
        if not session_id:
            print("Warning: session_id rỗng, đang tạo ID ngẫu nhiên")
            import uuid

            session_id = f"session_{uuid.uuid4().hex[:8]}"

        # Kiểm tra content không được để trống
        if not content:
            content = "<empty message>"

        try:
            # Bước 1: Kiểm tra và tạo conversation nếu chưa tồn tại
            conv_table = self.from_table("conversations")
            conv_result = conv_table.select("id").eq("session_id", session_id).execute()

            if hasattr(conv_result, "data") and len(conv_result.data) > 0:
                # Conversation đã tồn tại
                conversation_id = conv_result.data[0]["id"]
                print(f"Conversation đã tồn tại với id: {conversation_id}")

                # Cập nhật last_updated
                conv_table.update({"last_updated": "NOW()"}).eq(
                    "id", conversation_id
                ).execute()
            else:
                # Tạo conversation mới
                conv_data = {"session_id": session_id, "last_updated": "NOW()"}

                if user_id:
                    conv_data["user_id"] = user_id

                conv_insert = conv_table.insert(conv_data).execute()

                if not hasattr(conv_insert, "data") or not conv_insert.data:
                    raise Exception("Không thể tạo conversation mới")

                conversation_id = conv_insert.data[0]["id"]
                print(f"Đã tạo conversation mới với id: {conversation_id}")

            # Bước 2: Thêm tin nhắn vào bảng messages
            message_data = {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
            }

            if metadata:
                # Đảm bảo metadata là JSON hợp lệ
                import json

                try:
                    # Kiểm tra bằng cách encode/decode
                    json.dumps(metadata)
                    message_data["metadata"] = metadata
                except Exception as e:
                    print(
                        f"Warning: Metadata không phải JSON hợp lệ ({str(e)}), sẽ bỏ qua"
                    )

            # Lưu tin nhắn
            msg_table = self.from_table("messages")
            result = msg_table.insert(message_data).execute()

            print(
                f"Kết quả lưu tin nhắn: ID = {result.data[0].get('id') if hasattr(result, 'data') and result.data else 'không có ID'}"
            )
            return result

        except Exception as e:
            print(f"Lỗi khi lưu tin nhắn vào database: {str(e)}")
            import traceback

            print(f"Chi tiết lỗi: {traceback.format_exc()}")
            raise e

    def get_conversation_history(self, session_id: str, limit: int = 100) -> List[Dict]:
        """
        Lấy lịch sử hội thoại cho một phiên cụ thể với cấu trúc bảng mới

        Args:
            session_id: ID phiên hội thoại
            limit: Số lượng tin nhắn tối đa cần lấy

        Returns:
            Danh sách tin nhắn của cuộc hội thoại, sắp xếp theo thời gian
        """
        try:
            # Bước 1: Lấy conversation_id từ session_id
            conv_result = (
                self.from_table("conversations")
                .select("id")
                .eq("session_id", session_id)
                .execute()
            )

            if not hasattr(conv_result, "data") or not conv_result.data:
                print(f"Không tìm thấy conversation với session_id: {session_id}")
                return []

            conversation_id = conv_result.data[0]["id"]

            # Bước 2: Lấy tin nhắn từ bảng messages
            msg_result = (
                self.from_table("messages")
                .select("*")
                .eq("conversation_id", conversation_id)
                .order("created_at")
                .limit(limit)
                .execute()
            )

            if not hasattr(msg_result, "data"):
                return []

            # Chuyển đổi định dạng để tương thích với code cũ
            messages = []
            for msg in msg_result.data:
                message = {
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg["created_at"],  # Đổi tên trường để tương thích
                }

                if "metadata" in msg and msg["metadata"]:
                    message["metadata"] = msg["metadata"]

                messages.append(message)

            return messages

        except Exception as e:
            print(f"Lỗi khi lấy lịch sử hội thoại: {str(e)}")
            import traceback

            print(f"Chi tiết lỗi: {traceback.format_exc()}")
            return []

    def clear_conversation_history(self, session_id: str) -> Dict:
        """
        Xóa tất cả tin nhắn trong một phiên hội thoại nhưng giữ lại phiên

        Args:
            session_id: ID phiên hội thoại

        Returns:
            Kết quả của thao tác
        """
        try:
            # Bước 1: Lấy conversation_id từ session_id
            conv_result = (
                self.from_table("conversations")
                .select("id")
                .eq("session_id", session_id)
                .execute()
            )

            if not hasattr(conv_result, "data") or not conv_result.data:
                print(f"Không tìm thấy conversation với session_id: {session_id}")
                return {"error": "Không tìm thấy phiên hội thoại"}

            conversation_id = conv_result.data[0]["id"]

            # Bước 2: Xóa tất cả tin nhắn của conversation này
            # (giữ lại conversation để có thể thêm tin nhắn mới)
            result = (
                self.from_table("messages")
                .delete()
                .eq("conversation_id", conversation_id)
                .execute()
            )

            # Bước 3: Cập nhật last_updated cho conversation
            self.from_table("conversations").update({"last_updated": "NOW()"}).eq(
                "id", conversation_id
            ).execute()

            return result

        except Exception as e:
            print(f"Lỗi khi xóa lịch sử hội thoại: {str(e)}")
            import traceback

            print(f"Chi tiết lỗi: {traceback.format_exc()}")
            return {"error": str(e)}

    # User Feedback Management

    def create_feedback_table(self):
        """Create the feedback table if it doesn't exist"""
        sql = """
        CREATE TABLE IF NOT EXISTS user_feedback (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            question_id TEXT NOT NULL,
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            is_helpful BOOLEAN,
            comment TEXT,
            specific_feedback JSONB,
            user_id TEXT,
            timestamp TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Create indexes for faster queries
        CREATE INDEX IF NOT EXISTS idx_user_feedback_question_id ON user_feedback(question_id);
        CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON user_feedback(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_feedback_timestamp ON user_feedback(timestamp);
        """
        return self.query(sql)

    def save_feedback(
        self,
        question_id: str,
        rating: int,
        is_helpful: bool,
        comment: Optional[str] = None,
        specific_feedback: Optional[Dict] = None,
        user_id: Optional[str] = None,
    ) -> Dict:
        """
        Save user feedback to the database

        Args:
            question_id: ID of the question being rated
            rating: Numerical rating (1-5)
            is_helpful: Whether the response was helpful
            comment: Optional comment text
            specific_feedback: Optional structured feedback
            user_id: Optional ID of the user providing feedback

        Returns:
            The created record
        """
        table = self.from_table("user_feedback")

        data = {"question_id": question_id, "rating": rating, "is_helpful": is_helpful}

        if comment:
            data["comment"] = comment

        if specific_feedback:
            data["specific_feedback"] = specific_feedback

        if user_id:
            data["user_id"] = user_id

        return table.insert(data).execute()

    def get_feedback_stats(self) -> Dict:
        """
        Get aggregated feedback statistics

        Returns:
            Dictionary with feedback statistics
        """
        sql = """
        SELECT 
            COUNT(*) as total_feedback,
            AVG(rating) as average_rating,
            SUM(CASE WHEN is_helpful THEN 1 ELSE 0 END) as helpful_count,
            SUM(CASE WHEN NOT is_helpful THEN 1 ELSE 0 END) as not_helpful_count
        FROM user_feedback
        """
        response = self.query(sql)
        if response and hasattr(response, "data") and len(response.data) > 0:
            return response.data[0]
        return {
            "total_feedback": 0,
            "average_rating": 0,
            "helpful_count": 0,
            "not_helpful_count": 0,
        }

    # Document Metadata Management

    def create_document_metadata_table(self):
        """Create the document metadata table if it doesn't exist"""
        sql = """
        CREATE TABLE IF NOT EXISTS document_metadata (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT,
            file_size INTEGER,
            upload_date TIMESTAMPTZ DEFAULT NOW(),
            user_id TEXT,
            category TEXT,
            title TEXT,
            description TEXT,
            is_indexed BOOLEAN DEFAULT FALSE,
            last_indexed TIMESTAMPTZ,
            metadata JSONB
        );
        
        -- Create indexes for faster queries
        CREATE INDEX IF NOT EXISTS idx_document_metadata_filename ON document_metadata(filename);
        CREATE INDEX IF NOT EXISTS idx_document_metadata_user_id ON document_metadata(user_id);
        CREATE INDEX IF NOT EXISTS idx_document_metadata_category ON document_metadata(category);
        """
        return self.query(sql)

    def save_document_metadata(
        self,
        filename: str,
        file_path: str,
        file_type: Optional[str] = None,
        file_size: Optional[int] = None,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Save document metadata to the database

        Args:
            filename: Name of the file
            file_path: Path to the file (in storage)
            file_type: Type of the file (extension)
            file_size: Size of the file in bytes
            user_id: ID of the user who uploaded the file
            category: Category of the document
            title: Title of the document
            description: Description of the document
            metadata: Additional metadata

        Returns:
            The created record
        """
        table = self.from_table("document_metadata")

        data = {"filename": filename, "file_path": file_path}

        if file_type:
            data["file_type"] = file_type

        if file_size:
            data["file_size"] = file_size

        if user_id:
            data["user_id"] = user_id

        if category:
            data["category"] = category

        if title:
            data["title"] = title

        if description:
            data["description"] = description

        if metadata:
            data["metadata"] = metadata

        return table.insert(data).execute()

    def get_document_metadata(
        self, filename: str = None, user_id: str = None
    ) -> List[Dict]:
        """
        Get document metadata from the database

        Args:
            filename: Optional filename to filter by
            user_id: Optional user ID to filter by

        Returns:
            List of document metadata records
        """
        table = self.from_table("document_metadata")
        query = table.select("*")

        if filename:
            query = query.eq("filename", filename)

        if user_id:
            query = query.eq("user_id", user_id)

        response = query.execute()
        return response.data

    def update_document_indexed_status(
        self, filename: str, is_indexed: bool = True
    ) -> Dict:
        """
        Update the indexed status of a document

        Args:
            filename: Name of the file
            is_indexed: Whether the document has been indexed

        Returns:
            The updated record
        """
        table = self.from_table("document_metadata")
        data = {"is_indexed": is_indexed, "last_indexed": "NOW()"}

        return table.update(data).eq("filename", filename).execute()

    def delete_document_metadata(self, filename: str) -> Dict:
        """
        Delete document metadata from the database

        Args:
            filename: Name of the file

        Returns:
            Result of the operation
        """
        table = self.from_table("document_metadata")
        return table.delete().eq("filename", filename).execute()
