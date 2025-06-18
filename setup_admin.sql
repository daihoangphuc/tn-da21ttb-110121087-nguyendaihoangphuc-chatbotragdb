-- Đăng ký một người dùng thường trước
SELECT public.create_admin_from_email('phucadmin@gmail.com');
-- Kiểm tra 
-- Xem danh sách tất cả admin
SELECT * FROM public.get_all_admins();

-- Hoặc kiểm tra health system
SELECT public.system_health_check();