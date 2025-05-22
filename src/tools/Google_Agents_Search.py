#!/usr/bin/env python3
# filename: Google_Agents_Search.py

import os
import asyncio
from dotenv import load_dotenv
import uuid # Thêm uuid để tạo session_id động
import logging

# --- Load environment variables from .env ---
load_dotenv()

# --- Google ADK & GenAI imports ---
from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from typing import List, Dict # Thêm typing

# Cấu hình logging cho module này
logger = logging.getLogger(__name__)
# Ghi đè hàm print để thêm prefix
original_print = print
def print(*args, **kwargs):
    prefix = "[GoogleAgentSearch] "
    original_print(prefix + " ".join(map(str, args)), **kwargs)


# Biến toàn cục để tránh khởi tạo lại mỗi lần gọi
_search_agent_global = None
_session_service_global = None
_google_search_configured = False

def configure_google_search_auth():
    """Cấu hình xác thực và khởi tạo các thành phần dùng chung cho Google Search Agent."""
    global _search_agent_global, _session_service_global, _google_search_configured
    if _google_search_configured:
        # print("Google Search đã được cấu hình trước đó.")
        return

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("Thiếu GOOGLE_API_KEY! Vui lòng thêm vào file .env.")
        raise RuntimeError(
            "Thiếu GOOGLE_API_KEY! Vui lòng thêm vào file .env."
        )
    
    # print("Đang cấu hình Google Search Agent...")
    _search_agent_global = LlmAgent(
        model=os.getenv("GOOGLE_SEARCH_AGENT_MODEL", "gemini-1.5-flash-latest"),
        name="rag_google_search_agent",
        description="Agent hỗ trợ tìm kiếm thông tin trên Google cho hệ thống RAG.",
        instruction=(
            "Bạn là một trợ lý tìm kiếm hiệu quả. "
            "Khi nhận được yêu cầu, hãy sử dụng công cụ google_search để tìm thông tin. "
            "Mục tiêu chính là trích xuất nội dung văn bản và URL nguồn của các kết quả tìm thấy. "
            "Chỉ trả về các kết quả trực tiếp từ công cụ tìm kiếm, không thêm bất kỳ phân tích hay tổng hợp nào của riêng bạn. "
            "Đảm bảo mỗi kết quả trả về bao gồm cả văn bản tìm được và URL nguồn đầy đủ."
        ),
        tools=[google_search],
    )
    _session_service_global = InMemorySessionService()
    _google_search_configured = True
    print("Đã cấu hình Google Search Agent thành công.")

async def search_google_for_rag(query: str, user_id: str = "rag_fallback_user") -> List[Dict]:
    """
    Sử dụng Google Agent để tìm kiếm thông tin cho RAG fallback.
    Trả về một danh sách các dictionary, mỗi dict chứa 'text' và 'source' (URL).
    """
    global _search_agent_global, _session_service_global, _google_search_configured

    if not _google_search_configured:
        try:
            print("Google Search chưa được cấu hình. Đang thử cấu hình...")
            configure_google_search_auth()
        except RuntimeError as e:
            logger.error(f"Lỗi cấu hình Google Search Agent: {e}")
            return [] # Trả về rỗng nếu không cấu hình được

    if not _search_agent_global or not _session_service_global:
        logger.error("Google Search Agent hoặc Session Service chưa được khởi tạo.")
        return []

    runner = Runner(
        agent=_search_agent_global,
        app_name="rag_google_search_fallback_app", # Tên app_name duy nhất
        session_service=_session_service_global,
    )

    session_id = f"rag_fallback_session_{uuid.uuid4().hex}"

    try:
        await _session_service_global.create_session(
            user_id=user_id,
            session_id=session_id,
            app_name="rag_google_search_fallback_app",
        )

        search_query_content = types.Content(role="user", parts=[types.Part(text=query)])
        
        google_results: List[Dict] = []
        print(f"Đang thực hiện tìm kiếm trên Google cho query: '{query}'")

        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=search_query_content
        ):
            if hasattr(event, "tool_code") and event.tool_code:
                print(f"Agent đang gọi tool: {event.tool_code.name} với input: {event.tool_code.input}")

            if hasattr(event, "tool_response") and event.tool_response and event.tool_response.documents:
                print(f"Nhận được {len(event.tool_response.documents)} tài liệu từ Google Search.")
                for doc in event.tool_response.documents:
                    source_url = doc.metadata.get("source", "Không rõ nguồn")
                    doc_text = doc.text.strip() if doc.text else ""
                    
                    if doc_text and source_url and source_url.startswith("http"):
                        google_results.append({
                            "text": doc_text,
                            "source": source_url,
                            # metadata sẽ được thêm ở rag.py để có cấu trúc đồng nhất
                        })
            
            if event.is_final_response():
                # print(f"Phản hồi cuối cùng từ search agent (thường không cần thiết nếu chỉ lấy tool data): {event.content.parts[0].text if event.content and event.content.parts else 'Không có'}")
                # Vì instruction yêu cầu agent chỉ trả về kết quả thô từ tool,
                # final_response có thể không chứa thông tin hữu ích cho việc gộp context.
                # Chúng ta chủ yếu dựa vào tool_response.
                break # Thoát sớm khi có final response để không xử lý các event không cần thiết khác

    except Exception as e:
        logger.error(f"Lỗi trong quá trình chạy Google search agent: {e}", exc_info=True)
    finally:
        try:
            await _session_service_global.delete_session(user_id=user_id, session_id=session_id)
            # print(f"Đã xóa session: {session_id}")
        except Exception as e_del:
            logger.error(f"Lỗi khi xóa session {session_id}: {e_del}")
            
    print(f"Tìm kiếm Google hoàn tất. Trả về {len(google_results)} kết quả.")
    return google_results

async def _test_run():
    """Hàm test cho module này."""
    try:
        configure_google_search_auth()
    except RuntimeError as e:
        print(f"Lỗi cấu hình: {e}")
        return

    # test_query = "Mô tả về primary key và unique trong cơ sở dữ liệu?"
    test_query = "Các loại join phổ biến trong SQL là gì?"
    print(f"\nBắt đầu test tìm kiếm Google cho query: '{test_query}'")
    
    results = await search_google_for_rag(test_query)
    
    print("\n=== Kết quả Google Search trả về cho RAG (test) ===")
    if results:
        for i, res in enumerate(results, 1):
            print(f"  Kết quả {i}:")
            print(f"    Text: {res['text'][:200]}...")
            print(f"    Source: {res['source']}")
    else:
        print("  Không có kết quả nào từ Google Search.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    asyncio.run(_test_run())