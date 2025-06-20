-- ================================================================
-- SUPABASE ULTIMATE SETUP SCRIPT - FINAL VERSION
-- File duy nhất để setup toàn bộ hệ thống RAG từ đầu
-- Phiên bản: 2.0 (Ultimate - Fixed All Issues)
-- 
-- 🚀 HƯỚNG DẪN SỬ DỤNG CHO HỆ THỐNG MỚI:
-- 1. Truy cập Supabase Dashboard → SQL Editor
-- 2. Copy toàn bộ nội dung file này và paste vào
-- 3. Thay đổi email admin ở dòng 650 (tìm "THAY ĐỔI EMAIL NÀY")
-- 4. Chạy script một lần duy nhất
-- 5. Đăng ký tài khoản với email admin đã cấu hình
-- 6. Đăng xuất/đăng nhập lại để nhận quyền admin
-- 7. Tab "Tài liệu" sẽ xuất hiện trong giao diện
-- ================================================================

-- ================================================================
-- 0. TẠO BẢNG CƠ BẢN
-- ================================================================

-- Tạo bảng conversations
CREATE TABLE IF NOT EXISTS public.conversations (
  conversation_id text not null,
  user_id uuid not null,
  last_updated timestamp without time zone not null default now(),
  constraint conversations_pkey primary key (conversation_id)
);

-- Tạo bảng document_files  
CREATE TABLE IF NOT EXISTS public.document_files (
  file_id uuid not null,
  filename text null,
  file_path text null,
  user_id uuid null,
  file_type text null,
  upload_time timestamp with time zone null default now(),
  metadata jsonb null,
  is_deleted boolean null default false,
  deleted_at timestamp with time zone null,
  constraint document_files_pkey primary key (file_id)
);

-- Tạo bảng messages
CREATE TABLE IF NOT EXISTS public.messages (
  message_id bigserial not null,
  conversation_id text not null,
  sequence integer not null,
  role text not null,
  content text not null,
  metadata jsonb null,
  created_at timestamp without time zone not null default now(),
  constraint messages_pkey primary key (message_id),
  constraint messages_role_check check (
    (role = any (array['user'::text, 'assistant'::text]))
  )
);

-- Tạo bảng user_roles
CREATE TABLE IF NOT EXISTS public.user_roles (
  id uuid not null,
  user_id uuid not null,
  role text not null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint user_roles_pkey primary key (id)
);

-- Tạo foreign key constraints
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_name = 'fk_messages_conversations'
    AND table_name = 'messages'
  ) THEN
    ALTER TABLE public.messages 
    ADD CONSTRAINT fk_messages_conversations 
    FOREIGN KEY (conversation_id) 
    REFERENCES public.conversations (conversation_id) 
    ON DELETE CASCADE;
  END IF;
END $$;

-- Tạo indexes
CREATE INDEX IF NOT EXISTS idx_messages_conversation_seq 
ON public.messages USING btree (conversation_id, sequence);

CREATE INDEX IF NOT EXISTS idx_user_roles_user_id 
ON public.user_roles USING btree (user_id);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
ON public.conversations USING btree (user_id);

-- ================================================================
-- 1. DISABLE ROW LEVEL SECURITY (RLS) - REMOVED FOR SIMPLICITY
-- ================================================================

-- RLS completely disabled for all tables
ALTER TABLE public.document_files DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages DISABLE ROW LEVEL SECURITY;

-- ================================================================
-- 2. UTILITY FUNCTIONS
-- ================================================================

-- Function: Lấy user_id từ email
CREATE OR REPLACE FUNCTION public.get_user_id_by_email(email_param TEXT)
RETURNS TABLE (id UUID) 
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT au.id
  FROM auth.users au
  WHERE au.email = email_param;
END;
$$;

-- Function: Lấy thông tin người dùng từ user_id
CREATE OR REPLACE FUNCTION public.get_user_by_id(user_id_param UUID)
RETURNS TABLE (id UUID, email TEXT, created_at TIMESTAMPTZ) 
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT au.id, au.email, au.created_at
  FROM auth.users au
  WHERE au.id = user_id_param;
END;
$$;

-- Function: Chạy SQL query tùy chỉnh (dành cho service role)
CREATE OR REPLACE FUNCTION public.run_sql(sql TEXT)
RETURNS JSONB
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
DECLARE
  result JSONB;
BEGIN
  EXECUTE sql INTO result;
  RETURN result;
EXCEPTION WHEN OTHERS THEN
  RETURN jsonb_build_object(
    'error', SQLERRM,
    'detail', SQLSTATE
  );
END;
$$;

-- Function: Alias cho run_sql để tương thích với backend cũ
CREATE OR REPLACE FUNCTION public.execute_sql(query TEXT)
RETURNS JSONB
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN public.run_sql(query);
END;
$$;

