"""
Google Search Module for RAG System
──────────────────────────────────────────────────────────────────────────────
Module tìm kiếm Google sử dụng Custom Search JSON API.

CHỮ KÝ PUBLIC (GIỮ NGUYÊN ĐỂ TƯƠNG THÍCH)
──────────────────────────────
get_search_instance()
run_query_with_sources(query)
get_raw_search_results(query)
tavily_with_sources(query)

ENV bắt buộc:
• GOOGLE_API_KEY      – API key cho Google Custom Search
• GOOGLE_CSE_ID       – Custom Search Engine ID
Tùy chọn:
• TAVILY_API_KEY      – fallback cho Tavily (để tương thích cũ)
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import requests
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from googleapiclient.discovery import build
except ImportError:
    build = None

# Fallback Tavily imports (sử dụng package mới)
try:
    from langchain_tavily import TavilySearch
except ImportError:
    # Fallback to old import if new package not available
    try:
        from langchain_community.tools import TavilySearch
    except ImportError:
        TavilySearch = None

# ────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[Google_Search] %(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================= CONFIG ======================================

@dataclass
class SearchConfig:
    # Hành vi chung
    max_results: int = 10
    min_docs: int = 3
    max_content_length: int = 4000
    cache_ttl_hours: int = 24
    rate_limit_per_minute: int = 30

    # Google Custom Search
    language: str = 'vi'
    country: str = 'countryVN'
    use_google_custom_search: bool = True

    # Tavily fallback
    use_tavily_fallback: bool = True
    include_answer: bool = True
    include_raw_content: bool = False


# ============================= HELPERS =====================================

class RateLimiter:
    """Giới hạn số lần gọi API / phút."""

    def __init__(self, max_calls_per_minute: int):
        self.max_calls = max_calls_per_minute
        self.calls: List[datetime] = []

    def can_make_call(self) -> bool:
        now = datetime.now()
        self.calls = [t for t in self.calls if now - t < timedelta(minutes=1)]
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        return False

    def wait_time(self) -> float:
        if not self.calls:
            return 0.0
        oldest = min(self.calls)
        return max(0.0, (oldest + timedelta(minutes=1) - datetime.now()).total_seconds())


class SearchCache:
    """Cache trong RAM cho kết quả tìm kiếm."""

    def __init__(self, ttl_hours: int):
        self.ttl = ttl_hours
        self.store: Dict[str, Dict] = {}

    def _key(self, query: str) -> str:
        return hashlib.md5(query.lower().strip().encode()).hexdigest()

    def get(self, query: str) -> Optional[Tuple[str, List[str]]]:
        k = self._key(query)
        entry = self.store.get(k)
        if not entry:
            return None
        if datetime.now() - entry["ts"] > timedelta(hours=self.ttl):
            del self.store[k]
            return None
        logger.info("🎯 Cache hit cho query: %s…", query[:60])
        return entry["content"], entry["urls"]

    def set(self, query: str, content: str, urls: List[str]):
        self.store[self._key(query)] = {
            "content": content,
            "urls": urls,
            "ts": datetime.now(),
        }


# ========================== GOOGLE SEARCH MODULE ===========================

class GoogleSearchModule:
    """
    Module thực hiện tìm kiếm Google bằng Custom Search JSON API.

    Thuộc tính:
        api_key (str): Khóa API cho Custom Search API.
        cse_id (str): ID của công cụ tìm kiếm tùy chỉnh.
        language (str): Mã ngôn ngữ cho giao diện tìm kiếm (mặc định: 'vi').
        country (str): Mã quốc gia để giới hạn kết quả (mặc định: 'countryVN').
    """

    def __init__(self, api_key, cse_id, language='vi', country='countryVN'):
        """
        Khởi tạo GoogleSearchModule.

        Tham số:
            api_key (str): Khóa API cho Custom Search API.
            cse_id (str): ID của công cụ tìm kiếm tùy chỉnh.
            language (str): Mã ngôn ngữ cho giao diện tìm kiếm (mặc định: 'vi').
            country (str): Mã quốc gia để giới hạn kết quả (mặc định: 'countryVN').
        """
        if not build:
            raise ImportError("googleapiclient.discovery không có sẵn. Cài đặt: pip install google-api-python-client")
        
        self.api_key = api_key
        self.cse_id = cse_id
        self.language = language
        self.country = country
        self.service = build("customsearch", "v1", developerKey=api_key)

    def search(self, query, num=10):
        """
        Thực hiện tìm kiếm bằng Google Custom Search API.

        Tham số:
            query (str): Truy vấn tìm kiếm.
            num (int): Số lượng kết quả trả về (mặc định: 10).

        Trả về:
            list: Danh sách các từ điển chứa 'title', 'link', và 'snippet' cho mỗi kết quả.
        """
        try:
            res = self.service.cse().list(
                q=query,
                cx=self.cse_id,
                num=min(num, 10),  # Google Custom Search giới hạn 10 kết quả/request
                hl=self.language,
                cr=self.country
            ).execute()
            
            if 'items' not in res:
                return []
                
            return [
                {
                    'title': item.get('title', 'No title'),
                    'link': item.get('link', ''),
                    'snippet': item.get('snippet', '')
                }
                for item in res['items']
            ]
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện tìm kiếm Google Custom Search: {e}")
            return []


# ========================== MAIN SEARCH CLASS ==============================

class OptimizedGoogleSearch:
    """Tìm kiếm Google sử dụng Custom Search API với fallback Tavily."""

    def __init__(self, config: SearchConfig = SearchConfig()):
        self.cfg = config
        self.rate_limiter = RateLimiter(config.rate_limit_per_minute)
        self.cache = SearchCache(config.cache_ttl_hours)

        self._init_search_tools()

    def _init_search_tools(self):
        # Google Custom Search
        self.google_search: Optional[GoogleSearchModule] = None
        google_api_key = os.getenv("GOOGLE_API_KEY")
        google_cse_id = os.getenv("GOOGLE_CSE_ID")
        
        if (
            self.cfg.use_google_custom_search
            and google_api_key
            and google_cse_id
            and build is not None
        ):
            try:
                self.google_search = GoogleSearchModule(
                    api_key=google_api_key,
                    cse_id=google_cse_id,
                    language=self.cfg.language,
                    country=self.cfg.country
                )
                logger.info("✅ Google Custom Search initialized")
            except Exception as e:
                logger.warning(f"Không thể khởi tạo Google Custom Search: {e}")
                self.google_search = None
        else:
            logger.info("ℹ️ Google Custom Search disabled hoặc thiếu cấu hình")

        # Tavily fallback
        self.tavily_search: Optional[TavilySearch] = None
        if (
            self.cfg.use_tavily_fallback
            and os.getenv("TAVILY_API_KEY")
            and TavilySearch is not None
        ):
            try:
                self.tavily_search = TavilySearch(
                    max_results=self.cfg.max_results,
                    include_answer=self.cfg.include_answer,
                    include_raw_content=self.cfg.include_raw_content,
                )
                logger.info("✅ Tavily fallback initialized")
            except Exception as e:
                logger.warning(f"Không thể khởi tạo Tavily fallback: {e}")
                self.tavily_search = None
        else:
            logger.info("ℹ️ Tavily fallback disabled")

    def _process_google_results(self, results: List[Dict], max_len: int) -> Tuple[List[str], str]:
        """Xử lý kết quả từ Google Custom Search."""
        urls, md = [], []
        
        for item in results:
            url = item.get('link', '')
            if not url or url in urls:
                continue
                
            urls.append(url)
            title = item.get('title', 'No title')
            snippet = item.get('snippet', '')[:max_len]
            md.append(f"- **{title}** ({url})\n{snippet}\n")
            
        return urls, "\n".join(md)

    def _process_tavily_results(self, res: Any, max_len: int) -> Tuple[List[str], str]:
        """Xử lý kết quả từ Tavily."""
        urls, md = [], []
        iterable = res if isinstance(res, list) else [res]
        
        for item in iterable:
            if not isinstance(item, dict) or "url" not in item:
                continue
            url = item["url"]
            if url in urls:
                continue
            urls.append(url)
            title = item.get("title", "No title")
            content = item.get("content", "")[:max_len]
            if len(item.get("content", "")) > max_len:
                content += "…"
            md.append(f"- **{title}** ({url})\n{content}\n")
        return urls, "\n".join(md)

    def search_raw_results(self, query: str) -> Tuple[str, List[str]]:
        """Trả về (markdown_content, url_list)."""
        query = query.strip()
        if not query:
            raise ValueError("Query trống")

        # Cache check
        hit = self.cache.get(query)
        if hit:
            return hit

        # Rate limiting
        if not self.rate_limiter.can_make_call():
            time.sleep(self.rate_limiter.wait_time())

        urls: List[str] = []
        content_parts: List[str] = []

        # 1️⃣ Thử Google Custom Search trước
        if self.google_search:
            try:
                google_results = self.google_search.search(query, num=self.cfg.max_results)
                if google_results:
                    urls_g, md_g = self._process_google_results(
                        google_results, self.cfg.max_content_length
                    )
                    urls.extend(urls_g)
                    content_parts.append(md_g)
                    logger.info(f"🔍 Google Custom Search: {len(urls_g)} kết quả")
                else:
                    logger.info("🔍 Google Custom Search: Không có kết quả")
            except Exception as e:
                logger.warning(f"Google Custom Search error: {e}")

        # 2️⃣ Fallback Tavily nếu cần
        if (
            len(urls) < self.cfg.min_docs
            and self.tavily_search
        ):
            try:
                tavily_results = self.tavily_search.invoke({"query": query})
                urls_t, md_t = self._process_tavily_results(
                    tavily_results, self.cfg.max_content_length
                )
                # Thêm URLs mới (không trùng)
                urls.extend([u for u in urls_t if u not in urls])
                content_parts.append(md_t)
                logger.info(f"🔍 Tavily fallback: {len(urls_t)} kết quả")
            except Exception as e:
                logger.warning(f"Tavily fallback error: {e}")

        if not urls:
            content = "🔍 Không tìm thấy thông tin liên quan đến truy vấn này."
        else:
            content = "\n".join(filter(None, content_parts))

        logger.info(f"🔍 Hoàn tất tìm kiếm – {len(urls)} nguồn")

        # Cache kết quả
        self.cache.set(query, content, urls)
        return content, urls

    def search_with_sources(self, query: str) -> Tuple[str, List[str]]:
        """Giống search_raw_results (để tương thích)."""
        return self.search_raw_results(query)

    # Debug helpers
    def get_cache_stats(self) -> Dict[str, Any]:
        return {
            "cache_size": len(self.cache.store),
            "rate_limit_calls": len(self.rate_limiter.calls),
            "max_calls_per_minute": self.rate_limiter.max_calls,
        }

    def clear_cache(self):
        self.cache.store.clear()
        logger.info("🗑️ Cache cleared")


# ================== SINGLETON & LEGACY WRAPPERS ============================

_search_instance: Optional[OptimizedGoogleSearch] = None


def get_search_instance(config: SearchConfig = SearchConfig()) -> OptimizedGoogleSearch:
    """Trả về singleton (dùng chung trong cả app)."""
    global _search_instance
    if _search_instance is None:
        _search_instance = OptimizedGoogleSearch(config)
    return _search_instance


# --- Legacy aliases (giữ nguyên chữ ký để tương thích) ---

def run_query_with_sources(query: str) -> Tuple[str, List[str]]:
    """Legacy function - migrate to get_search_instance().search_with_sources"""
    logger.warning("⚠️ Legacy function – nên migrate sang get_search_instance().search_with_sources")
    return get_search_instance().search_with_sources(query)


def get_raw_search_results(query: str) -> Tuple[str, List[str]]:
    """Legacy function - giữ nguyên để tương thích với rag.py"""
    return get_search_instance().search_raw_results(query)


def tavily_with_sources(query: str) -> Tuple[List[str], str]:
    """Legacy function - migrate to search_with_sources"""
    logger.warning("⚠️ Legacy function – nên migrate sang search_with_sources")
    answer, urls = get_search_instance().search_with_sources(query)
    return urls, answer


# ============================== TESTING ====================================
if __name__ == "__main__":
    # Test với dummy config
    os.environ.setdefault("GOOGLE_API_KEY", "DUMMY")
    os.environ.setdefault("GOOGLE_CSE_ID", "DUMMY")
    
    cfg = SearchConfig(max_results=5)
    search = OptimizedGoogleSearch(cfg)
    
    test_queries = [
        "Hệ quản trị cơ sở dữ liệu nào tốt nhất?",
        "ACID vs BASE database",
    ]
    
    for q in test_queries:
        print("—" * 80)
        print("🔍", q)
        try:
            content, urls = search.search_raw_results(q)
            print(content[:500] + ("…" if len(content) > 500 else ""))
            print(f"\nNguồn ({len(urls)}):")
            for i, u in enumerate(urls, 1):
                print(f"{i}. {u}")
        except Exception as e:
            print(f"Lỗi: {e}")
