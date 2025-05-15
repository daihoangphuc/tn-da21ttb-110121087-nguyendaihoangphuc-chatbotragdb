-- Bảng lưu phiên làm việc chính
CREATE TABLE conversations (
  conversation_id    TEXT        PRIMARY KEY,                  -- Khóa chính duy nhất cho mỗi session
  user_id       UUID        NOT NULL,                     -- ID người dùng (IdentityUser.Id)
  last_updated  TIMESTAMP   NOT NULL DEFAULT now()        -- Thời gian cập nhật cuối cùng
);

-- Bảng lưu chi tiết các tin nhắn cho mỗi phiên
CREATE TABLE messages (
  message_id    BIGSERIAL   PRIMARY KEY,                  -- Khóa tự tăng
  conversation_id    TEXT        NOT NULL,                     -- Khóa ngoại liên kết về sessions.session_id
  sequence      INT         NOT NULL,                     -- Thứ tự tin nhắn trong phiên
  role          TEXT        NOT NULL CHECK (role IN ('user','assistant')), 
                                                    -- Vai trò: user hoặc assistant
  content       TEXT        NOT NULL,                     -- Nội dung tin nhắn
  CONSTRAINT fk_messages_conversations
    FOREIGN KEY (conversation_id)
    REFERENCES conversations(conversation_id)
    ON DELETE CASCADE
);

-- Tạo index để truy vấn nhanh các tin nhắn theo session và thứ tự
CREATE INDEX idx_messages_conversation_seq
  ON messages(conversation_id, sequence);
