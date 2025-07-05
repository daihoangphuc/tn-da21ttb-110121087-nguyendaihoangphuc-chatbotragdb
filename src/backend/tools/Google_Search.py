import os
import logging
import asyncio
import time
import hashlib
from typing import Tuple, List, Any, Optional, Dict
from dataclasses import dataclass
from functools import lru_cache
from datetime import datetime, timedelta
import json

from langchain.agents import initialize_agent, Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import TavilySearchResults
from dotenv import load_dotenv

load_dotenv()

# Cấu hình logging với format tùy chỉnh
logging.basicConfig(
    level=logging.INFO, 
    format='[Google_Search] %(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SearchConfig:
    """Cấu hình cho Google Search tool"""
    max_results: int = 2
    include_answer: bool = True
    include_raw_content: bool = True
    temperature: float = 0.0
    model: str = "gemini-1.5-flash"
    cache_ttl_hours: int = 24
    rate_limit_per_minute: int = 30
    max_content_length: int = 8000
    timeout_seconds: int = 30
    enable_llm: bool = False

class RateLimiter:
    """Simple rate limiter để tránh spam API"""
    
    def __init__(self, max_calls_per_minute: int = 30):
        self.max_calls = max_calls_per_minute
        self.calls = []
    
    def can_make_call(self) -> bool:
        """Kiểm tra xem có thể gọi API không"""
        now = datetime.now()
        # Loại bỏ các calls cũ hơn 1 phút
        self.calls = [call_time for call_time in self.calls 
                     if now - call_time < timedelta(minutes=1)]
        
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        return False
    
    def wait_time(self) -> float:
        """Tính thời gian cần đợi (seconds)"""
        if not self.calls:
            return 0.0
        oldest_call = min(self.calls)
        wait_until = oldest_call + timedelta(minutes=1)
        wait_seconds = (wait_until - datetime.now()).total_seconds()
        return max(0.0, wait_seconds)

class SearchCache:
    """Cache system cho search results"""
    
    def __init__(self, ttl_hours: int = 24):
        self.cache: Dict[str, Dict] = {}
        self.ttl_hours = ttl_hours
    
    def _get_cache_key(self, query: str) -> str:
        """Tạo cache key từ query"""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def get(self, query: str) -> Optional[Tuple[Any, List[str]]]:
        """Lấy kết quả từ cache"""
        key = self._get_cache_key(query)
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        # Kiểm tra TTL
        cache_time = datetime.fromisoformat(entry['timestamp'])
        if datetime.now() - cache_time > timedelta(hours=self.ttl_hours):
            del self.cache[key]
            return None
        
        logger.info(f"🎯 Cache hit cho query: {query[:50]}...")
        return entry['result'], entry['sources']
    
    def set(self, query: str, result: Any, sources: List[str]):
        """Lưu kết quả vào cache"""
        key = self._get_cache_key(query)
        self.cache[key] = {
            'result': result,
            'sources': sources,
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"💾 Cached result cho query: {query[:50]}...")
    
    def clear_expired(self):
        """Xóa các entry đã hết hạn"""
        now = datetime.now()
        expired_keys = []
        
        for key, entry in self.cache.items():
            cache_time = datetime.fromisoformat(entry['timestamp'])
            if now - cache_time > timedelta(hours=self.ttl_hours):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"🗑️ Đã xóa {len(expired_keys)} cache entries hết hạn")

