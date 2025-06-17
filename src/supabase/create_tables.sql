-- Tạo bảng document_files nếu chưa tồn tại
CREATE TABLE IF NOT EXISTS document_files (
    file_id UUID PRIMARY KEY,
    filename TEXT,
    file_path TEXT,
    user_id UUID,
    file_type TEXT,
    upload_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Tạo bảng user_roles nếu chưa tồn tại
CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Bật RLS cho bảng document_files
ALTER TABLE document_files ENABLE ROW LEVEL SECURITY;

-- Tạo policy cho phép tất cả người dùng xem tài liệu
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'document_files' AND policyname = 'Users can view all files'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can view all files" ON document_files
        FOR SELECT
        USING (true)';
    END IF;
END
$$;

-- Tạo policy chỉ cho phép admin thêm tài liệu
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE tablename = 'document_files'
      AND policyname = 'Only admin can insert files'
  ) THEN
    EXECUTE '
      CREATE POLICY "Only admin can insert files"
        ON document_files
       FOR INSERT
       TO authenticated
    WITH CHECK (
      EXISTS (
        SELECT 1
          FROM user_roles
         WHERE user_id = auth.uid()
           AND role    = ''admin''
      )
    )';
  END IF;
END
$$;


-- Tạo policy chỉ cho phép admin cập nhật tài liệu của họ
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'document_files' AND policyname = 'Only admin can update their files'
    ) THEN
        EXECUTE 'CREATE POLICY "Only admin can update their files" ON document_files
        FOR UPDATE
        USING (
            EXISTS (
                SELECT 1 FROM user_roles
                WHERE user_id = auth.uid() AND role = ''admin''
            ) AND user_id = auth.uid()
        )';
    END IF;
END
$$;

-- Tạo policy chỉ cho phép admin xóa tài liệu của họ
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'document_files' AND policyname = 'Only admin can delete their files'
    ) THEN
        EXECUTE 'CREATE POLICY "Only admin can delete their files" ON document_files
        FOR DELETE
        USING (
            EXISTS (
                SELECT 1 FROM user_roles
                WHERE user_id = auth.uid() AND role = ''admin''
            ) AND user_id = auth.uid()
        )';
    END IF;
END
$$; 