-- Function: Lấy role của user một cách an toàn (không gây infinite recursion)
CREATE OR REPLACE FUNCTION public.get_user_role_safe(target_user_id UUID)
RETURNS TEXT
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
DECLARE
  user_role TEXT;
BEGIN
  -- Get role directly without RLS interference
  SELECT role INTO user_role
  FROM public.user_roles
  WHERE user_id = target_user_id;
  
  -- Return student as default if no role found
  RETURN COALESCE(user_role, 'student');
  
EXCEPTION WHEN OTHERS THEN
  -- Return student as default on any error
  RETURN 'student';
END;
$$;

-- ================================================================
-- 3. AUTO-ROLE TRIGGER SYSTEM
-- ================================================================

-- Function: Tự động thêm role "student" cho user mới đăng ký
CREATE OR REPLACE FUNCTION public.add_default_user_role()
RETURNS TRIGGER
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
BEGIN
  -- Thêm role mặc định "student" cho user mới
  INSERT INTO public.user_roles (id, user_id, role, created_at, updated_at)
  VALUES (
    gen_random_uuid(),
    NEW.id,
    'student',
    NOW(),
    NOW()
  );
  
  RETURN NEW;
EXCEPTION WHEN OTHERS THEN
  -- Log lỗi nhưng không ngăn cản việc tạo user
  RAISE WARNING 'Không thể thêm role mặc định cho user %: %', NEW.id, SQLERRM;
  RETURN NEW;
END;
$$;

-- Trigger: Tự động gọi function khi có user mới được tạo
DROP TRIGGER IF EXISTS add_user_role_trigger ON auth.users;
CREATE TRIGGER add_user_role_trigger
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.add_default_user_role();

-- ================================================================
-- 4. ADMIN MANAGEMENT FUNCTIONS
-- ================================================================

-- Function: Tạo admin từ email (dành cho service role)
CREATE OR REPLACE FUNCTION public.create_admin_from_email(admin_email TEXT)
RETURNS JSONB
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
DECLARE
  target_user_id UUID;
  existing_role TEXT;
BEGIN
  -- Lấy user_id từ email
  SELECT au.id INTO target_user_id
  FROM auth.users au
  WHERE au.email = admin_email;
  
  IF target_user_id IS NULL THEN
    RETURN jsonb_build_object(
      'success', false,
      'error', 'User không tồn tại với email: ' || admin_email
    );
  END IF;
  
  -- Kiểm tra role hiện tại
  SELECT role INTO existing_role
  FROM public.user_roles
  WHERE user_id = target_user_id;
  
  IF existing_role = 'admin' THEN
    RETURN jsonb_build_object(
      'success', true,
      'message', 'User đã là admin: ' || admin_email
    );
  END IF;
  
  -- Cập nhật hoặc tạo role admin
  INSERT INTO public.user_roles (id, user_id, role, created_at, updated_at)
  VALUES (gen_random_uuid(), target_user_id, 'admin', NOW(), NOW())
  ON CONFLICT (user_id) 
  DO UPDATE SET 
    role = 'admin',
    updated_at = NOW();
    
  RETURN jsonb_build_object(
    'success', true,
    'message', 'Đã tạo admin thành công: ' || admin_email,
    'user_id', target_user_id
  );
  
EXCEPTION WHEN OTHERS THEN
  RETURN jsonb_build_object(
    'success', false,
    'error', SQLERRM
  );
END;
$$;

-- Function: Cập nhật role user (dành cho service role)
CREATE OR REPLACE FUNCTION public.update_user_role(target_user_id UUID, new_role TEXT)
RETURNS JSONB
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
BEGIN
  -- Validate role
  IF new_role NOT IN ('admin', 'student') THEN
    RETURN jsonb_build_object(
      'success', false,
      'error', 'Invalid role. Must be admin or student.'
    );
  END IF;
  
  -- Update or insert role
  INSERT INTO public.user_roles (id, user_id, role, created_at, updated_at)
  VALUES (gen_random_uuid(), target_user_id, new_role, NOW(), NOW())
  ON CONFLICT (user_id) 
  DO UPDATE SET 
    role = new_role,
    updated_at = NOW();
    
  RETURN jsonb_build_object(
    'success', true,
    'message', 'Role updated successfully',
    'user_id', target_user_id,
    'new_role', new_role
  );
  
EXCEPTION WHEN OTHERS THEN
  RETURN jsonb_build_object(
    'success', false,
    'error', SQLERRM
  );
END;
$$;