class OptimizedGoogleSearch:
    """
    Google Search tool được tối ưu với caching, rate limiting và error handling nâng cao
    """
    
    def __init__(self, config: SearchConfig = SearchConfig()):
        self.config = config
        self.cache = SearchCache(config.cache_ttl_hours)
        self.rate_limiter = RateLimiter(config.rate_limit_per_minute)
        
        # Khởi tạo API keys
        self.google_api_key = os.getenv('API_KEY_LLM_SEARCH_TOOL')
        self.tavily_api_key = os.getenv('TAVILY_API_KEY')
        
        # Validate API keys
        self._validate_api_keys()
        
        # Khởi tạo components
        self.llm = None
        self.tavily_search = None
        self._initialize_components()
    
    def _validate_api_keys(self):
        """Validate API keys"""
        if not self.google_api_key:
            logger.error("❌ GOOGLE_API_KEY không được tìm thấy trong biến môi trường")
            raise ValueError("Missing Google API key")
        
        if not self.tavily_api_key:
            logger.error("❌ TAVILY_API_KEY không được tìm thấy trong biến môi trường")
            raise ValueError("Missing Tavily API key")
        
        # Set environment variables
        os.environ["GEMINI_API_KEY"] = self.google_api_key
        os.environ["TAVILY_API_KEY"] = self.tavily_api_key
        
        logger.info("✅ API keys validated successfully")
    
    def _initialize_components(self):
        """Khởi tạo LLM và search components"""
        try:
            self.llm = ChatGoogleGenerativeAI(
                model=self.config.model,
                temperature=self.config.temperature,
                google_api_key=self.google_api_key,
                timeout=self.config.timeout_seconds
            )
            
            self.tavily_search = TavilySearchResults(
                max_results=self.config.max_results,
                include_answer=self.config.include_answer,
                include_raw_content=self.config.include_raw_content
            )
            
            logger.info("✅ Search components initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Lỗi khởi tạo components: {str(e)}")
            raise
    
    def _validate_query(self, query: str) -> str:
        """Validate và clean query"""
        if not query or not query.strip():
            raise ValueError("Query không được để trống")
        
        query = query.strip()
        if len(query) > 500:
            logger.warning(f"⚠️ Query quá dài ({len(query)} chars), sẽ truncate")
            query = query[:500] + "..."
        
        return query
    
    def _process_tavily_results(self, results: Any) -> Tuple[List[str], str]:
        """Xử lý kết quả từ Tavily với validation"""
        urls = []
        contents = []
        
        try:
            if isinstance(results, list):
                for item in results:
                    if isinstance(item, dict) and "url" in item:
                        urls.append(item["url"])
                        title = item.get('title', 'No title')
                        content = item.get('content', 'No content')
                        
                        # Truncate content nếu quá dài
                        if len(content) > self.config.max_content_length:
                            content = content[:self.config.max_content_length] + "..."
                        
                        contents.append(f"- **{title}** ({item['url']})\n{content}\n")
                        
            elif isinstance(results, dict) and "url" in results:
                urls.append(results["url"])
                title = results.get('title', 'No title')
                content = results.get('content', 'No content')
                
                if len(content) > self.config.max_content_length:
                    content = content[:self.config.max_content_length] + "..."
                
                contents.append(f"- **{title}** ({results['url']})\n{content}\n")
            
            return urls, "\n".join(contents)
            
        except Exception as e:
            logger.error(f"❌ Lỗi xử lý Tavily results: {str(e)}")
            return [], ""
    
    def _create_optimized_prompt(self, query: str, content: str) -> str:
        """Tạo prompt được tối ưu cho LLM"""
        return f"""Bạn là chuyên gia cơ sở dữ liệu. Hãy trả lời câu hỏi dựa trên kết quả tìm kiếm.

**NGUYÊN TẮC QUAN TRỌNG:**
✅ **BẮT BUỘC:** Cuối câu trả lời PHẢI có phần "## Nguồn tham khảo" với tất cả URL được tìm thấy
✅ **ĐỊNH DẠNG:** Sử dụng Markdown chuẩn (##, ###, **, -, ```sql)  
✅ **NỘI DUNG:** Trả lời chính xác, ngắn gọn, dễ hiểu về cơ sở dữ liệu
✅ **NGÔN NGỮ:** Tiếng Việt, giữ nguyên thuật ngữ chuyên ngành

**VÍ DỤ ĐỊNH DẠNG:**
Câu trả lời chính về chủ đề...

## Các loại CSDL phổ biến
- **PostgreSQL**: Mã nguồn mở, mạnh mẽ
- **MySQL**: Phổ biến cho web
- **SQL Server**: Của Microsoft

## Nguồn tham khảo  
- https://example1.com
- https://example2.com

**KẾT QUẢ TÌM KIẾM:**
{content}

**CÂU HỎI:** {query}

Hãy trả lời dựa trên thông tin trên và NHẤT ĐỊNH phải có phần "## Nguồn tham khảo" ở cuối với tất cả URL."""
    
    def _validate_llm_response(self, response: Any) -> str:
        """Validate và clean LLM response"""
        try:
            if hasattr(response, 'content'):
                content = response.content
            elif isinstance(response, str):
                content = response
            else:
                content = str(response)
            
            # Kiểm tra xem có URL nguồn không
            if '[http' not in content and '[www' not in content:
                logger.warning("⚠️ LLM response thiếu URL nguồn")
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"❌ Lỗi validate LLM response: {str(e)}")
            return "Lỗi xử lý phản hồi từ AI."
    
    def search_raw_results(self, query: str) -> Tuple[str, List[str]]:
        """
        Tìm kiếm và trả về kết quả thô (không qua LLM processing)
        
        Args:
            query: Câu hỏi cần tìm kiếm
            
        Returns:
            Tuple[str, List[str]]: (raw_search_content, source_urls)
        """
        try:
            # Validate query
            query = self._validate_query(query)
            
            # Check cache trước
            cached_result = self.cache.get(query)
            if cached_result:
                return cached_result
            
            # Rate limiting
            if not self.rate_limiter.can_make_call():
                wait_time = self.rate_limiter.wait_time()
                logger.warning(f"⏳ Rate limit reached. Đợi {wait_time:.1f}s...")
                time.sleep(wait_time)
            
            # Validate components
            if not self.llm or not self.tavily_search:
                error_msg = "❌ Search components chưa được khởi tạo"
                logger.error(error_msg)
                return error_msg, []
            
            logger.info(f"🔍 Đang tìm kiếm: {query[:100]}...")
            
            # Gọi Tavily API
            start_time = time.time()
            results = self.tavily_search.invoke({"query": query})
            search_time = time.time() - start_time
            
            logger.info(f"📊 Tavily search completed in {search_time:.2f}s")
            
            # Xử lý kết quả
            urls, content = self._process_tavily_results(results)
            
            if not content:
                no_result_msg = "🔍 Không tìm thấy thông tin liên quan đến truy vấn này."
                logger.warning(no_result_msg)
                return no_result_msg, []
            
            # Trả về kết quả thô (không qua LLM processing)
            # Cache kết quả thô
            self.cache.set(query, content, urls)
            
            total_time = time.time() - start_time
            logger.info(f"✅ Raw search hoàn thành trong {total_time:.2f}s với {len(urls)} nguồn")
            
            return content, urls
            
        except Exception as e:
            error_msg = f"❌ Lỗi tìm kiếm: {str(e)}"
            logger.error(error_msg)
            return error_msg, []

    def search_with_sources(self, query: str) -> Tuple[str, List[str]]:
        """
        Tìm kiếm với sources và LLM processing (để backward compatibility)
        
        Args:
            query: Câu hỏi cần tìm kiếm
            
        Returns:
            Tuple[str, List[str]]: (processed_answer, source_urls)
        """
        try:
            # Lấy kết quả thô
            raw_content, urls = self.search_raw_results(query)
            
            if not raw_content or raw_content.startswith("🔍 Không tìm thấy"):
                return raw_content, urls
            
            # Xử lý với LLM nếu cần
            prompt = self._create_optimized_prompt(query, raw_content)
            
            logger.info("🤖 Đang xử lý với LLM...")
            llm_start = time.time()
            
            try:
                llm_response = self.llm.invoke(prompt)
                llm_time = time.time() - llm_start
                logger.info(f"🧠 LLM processing completed in {llm_time:.2f}s")
                
                # Validate và clean response
                final_response = self._validate_llm_response(llm_response)
                return final_response, urls
                
            except Exception as llm_error:
                logger.error(f"❌ LLM error: {str(llm_error)}")
                fallback_msg = f"Lỗi xử lý AI, nhưng đã tìm thấy {len(urls)} nguồn liên quan."
                return fallback_msg, urls
                
        except Exception as e:
            error_msg = f"❌ Lỗi tìm kiếm: {str(e)}"
            logger.error(error_msg)
            return error_msg, []
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Lấy thống kê cache"""
        return {
            "cache_size": len(self.cache.cache),
            "rate_limit_calls": len(self.rate_limiter.calls),
            "max_calls_per_minute": self.rate_limiter.max_calls
        }
    
    def clear_cache(self):
        """Xóa cache"""
        self.cache.cache.clear()
        logger.info("🗑️ Cache đã được xóa")
    
    def cleanup_expired_cache(self):
        """Cleanup expired cache entries"""
        self.cache.clear_expired()

# Global instance
_search_instance = None

def get_search_instance(config: SearchConfig = SearchConfig()) -> OptimizedGoogleSearch:
    """Singleton pattern để tái sử dụng instance"""
    global _search_instance
    if _search_instance is None:
        _search_instance = OptimizedGoogleSearch(config)
    return _search_instance

# Backwards compatibility functions
def tavily_with_sources(query: str) -> Tuple[List[str], str]:
    """Legacy function for backwards compatibility"""
    logger.warning("⚠️ Đang sử dụng legacy function. Khuyến nghị dùng OptimizedGoogleSearch class")
    search = get_search_instance()
    response, urls = search.search_with_sources(query)
    return urls, response

def run_query_with_sources(query: str) -> Tuple[Any, List[str]]:
    """Legacy function for backwards compatibility"""
    logger.warning("⚠️ Đang sử dụng legacy function. Khuyến nghị dùng OptimizedGoogleSearch class")
    search = get_search_instance()
    return search.search_with_sources(query)

def get_raw_search_results(query: str) -> Tuple[str, List[str]]:
    """Function to get raw search results without LLM processing"""
    search = get_search_instance()
    return search.search_raw_results(query)

# Main execution
if __name__ == "__main__":
    # Test với multiple queries
    test_queries = [
        "Cú pháp select mới nhất và đầy đủ của lệnh select trong csdl?",
        "Best practices for database indexing in 2024",
        "Khái niệm ACID trong cơ sở dữ liệu"
    ]
    
    config = SearchConfig(
        max_results=3,
        cache_ttl_hours=1,  # Test cache
        rate_limit_per_minute=20
    )
    
    search = OptimizedGoogleSearch(config)
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"🔍 Query: {query}")
        print('='*60)
        
        start_time = time.time()
        response, sources = search.search_with_sources(query)
        elapsed = time.time() - start_time
        
        print(f"\n⏱️ Thời gian: {elapsed:.2f}s")
        print(f"📊 Số nguồn: {len(sources)}")
        print(f"\n📝 Kết quả:\n{response}")
        print(f"\n🔗 Nguồn tham khảo:")
        for i, url in enumerate(sources, 1):
            print(f"  {i}. {url}")
        
        # Test cache lần 2
        print(f"\n🔄 Testing cache...")
        start_time = time.time()
        cached_response, cached_sources = search.search_with_sources(query)
        cache_elapsed = time.time() - start_time
        print(f"⚡ Cache hit time: {cache_elapsed:.3f}s")
    
    # Print cache stats
    stats = search.get_cache_stats()
    print(f"\n📊 Cache Stats: {stats}")
