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

# 3) Định nghĩa tools: Tìm kiếm + Thời gian
search_tool = GoogleSerperAPIWrapper(hl="vi", gl="VN")
tools = [
    Tool(
        name="Tìm kiếm",
        func=search_tool.run,
        description="Tìm thông tin trên Google (ưu tiên nguồn tiếng Việt).",
    ),
    Tool(
        name="Thời gian",
        func=lambda _: datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime(
            "%A, %d %B %Y, %H:%M:%S"
        ),
        description="Trả về ngày giờ hiện tại theo định dạng Wday, dd Month yyyy, HH:MM:SS.",
    ),
]

# 4) Xây dựng prompt với System + Human
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
- Nếu input có “hôm nay” hoặc “ngày…”, phải gọi ngay tool “Thời gian” trước tool khác.  
- Tập trung chủ yếu vào khái niệm và dữ liệu cơ sở dữ liệu.
"""
)

prompt = ChatPromptTemplate.from_messages([system, human])

# 5) Khởi tạo agent
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

# 6) Test
if __name__ == "__main__":
    out = agent({"input": "Cho tôi bảng sổ số các giải của đài Bình Phước hôm nay?"})
    print(out["output"])
