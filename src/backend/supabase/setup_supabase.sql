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


CREATE POLICY "Only admin can insert files" ON document_files
FOR INSERT
USING (
    EXISTS (
        SELECT 1 FROM user_roles
        WHERE user_id = auth.uid() AND role = 'admin'
    )
);

-- **NEW: Policy cho phép admin xóa tất cả file**
CREATE POLICY "Admin can delete all files" ON document_files
FOR DELETE
USING (
    EXISTS (
        SELECT 1 FROM user_roles
        WHERE user_id = auth.uid() AND role = 'admin'
    )
);

-- **NEW: Policy cho phép admin cập nhật tất cả file**
CREATE POLICY "Admin can update all files" ON document_files
FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM user_roles
        WHERE user_id = auth.uid() AND role = 'admin'
    )
);

-- **NEW: Policy cho phép admin xem tất cả file**
CREATE POLICY "Admin can view all files" ON document_files
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM user_roles
        WHERE user_id = auth.uid() AND role = 'admin'
    )
);

-- Tạo bảng user_roles
CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Policies cho user_roles
CREATE POLICY "Người dùng chỉ thấy role của mình" 
ON user_roles FOR SELECT 
USING (auth.uid() = user_id);

-- Policies cho conversations
CREATE POLICY "Người dùng chỉ thấy hội thoại của mình" 
ON conversations FOR SELECT 
USING (auth.uid() = user_id);

CREATE POLICY "Người dùng có thể tạo hội thoại" 
ON conversations FOR INSERT 
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Người dùng có thể cập nhật hội thoại của mình" 
ON conversations FOR UPDATE 
USING (auth.uid() = user_id);

CREATE POLICY "Người dùng có thể xóa hội thoại của mình" 
ON conversations FOR DELETE 
USING (auth.uid() = user_id);

-- Policies cho messages
CREATE POLICY "Người dùng chỉ thấy tin nhắn của hội thoại mình" 
ON messages FOR SELECT 
USING (
    EXISTS (
        SELECT 1 FROM conversations 
        WHERE conversations.conversation_id = messages.conversation_id 
        AND conversations.user_id = auth.uid()
    )
);

CREATE POLICY "Người dùng có thể tạo tin nhắn trong hội thoại của mình" 
ON messages FOR INSERT 
WITH CHECK (
    EXISTS (
        SELECT 1 FROM conversations 
        WHERE conversations.conversation_id = messages.conversation_id 
        AND conversations.user_id = auth.uid()
    )
);

CREATE POLICY "Người dùng có thể cập nhật tin nhắn trong hội thoại của mình" 
ON messages FOR UPDATE 
USING (
    EXISTS (
        SELECT 1 FROM conversations 
        WHERE conversations.conversation_id = messages.conversation_id 
        AND conversations.user_id = auth.uid()
    )
);

CREATE POLICY "Người dùng có thể xóa tin nhắn trong hội thoại của mình" 
ON messages FOR DELETE 
USING (
    EXISTS (
        SELECT 1 FROM conversations 
        WHERE conversations.conversation_id = messages.conversation_id 
        AND conversations.user_id = auth.uid()
    )
);