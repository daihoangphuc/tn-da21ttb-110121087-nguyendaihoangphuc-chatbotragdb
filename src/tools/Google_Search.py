import os
import logging
from typing import Tuple, List, Any
from langchain.agents import initialize_agent, Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import TavilySearchResults
from dotenv import load_dotenv

load_dotenv()

# Thiết lập API keys
google_api_key = os.getenv('API_KEY_LLM_SEARCH_TOOL')
tavily_api_key = os.getenv('TAVILY_API_KEY')

# Kiểm tra và thông báo nếu API key không tồn tại
if not google_api_key:
    print("GEMINI_API_KEY không được tìm thấy trong biến môi trường")
else:
    os.environ["GEMINI_API_KEY"] = google_api_key

if not tavily_api_key:
    print("TAVILY_API_KEY không được tìm thấy trong biến môi trường")
else:
    os.environ["TAVILY_API_KEY"] = tavily_api_key

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Khởi tạo các components
llm = None
tavily_search = None

try:
    if google_api_key:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0,
            google_api_key=google_api_key
        )
    if tavily_api_key:
        tavily_search = TavilySearchResults(
            max_results=3,
            include_answer=True,
            include_raw_content=True
        )
except Exception as e:
    logger.error(f"Lỗi khi khởi tạo components: {str(e)}")


def tavily_with_sources(query: str) -> Tuple[List[str], str]:
    """
    Truy vấn Tavily để lấy kết quả có cấu trúc (bao gồm URL)
    """
    if not tavily_search:
        logger.error("Tavily search không được khởi tạo do thiếu API key")
        return [], ""
    try:
        results = tavily_search.invoke({"query": query})
        urls = []
        contents = []
        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict) and "url" in item:
                    urls.append(item["url"])
                    contents.append(
                        f"- {item.get('title','')} ({item['url']})\n{item.get('content','')}\n"
                    )
        elif isinstance(results, dict) and "url" in results:
            urls.append(results["url"])
            contents.append(
                f"- {results.get('title','')} ({results['url']})\n{results.get('content','')}\n"
            )
        return urls, "\n".join(contents)
    except Exception as e:
        logger.error(f"Tìm kiếm từ Tavily thất bại: {str(e)}")
        return [], ""


def run_query_with_sources(query: str) -> Tuple[Any, List[str]]:
    """
    Chạy truy vấn và tổng hợp kết quả từ Tavily Search
    """
    if not llm or not tavily_search:
        error_msg = (
            "Không thể thực hiện tìm kiếm do thiếu API key hoặc các components chưa được khởi tạo"
        )
        logger.error(error_msg)
        return error_msg, []

    urls, content = tavily_with_sources(query)
    if not content:
        logger.warning("Không tìm thấy thông tin liên quan đến truy vấn này.")
        return "Không tìm thấy thông tin liên quan đến truy vấn này.", []

    # Xây dựng prompt với system directive và delimiters nhằm ép trích nguyên văn
    prompt = f"""
Bạn là một trợ lý tìm kiếm thông tin chính xác. Nhiệm vụ của bạn là trích dẫn thông tin từ kết quả tìm kiếm web để trả lời câu hỏi.

HƯỚNG DẪN TRÍCH DẪN NGUỒN:
1. Đọc kỹ kết quả tìm kiếm được cung cấp giữa <<RESULT_BEGIN>> và <<RESULT_END>>
2. Trích dẫn NGUYÊN VĂN các đoạn phù hợp từ kết quả tìm kiếm, KHÔNG được thêm, bớt, paraphrase hay giải thích.
3. LUÔN PHẢI kèm URL nguồn trong ngoặc vuông sau mỗi đoạn trích dẫn, theo định dạng: [URL nguồn]
4. Nếu có nhiều nguồn khác nhau, hãy liệt kê từng nguồn riêng biệt.
5. KHÔNG ĐƯỢC BỎ QUA URL nguồn trong bất kỳ trường hợp nào.

ĐỊNH DẠNG ĐẦU RA:
- Sử dụng Markdown chuẩn.
- Với mỗi đoạn trích dẫn, luôn kết thúc bằng URL nguồn trong ngoặc vuông, ví dụ: [https://example.com]
- Nếu trích dẫn từ nhiều nguồn, phân tách rõ ràng giữa các nguồn.

<<RESULT_BEGIN>>
{content}
<<RESULT_END>>

Hãy *chỉ* trích từng đoạn văn hoặc câu trả lời phù hợp nguyên văn giữa hai delimiters bên trên để trả lời cho câu hỏi: \"{query}\".
QUAN TRỌNG: LUÔN PHẢI kèm theo URL nguồn trong ngoặc vuông sau mỗi đoạn trích dẫn.
"""
    try:
        # Gọi LLM với prompt dạng string đơn
        summary = llm.invoke(prompt)
        return summary, urls
    except Exception as e:
        logger.error(f"Xử lý LLM thất bại: {str(e)}")
        return "Đã xảy ra lỗi khi xử lý kết quả tìm kiếm.", urls


if __name__ == "__main__":
    query = "Cú pháp select mới nhất và đầy đủ của lệnh select trong csdl?"
    summary, sources = run_query_with_sources(query)
    print("Câu trả lời tóm tắt:\n")
    print(summary)
    print("\nNguồn tham khảo:")
    for url in sources:
        print("-", url)
