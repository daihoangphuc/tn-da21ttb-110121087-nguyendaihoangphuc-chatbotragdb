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







-- Tạo bảng document_files để lưu trữ thông tin file
CREATE TABLE document_files (
  file_id UUID PRIMARY KEY,
  filename TEXT NOT NULL,
  file_path TEXT NOT NULL,
  user_id UUID NOT NULL REFERENCES auth.users(id),
  upload_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  file_type TEXT,
  is_deleted BOOLEAN DEFAULT FALSE,
  deleted_at TIMESTAMPTZ,
  metadata JSONB
);

-- Tạo index để tìm kiếm nhanh
CREATE INDEX idx_document_files_user_id ON document_files(user_id);
CREATE INDEX idx_document_files_filename ON document_files(filename);
CREATE INDEX idx_document_files_upload_time ON document_files(upload_time);


-- Policy để mỗi người dùng chỉ thấy file của mình
CREATE POLICY "Người dùng chỉ thấy file của mình" 
ON document_files FOR SELECT 
USING (auth.uid() = user_id);

-- Policy cho phép người dùng tạo file của mình
CREATE POLICY "Người dùng có thể tạo file" 
ON document_files FOR INSERT 
WITH CHECK (auth.uid() = user_id);

-- Policy cho phép người dùng cập nhật file của mình
CREATE POLICY "Người dùng có thể cập nhật file của mình" 
ON document_files FOR UPDATE 
USING (auth.uid() = user_id);

-- Policy cho phép người dùng xóa file của mình
CREATE POLICY "Người dùng có thể xóa file của mình" 
ON document_files FOR DELETE 
USING (auth.uid() = user_id);