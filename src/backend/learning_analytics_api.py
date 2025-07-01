import os
import json
import hashlib
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta, date
import logging

# Cấu hình logging
logging.basicConfig(format="[Learning Analytics API] %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def print(*args, **kwargs):
    prefix = "[Learning Analytics API] "
    logger.info(prefix + " ".join(map(str, args)))

class APIAnalyticsService:
    def __init__(self, api_provider="gemini"):
        self.api_provider = api_provider
        self.cache = {}  # Simple in-memory cache
        
        # Khởi tạo Gemini LLM client
        try:
            from backend.llm import GeminiLLM
            self.client = GeminiLLM()
            print("Đã khởi tạo GeminiLLM cho Learning Analytics")
        except Exception as e:
            print(f"Warning: Không thể khởi tạo GeminiLLM: {e}")
            self.client = None
            
    def _create_question_hash(self, question: str) -> str:
        """Tạo hash cho câu hỏi để cache"""
        return hashlib.md5(question.lower().encode()).hexdigest()
        
    def create_analysis_prompt(self, question: str) -> str:
        """Tạo prompt để gửi cho API phân tích"""
        return f"""
Hãy phân tích câu hỏi về cơ sở dữ liệu sau đây:

Câu hỏi: "{question}"

Vui lòng trả về kết quả phân tích dưới dạng JSON với format sau:

{{
  "bloom_level": "Remember|Understand|Apply|Analyze|Evaluate|Create",
  "bloom_explanation": "Giải thích ngắn gọn tại sao được phân loại như vậy",
  "topics_detected": ["chủ đề 1", "chủ đề 2"],
  "difficulty_level": "basic|intermediate|advanced", 
  "question_type": "definition|example|problem_solving|comparison|other",
  "keywords": ["từ khóa 1", "từ khóa 2"]
}}

Định nghĩa các mức Bloom:
- Remember: Nhớ, nhận biết (là gì, định nghĩa, liệt kê)
- Understand: Hiểu, giải thích (tại sao, như thế nào, so sánh)
- Apply: Áp dụng (sử dụng, thực hiện, viết code/SQL)
- Analyze: Phân tích (so sánh, phân biệt, tách nhỏ)
- Evaluate: Đánh giá (tốt nhất, hiệu quả, lựa chọn)
- Create: Sáng tạo (thiết kế, xây dựng, đề xuất)

Chủ đề CSDL phổ biến: SQL, Chuẩn hóa, ERD, Index, Transaction, NoSQL, Stored Procedure, View, Trigger, etc.

Difficulty levels:
- basic: Câu hỏi cơ bản, định nghĩa
- intermediate: Câu hỏi ứng dụng, so sánh
- advanced: Câu hỏi phức tạp, thiết kế, tối ưu

QUAN TRỌNG: Chỉ trả về JSON, không có text khác.
"""

    async def analyze_question(self, question: str) -> dict:
        """Gửi câu hỏi đến API và nhận kết quả phân tích"""
        try:
            # Kiểm tra cache
            question_hash = self._create_question_hash(question)
            if question_hash in self.cache:
                print(f"Using cached analysis for question: {question[:50]}...")
                return self.cache[question_hash]
            
            if not self.client:
                print("API client not initialized, using fallback analysis")
                return self._fallback_analysis(question)
                
            prompt = self.create_analysis_prompt(question)
            
            if self.api_provider == "gemini":
                response = await self._call_gemini_api(prompt)
            else:
                response = await self._call_gemini_api(prompt)  # Fallback
                
            # Parse JSON response
            try:
                result = json.loads(response)
                # Validate result structure
                result = self._validate_and_fix_result(result, question)
                
                # Cache result
                self.cache[question_hash] = result
                print(f"Successfully analyzed question: {question[:50]}... -> {result['bloom_level']}")
                return result
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response: {e}")
                print(f"Raw response: {response}")
                return self._fallback_analysis(question)
                
        except Exception as e:
            print(f"Error in API analysis: {e}")
            return self._fallback_analysis(question)
    
    def _validate_and_fix_result(self, result: dict, question: str) -> dict:
        """Validate và fix kết quả phân tích"""
        valid_bloom_levels = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
        valid_difficulties = ["basic", "intermediate", "advanced"]
        valid_question_types = ["definition", "example", "problem_solving", "comparison", "other"]
        
        # Fix bloom_level
        if result.get("bloom_level") not in valid_bloom_levels:
            result["bloom_level"] = "Remember"
            
        # Fix difficulty_level
        if result.get("difficulty_level") not in valid_difficulties:
            result["difficulty_level"] = "basic"
            
        # Fix question_type
        if result.get("question_type") not in valid_question_types:
            result["question_type"] = "other"
            
        # Ensure lists
        if not isinstance(result.get("topics_detected"), list):
            result["topics_detected"] = ["CSDL"]
            
        if not isinstance(result.get("keywords"), list):
            result["keywords"] = []
            
        # Ensure explanation exists
        if not result.get("bloom_explanation"):
            result["bloom_explanation"] = f"Được phân loại là {result['bloom_level']}"
            
        return result
    
    async def _call_gemini_api(self, prompt: str) -> str:
        """Gọi Gemini API"""
        try:
            # Tạo prompt với system message
            full_prompt = """Bạn là chuyên gia phân tích câu hỏi giáo dục về cơ sở dữ liệu. Chỉ trả về JSON.

""" + prompt

            response = await self.client.invoke(full_prompt)
            
            # Gemini trả về object có .content attribute
            content = response.content if hasattr(response, 'content') else str(response)
            return content.strip()
            
        except Exception as e:
            print(f"Gemini API error: {e}")
            raise
    
    def _fallback_analysis(self, question: str) -> dict:
        """Phân tích fallback khi API lỗi"""
        print(f"Using fallback analysis for: {question[:50]}...")
        
        # Simple rule-based analysis
        question_lower = question.lower()
        
        # Detect bloom level
        if any(word in question_lower for word in ["là gì", "what is", "định nghĩa", "khái niệm"]):
            bloom_level = "Remember"
        elif any(word in question_lower for word in ["tại sao", "why", "giải thích", "mô tả"]):
            bloom_level = "Understand"
        elif any(word in question_lower for word in ["sử dụng", "viết", "tạo", "thực hiện"]):
            bloom_level = "Apply"
        elif any(word in question_lower for word in ["so sánh", "phân tích", "khác nhau"]):
            bloom_level = "Analyze"
        else:
            bloom_level = "Remember"
            
        # Detect topics
        topics = []
        if any(word in question_lower for word in ["sql", "select", "insert", "update", "delete"]):
            topics.append("SQL")
        if any(word in question_lower for word in ["chuẩn hóa", "3nf", "2nf", "1nf", "bcnf"]):
            topics.append("Chuẩn hóa")
        if any(word in question_lower for word in ["erd", "thực thể", "entity", "mối quan hệ"]):
            topics.append("ERD")
        if any(word in question_lower for word in ["index", "chỉ mục"]):
            topics.append("Index")
        if not topics:
            topics = ["CSDL"]
            
        return {
            "bloom_level": bloom_level,
            "bloom_explanation": f"Fallback analysis: được phân loại là {bloom_level}",
            "topics_detected": topics,
            "difficulty_level": "basic",
            "question_type": "definition" if bloom_level == "Remember" else "other",
            "keywords": topics
        }

class LearningAnalyticsService:
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.api_analyzer = APIAnalyticsService()
    
    async def process_user_message(self, message_id: int, content: str, user_id: str, conversation_id: str):
        """Xử lý tin nhắn của user - gọi API và lưu kết quả"""
        try:
            print(f"Processing message analysis for user {user_id}: {content[:50]}...")
            
            # 1. Gọi API phân tích
            analysis_result = await self.api_analyzer.analyze_question(content)
            
            # 2. Lưu kết quả vào database
            analysis_data = {
                "message_id": message_id,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "bloom_level": analysis_result["bloom_level"],
                "bloom_explanation": analysis_result["bloom_explanation"],
                "topics_detected": analysis_result["topics_detected"],
                "difficulty_level": analysis_result["difficulty_level"],
                "question_type": analysis_result["question_type"],
                "keywords": analysis_result["keywords"],
                "api_provider": self.api_analyzer.api_provider,
                "raw_api_response": analysis_result
            }
            
            result = self.supabase.table("message_analysis").insert(analysis_data).execute()
            
            # 3. Cập nhật metrics hàng tuần (async, không block)
            asyncio.create_task(self.update_weekly_metrics(user_id))
            
            print(f"Successfully saved analysis for message {message_id}")
            return result.data[0] if result.data else None
            
        except Exception as e:
            print(f"Error processing message analysis: {e}")
            return None
    
    async def update_weekly_metrics(self, user_id: str):
        """Cập nhật metrics tuần cho user"""
        try:
            # Lấy tuần hiện tại (thứ 2 đầu tuần)
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())
            
            print(f"Updating weekly metrics for user {user_id}, week starting {week_start}")
            
            # Lấy tất cả phân tích của tuần này
            week_analyses = self.supabase.table("message_analysis").select("*").eq(
                "user_id", user_id
            ).gte("analysis_timestamp", week_start.isoformat()).execute()
            
            if not week_analyses.data:
                print(f"No analyses found for user {user_id} this week")
                return
            
            analyses = week_analyses.data
            print(f"Found {len(analyses)} analyses for this week")
            
            # Tính toán metrics
            metrics = self._calculate_weekly_metrics(analyses, week_start)
            
            # Upsert metrics
            existing_metric = self.supabase.table("learning_metrics").select("*").eq(
                "user_id", user_id
            ).eq("date_week", week_start.isoformat()).execute()
            
            if existing_metric.data:
                # Update
                self.supabase.table("learning_metrics").update(metrics).eq(
                    "metric_id", existing_metric.data[0]["metric_id"]
                ).execute()
                print(f"Updated existing weekly metrics for user {user_id}")
            else:
                # Insert
                metrics.update({"user_id": user_id, "date_week": week_start.isoformat()})
                self.supabase.table("learning_metrics").insert(metrics).execute()
                print(f"Created new weekly metrics for user {user_id}")
            
            # Tạo recommendations nếu cần
            await self.generate_simple_recommendations(user_id, metrics)
            
        except Exception as e:
            print(f"Error updating weekly metrics: {e}")
    
    def _calculate_weekly_metrics(self, analyses: List[dict], week_start: date) -> dict:
        """Tính toán metrics từ dữ liệu phân tích"""
        total_questions = len(analyses)
        
        # Bloom distribution
        bloom_counts = {}
        for analysis in analyses:
            bloom = analysis["bloom_level"]
            bloom_counts[bloom] = bloom_counts.get(bloom, 0) + 1
        
        # Topics covered
        all_topics = []
        for analysis in analyses:
            topics = analysis.get("topics_detected", [])
            if isinstance(topics, list):
                all_topics.extend(topics)
        
        unique_topics = list(set(all_topics))
        most_frequent_topic = max(set(all_topics), key=all_topics.count) if all_topics else "CSDL"
        
        # Difficulty distribution
        difficulty_counts = {}
        for analysis in analyses:
            diff = analysis["difficulty_level"]
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
        
        # Autonomy score (% câu hỏi mức cao)
        higher_order_thinking = ["Apply", "Analyze", "Evaluate", "Create"]
        higher_count = sum(bloom_counts.get(level, 0) for level in higher_order_thinking)
        autonomy_score = higher_count / total_questions if total_questions > 0 else 0
        
        return {
            "total_questions": total_questions,
            "bloom_distribution": bloom_counts,
            "topics_covered": unique_topics,
            "difficulty_distribution": difficulty_counts,
            "most_frequent_topic": most_frequent_topic,
            "autonomy_score": autonomy_score
        }
    
    async def generate_simple_recommendations(self, user_id: str, metrics: dict):
        """Tạo gợi ý đơn giản dựa trên metrics"""
        try:
            recommendations = []
            
            # Gợi ý 1: Nếu chủ yếu là Remember level
            bloom_dist = metrics.get("bloom_distribution", {})
            total_questions = metrics.get("total_questions", 1)
            remember_ratio = bloom_dist.get("Remember", 0) / total_questions
            
            if remember_ratio > 0.7 and total_questions >= 3:  # 70% câu hỏi ở mức Remember
                recommendations.append({
                    "title": "Thử thách bản thân với câu hỏi ứng dụng",
                    "description": "Bạn đã nắm vững kiến thức cơ bản. Hãy thử đặt câu hỏi về cách áp dụng vào thực tế!",
                    "recommendation_type": "advance",
                    "target_topic": metrics.get("most_frequent_topic"),
                    "current_level": "Remember",
                    "suggested_level": "Apply"
                })
            
            # Gợi ý 2: Nếu tập trung quá nhiều vào 1 chủ đề
            unique_topics = len(metrics.get("topics_covered", []))
            if unique_topics == 1 and total_questions >= 5:
                topic = metrics["most_frequent_topic"]
                recommendations.append({
                    "title": f"Mở rộng kiến thức ngoài {topic}",
                    "description": f"Bạn đã hỏi nhiều về {topic}. Hãy khám phá các chủ đề khác như SQL, ERD, Transaction!",
                    "recommendation_type": "review",
                    "target_topic": "CSDL tổng quát",
                    "current_level": "focused",
                    "suggested_level": "diversified"
                })
            
            # Gợi ý 3: Autonomy score cao
            if metrics.get("autonomy_score", 0) > 0.6:
                recommendations.append({
                    "title": "Xuất sắc! Bạn đang tư duy tốt",
                    "description": "Bạn đang đặt nhiều câu hỏi ở mức độ cao. Hãy tiếp tục duy trì!",
                    "recommendation_type": "encourage",
                    "target_topic": metrics.get("most_frequent_topic"),
                    "current_level": "high",
                    "suggested_level": "maintain"
                })
            
            # Lưu recommendations
            for rec in recommendations:
                rec["user_id"] = user_id
                
                # Kiểm tra đã tồn tại chưa để tránh duplicate
                existing = self.supabase.table("learning_recommendations").select("*").eq(
                    "user_id", user_id
                ).eq("title", rec["title"]).eq("status", "active").execute()
                
                if not existing.data:
                    self.supabase.table("learning_recommendations").insert(rec).execute()
                    print(f"Created recommendation: {rec['title']}")
                    
        except Exception as e:
            print(f"Error generating recommendations: {e}")
    
    async def get_dashboard_data(self, user_id: str, weeks: int = 4) -> dict:
        """Lấy dữ liệu dashboard cho user"""
        try:
            # Lấy metrics gần nhất
            end_date = datetime.now().date()
            start_date = end_date - timedelta(weeks=weeks)
            week_start = start_date - timedelta(days=start_date.weekday())
            
            metrics_result = self.supabase.table("learning_metrics").select("*").eq(
                "user_id", user_id
            ).gte("date_week", week_start.isoformat()).order("date_week", desc=True).execute()
            
            # Lấy recommendations active
            recommendations_result = self.supabase.table("learning_recommendations").select("*").eq(
                "user_id", user_id
            ).eq("status", "active").gte("expires_at", datetime.now().isoformat()).execute()
            
            # Tổng hợp dữ liệu
            dashboard_data = {
                "user_id": user_id,
                "period": {"weeks": weeks, "from": week_start.isoformat(), "to": end_date.isoformat()},
                "weekly_metrics": metrics_result.data,
                "recommendations": recommendations_result.data,
                "summary": self._calculate_summary(metrics_result.data)
            }
            
            return dashboard_data
            
        except Exception as e:
            print(f"Error getting dashboard data: {e}")
            raise
    
    def _calculate_summary(self, weekly_metrics: List[dict]) -> dict:
        """Tính toán summary từ weekly metrics"""
        if not weekly_metrics:
            return {"total_questions": 0, "topics_learned": 0, "current_trend": "no_data", "latest_autonomy_score": 0}
        
        total_questions = sum(m.get("total_questions", 0) for m in weekly_metrics)
        all_topics = []
        for m in weekly_metrics:
            topics = m.get("topics_covered", [])
            if isinstance(topics, list):
                all_topics.extend(topics)
        unique_topics = len(set(all_topics))
        
        # Autonomy trend (so sánh 2 tuần gần nhất)
        if len(weekly_metrics) >= 2:
            recent_autonomy = weekly_metrics[0].get("autonomy_score", 0)
            previous_autonomy = weekly_metrics[1].get("autonomy_score", 0)
            trend = "improving" if recent_autonomy > previous_autonomy else "stable"
        else:
            trend = "stable"
        
        latest_autonomy = weekly_metrics[0].get("autonomy_score", 0) if weekly_metrics else 0
        
        return {
            "total_questions": total_questions,
            "topics_learned": unique_topics,
            "current_trend": trend,
            "latest_autonomy_score": latest_autonomy
        } 