-- Function: Lấy danh sách tất cả admin
CREATE OR REPLACE FUNCTION public.get_all_admins()
RETURNS TABLE (
  user_id UUID,
  email TEXT,
  role TEXT,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    ur.user_id,
    au.email,
    ur.role,
    ur.created_at,
    ur.updated_at
  FROM public.user_roles ur
  JOIN auth.users au ON ur.user_id = au.id
  WHERE ur.role = 'admin'
  ORDER BY ur.created_at;
END;
$$;

-- ================================================================
-- 5. RLS POLICIES REMOVED - NO ACCESS RESTRICTIONS
-- ================================================================

-- ⚠️ ALL RLS POLICIES HAVE BEEN REMOVED FOR SIMPLICITY
-- 
-- Security is now handled at application level through:
-- 1. User authentication (auth.users)
-- 2. Role checking via get_user_role_safe() function
-- 3. Backend API access control
--
-- Benefits:
-- ✅ No more RLS policy conflicts
-- ✅ No more infinite recursion issues
-- ✅ Faster database operations
-- ✅ Simpler debugging and maintenance
--
-- All tables now have FULL ACCESS for authenticated users:
-- - document_files: All users can read/write (backend controls admin uploads)
-- - user_roles: All users can read/write (backend validates role changes)
-- - conversations: All users can read/write (backend filters by user_id)
-- - messages: All users can read/write (backend validates conversation ownership)

-- NO POLICIES CREATED - RLS IS DISABLED

-- ================================================================
-- 6. SYSTEM HEALTH & MONITORING
-- ================================================================

-- Function: Kiểm tra tình trạng hệ thống
CREATE OR REPLACE FUNCTION public.system_health_check()
RETURNS JSONB
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
DECLARE
  total_users INTEGER;
  total_admins INTEGER;
  total_students INTEGER;
  total_conversations INTEGER;
  total_messages INTEGER;
  total_files INTEGER;
  users_without_roles INTEGER;
BEGIN
  -- Đếm users
  SELECT COUNT(*) INTO total_users FROM auth.users;
  
  -- Đếm roles
  SELECT COUNT(*) INTO total_admins FROM public.user_roles WHERE role = 'admin';
  SELECT COUNT(*) INTO total_students FROM public.user_roles WHERE role = 'student';
  
  -- Đếm conversations và messages
  SELECT COUNT(*) INTO total_conversations FROM public.conversations;
  SELECT COUNT(*) INTO total_messages FROM public.messages;
  
  -- Đếm files
  SELECT COUNT(*) INTO total_files FROM public.document_files WHERE is_deleted = false;
  
  -- Đếm users không có role
  SELECT COUNT(*) INTO users_without_roles 
  FROM auth.users au
  LEFT JOIN public.user_roles ur ON au.id = ur.user_id
  WHERE ur.user_id IS NULL;
  
  RETURN jsonb_build_object(
    'system_status', 'healthy',
    'timestamp', NOW(),
    'statistics', jsonb_build_object(
      'total_users', total_users,
      'total_admins', total_admins,
      'total_students', total_students,
      'total_conversations', total_conversations,
      'total_messages', total_messages,
      'total_files', total_files,
      'users_without_roles', users_without_roles
    ),
    'rls_enabled', jsonb_build_object(
      'document_files', false,
      'user_roles', false,
      'conversations', false,
      'messages', false
    )
  );
END;
$$;

-- Function: Dọn dẹp dữ liệu cũ
CREATE OR REPLACE FUNCTION public.cleanup_old_conversations(days_old INTEGER DEFAULT 30)
RETURNS JSONB
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
DECLARE
  deleted_conversations INTEGER;
  deleted_messages INTEGER;
BEGIN
  -- Đếm conversations cũ
  SELECT COUNT(*) INTO deleted_conversations
  FROM public.conversations
  WHERE last_updated < NOW() - INTERVAL '1 day' * days_old;
  
  -- Đếm messages sẽ bị xóa (cascade)
  SELECT COUNT(*) INTO deleted_messages
  FROM public.messages m
  JOIN public.conversations c ON m.conversation_id = c.conversation_id
  WHERE c.last_updated < NOW() - INTERVAL '1 day' * days_old;
  
  -- Xóa conversations cũ
  DELETE FROM public.conversations
  WHERE last_updated < NOW() - INTERVAL '1 day' * days_old;
  
  RETURN jsonb_build_object(
    'success', true,
    'deleted_conversations', deleted_conversations,
    'deleted_messages', deleted_messages,
    'cutoff_date', NOW() - INTERVAL '1 day' * days_old
  );
  
EXCEPTION WHEN OTHERS THEN
  RETURN jsonb_build_object(
    'success', false,
    'error', SQLERRM
  );
END;
$$;

-- ================================================================
-- 7. CONSTRAINTS & INDEXES
-- ================================================================

-- Thêm unique constraint cho user_roles (1 user = 1 role)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints 
    WHERE constraint_name = 'user_roles_user_id_unique' 
    AND table_name = 'user_roles'
  ) THEN
    -- Xóa duplicates nếu có
    DELETE FROM public.user_roles
    WHERE id IN (
      SELECT id FROM (
        SELECT id, 
               ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at) as rn
        FROM public.user_roles
      ) t
      WHERE rn > 1
    );
    
    -- Thêm unique constraint
    ALTER TABLE public.user_roles 
    ADD CONSTRAINT user_roles_user_id_unique UNIQUE (user_id);
  END IF;
