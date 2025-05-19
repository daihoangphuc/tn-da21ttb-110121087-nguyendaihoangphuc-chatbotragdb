from dotenv import load_dotenv
import os, warnings
from datetime import datetime
from zoneinfo import ZoneInfo
from langchain_core._api.deprecation import (
    LangChainDeprecationWarning,
    LangChainPendingDeprecationWarning,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain.agents import Tool, initialize_agent, AgentType
from langchain.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)

# 1) Ẩn cảnh báo LangChain
warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)

# 2) Load API keys
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
if not GOOGLE_API_KEY or not SERPER_API_KEY:
    raise ValueError("Thiếu GOOGLE_API_KEY hoặc SERPER_API_KEY")
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
os.environ["SERPER_API_KEY"] = SERPER_API_KEY

# 3) Khởi tạo GoogleSerperAPIWrapper
search_tool = GoogleSerperAPIWrapper(hl="vi", gl="VN")


# 3.1) Định nghĩa hàm tìm kiếm có kèm nguồn (URL)
def search_with_source(query: str) -> str:
    """
    Gọi GoogleSerperAPIWrapper.results() để nhận dict kết quả,
    rồi ghép cả tiêu đề, snippet và URL nguồn (link) cho mỗi mục.
    """
    # 1) Lấy dict trả về
    response = search_tool.results(query)  # sửa từ .search() thành .results()

    # 2) Trích danh sách kết quả organic_results
    organic = response.get("organic_results", [])
    if not organic:
        return "Không tìm thấy kết quả nào."

    # 3) Duyệt và nối chuỗi
    lines = []
    for idx, item in enumerate(organic, start=1):
        title = item.get("title", "<Không có tiêu đề>")
        snippet = item.get("snippet", "").strip()
        link = item.get("link") or item.get("url") or "<Không có link>"
        text = f"{idx}. {title}\n{snippet}\nNguồn: {link}"
        lines.append(text)

    return "\n\n".join(lines)


# 4) Định nghĩa tools: Tìm kiếm (bây giờ dùng search_with_source) + Thời gian
tools = [
    Tool(
        name="Tìm kiếm",
        func=search_with_source,  # đã sửa để gọi .results()
        description="Tìm thông tin trên Google (ưu tiên nguồn tiếng Việt) và kèm đường dẫn nguồn.",
    ),
    Tool(
        name="Thời gian hiện tại",
        func=lambda _: datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime(
            "%A, %d %B %Y, %H:%M:%S"
        ),
        description="Trả về ngày giờ hiện tại theo định dạng Wday, dd Month yyyy, HH:MM:SS.",
    ),
]


# 5) Xây dựng prompt với System + Human
system = SystemMessagePromptTemplate.from_template(
    "Bạn là trợ lý cơ sở dữ liệu chuyên nghiệp. "
    "**MỌI ĐẦU RA** (kể cả Thought, Action, Observation, Final Answer) "
    "phải hoàn toàn BẰNG TIẾNG VIỆT — không dùng tiếng Anh dưới bất kỳ hình thức nào."
)

human = HumanMessagePromptTemplate.from_template(
    """
**Định dạng ReAct (giữ nguyên dấu, bắt buộc):**

Question: {input}  
{agent_scratchpad}

Thought (tiếng Việt): <suy nghĩ của bạn>  
Action: <tên tool>  
Action Input: <đầu vào cho tool>  
Observation: <kết quả từ tool>  
… (lặp Thought/Action/Observation)  
Thought (tiếng Việt): <suy nghĩ cuối cùng>  
Final Answer (tiếng Việt): <câu trả lời cuối cùng>

**Lưu ý thêm:**  
- Nếu input có “hôm nay” hoặc “ngày…”, phải gọi ngay tool “Thời gian hiện tại” trước tool khác.  
- Tập trung chủ yếu vào khái niệm và dữ liệu cơ sở dữ liệu.
"""
)

prompt = ChatPromptTemplate.from_messages([system, human])

# 6) Khởi tạo agent
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    prompt=prompt,
    verbose=True,
    handle_parsing_errors=True,
    agent_kwargs={"stop": ["\nFinal Answer:"], "early_stopping_method": "force"},
)

# 7) Test
if __name__ == "__main__":
    out = agent({"input": "cho tôi bảng so sánh hệ quản trị csdl và csdl mới nhất?"})
    print(out["output"])
