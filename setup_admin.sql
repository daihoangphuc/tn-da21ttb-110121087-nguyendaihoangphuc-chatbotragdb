-- Thay đổi email này thành email admin của bạn
DO $$
DECLARE
  admin_email TEXT := 'phucadmin@gmail.com'; 
  target_user_id UUID;
  admin_result JSONB;
BEGIN
  -- Kiểm tra xem user đã tồn tại chưa
  SELECT au.id INTO target_user_id
  FROM auth.users au
  WHERE au.email = admin_email;
  
  IF target_user_id IS NOT NULL THEN
    -- User đã tồn tại, tạo admin ngay
    SELECT public.create_admin_from_email(admin_email) INTO admin_result;
    RAISE NOTICE 'Admin creation result: %', admin_result;
  ELSE
    -- User chưa tồn tại, sẽ được tạo admin sau khi đăng ký
    RAISE NOTICE 'User % chưa tồn tại. Hãy đăng ký tài khoản với email này trước.', admin_email;
    RAISE NOTICE 'Sau khi đăng ký, chạy: SELECT public.create_admin_from_email(''%'');', admin_email;
  END IF;
END $$;