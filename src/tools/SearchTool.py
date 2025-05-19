from dotenv import load_dotenv
import os
import warnings
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

# 1) Configure logging to show internal agent flow
logging.basicConfig(
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    level=logging.DEBUG,
    datefmt="%H:%M:%S",
)
# Set specific loggers to DEBUG for detailed trace
logging.getLogger("langgraph").setLevel(logging.DEBUG)
logging.getLogger("langchain_core").setLevel(logging.DEBUG)

# 2) Load environment variables and verify API keys
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
if not GOOGLE_API_KEY or not SERPER_API_KEY:
    raise ValueError("Thiếu GOOGLE_API_KEY hoặc SERPER_API_KEY trong .env file")

# 3) Initialize LLM
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

# 4) Define tool functions
from langchain_community.utilities import GoogleSerperAPIWrapper

search_api = GoogleSerperAPIWrapper(hl="vi", gl="VN")


def tim_kiem(query: str) -> str:
    """Tìm kiếm thông tin bằng Google Serper (Việt Nam)."""
    logging.debug(f"Calling tim_kiem with query: {query}")
    result = search_api.run(query)
    logging.debug(f"tim_kiem result length: {len(result)} characters")
    return result


def thoi_gian() -> str:
    """Trả về ngày giờ hiện tại ở Asia/Ho_Chi_Minh."""
    now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime(
        "%A, %d %B %Y, %H:%M:%S",
    )
    logging.debug(f"thoi_gian returns: {now}")
    return now


# 5) Create ReAct agent with debug True to print flow
from langgraph.prebuilt import create_react_agent

system_prompt = (
    "Bạn là trợ lý CSDL chuyên nghiệp, dùng TIẾNG VIỆT. "
    "Bạn có hai công cụ: tim_kiem(query) và thoi_gian(). "
    "Khi có yêu cầu về xổ số, hãy gọi tim_kiem để lấy kết quả và định dạng trả về rõ ràng."
)
agent = create_react_agent(
    model=llm,
    tools=[tim_kiem, thoi_gian],
    prompt=system_prompt,
    debug=True,
    version="v2",
)

# 6) Invoke the agent and pretty-print the result
if __name__ == "__main__":
    user_query = "cho tôi bảng so sánh hệ quản trị csdl và csdl mới nhất?"
    logging.info(f"User query: {user_query}")
    raw = agent.invoke({"messages": [{"role": "user", "content": user_query}]})
    messages = raw.get("messages", [])
    logging.debug(f"Full agent message flow: {messages}")
    if messages and hasattr(messages[-1], "content"):
        print("\n=== KẾT QUẢ ===")
        print(messages[-1].content.strip())
    else:
        print("Không nhận được câu trả lời phù hợp.")
