"""
optimized_google_search.py
──────────────────────────────────────────────────────────────────────────────
Module tìm kiếm (Google + Tavily) tối ưu cho hệ thống RAG.

• Nếu có SERPER_API_KEY  → ưu tiên Google (Serper.dev) và lấy full‑text của
  N URL đầu tiên (google_top_k).
• Sau đó mới fallback Tavily basic / advanced.
• Trả về tuple (markdown_content, url_list) – giữ nguyên chữ ký hàm cũ.

CHỮ KÝ PUBLIC (KHÔNG THAY ĐỔI)
──────────────────────────────
get_search_instance()
run_query_with_sources(query)
get_raw_search_results(query)
tavily_with_sources(query)

ENV bắt buộc:
• TAVILY_API_KEY
Tùy chọn:
• SERPER_API_KEY          – kích hoạt Serper (Google)
• GOOGLE_API_KEY|GEMINI_API_KEY – kích hoạt Gemini tóm tắt
"""

from __future__ import annotations

import hashlib
import html2text
import logging
import os
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from langchain_tavily import TavilySearch
import requests
from readability import Document  # pip install readability-lxml
# LangChain tools -----------------------------------------------------------
from langchain_community.tools import TavilySearchResults  # type: ignore
try:
    from langchain_community.tools import GoogleSerperResults  # type: ignore
except ImportError:                                            # pragma: no cover
    GoogleSerperResults = None

# Gemini LLM (tùy chọn) -----------------------------------------------------
try:
    from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
except ImportError:                                            # pragma: no cover
    ChatGoogleGenerativeAI = None  # không bắt buộc

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
    max_results: int = 3
    min_docs: int = 3
    max_content_length: int = 4000
    cache_ttl_hours: int = 24
    rate_limit_per_minute: int = 30

    # Google ưu tiên
    prefer_google: bool = True
    google_top_k: int = 3   # số URL đầu tiên sẽ crawl nội dung

    # Tavily
    include_answer: bool = True
    include_raw_content: bool = False
    search_depth_basic: str = "basic"
    search_depth_advanced: str = "advanced"
    escalate_to_advanced: bool = True

    # Serper (Google)
    use_serper: bool = True
    serper_max_results: int = 10

    # LLM (tùy chọn)
    enable_llm: bool = False
    llm_temperature: float = 0.0
    llm_model: str = "gemini-1.5-flash"


# ============================= HELPERS =====================================

class RateLimiter:
    """Giới hạn số lần gọi API / phút (cực đơn giản)."""

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
    """Cache trong RAM – đủ nhanh cho hầu hết use‑case."""

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


# ========================== MAIN CLASS =====================================

