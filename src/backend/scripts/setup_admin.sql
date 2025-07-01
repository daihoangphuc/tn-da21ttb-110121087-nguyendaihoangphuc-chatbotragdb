-- Thêm 3 bảng mới
CREATE TABLE message_analysis (
  analysis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  message_id BIGINT REFERENCES messages(message_id),
  user_id UUID REFERENCES auth.users(id),
  conversation_id TEXT REFERENCES conversations(conversation_id),
  
  -- Kết quả từ API
  bloom_level VARCHAR(50), -- Remember, Understand, Apply, Analyze, Evaluate, Create
  bloom_explanation TEXT, -- Giải thích tại sao được phân loại như vậy
  
  topics_detected JSONB, -- ["Chuẩn hóa", "SQL", "ERD"]
  difficulty_level VARCHAR(20), -- "basic", "intermediate", "advanced"
  
  question_type VARCHAR(50), -- "definition", "example", "problem_solving", "comparison"
  keywords JSONB, -- ["3NF", "chuẩn hóa", "CSDL"]
  
  -- Metadata
  api_provider VARCHAR(50), -- "openai", "claude", "gemini"
  analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Lưu raw response để debug
  raw_api_response JSONB
);

CREATE TABLE learning_metrics (
  metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id),
  date_week DATE NOT NULL, -- Tuần tính từ thứ 2
  
  -- Metrics cơ bản
  total_questions INTEGER DEFAULT 0,
  bloom_distribution JSONB, -- {"Remember": 5, "Apply": 3, ...}
  topics_covered JSONB, -- ["SQL", "Chuẩn hóa", "ERD"]
  difficulty_distribution JSONB, -- {"basic": 8, "intermediate": 4, "advanced": 1}
  
  -- Insights đơn giản
  most_frequent_topic VARCHAR(100),
  current_bloom_trend VARCHAR(50), -- "improving", "stable", "declining"
  autonomy_score FLOAT, -- % câu hỏi Apply/Analyze/Evaluate/Create
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


CREATE TABLE learning_recommendations (
  recommendation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id),
  
  title VARCHAR(200) NOT NULL,
  description TEXT,
  recommendation_type VARCHAR(50), -- "review", "practice", "advance"
  
  target_topic VARCHAR(100),
  current_level VARCHAR(20),
  suggested_level VARCHAR(20),
  
  status VARCHAR(20) DEFAULT 'active', -- 'active', 'dismissed'
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '7 days')
); 



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