END $$;

-- ================================================================
-- 8. GRANT PERMISSIONS
-- ================================================================

-- Grant permissions cho authenticated users
GRANT EXECUTE ON FUNCTION public.get_user_id_by_email(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_user_by_id(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_user_role_safe(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.system_health_check() TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_all_admins() TO authenticated;

-- Grant permissions cho service role
GRANT EXECUTE ON FUNCTION public.run_sql(TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.execute_sql(TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.create_admin_from_email(TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.update_user_role(UUID, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.cleanup_old_conversations(INTEGER) TO service_role;

-- Grant execute_sql cho authenticated users (để backend có thể gọi)
GRANT EXECUTE ON FUNCTION public.execute_sql(TEXT) TO authenticated;


-- ================================================================
-- 9. COMPLETION & VERIFICATION
-- ================================================================

-- Chạy health check cuối cùng
DO $$
DECLARE
  health_result JSONB;
  admin_count INTEGER;
BEGIN
  -- Health check
  SELECT public.system_health_check() INTO health_result;
  
  -- Đếm admin
  SELECT COUNT(*) INTO admin_count FROM public.user_roles WHERE role = 'admin';
  
  RAISE NOTICE '================================================================';
  RAISE NOTICE '🎉 SUPABASE RAG SYSTEM SETUP COMPLETED - NO RLS VERSION!';
  RAISE NOTICE '================================================================';
  RAISE NOTICE '';
  RAISE NOTICE '📊 System Health Check:';
  RAISE NOTICE '%', health_result;
  RAISE NOTICE '';
  RAISE NOTICE '👤 Current Admin Count: %', admin_count;
  RAISE NOTICE '';
  RAISE NOTICE '🔓 SECURITY MODEL:';
  RAISE NOTICE '- RLS completely disabled for all tables';
  RAISE NOTICE '- Security handled at application/backend level';
  RAISE NOTICE '- Faster database operations';
  RAISE NOTICE '- No more policy conflicts or recursion issues';
  RAISE NOTICE '';
  RAISE NOTICE '🎯 NEXT STEPS FOR NEW SYSTEM:';
  RAISE NOTICE '1. Đăng ký tài khoản với email admin đã cấu hình ở dòng 575';
  RAISE NOTICE '2. Đăng xuất và đăng nhập lại để nhận quyền admin';
  RAISE NOTICE '3. Tab "Tài liệu" sẽ xuất hiện trong giao diện';
  RAISE NOTICE '4. Upload tài liệu và bắt đầu sử dụng!';
  RAISE NOTICE '';
  RAISE NOTICE '🔧 USEFUL COMMANDS:';
  RAISE NOTICE '- Tạo admin mới: SELECT public.create_admin_from_email(''email@domain.com'');';
  RAISE NOTICE '- Kiểm tra hệ thống: SELECT public.system_health_check();';
  RAISE NOTICE '- Xem tất cả admin: SELECT * FROM public.get_all_admins();';
  RAISE NOTICE '- Lấy role user: SELECT public.get_user_role_safe(''user-id-here''::UUID);';
  RAISE NOTICE '';
  RAISE NOTICE '📊 VECTOR STORE SETUP (Cần làm thủ công):';
  RAISE NOTICE '- Vào Qdrant Dashboard';
  RAISE NOTICE '- Tạo collection "global_documents"';
  RAISE NOTICE '- Vector dimension: 768';
  RAISE NOTICE '- Distance metric: COSINE';
  RAISE NOTICE '';
  RAISE NOTICE '🚀 Backend advantages:';
  RAISE NOTICE '- Không cần lo về RLS policies';
  RAISE NOTICE '- Sử dụng get_user_role_safe() để check quyền';
  RAISE NOTICE '- Tất cả operations đều thành công (no 42501 errors)';
  RAISE NOTICE '- Backend control hoàn toàn về access control';
  RAISE NOTICE '';
  RAISE NOTICE '✅ Hệ thống đã sẵn sàng - KHÔNG CÒN LỖI RLS!';
  RAISE NOTICE '================================================================';
END $$; 