class OptimizedGoogleSearch:
    """Serper (Google) ➜ Tavily basic ➜ Tavily advanced (fallback)."""

    # ---------------------------------------------------------------------

    def __init__(self, config: SearchConfig = SearchConfig()):
        self.cfg = config
        self.rate_limiter = RateLimiter(config.rate_limit_per_minute)
        self.cache = SearchCache(config.cache_ttl_hours)

        if not os.getenv("TAVILY_API_KEY"):
            raise ValueError("❌ Thiếu TAVILY_API_KEY trong .env")

        self._init_search_tools()
        self._init_llm()

    # ---------------------------------------------------------------------

    def _init_search_tools(self):
        # Serper (Google)
        self.serper: Optional[GoogleSerperResults] = None
        if (
            self.cfg.use_serper
            and os.getenv("SERPER_API_KEY")
            and GoogleSerperResults is not None
        ):
            self.serper = GoogleSerperResults(k=self.cfg.serper_max_results)
            logger.info("✅ Serper (Google) initialized")
        else:
            logger.info("ℹ️ Serper disabled")

        # Tavily
        common = dict(
            include_answer=self.cfg.include_answer,
            include_raw_content=self.cfg.include_raw_content,
        )
        self.tavily_basic = TavilySearchResults(
            max_results=self.cfg.max_results,
            search_depth=self.cfg.search_depth_basic,
            **common,
        )
        self.tavily_advanced = TavilySearchResults(
            max_results=max(self.cfg.max_results, 10),
            search_depth=self.cfg.search_depth_advanced,
            **common,
        )

    def _init_llm(self):
        self.llm = None
        google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if self.cfg.enable_llm and google_key and ChatGoogleGenerativeAI:
            os.environ["GEMINI_API_KEY"] = google_key
            self.llm = ChatGoogleGenerativeAI(
                model=self.cfg.llm_model,
                temperature=self.cfg.llm_temperature,
            )
            logger.info("✅ Gemini LLM ready")

    # ===================== GOOGLE HELPERS =================================

    @staticmethod
    def _process_serper_results(res: Any, max_len: int) -> Tuple[List[str], str]:
        """Trả về (urls, markdown snippet)."""
        urls, md = [], []
        if not isinstance(res, dict):
            return urls, ""
        # Serper giữ thứ tự organic theo 'position'
        for item in res.get("organic", []):
            url = item.get("link")
            if not url or url in urls:
                continue
            urls.append(url)
            title = item.get("title", "No title")
            snippet = item.get("snippet", "")[:max_len]
            md.append(f"- **{title}** ({url})\n{snippet}\n")
        return urls, "\n".join(md)

    @staticmethod
    def _process_tavily_results(res: Any, max_len: int) -> Tuple[List[str], str]:
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

    # ---------- Crawl page text ------------------------------------------

    @staticmethod
    def _fetch_page_content(url: str, max_len: int = 2_000) -> str:
        try:
            resp = requests.get(
                url,
                timeout=8,
                headers={
                    "User-Agent": "Mozilla/5.0 (RAG/1.0) AppleWebKit/537.36"
                },
            )
            resp.raise_for_status()
            doc = Document(resp.text)
            text = html2text.html2text(doc.summary())
            text = unicodedata.normalize("NFKC", re.sub(r"\s+", " ", text))
            return text[:max_len] + ("…" if len(text) > max_len else "")
        except Exception:
            logger.debug("⚠️ Không lấy được nội dung %s", url)
            return ""

    # =================== PUBLIC METHODS ===================================

    def search_raw_results(self, query: str) -> Tuple[str, List[str]]:
        """Trả về (markdown, urls)."""
        query = query.strip()
        if not query:
            raise ValueError("Query trống")

        # Cache
        hit = self.cache.get(query)
        if hit:
            return hit

        # Rate limit
        if not self.rate_limiter.can_make_call():
            time.sleep(self.rate_limiter.wait_time())

        urls: List[str] = []
        content_parts: List[str] = []

        # 1️⃣ SERPER (Google)
        if self.serper:
            try:
                s_res = self.serper.invoke({"query": query})
                urls_s, md_s = self._process_serper_results(
                    s_res, self.cfg.max_content_length
                )
                # Crawl nội dung Top‑K nếu prefer_google
                if self.cfg.prefer_google:
                    top_urls = urls_s[: self.cfg.google_top_k]
                    if top_urls:                       # <— thêm
                        with ThreadPoolExecutor(max_workers=min(len(top_urls), 8)) as ex:
                            futures = {
                                ex.submit(
                                    self._fetch_page_content, u, self.cfg.max_content_length
                                ): u
                                for u in top_urls
                            }
                        for fut in as_completed(futures):
                            u = futures[fut]
                            txt = fut.result()
                            if txt:
                                texts[u] = txt
                    for u in top_urls:
                        if u in texts:
                            content_parts.append(f"### {u}\n{texts[u]}\n")
                        if u not in urls:
                            urls.append(u)

                    # Nếu còn URL Google ngoài Top‑K → thêm cuối danh sách
                    for u in urls_s[self.cfg.google_top_k :]:
                        if u not in urls:
                            urls.append(u)
                    # snippets Google (md_s) vẫn hữu ích để LLM hiểu ngữ cảnh
                    content_parts.append(md_s)
                else:
                    urls.extend(urls_s)
                    content_parts.append(md_s)
            except Exception as e:  # pragma: no cover
                logger.warning("Serper error: %s – bỏ qua", e)

        # 2️⃣ TAVILY BASIC
        try:
            t_basic = self.tavily_basic.invoke({"query": query})
            urls_t, md_t = self._process_tavily_results(
                t_basic, self.cfg.max_content_length
            )
            urls.extend([u for u in urls_t if u not in urls])
            content_parts.append(md_t)
        except Exception as e:  # pragma: no cover
            logger.warning("Tavily basic error: %s", e)

        # 3️⃣ TAVILY ADVANCED (fallback)
        if (
            self.cfg.escalate_to_advanced
            and len(urls) < self.cfg.min_docs
        ):
            try:
                t_adv = self.tavily_advanced.invoke({"query": query})
                urls_a, md_a = self._process_tavily_results(
                    t_adv, self.cfg.max_content_length
                )
                urls.extend([u for u in urls_a if u not in urls])
                content_parts.append(md_a)
            except Exception as e:  # pragma: no cover
                logger.warning("Tavily advanced error: %s", e)

        if not urls:
            content = "🔍 Không tìm thấy thông tin liên quan đến truy vấn này."
        else:
            content = "\n".join(filter(None, content_parts))

        logger.info("🔍 Hoàn tất tìm kiếm – %d nguồn", len(urls))

        # Cache
        self.cache.set(query, content, urls)
        return content, urls

    # ---------------------------------------------------------------------

    def search_with_sources(self, query: str) -> Tuple[str, List[str]]:
        """Nếu enable_llm → tóm tắt; ngược lại trả raw_content."""
        raw_content, urls = self.search_raw_results(query)
        if not self.llm or raw_content.startswith("🔍"):
            return raw_content, urls

        prompt = f"""Bạn là trợ lý tóm tắt. Hãy trả lời (TV) gồm:
1. **Tóm tắt** thông tin chính.
2. **Nguồn**: liệt kê URL mỗi dòng.

---
{raw_content}
---"""
        try:
            summary = self.llm.invoke(prompt).content.strip()
            return summary, urls
        except Exception as e:  # pragma: no cover
            logger.warning("LLM error, trả raw: %s", e)
            return raw_content, urls

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


