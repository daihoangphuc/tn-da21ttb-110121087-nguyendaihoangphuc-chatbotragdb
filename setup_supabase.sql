-- Tạo bảng conversation_history
CREATE TABLE IF NOT EXISTS conversation_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT NOT NULL,
    user_id TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    metadata JSONB
);
        
-- Tạo indexes để tìm kiếm nhanh hơn
CREATE INDEX IF NOT EXISTS idx_conversation_history_session_id ON conversation_history(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_user_id ON conversation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_timestamp ON conversation_history(timestamp);


-- Tạo bảng user_feedback
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
        
-- Tạo indexes để tìm kiếm nhanh hơn
CREATE INDEX IF NOT EXISTS idx_user_feedback_question_id ON user_feedback(question_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_timestamp ON user_feedback(timestamp);

-- Tạo bảng document_metadata
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
        
-- Tạo indexes để tìm kiếm nhanh hơn
CREATE INDEX IF NOT EXISTS idx_document_metadata_filename ON document_metadata(filename);
CREATE INDEX IF NOT EXISTS idx_document_metadata_user_id ON document_metadata(user_id);
CREATE INDEX IF NOT EXISTS idx_document_metadata_category ON document_metadata(category);