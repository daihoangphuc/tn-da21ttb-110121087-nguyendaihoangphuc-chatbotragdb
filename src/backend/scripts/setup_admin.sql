-- XÓA USER VÀ TẤT CẢ BẢNG LIÊN QUAN USER VÀ THÊM 3 BẢNG MỚI

alter table public.message_analysis
  drop constraint if exists message_analysis_conversation_id_fkey,
  add  constraint message_analysis_conversation_id_fkey
       foreign key (conversation_id)
       references public.conversations (conversation_id)
       on delete cascade;

ALTER TABLE public.learning_metrics
ADD COLUMN IF NOT EXISTS daily_question_counts JSONB;

-- 1. conversations.user_id  ──► auth.users(id)  (đổi sang CASCADE)
ALTER TABLE public.conversations
  DROP CONSTRAINT IF EXISTS fk_conversations_user,
  ADD  CONSTRAINT fk_conversations_user
  FOREIGN KEY (user_id)
  REFERENCES auth.users(id)
  ON DELETE CASCADE;

-- 2. messages.conversation_id  ──► conversations.conversation_id  (đã CASCADE sẵn, chỉ đảm bảo)
ALTER TABLE public.messages
  DROP CONSTRAINT IF EXISTS fk_messages_conversations,
  ADD  CONSTRAINT fk_messages_conversations
  FOREIGN KEY (conversation_id)
  REFERENCES public.conversations(conversation_id)
  ON DELETE CASCADE;

-- 3. message_analysis.message_id  ──► messages.message_id
ALTER TABLE public.message_analysis
  DROP CONSTRAINT IF EXISTS message_analysis_message_id_fkey,
  ADD  CONSTRAINT message_analysis_message_id_fkey
  FOREIGN KEY (message_id)
  REFERENCES public.messages(message_id)
  ON DELETE CASCADE;

-- 4. Ba FK còn lại trỏ thẳng lên auth.users – đổi sang CASCADE
ALTER TABLE public.message_analysis
  DROP CONSTRAINT IF EXISTS message_analysis_user_id_fkey,
  ADD  CONSTRAINT message_analysis_user_id_fkey
  FOREIGN KEY (user_id)
  REFERENCES auth.users(id)
  ON DELETE CASCADE;

ALTER TABLE public.learning_metrics
  DROP CONSTRAINT IF EXISTS learning_metrics_user_id_fkey,
  ADD  CONSTRAINT learning_metrics_user_id_fkey
  FOREIGN KEY (user_id)
  REFERENCES auth.users(id)
  ON DELETE CASCADE;

ALTER TABLE public.learning_recommendations
  DROP CONSTRAINT IF EXISTS learning_recommendations_user_id_fkey,
  ADD  CONSTRAINT learning_recommendations_user_id_fkey
  FOREIGN KEY (user_id)
  REFERENCES auth.users(id)
  ON DELETE CASCADE;




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
  
  analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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