# --- Legacy aliases (giữ nguyên chữ ký) -----------------------------------

def run_query_with_sources(query: str) -> Tuple[str, List[str]]:
    logger.warning("⚠️ Legacy function – nên migrate sang get_search_instance().search_with_sources")
    return get_search_instance().search_with_sources(query)


def get_raw_search_results(query: str) -> Tuple[str, List[str]]:
    return get_search_instance().search_raw_results(query)


def tavily_with_sources(query: str) -> Tuple[List[str], str]:
    logger.warning("⚠️ Legacy function – nên migrate sang search_with_sources")
    answer, urls = get_search_instance().search_with_sources(query)
    return urls, answer


# ============================== SELF‑TEST ==================================
if __name__ == "__main__":
    os.environ.setdefault("TAVILY_API_KEY", "DUMMY")
    os.environ.setdefault("SERPER_API_KEY", "DUMMY")
    cfg = SearchConfig(enable_llm=False, google_top_k=3)
    search = OptimizedGoogleSearch(cfg)
    for q in [
        "Những hệ quản trị cơ sở dữ liệu nào đang dẫn đầu về hiệu suất và tính năng trong năm 2025?",
        "ACID vs BASE database",
    ]:
        print("—" * 80)
        print("🔍", q)
        content, urls = search.search_raw_results(q)
        print(content[:800] + ("…" if len(content) > 800 else ""))
        print("\nNguồn:")
        for i, u in enumerate(urls, 1):
            print(f"{i}. {u}")
