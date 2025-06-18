-- Script để cập nhật policies cho admin có thể quản lý tất cả file

-- Xóa policy cũ nếu tồn tại
DROP POLICY IF EXISTS "Admin can delete all files" ON document_files;
DROP POLICY IF EXISTS "Admin can update all files" ON document_files;
DROP POLICY IF EXISTS "Admin can view all files" ON document_files;

-- Tạo policy mới cho phép admin xóa tất cả file
CREATE POLICY "Admin can delete all files" ON document_files
FOR DELETE
USING (
    EXISTS (
        SELECT 1 FROM user_roles
        WHERE user_id = auth.uid() AND role = 'admin'
    )
);

-- Tạo policy mới cho phép admin cập nhật tất cả file
CREATE POLICY "Admin can update all files" ON document_files
FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM user_roles
        WHERE user_id = auth.uid() AND role = 'admin'
    )
);

-- Tạo policy mới cho phép admin xem tất cả file
CREATE POLICY "Admin can view all files" ON document_files
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM user_roles
        WHERE user_id = auth.uid() AND role = 'admin'
    )
);

-- Kiểm tra các policy đã được tạo
SELECT schemaname, tablename, policyname, cmd, qual 
FROM pg_policies 
WHERE tablename = 'document_files' 
ORDER BY policyname; 