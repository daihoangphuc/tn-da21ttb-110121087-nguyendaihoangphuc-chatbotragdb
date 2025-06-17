-- Function để lấy user_id từ email trong bảng auth.users
CREATE OR REPLACE FUNCTION get_user_id_by_email(email_param TEXT)
RETURNS TABLE (id UUID) 
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT au.id
  FROM auth.users au
  WHERE au.email = email_param;
END;
$$ LANGUAGE plpgsql;

-- Function để lấy thông tin người dùng từ user_id
CREATE OR REPLACE FUNCTION get_user_by_id(user_id_param UUID)
RETURNS TABLE (id UUID, email VARCHAR(255), created_at TIMESTAMPTZ) 
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT au.id, au.email, au.created_at
  FROM auth.users au
  WHERE au.id = user_id_param;
END;
$$ LANGUAGE plpgsql;

-- Function để chạy SQL query tùy chỉnh (chỉ dùng cho admin)
CREATE OR REPLACE FUNCTION run_sql(sql TEXT)
RETURNS JSONB
SECURITY DEFINER
SET search_path = public
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
$$ LANGUAGE plpgsql; 