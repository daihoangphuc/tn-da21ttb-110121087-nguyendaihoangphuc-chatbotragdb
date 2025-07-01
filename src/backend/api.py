from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Form,
    HTTPException,
    BackgroundTasks,
    Depends,
    Query,
    Path,
    Header,
    Cookie,
    Response,
    status,
    APIRouter,
    Body,
    Request,
)
from fastapi.responses import (
    JSONResponse,
    StreamingResponse,
    HTMLResponse,
    FileResponse,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Dict, Optional, Union, Any
import os
import uvicorn
import shutil
from uuid import uuid4
import time
import uuid
import httpx
from urllib.parse import urljoin
import json
import traceback
from datetime import datetime, timezone, timedelta
from os import path
from dotenv import load_dotenv
import supabase
import re
import asyncio
import pytz
from uuid import UUID

from backend.rag import AdvancedDatabaseRAG
from backend.supabase.conversation_manager import SupabaseConversationManager

# Load biến môi trường từ .env
load_dotenv()

# Thêm prefix API
PREFIX = os.getenv("API_PREFIX", "/api")
from backend.suggestion_manager import SuggestionManager

# Khởi tạo SuggestionManager
suggestion_manager = SuggestionManager()
# Khởi tạo ứng dụng FastAPI
app = FastAPI(
    title=os.getenv("API_TITLE", "Hệ thống RAG cho Cơ sở dữ liệu"),
    description=os.getenv(
        "API_DESCRIPTION", "API cho hệ thống tìm kiếm và trả lời câu hỏi sử dụng RAG"
    ),
    version=os.getenv("API_VERSION", "1.0.0"),
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware để giới hạn kích thước request body (10MB)
@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    # Chỉ áp dụng cho upload endpoints
    if request.url.path.endswith("/upload"):
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            max_size = 10 * 1024 * 1024  # 10MB
            if content_length > max_size:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"Request body quá lớn. Kích thước tối đa: 10MB, nhận được: {content_length / (1024*1024):.2f}MB"
                    }
                )
    
    response = await call_next(request)
    return response

# Khởi tạo hệ thống RAG
rag_system = AdvancedDatabaseRAG()

# Hàm utility để lấy thời gian Việt Nam
def get_vietnam_time():
    """Lấy thời gian hiện tại theo múi giờ Việt Nam"""
    vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    return datetime.now(vietnam_tz)

def format_vietnam_time_iso(dt=None):
    """Format thời gian Việt Nam thành ISO string"""
    if dt is None:
        dt = get_vietnam_time()
    return dt.isoformat()

def parse_and_format_vietnam_time(time_str):
    """Parse thời gian từ database và chuyển về múi giờ Việt Nam"""
    try:
        # Kiểm tra nếu time_str là None hoặc chuỗi rỗng
        if not time_str or time_str == "":
            return ""
        
        if isinstance(time_str, str):
            # Xử lý các format thời gian khác nhau
            time_str_cleaned = time_str.strip()
            
            # Nếu có 'Z' thì thay bằng '+00:00'
            if time_str_cleaned.endswith('Z'):
                time_str_cleaned = time_str_cleaned.replace('Z', '+00:00')
            
            # Nếu không có timezone và có dấu chấm (microseconds)
            elif '+' not in time_str_cleaned and 'T' in time_str_cleaned:
                # Thêm timezone UTC nếu không có
                if '.' in time_str_cleaned:
                    # Cắt microseconds về 6 chữ số nếu cần
                    parts = time_str_cleaned.split('.')
                    if len(parts) == 2:
                        microseconds = parts[1][:6].ljust(6, '0')  # Đảm bảo có đúng 6 chữ số
                        time_str_cleaned = f"{parts[0]}.{microseconds}+00:00"
                else:
                    time_str_cleaned = f"{time_str_cleaned}+00:00"
            
            # Parse thời gian từ string ISO
            dt = datetime.fromisoformat(time_str_cleaned)
            
            # Chuyển về múi giờ Việt Nam
            vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            if dt.tzinfo is None:
                # Nếu không có timezone info, coi như UTC
                dt = pytz.UTC.localize(dt)
            
            vietnam_time = dt.astimezone(vietnam_tz)
            return vietnam_time.isoformat()
        
        return time_str
    except Exception as e:
        print(f"Lỗi khi parse thời gian '{time_str}': {e}")
        # Trả về chuỗi gốc hoặc chuỗi rỗng thay vì None để tránh lỗi JSON
        return time_str if time_str else ""

# Khởi tạo quản lý hội thoại
try:
    conversation_manager = SupabaseConversationManager()
    print(
        "Khởi tạo SupabaseConversationManager thành công để lưu trữ hội thoại qua Supabase"
    )
except Exception as e:
    print(f"Lỗi khi khởi tạo SupabaseConversationManager: {str(e)}")
    print("Không thể sử dụng SupabaseConversationManager")
    import traceback

    print(f"Chi tiết lỗi: {traceback.format_exc()}")
    raise

# Sẽ khởi tạo Learning Analytics Service sau khi có supabase_client
analytics_service = None

# Đường dẫn lưu dữ liệu tạm thời
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "backend/data")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Hàm để lấy đường dẫn thư mục của user
def get_user_upload_dir(user_id: str) -> str:
    """Tạo và trả về đường dẫn thư mục upload cho user cụ thể"""
    user_dir = os.path.join(UPLOAD_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


# Models cho API
class QuestionRequest(BaseModel):
    question: str
    # sources: Optional[List[str]] = None  # Danh sách các file nguồn cần tìm kiếm (không khuyến khích sử dụng)
    # file_id: Optional[List[str]] = None  # Danh sách các file_id cần tìm kiếm (tùy chọn, nếu không cung cấp sẽ tìm kiếm trên toàn bộ tài liệu)
    conversation_id: Optional[str] = (
        None  # ID phiên hội thoại, tự động tạo nếu không có
    )

class SQLAnalysisRequest(BaseModel):
    sql_query: str
    database_context: Optional[str] = None


class SQLAnalysisResponse(BaseModel):
    query: str
    analysis: str
    suggestions: List[str]
    optimized_query: Optional[str] = None


class IndexingStatusResponse(BaseModel):
    status: str
    message: str
    processed_files: int


class CategoryStatsResponse(BaseModel):
    total_documents: int
    documents_by_category: Dict[str, int]
    categories: List[str]

# Model cho quên mật khẩu
class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    redirect_to: Optional[str] = None  # URL chuyển hướng sau khi đặt lại mật khẩuAdd commentMore actions


# Model cho đặt lại mật khẩu
class ResetPasswordRequest(BaseModel):
    password: str
    access_token: str  # Thêm trường access_token từ body request
    
    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, v):
        # Kiểm tra độ dài mật khẩu
        if len(v) < 8:
            raise ValueError("Mật khẩu phải có ít nhất 8 ký tự")
        # Kiểm tra có ít nhất một chữ hoa
        if not any(c.isupper() for c in v):
            raise ValueError("Mật khẩu phải có ít nhất một chữ cái viết hoa")
        # Kiểm tra có ít nhất một chữ thường
        if not any(c.islower() for c in v):
            raise ValueError("Mật khẩu phải có ít nhất một chữ cái viết thường")
        # Kiểm tra có ít nhất một chữ số
        if not any(c.isdigit() for c in v):
            raise ValueError("Mật khẩu phải có ít nhất một chữ số")
        return v


# Model cho phản hồi quên mật khẩu
class ForgotPasswordResponse(BaseModel):
    status: str
    message: str


# Biến lưu trạng thái quá trình indexing
indexing_status = {
    "is_running": False,
    "status": "idle",
    "message": "Hệ thống sẵn sàng",
    "processed_files": 0,
}

# Lưu lịch sử câu hỏi
questions_history = {}


# Hàm xử lý indexing trong background
def indexing_documents():
    global indexing_status

    try:
        indexing_status["is_running"] = True
        indexing_status["status"] = "running"
        indexing_status["message"] = "Đang tải và xử lý tài liệu..."

        # Tải và xử lý tài liệu
        documents = rag_system.load_documents(UPLOAD_DIR)
        indexing_status["processed_files"] = len(documents)
        indexing_status["message"] = f"Đã tải {len(documents)} tài liệu. Đang xử lý..."

        processed_chunks = rag_system.process_documents(documents)
        indexing_status["message"] = (
            f"Đã xử lý {len(processed_chunks)} chunks. Đang index..."
        )

        # Index lên vector store
        rag_system.index_to_qdrant(processed_chunks)

        # # Cập nhật BM25 index sau khi đã index xong tài liệu
        # indexing_status["message"] = "Đang cập nhật BM25 index..."
        # rag_system.search_manager.update_bm25_index()

        indexing_status["status"] = "completed"
        indexing_status["message"] = (
            f"Đã hoàn thành index {len(processed_chunks)} chunks từ {len(documents)} tài liệu"
        )
    except Exception as e:
        indexing_status["status"] = "error"
        indexing_status["message"] = f"Lỗi khi indexing: {str(e)}"
    finally:
        indexing_status["is_running"] = False


# Thêm model mới cho danh sách file
class FileInfo(BaseModel):
    filename: str
    path: str
    size: int
    upload_date: Optional[str] = None
    extension: str
    category: Optional[str] = None
    id: Optional[str] = None  # Thêm trường id để lưu file_id


class FileListResponse(BaseModel):
    total_files: int
    files: List[FileInfo]


class FileDeleteResponse(BaseModel):
    filename: str
    status: str
    message: str
    removed_points: Optional[int] = None


# Thêm model để quản lý phiên hội thoại
class ConversationRequest(BaseModel):
    conversation_id: str


class CreateConversationResponse(BaseModel):
    status: str
    message: str
    conversation_id: str


class DeleteConversationResponse(BaseModel):
    status: str
    message: str
    conversation_id: str


# Models cho API xác thực
class UserSignUpRequest(BaseModel):
    email: EmailStr
    password: str


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    code: Optional[str] = None
    access_token: Optional[str] = None
    provider: str = "google"

    @field_validator("code", "access_token")
    @classmethod
    def check_auth_method(cls, v, info):
        # Get field values from ValidationInfo
        data = info.data if hasattr(info, 'data') else {}
        if not any([data.get("code"), data.get("access_token"), v]):
            raise ValueError("Phải cung cấp một trong hai: code hoặc access_token")
        return v


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: Optional[str] = "student"  # Default role is student


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None


# Khởi tạo thư viện xác thực
auth_bearer = HTTPBearer(auto_error=False)

# Khởi tạo client Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase_client = None

# Khởi tạo biến current_conversation_id
current_conversation_id = None

if supabase_url and supabase_key:
    try:
        supabase_client = supabase.create_client(supabase_url, supabase_key)
    except Exception as e:
        print(f"Lỗi khi khởi tạo Supabase client: {str(e)}")
else:
    print("Cảnh báo: Chưa cấu hình SUPABASE_URL và SUPABASE_KEY trong .env")

# Khởi tạo Learning Analytics Service sau khi có supabase_client
if supabase_client:
    try:
        from backend.learning_analytics_api import LearningAnalyticsService
        analytics_service = LearningAnalyticsService(supabase_client)
        print("Khởi tạo LearningAnalyticsService thành công")
    except Exception as e:
        print(f"Lỗi khi khởi tạo LearningAnalyticsService: {str(e)}")
        analytics_service = None


# Hàm để lấy người dùng hiện tại từ token
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_bearer),
):
    if not supabase_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ xác thực chưa được cấu hình",
        )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không tìm thấy thông tin xác thực",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Thử lấy thông tin người dùng hiện tại bằng token từ request
        try:
            # Lấy access token từ request
            token = credentials.credentials

            # Xử lý trường hợp token bị lặp lại "Bearer"
            if token.lower().startswith("bearer "):
                token = token[7:]  # Cắt bỏ "Bearer " từ đầu token
                print(f"Đã phát hiện và xử lý token có prefix 'Bearer' trùng lặp")

            # Sử dụng token để xác thực
            response = supabase_client.auth.get_user(jwt=token)
            user_response = response

            if not user_response or not user_response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Kiểm tra và lấy vai trò của người dùng từ metadata hoặc từ bảng users
            try:
                user_id = user_response.user.id
                # Kiểm tra xem người dùng có vai trò admin không
                # Truy vấn bảng user_roles hoặc metadata để lấy vai trò
                role_data = supabase_client.table("user_roles").select("role").eq("user_id", user_id).execute()
                
                # Mặc định vai trò là student
                user_role = "student"
                
                # Nếu có dữ liệu về vai trò, cập nhật vai trò
                if role_data.data and len(role_data.data) > 0:
                    user_role = role_data.data[0].get("role", "student")
                
                # Gán vai trò vào đối tượng user
                user_response.user.role = user_role
                
                print(f"Người dùng {user_response.user.email} có vai trò: {user_role}")
            except Exception as e:
                print(f"Lỗi khi lấy vai trò người dùng: {str(e)}")
                # Nếu không lấy được vai trò, mặc định là student
                user_response.user.role = "student"
        except Exception as e:
            print(f"Lỗi khi lấy thông tin người dùng từ token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ hoặc đã hết hạn",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user_response.user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Lỗi xác thực: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# API routes
@app.get(f"{PREFIX}/")
async def root():
    return {
        "message": "Chào mừng đến với API của hệ thống RAG. Truy cập /docs để xem tài liệu API."
    }

@app.post(f"{PREFIX}/ask/stream")
async def ask_question_stream(
    request: QuestionRequest,
    max_sources: Optional[int] = Query(
        None,
        description="Số lượng nguồn tham khảo tối đa trả về. Để None để hiển thị tất cả.",
        ge=1,
        le=50,
    ),
    current_user=Depends(get_current_user),
):
    """
    Đặt câu hỏi và nhận câu trả lời từ hệ thống RAG dưới dạng stream

    - **question**: Câu hỏi cần trả lời
    - **file_id**: Danh sách các file_id của tài liệu cần tìm kiếm (không bắt buộc)
    - **current_conversation_id**: ID phiên hội thoại để duy trì ngữ cảnh cuộc hội thoại
    - **max_sources**: Số lượng nguồn tham khảo tối đa trả về (query parameter)
    """
    try:
        # Lấy hoặc tạo ID phiên hội thoại
        user_id = current_user.id

        # Đặt collection_name cho vector store
        rag_system.vector_store.collection_name = "global_documents"
        # Cập nhật user_id cho vector_store trong SearchManager
        rag_system.vector_store.user_id = user_id

        # Lấy danh sách file_id từ request nếu có
        search_file_ids = None
        
        # Nếu không có file_id trong request, lấy tất cả file_id có sẵn từ Supabase
        if not search_file_ids or len(search_file_ids) == 0:
            try:
                # Sử dụng service client để lấy tất cả file_id
                from backend.supabase.files_manager import FilesManager
                from backend.supabase.client import SupabaseClient
                
                supabase_client_with_service_role = SupabaseClient(use_service_key=True)
                client = supabase_client_with_service_role.get_client()
                files_manager = FilesManager(client)
                
                # Lấy tất cả file từ database
                all_files = files_manager.get_all_files(include_deleted=False)
                
                # Tạo danh sách file_id từ kết quả
                search_file_ids = [file.get("file_id") for file in all_files if file.get("file_id")]
                
                print(f"Tự động tìm kiếm trên {len(search_file_ids)} file có sẵn trong hệ thống")
            except Exception as e:
                print(f"Lỗi khi lấy danh sách file_id: {str(e)}")
                search_file_ids = []

        # Tạo ID cho câu hỏi
        question_id = f"q_{uuid4().hex[:8]}"

        # Thêm tin nhắn người dùng vào bộ nhớ hội thoại
        conversation_manager.add_user_message(
            conversation_manager.get_current_conversation_id(),
            request.question,
            user_id=user_id,
        )
        
        # Thêm phân tích learning analytics (async, không block)
        if analytics_service and current_user:
            # Lưu message_id từ message vừa được lưu
            try:
                # Lấy message_id mới nhất của user trong conversation này
                latest_message_result = supabase_client.table("messages").select("message_id").eq(
                    "conversation_id", conversation_manager.get_current_conversation_id()
                ).eq("role", "user").order("message_id", desc=True).limit(1).execute()
                
                if latest_message_result.data:
                    message_id = latest_message_result.data[0]["message_id"]
                    # Chạy phân tích async (không block response)
                    asyncio.create_task(
                        analytics_service.process_user_message(
                            message_id=message_id,
                            content=request.question,
                            user_id=current_user.id,
                            conversation_id=conversation_manager.get_current_conversation_id()
                        )
                    )
                    print(f"[ANALYTICS] Đã khởi chạy phân tích cho message {message_id}")
            except Exception as e:
                print(f"[ANALYTICS] Lỗi khi khởi chạy phân tích: {str(e)}")
                # Không để lỗi analytics ảnh hưởng đến flow chính

        # Lấy lịch sử hội thoại để sử dụng trong prompt
        conversation_history = conversation_manager.format_for_prompt(
            conversation_manager.get_current_conversation_id()
        )
        print(
            f"Lịch sử hội thoại cho conversation {conversation_manager.get_current_conversation_id()}:"
        )
        print(
            conversation_history[:200] + "..."
            if len(conversation_history) > 200
            else conversation_history
        )

        # Hàm generator để cung cấp dữ liệu cho SSE
        async def generate_response_stream():
            try:
                # Gọi RAG để lấy kết quả dạng stream với file_id
                stream_generator = rag_system.query_with_sources_streaming(
                    request.question,
                    # file_id=search_file_ids,
                    conversation_history=conversation_history,
                )

                # Thu thập toàn bộ nội dung để lưu lịch sử
                full_answer = ""

                # Sử dụng async for để lặp qua stream generator
                async for chunk in stream_generator:
                    # Xử lý chunk tùy theo loại
                    if chunk["type"] == "start":
                        # Truyền thông tin bắt đầu
                        chunk["data"]["question_id"] = question_id
                        chunk["data"][
                            "conversation_id"
                        ] = conversation_manager.get_current_conversation_id()
                        yield f"event: start\ndata: {json.dumps(chunk['data'])}\n\n"

                    elif chunk["type"] == "sources":
                        # Giới hạn số lượng nguồn trả về theo tham số nếu người dùng yêu cầu
                        if (
                            max_sources
                            and chunk["data"]["sources"]
                            and len(chunk["data"]["sources"]) > max_sources
                        ):
                            chunk["data"]["sources"] = chunk["data"]["sources"][
                                :max_sources
                            ]

                        # Thêm question_id và conversation_id vào kết quả
                        chunk["data"]["question_id"] = question_id
                        chunk["data"][
                            "conversation_id"
                        ] = conversation_manager.get_current_conversation_id()

                        # Trả về nguồn dưới dạng SSE
                        yield f"event: sources\ndata: {json.dumps(chunk['data'])}\n\n"

                    elif chunk["type"] == "content":
                        # Trả về từng đoạn nội dung
                        yield f"event: content\ndata: {json.dumps({'content': chunk['data']['content']})}\n\n"

                        # Thu thập toàn bộ nội dung
                        full_answer += chunk["data"]["content"]

                    elif chunk["type"] == "end":
                        # Khi kết thúc, thêm thông tin bổ sung
                        chunk["data"]["question_id"] = question_id
                        chunk["data"][
                            "conversation_id"
                        ] = conversation_manager.get_current_conversation_id()

                        # Thêm câu trả lời của AI vào bộ nhớ hội thoại
                        if full_answer:
                            conversation_manager.add_ai_message(
                                conversation_manager.get_current_conversation_id(),
                                full_answer,
                                user_id=user_id,
                            )

                            # Tạo các câu hỏi liên quan sau khi có kết quả đầy đủ
                            try:
                                related_questions = (
                                    await rag_system.generate_related_questions(
                                        request.question, full_answer
                                    )
                                )
                                # Thêm vào chunk data để trả về cho client
                                chunk["data"]["related_questions"] = related_questions
                            except Exception as e:
                                print(f"Lỗi khi tạo câu hỏi liên quan: {str(e)}")
                                # Mặc định nếu có lỗi
                                chunk["data"]["related_questions"] = [
                                    "Bạn muốn tìm hiểu thêm điều gì về chủ đề này?",
                                    "Bạn có thắc mắc nào khác liên quan đến nội dung này không?",
                                    "Bạn có muốn biết thêm thông tin về ứng dụng thực tế của kiến thức này không?",
                                ]

                            # Lưu vào lịch sử
                            questions_history[question_id] = {
                                "question": request.question,
                                "file_id": search_file_ids,  # Lưu file_id đã tìm kiếm
                                "timestamp": datetime.now().isoformat(),
                                "answer": full_answer,
                                "processing_time": chunk["data"].get(
                                    "processing_time", 0
                                ),
                                "conversation_id": conversation_manager.get_current_conversation_id(),
                                "related_questions": chunk["data"].get(
                                    "related_questions", []
                                ),
                            }

                        # Trả về sự kiện kết thúc
                        yield f"event: end\ndata: {json.dumps(chunk['data'])}\n\n"

            except Exception as e:
                # Trả về lỗi dưới dạng SSE
                error_data = {
                    "error": True,
                    "message": str(e),
                    "question_id": question_id,
                    "conversation_id": conversation_manager.get_current_conversation_id(),
                }
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                print(f"Lỗi khi xử lý stream: {str(e)}")
                import traceback

                print(f"Chi tiết lỗi: {traceback.format_exc()}")

        # Trả về StreamingResponse với định dạng SSE
        return StreamingResponse(
            generate_response_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Vô hiệu hóa buffering cho nginx
            },
        )

    except Exception as e:
        # Trả về lỗi dưới dạng JSON thông thường
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý câu hỏi: {str(e)}")

@app.post(f"{PREFIX}/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    current_user=Depends(get_current_user),
):
    """
    Upload tài liệu và index vào vector database - CHỈ ADMIN

    - **file**: File cần upload (PDF, DOCX, TXT)
    - **category**: Danh mục của tài liệu (tùy chọn)
    """
    # KIỂM TRA QUYỀN ADMIN
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Chỉ admin mới có quyền upload tài liệu"
        )
    
    # KIỂM TRA KÍCH THƯỚC FILE (10MB limit)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File quá lớn. Kích thước tối đa cho phép là 10MB. File của bạn: {file.size / (1024*1024):.2f}MB"
        )
    
    # KIỂM TRA ĐỊNH DẠNG FILE
    allowed_extensions = ['.pdf', '.docx', '.doc', '.txt', '.sql', '.md']
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng file {file_extension} không được hỗ trợ. Chỉ hỗ trợ: {', '.join(allowed_extensions)}"
        )
    
    try:
        # LƯU FILE VÀO THỂ MỤC DATA CHUNG (không phân chia theo user)
        upload_dir = os.getenv("UPLOAD_DIR", "backend/data")
        os.makedirs(upload_dir, exist_ok=True)

        # Lưu file vào thư mục data chung
        file_name = file.filename
        original_file_name = file_name
        file_path = os.path.join(upload_dir, file_name)
        original_file_path = file_path
        
        # CẤU HÌNH VECTOR STORE KHÔNG DÙNG USER_ID
        # Đặt collection_name cho vector store - sử dụng collection chung
        rag_system.vector_store.collection_name = "global_documents"
        # Không set user_id cho vector_store vì giờ dùng chung
        rag_system.vector_store.user_id = None
        
        print(f"[UPLOAD] Admin {current_user.email} đang upload file vào thư mục chung")

        with open(file_path, "wb+") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"[UPLOAD] Đã lưu file {file_name} vào {file_path}")

        # Xác định loại file
        file_extension = os.path.splitext(file_name)[1].lower()
        original_file_extension = file_extension
        file_type = None
        
        # Đọc nội dung file và xử lý
        documents = None
        try:
            document_processor = rag_system.document_processor
            documents = document_processor.load_document_with_category(file_path, category)
            
            # Lấy đường dẫn file sau khi chuyển đổi (nếu có)
            converted_file_path = document_processor.get_converted_path(file_path)
            if converted_file_path and converted_file_path != file_path:
                file_path = converted_file_path
                file_extension = os.path.splitext(file_path)[1].lower()
            
            if original_file_extension == ".pdf":
                file_type = "pdf"
            elif original_file_extension == ".docx":
                file_type = "docx"
            elif original_file_extension == ".txt":
                file_type = "txt"
            elif original_file_extension == ".sql":
                file_type = "sql"
            elif original_file_extension == ".md":
                file_type = "md"
            else:
                return {
                    "filename": file.filename,
                    "status": "error",
                    "message": f"Không hỗ trợ định dạng file {original_file_extension}",
                }
        except Exception as e:
            print(f"[UPLOAD] Lỗi khi đọc file {file_name}: {str(e)}")
            return {
                "filename": file.filename,
                "status": "error",
                "message": f"Lỗi khi đọc file: {str(e)}",
            }

        if not documents:
            return {
                "filename": file.filename,
                "status": "error",
                "message": "Không thể tải tài liệu hoặc tài liệu rỗng",
            }

        # Sử dụng phương pháp chunking thông thường
        processed_chunks = rag_system.document_processor.process_documents(documents)

        # Index lên vector store KHÔNG DÙNG USER_ID
        if processed_chunks:
            # Tạo embeddings cho các chunks
            texts = [chunk["text"] for chunk in processed_chunks]
            embeddings = await rag_system.embedding_model.encode(texts)

            # Đảm bảo collection đã tồn tại với kích thước vector đúng
            await rag_system.vector_store.ensure_collection_exists(len(embeddings[0]))

            # Index embeddings KHÔNG DÙNG USER_ID - file sẽ được chia sẻ cho tất cả user
            print(f"[UPLOAD] Đang index {len(processed_chunks)} chunks vào collection chung global_documents")
            file_id = str(uuid.uuid4())
            
            # Gọi index_documents với user_id=None để lưu vào collection chung
            await rag_system.vector_store.index_documents(
                processed_chunks,
                embeddings,
                user_id=None,  # Không dùng user_id
                file_id=file_id,
            )
            
            # LƯU THÔNG TIN FILE VÀO DATABASE VỚI USER_ID CỦA ADMIN
            try:
                from backend.supabase.files_manager import FilesManager
                from backend.supabase.client import SupabaseClient
                
                # Lấy kích thước file gốc
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                if file_size == 0 and os.path.exists(original_file_path):
                    file_size = os.path.getsize(original_file_path)
                
                # Tạo metadata - ghi nhận ai upload
                metadata = {
                    "category": category,
                    "file_size": file_size,
                    "chunks_count": len(processed_chunks),
                    "is_indexed": True,
                    "last_indexed": datetime.now().isoformat(),
                    "original_file_name": original_file_name,
                    "original_extension": original_file_extension,
                    "converted_to_pdf": original_file_extension != ".pdf" and file_extension == ".pdf",
                    "uploaded_by_admin": current_user.email,  # Ghi nhận admin upload
                    "uploaded_by_admin_id": current_user.id,
                    "is_shared_resource": True  # Đánh dấu là tài nguyên chia sẻ
                }
                
                # Sử dụng client với service role để bypass RLS
                supabase_client_with_service_role = SupabaseClient(use_service_key=True)
                client = supabase_client_with_service_role.get_client()
                files_manager = FilesManager(client)
                
                # Lưu metadata vào Supabase với user_id của admin
                save_result = files_manager.save_file_metadata(
                    file_id=file_id,
                    filename=original_file_name,
                    file_path=file_path,
                    user_id=current_user.id,  # Lưu ID admin upload
                    file_type=file_type,
                    metadata=metadata
                )
                
                print(f"[UPLOAD] Đã lưu thông tin file vào Supabase với file_id={file_id}")
            except Exception as e:
                print(f"[UPLOAD] Lỗi khi lưu thông tin file vào Supabase: {str(e)}")
                # Không dừng quá trình nếu lưu vào Supabase thất bại

        return {
            "filename": original_file_name,
            "status": "success",
            "message": f"Admin đã tải lên và index thành công {len(processed_chunks)} chunks từ tài liệu vào hệ thống chung",
            "chunks_count": len(processed_chunks),
            "category": category,
            "file_id": file_id,
            "shared_resource": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý tài liệu: {str(e)}")


@app.delete(f"{PREFIX}/collection/reset")
async def reset_collection():
    """
    Xóa toàn bộ dữ liệu đã index trong collection
    """
    try:
        # Lấy thông tin collection
        collection_info = rag_system.vector_store.get_collection_info()
        if not collection_info:
            return {
                "status": "warning",
                "message": f"Collection {rag_system.vector_store.collection_name} không tồn tại",
            }

        # Xóa collection cũ
        rag_system.vector_store.delete_collection()

        # Lấy kích thước vector từ mô hình embedding
        # Tạo một vector mẫu để xác định kích thước
        sample_embedding = await rag_system.embedding_model.encode(["Sample text"])
        vector_size = len(sample_embedding[0])

        # Tạo lại collection mới
        await rag_system.vector_store.ensure_collection_exists(vector_size)

        return {
            "status": "success",
            "message": f"Đã xóa và tạo lại collection {rag_system.vector_store.collection_name}",
            "vector_size": vector_size,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi reset collection: {str(e)}"
        )


# Thêm API endpoint lấy danh sách file đã upload
@app.get(f"{PREFIX}/files", response_model=FileListResponse)
async def get_uploaded_files(current_user=Depends(get_current_user)):
    """
    Lấy danh sách các file đã upload trong hệ thống chung (do admin upload)

    Returns:
        Danh sách các file đã upload trong hệ thống chung
    """
    try:
        files = []

        # Lấy danh sách file từ database
        try:
            from backend.supabase.files_manager import FilesManager
            from backend.supabase.client import SupabaseClient

            # Sử dụng client với service role để bypass RLS
            supabase_client_with_service_role = SupabaseClient(use_service_key=True)
            client = supabase_client_with_service_role.get_client()
            files_manager = FilesManager(client)

            # Lấy tất cả file từ database (do admin upload)
            db_files = files_manager.get_all_files(include_deleted=False)
            print(f"[FILES] Tìm thấy {len(db_files)} file trong hệ thống chung")
        except Exception as e:
            print(f"[FILES] Lỗi khi lấy danh sách file từ database: {str(e)}")
            db_files = []

        if db_files:
            for file_record in db_files:
                # Convert từ dữ liệu database sang model FileInfo
                file_path = file_record.get("file_path", "")
                filename = file_record.get("filename", "")
                
                # Lấy metadata
                metadata = file_record.get("metadata", {}) or {}
                
                # Ưu tiên sử dụng tên file gốc từ metadata nếu có
                original_file_name = metadata.get("original_file_name", filename)
                # Sử dụng phần mở rộng gốc nếu có
                original_extension = metadata.get("original_extension", "")
                if original_extension:
                    extension = original_extension
                else:
                    extension = os.path.splitext(filename)[1].lower() if filename else ""
                
                upload_time = file_record.get("upload_time", "")
                category = metadata.get("category", None)
                # Lấy kích thước file từ metadata hoặc mặc định là 0
                file_size = metadata.get("file_size", 0)
                
                # Lấy thông tin admin upload
                uploaded_by_admin = metadata.get("uploaded_by_admin", "Unknown Admin")
                is_shared_resource = metadata.get("is_shared_resource", False)

                files.append(
                    FileInfo(
                        filename=original_file_name,  # Sử dụng tên file gốc
                        path=file_path,
                        size=file_size,
                        upload_date=upload_time,
                        extension=extension,
                        category=category,
                        id=file_record.get("file_id"),
                    )
                )
        else:
            # Không có dữ liệu trong database, trả về danh sách rỗng thay vì đọc từ filesystem
            print(f"[FILES] Không tìm thấy dữ liệu trong database, trả về danh sách rỗng")
            files = []

        # Sắp xếp theo thời gian tạo mới nhất
        files.sort(key=lambda x: x.upload_date, reverse=True)

        return {"total_files": len(files), "files": files}
    except Exception as e:
        print(f"[FILES] Lỗi khi lấy danh sách file: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi lấy danh sách file: {str(e)}"
        )


@app.delete(f"{PREFIX}/files/{{filename}}", response_model=FileDeleteResponse)
async def delete_file(filename: str, current_user=Depends(get_current_user)):
    """
    Xóa file đã upload và các index liên quan trong vector store - CHỈ ADMIN
    """
    # KIỂM TRA QUYỀN ADMIN
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Chỉ admin mới có quyền xóa file"
        )
        
    try:
        # LẤY THÔNG TIN FILE TỪ DATABASE TRƯỚC
        from backend.supabase.files_manager import FilesManager
        from backend.supabase.client import SupabaseClient
        
        supabase_client_with_service_role = SupabaseClient(use_service_key=True)
        client = supabase_client_with_service_role.get_client()
        files_manager = FilesManager(client)
        
        # Tìm file trong database theo tên
        db_files = files_manager.get_file_by_name_for_admin(filename)
        
        if not db_files:
            raise HTTPException(
                status_code=404, 
                detail=f"Không tìm thấy file {filename} trong hệ thống"
            )
        
        # Lấy file đầu tiên (nếu có nhiều file cùng tên)
        file_record = db_files[0]
        file_id = file_record.get("file_id")
        file_path = file_record.get("file_path")
        
        print(f"[DELETE] Admin {current_user.email} đang xóa file: {filename}")
        print(f"[DELETE] File path từ database: {file_path}")
        print(f"[DELETE] File ID: {file_id}")

        # XÁC ĐỊNH ĐƯỜNG DẪN FILE THỰC TẾ
        upload_dir = os.getenv("UPLOAD_DIR", "backend/data")
        
        # Thử các đường dẫn có thể có
        possible_paths = [
            file_path,  # Đường dẫn từ database
            os.path.join(upload_dir, filename),  # Đường dẫn mới (data chung)
            os.path.join(upload_dir, os.path.basename(file_path)) if file_path else None,  # Chỉ tên file trong thư mục data
        ]
        
        # Loại bỏ các đường dẫn None
        possible_paths = [p for p in possible_paths if p is not None]
        
        actual_file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                actual_file_path = path
                print(f"[DELETE] Tìm thấy file tại: {actual_file_path}")
                break
        
        if not actual_file_path:
            print(f"[DELETE] Cảnh báo: Không tìm thấy file vật lý, tiếp tục xóa dữ liệu trong database và vector store")

        print(f"[DELETE] Đang xóa các điểm dữ liệu liên quan đến file: {filename}")

        # CẤU HÌNH VECTOR STORE ĐỂ XÓA TỪ COLLECTION CHUNG
        original_collection = rag_system.vector_store.collection_name
        rag_system.vector_store.collection_name = "global_documents"
        rag_system.vector_store.user_id = None  # Không dùng user_id
        print(f"[DELETE] Sử dụng collection: {rag_system.vector_store.collection_name}")

        # XÓA TỪ VECTOR STORE THEO FILE_ID
        deleted_points_count = 0
        deletion_success = False

        if file_id:
            try:
                print(f"[DELETE] Thử xóa theo file_id: {file_id}")
                success, message = rag_system.vector_store.delete_by_file_id(file_id)
                
                if success:
                    import re
                    match = re.search(r"Đã xóa (\d+) điểm", message)
                    if match:
                        deleted_points_count = int(match.group(1))
                    print(f"[DELETE] Xóa thành công theo file_id: {message}")
                    deletion_success = True
            except Exception as e:
                print(f"[DELETE] Lỗi khi xóa theo file_id: {str(e)}")

        # NẾU XÓA THEO FILE_ID THẤT BẠI, THỬ XÓA THEO ĐƯỜNG DẪN
        if not deletion_success and actual_file_path:
            try:
                print(f"[DELETE] Thử xóa theo đường dẫn file: {actual_file_path}")
                success, message = rag_system.vector_store.delete_by_file_path(actual_file_path)
                
                if success:
                    import re
                    match = re.search(r"Đã xóa (\d+) điểm", message)
                    if match:
                        deleted_points_count = int(match.group(1))
                    print(f"[DELETE] Xóa thành công theo đường dẫn: {message}")
                    deletion_success = True
            except Exception as e:
                print(f"[DELETE] Lỗi khi xóa theo đường dẫn: {str(e)}")

        # XÓA FILE VẬT LÝ
        if actual_file_path and os.path.exists(actual_file_path):
            try:
                os.remove(actual_file_path)
                print(f"[DELETE] Đã xóa file vật lý: {actual_file_path}")
            except Exception as e:
                print(f"[DELETE] Lỗi khi xóa file vật lý: {str(e)}")

        # XÓA VĨNH VIỄN FILE TRONG DATABASE (HARD DELETE)
        try:
            if file_id:
                files_manager.delete_file_permanently(file_id)
                print(f"[DELETE] Đã xóa vĩnh viễn file {filename} khỏi database")
        except Exception as e:
            print(f"[DELETE] Lỗi khi xóa file khỏi database: {str(e)}")

        # Khôi phục collection_name gốc
        rag_system.vector_store.collection_name = original_collection

        return {
            "filename": filename,
            "status": "success",
            "message": f"Admin đã xóa thành công file {filename} khỏi hệ thống chung",
            "removed_points": deleted_points_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[DELETE] Lỗi không mong muốn: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa file: {str(e)}")

@app.post(f"{PREFIX}/collections/delete-by-filter")
async def delete_points_by_filter(filter_request: Dict):
    """
    Xóa các điểm trong collection theo filter

    Filter format:
    {
      "filter": {
        "must": [
          {
            "key": "source",
            "match": {
              "value": "tên_file.pdf"
            }
          },
          {
            "key": "user_id",
            "match": {
              "value": "default_user"
            }
          }
        ]
      }
    }
    """
    try:
        print(f"[DELETE-FILTER] Bắt đầu xóa điểm theo filter: {filter_request}")

        # Ghi log filter chi tiết
        if "filter" in filter_request and "must" in filter_request["filter"]:
            for condition in filter_request["filter"]["must"]:
                if "key" in condition and "match" in condition:
                    print(
                        f"[DELETE-FILTER] Điều kiện: key={condition['key']}, value={condition['match'].get('value', 'N/A')}"
                    )

        # Kiểm tra collection tồn tại
        collection_exists = rag_system.vector_store.client.collection_exists(
            rag_system.vector_store.collection_name
        )
        print(
            f"[DELETE-FILTER] Collection {rag_system.vector_store.collection_name} tồn tại: {collection_exists}"
        )

        # Lấy thông tin collection trước khi xóa
        if collection_exists:
            collection_info = rag_system.vector_store.get_collection_info()
            print(
                f"[DELETE-FILTER] Thông tin collection trước khi xóa: points_count={collection_info.get('points_count', 'N/A')}"
            )

        success, message = rag_system.vector_store.delete_points_by_filter(
            filter_request
        )
        print(f"[DELETE-FILTER] Kết quả xóa: success={success}, message={message}")

        # Lấy thông tin collection sau khi xóa
        if collection_exists:
            collection_info = rag_system.vector_store.get_collection_info()
            print(
                f"[DELETE-FILTER] Thông tin collection sau khi xóa: points_count={collection_info.get('points_count', 'N/A')}"
            )

        if success:
            return {"status": "success", "message": message}
        else:
            print(f"[DELETE-FILTER] Lỗi khi xóa: {message}")
            return JSONResponse(
                status_code=400, content={"status": "error", "message": message}
            )

    except Exception as e:
        print(f"[DELETE-FILTER] Exception: {str(e)}")
        import traceback

        traceback_str = traceback.format_exc()
        print(f"[DELETE-FILTER] Traceback: {traceback_str}")

        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi khi xóa điểm: {str(e)}"},
        )


# Đã xóa hàm get_all_conversations trùng lặp - sử dụng get_user_conversations thay thế


@app.get(f"{PREFIX}/conversations/{{conversation_id}}")
async def get_conversation_detail(
    conversation_id: str = Path(..., description="ID phiên hội thoại cần lấy chi tiết"),
    current_user=Depends(get_current_user),
):
    """
    Lấy chi tiết hội thoại cho một phiên cụ thể

    - **conversation_id**: ID phiên hội thoại cần lấy chi tiết
    """
    # Kiểm tra nếu conversation_id là "search", đây là path conflict với API tìm kiếm
    if conversation_id == "search":
        raise HTTPException(
            status_code=400, 
            detail="Không thể sử dụng 'search' làm ID hội thoại vì đây là endpoint dành riêng"
        )
        
    try:
        user_id = current_user.id

        # Lấy tin nhắn từ Supabase
        messages = conversation_manager.get_messages(conversation_id)
        conversation_manager.set_current_conversation_id(conversation_id)
        if not messages:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": f"Không tìm thấy hội thoại với ID {conversation_id}",
                    "conversation_id": conversation_id,
                },
            )

        # Tạo dữ liệu trả về
        conversation_data = {
            "conversation_id": conversation_id,
            "last_updated": format_vietnam_time_iso(),
            "messages": messages,
        }

        return {
            "status": "success",
            "message": f"Đã tìm thấy chi tiết hội thoại cho phiên {conversation_id}",
            "data": conversation_data,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi lấy chi tiết hội thoại: {str(e)}"
        )


# API xác thực (authentication)
@app.post(f"{PREFIX}/auth/signup", response_model=AuthResponse)
async def signup(request: UserSignUpRequest):
    """
    Đăng ký tài khoản mới với email và mật khẩu

    - **email**: Email đăng ký tài khoản
    - **password**: Mật khẩu đăng ký tài khoản
    """
    if not supabase_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ xác thực chưa được cấu hình",
        )

    try:
        print(f"Đang đăng ký tài khoản cho email: {request.email}")
        result = supabase_client.auth.sign_up(
            {"email": request.email, "password": request.password}
        )

        if not result.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Đăng ký thất bại, vui lòng thử lại",
            )

        user_id = result.user.id
        user_email = result.user.email

        # Đảm bảo user có role trong bảng user_roles
        try:
            # Kiểm tra xem user đã có role chưa
            role_check = supabase_client.table("user_roles").select("role").eq("user_id", user_id).execute()
            
            if not role_check.data or len(role_check.data) == 0:
                # Nếu chưa có role, thêm role mặc định "student"
                print(f"Thêm role mặc định 'student' cho user {user_email}")
                
                # Sử dụng service key để có quyền insert vào user_roles
                from backend.supabase.client import SupabaseClient
                service_client = SupabaseClient(use_service_key=True).get_client()
                
                service_client.table("user_roles").insert({
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "role": "student",
                    "created_at": "now()",
                    "updated_at": "now()"
                }).execute()
                
                print(f"✅ Đã thêm role 'student' cho user {user_email}")
            else:
                print(f"User {user_email} đã có role: {role_check.data[0]['role']}")
                
        except Exception as role_error:
            print(f"⚠️ Không thể thêm role cho user {user_email}: {str(role_error)}")
            # Không raise exception để không cản trở việc đăng ký

        # Chuyển đổi created_at từ datetime sang string nếu cần
        created_at = result.user.created_at
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()

        # Trả về thông tin người dùng và token
        return {
            "user": {
                "id": result.user.id,
                "email": result.user.email,
                "created_at": created_at,
                "name": result.user.user_metadata.get("name", result.user.email),
                "avatar_url": result.user.user_metadata.get("avatar_url", None),
                "role": "student",  # Luôn trả về "student" cho user mới đăng ký
            },
            "access_token": result.session.access_token if result.session else "",
            "expires_in": result.session.expires_in if result.session else None,
        }
    except Exception as e:
        error_message = str(e)
        
        # Xử lý các trường hợp lỗi cụ thể
        if "User already registered" in error_message or "already registered" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email này đã được đăng ký. Vui lòng sử dụng email khác hoặc đăng nhập.",
            )
        elif "Invalid email" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email không hợp lệ. Vui lòng kiểm tra lại.",
            )
        elif "Password should be at least" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mật khẩu quá yếu. Mật khẩu phải có ít nhất 6 ký tự.",
            )
        elif "signup is disabled" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Đăng ký tài khoản đã bị tắt. Vui lòng liên hệ quản trị viên.",
            )
        else:
            # Trả về lỗi chung cho các trường hợp không xác định
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lỗi khi đăng ký tài khoản: {error_message}",
            )


@app.post(f"{PREFIX}/auth/login", response_model=AuthResponse)
async def login(request: UserLoginRequest, response: Response):
    """
    Đăng nhập người dùng
    """
    try:
        # Đăng nhập với Supabase
        try:
            auth_response = supabase_client.auth.sign_in_with_password({
                "email": request.email,
                "password": request.password,
            })
        except Exception as auth_error:
            # Xử lý lỗi timeout
            if "timeout" in str(auth_error).lower() or "timed out" in str(auth_error).lower():
                print(f"Lỗi timeout khi kết nối đến Supabase: {str(auth_error)}")
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="Kết nối đến máy chủ xác thực bị timeout. Vui lòng thử lại sau."
                )
            # Xử lý các lỗi khác
            print(f"Lỗi khi đăng nhập: {str(auth_error)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Không thể đăng nhập. Vui lòng kiểm tra lại thông tin đăng nhập."
            )
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email hoặc mật khẩu không chính xác",
            )
        
        # Lấy thông tin người dùng từ Supabase
        user_data = auth_response.user
        
        # Kiểm tra và lấy vai trò của người dùng
        try:
            user_id = user_data.id
            role_data = supabase_client.table("user_roles").select("role").eq("user_id", user_id).execute()
            
            # Mặc định vai trò là student
            user_role = "student"
            
            # Nếu có dữ liệu về vai trò, cập nhật vai trò
            if role_data.data and len(role_data.data) > 0:
                user_role = role_data.data[0].get("role", "student")
            
            print(f"Người dùng {user_data.email} đăng nhập với vai trò: {user_role}")
        except Exception as e:
            print(f"Lỗi khi lấy vai trò người dùng: {str(e)}")
            user_role = "student"
        
        # Chuyển đổi created_at từ datetime sang string
        created_at = user_data.created_at
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        
        # Tạo đối tượng UserResponse
        user_response = UserResponse(
            id=user_data.id,
            email=user_data.email,
            created_at=created_at,  # Đã chuyển đổi sang string
            name=user_data.user_metadata.get("name") if user_data.user_metadata else None,
            avatar_url=user_data.user_metadata.get("avatar_url") if user_data.user_metadata else None,
            role=user_role
        )
        
        # Debug: In ra response để kiểm tra
        print(f"Login response: {user_response.model_dump()}")
        
        # Tạo response
        auth_response_data = AuthResponse(
            user=user_response,
            access_token=auth_response.session.access_token,
            token_type="bearer",
            expires_in=3600,  # 1 giờ
        )
        
        # Debug: In ra auth_response_data để kiểm tra
        print(f"Auth response data: {auth_response_data.model_dump()}")
        
        return auth_response_data
    except HTTPException:
        raise
    except Exception as e:
        print(f"Lỗi khi đăng nhập: {str(e)}")
        error_message = "Lỗi khi đăng nhập"
        
        # Xác định loại lỗi để trả về thông báo phù hợp
        if "Invalid login credentials" in str(e):
            error_message = "Email hoặc mật khẩu không chính xác"
            error_status = status.HTTP_401_UNAUTHORIZED
        elif "Email not confirmed" in str(e):
            error_message = "Email chưa được xác nhận. Vui lòng kiểm tra hộp thư để xác nhận email"
            error_status = status.HTTP_401_UNAUTHORIZED
        elif "User not found" in str(e):
            error_message = "Không tìm thấy tài khoản với email này"
            error_status = status.HTTP_401_UNAUTHORIZED
        elif "Invalid email" in str(e):
            error_message = "Email không hợp lệ"
            error_status = status.HTTP_400_BAD_REQUEST
        elif "rate limit" in str(e).lower():
            error_message = "Quá nhiều lần đăng nhập thất bại. Vui lòng thử lại sau"
            error_status = status.HTTP_429_TOO_MANY_REQUESTS
        elif "timeout" in str(e).lower() or "timed out" in str(e).lower():
            error_message = "Kết nối đến máy chủ xác thực bị timeout. Vui lòng thử lại sau."
            error_status = status.HTTP_504_GATEWAY_TIMEOUT
        else:
            # Trả về lỗi chi tiết từ Supabase nếu không khớp với các trường hợp trên
            error_message = f"Lỗi đăng nhập: {str(e)}"
            error_status = status.HTTP_400_BAD_REQUEST
    raise HTTPException(
            status_code=error_status,
            detail=error_message,
            )


@app.post(f"{PREFIX}/auth/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(auth_bearer),
):
    """
    Đăng xuất khỏi hệ thống, vô hiệu hóa token hiện tại
    """
    if not supabase_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ xác thực chưa được cấu hình",
        )

    if not credentials:
        return {"message": "Đã đăng xuất"}

    try:
        # Đăng xuất khỏi phiên hiện tại
        supabase_client.auth.sign_out()
        return {"message": "Đăng xuất thành công"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lỗi khi đăng xuất: {str(e)}",
        )

@app.post(f"{PREFIX}/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Gửi yêu cầu đặt lại mật khẩu đến email của người dùng
    
    - **email**: Email của người dùng cần đặt lại mật khẩu
    - **redirect_to**: URL chuyển hướng sau khi nhấp vào liên kết trong email
    """
    if not supabase_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ xác thực chưa được cấu hình",
        )

    try:
        print(f"Đang gửi yêu cầu đặt lại mật khẩu cho email: {request.email}")
        print(f"URL chuyển hướng: {request.redirect_to}")
        
        # Chuẩn bị options
        options = {}
        if request.redirect_to:
            options["redirect_to"] = request.redirect_to
            print(f"Đã thiết lập redirect_to: {options['redirect_to']}")
        
        # Gọi API Supabase để gửi email đặt lại mật khẩu
        supabase_client.auth.reset_password_for_email(request.email, options)
        
        return {
            "status": "success",
            "message": "Yêu cầu đặt lại mật khẩu đã được gửi đến email của bạn."
        }
    except Exception as e:
        print(f"Lỗi khi gửi yêu cầu đặt lại mật khẩu: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi gửi yêu cầu đặt lại mật khẩu: {str(e)}"
        )


@app.post(f"{PREFIX}/auth/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
):
    """
    Đặt lại mật khẩu với token xác thực
    - **password**: Mật khẩu mới
    - **access_token**: Token xác thực nhận được từ email
    """
    if not supabase_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ xác thực chưa được cấu hình",
        )
    
    try:
        print(f"Đang đặt lại mật khẩu cho người dùng")
        
        # Cập nhật mật khẩu mới
        try:
            import httpx
            import json
            from urllib.parse import urljoin
            
            # Sử dụng phương pháp gọi API trực tiếp đến Supabase Auth API
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                raise ValueError("Thiếu cấu hình Supabase URL hoặc Key")
                
            # Tạo URL endpoint cho API đặt lại mật khẩu
            auth_endpoint = urljoin(supabase_url, "auth/v1/user")
            
            # Tạo headers với token
            headers = {
                "apikey": supabase_key,
                "Authorization": f"Bearer {request.access_token}",
                "Content-Type": "application/json"
            }
            
            # Tạo payload cho request
            payload = {
                "password": request.password
            }
            
            # Gửi request đến Supabase Auth API
            print(f"Gửi request PUT đến {auth_endpoint} để cập nhật mật khẩu")
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    auth_endpoint,
                    headers=headers,
                    json=payload
                )
                
                # Kiểm tra kết quả
                if response.status_code >= 200 and response.status_code < 300:
                    print(f"Cập nhật mật khẩu thành công với status code: {response.status_code}")
                    response_data = response.json()
                    return {
                        "status": "success",
                        "message": "Mật khẩu đã được đặt lại thành công"
                    }
                else:
                    print(f"Lỗi khi cập nhật mật khẩu. Status code: {response.status_code}, Response: {response.text}")
                    # Xử lý lỗi trả về từ Supabase
                    try:
                        error_json = response.json()
                        error_code = error_json.get("error_code") or error_json.get("code")
                        error_msg = error_json.get("msg") or error_json.get("message") or str(error_json)
                    except Exception:
                        error_code = None
                        error_msg = response.text
                    
                    # Xử lý từng trường hợp lỗi cụ thể
                    if error_code == "same_password":
                        raise HTTPException(
                            status_code=422,
                            detail="Mật khẩu mới phải khác mật khẩu cũ."
                        )
                    elif error_code == "password_too_weak":
                        raise HTTPException(
                            status_code=422,
                            detail="Mật khẩu mới quá yếu. Vui lòng chọn mật khẩu mạnh hơn."
                        )
                    elif error_code == "invalid_token" or "invalid JWT" in error_msg or "JWT expired" in error_msg:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token không hợp lệ hoặc đã hết hạn",
                            headers={"WWW-Authenticate": "Bearer"},
                        )
                    else:
                        # Trả về thông báo lỗi gốc nếu không xác định được mã lỗi
                        raise HTTPException(
                            status_code=400,
                            detail=error_msg
                        )
        except HTTPException:
            raise
        except Exception as e:
            print(f"Lỗi khi cập nhật mật khẩu: {str(e)}")
            if "invalid JWT" in str(e) or "JWT expired" in str(e) or "session" in str(e).lower() or "invalid token" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token không hợp lệ hoặc đã hết hạn",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Lỗi khi cập nhật mật khẩu: {str(e)}"
                )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Lỗi không xác định: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi đặt lại mật khẩu: {str(e)}",
        )

@app.get(f"{PREFIX}/auth/user", response_model=UserResponse)
async def get_user(current_user=Depends(get_current_user)):
    """
    Lấy thông tin người dùng hiện tại
    """
    # Chuyển đổi created_at từ datetime sang string nếu cần
    created_at = current_user.created_at
    if hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()

    return {
        "id": current_user.id,
        "email": current_user.email,
        "created_at": created_at,
        "name": current_user.user_metadata.get("name", current_user.email),
        "avatar_url": current_user.user_metadata.get("avatar_url", None),
        "role": getattr(current_user, "role", "student"),  # Sử dụng getattr để lấy an toàn
    }


@app.get(f"{PREFIX}/auth/session")
async def session_info(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_bearer),
):
    """
    Kiểm tra thông tin phiên hiện tại
    """
    if not supabase_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ xác thực chưa được cấu hình",
        )

    if not credentials:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "is_authenticated": False,
                "message": "Không có thông tin xác thực",
            },
        )

    try:
        # Kiểm tra phiên
        session = supabase_client.auth.get_user()

        if not session or not session.user:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "is_authenticated": False,
                    "message": "Phiên không hợp lệ hoặc đã hết hạn",
                },
            )

        # Chuyển đổi created_at từ datetime sang string nếu cần
        created_at = session.user.created_at
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()

        # Trả về thông tin người dùng đơn giản
        return {
            "is_authenticated": True,
            "user_id": session.user.id,
            "email": session.user.email,
            "created_at": created_at,
            "name": session.user.user_metadata.get("name", session.user.email),
            "avatar_url": session.user.user_metadata.get("avatar_url", None),
            "role": getattr(session.user, "role", "student"),  # Sử dụng getattr để lấy an toàn
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"is_authenticated": False, "message": f"Lỗi: {str(e)}"},
        )


@app.post(f"{PREFIX}/auth/google")
async def login_with_google(request: GoogleAuthRequest):
    """
    Đăng nhập/đăng ký với Google OAuth

    - **code**: Authorization code nhận được từ Google OAuth (nếu có)
    - **access_token**: Access token Google đã cấp (nếu có)
    - **provider**: OAuth provider (mặc định là google)
    """
    if not supabase_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ xác thực chưa được cấu hình",
        )

    try:
        log_prefix = f"[GoogleAuth] Code: {bool(request.code)}, Token: {bool(request.access_token)}"
        print(f"{log_prefix} - Bắt đầu xử lý")

        # Xử lý dựa trên thông tin đăng nhập được cung cấp
        if request.code:
            print(f"{log_prefix} - Sử dụng authorization code")
            try:
                # Sửa: Truyền code dưới dạng dictionary với khóa "auth_code"
                auth_response = supabase_client.auth.exchange_code_for_session(
                    {"auth_code": request.code}
                )
            except Exception as e:
                print(
                    f"{log_prefix} - Lỗi exchange_code_for_session trực tiếp: {str(e)}"
                )
                # Thử phương pháp khác nếu cần
                try:
                    # Phương pháp dự phòng nếu cần
                    auth_response = supabase_client.auth.exchange_code_for_session(
                        {"auth_code": request.code}
                    )
                except Exception as e2:
                    print(f"{log_prefix} - Lỗi phương pháp dự phòng: {str(e2)}")
                    raise ValueError(
                        f"Không thể xác thực với code: {str(e)}, {str(e2)}"
                    )
            session = auth_response.session
        elif request.access_token:
            print(f"{log_prefix} - Sử dụng access token")
            auth_response = supabase_client.auth.sign_in_with_idp(
                {
                    "provider": request.provider,
                    "access_token": request.access_token,
                }
            )
            session = auth_response.session
        else:
            raise ValueError("Thiếu thông tin xác thực")

        if not session:
            raise ValueError("Không thể tạo phiên đăng nhập")

        # Lấy user data từ session
        user = session.user
        print(f"{log_prefix} - Đăng nhập thành công cho user: {user.email}")

        # Trả về thông tin người dùng, token và các thông tin khác
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.user_metadata.get("name", user.email),
                "avatar_url": user.user_metadata.get("avatar_url", None),
                "role": user.user_metadata.get("role", "student"),
            },
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "provider": request.provider,
        }
    except ValueError as e:
        print(f"Lỗi xác thực Google: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Lỗi không xác định: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Lỗi xác thực: {str(e)}"
        )


@app.get(f"{PREFIX}/auth/google/url")
async def google_sign_in_url(
    redirect_url: str = Query(
        None, description="URL chuyển hướng sau khi đăng nhập Google"
    )
):
    """Lấy URL để chuyển hướng đến trang đăng nhập Google"""
    if not supabase_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ xác thực chưa được cấu hình",
        )

    if not redirect_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu redirect_url"
        )

    try:
        print(f"Lấy URL đăng nhập Google với redirect URL: {redirect_url}")

        # Thử sử dụng các phương thức Supabase để lấy URL xác thực
        try:
            # Cách 1: Sử dụng sign_in_with_oauth
            auth_data = supabase_client.auth.sign_in_with_oauth(
                {
                    "provider": "google",
                    "options": {"redirect_to": redirect_url, "scopes": "email profile"},
                }
            )
            auth_url = auth_data.url
        except Exception as e:
            print(f"Lỗi sign_in_with_oauth: {str(e)}")

            # Cách 2: Sử dụng get_sign_in_with_oauth
            auth_url = supabase_client.auth.get_sign_in_with_oauth(
                {
                    "provider": "google",
                    "options": {"redirect_to": redirect_url, "scopes": "email profile"},
                }
            ).url

        if not auth_url:
            raise ValueError("Không thể lấy URL xác thực")

        return {"url": auth_url}
    except Exception as e:
        print(f"Lỗi lấy Google auth URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Lỗi: {str(e)}"
        )


@app.get(f"{PREFIX}/auth/callback")
async def auth_callback(
    code: str = Query(
        None, description="Authorization code được trả về từ OAuth provider"
    ),
    error: str = Query(None, description="Error trả về từ OAuth provider nếu có lỗi"),
    provider: str = Query("google", description="OAuth provider (mặc định là google)"),
):
    """
    Xử lý callback từ OAuth provider

    - **code**: Authorization code từ OAuth provider
    - **error**: Lỗi từ OAuth provider nếu có
    - **provider**: OAuth provider (mặc định là google)
    """
    if not supabase_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ xác thực chưa được cấu hình",
        )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lỗi xác thực OAuth: {error}",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thiếu authorization code",
        )

    try:
        print(f"Nhận code từ {provider}: {code[:10]}...")

        # Sử dụng code để xác thực với provider
        auth_result = supabase_client.auth.exchange_code_for_session(
            {"auth_code": code}
        )

        # Lấy phiên và token
        session = auth_result.session
        access_token = session.access_token
        refresh_token = session.refresh_token

        # Lấy thông tin người dùng
        user = session.user

        # Trả về thông tin người dùng và token
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.user_metadata.get("name", user.email),
                "avatar_url": user.user_metadata.get("avatar_url", None),
                "role": user.user_metadata.get("role", "student"),
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "provider": provider,
        }
    except Exception as e:
        print(f"Lỗi xử lý OAuth callback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lỗi xác thực OAuth: {str(e)}",
        )


@app.post(f"{PREFIX}/conversations/create", response_model=CreateConversationResponse)
async def create_conversation(current_user=Depends(get_current_user)):
    """
    Tạo một cuộc hội thoại mới

    Returns:
        CreateConversationResponse: Thông tin về cuộc hội thoại mới được tạo
    """
    try:
        user_id = current_user.id
        # Tạo conversation mới trong database
        current_conversation_id = conversation_manager.create_conversation(user_id)
        if not current_conversation_id:
            raise HTTPException(status_code=500, detail="Không thể tạo hội thoại mới")
        conversation_manager.set_current_conversation_id(current_conversation_id)
        return {
            "status": "success",
            "message": "Đã tạo hội thoại mới thành công",
            "conversation_id": current_conversation_id,
        }
    except Exception as e:
        print(f"Lỗi khi tạo hội thoại mới: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi tạo hội thoại mới: {str(e)}"
        )


@app.get(f"{PREFIX}/conversations")
async def get_user_conversations(
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    page_size: int = Query(10, ge=1, le=50, description="Số lượng hội thoại mỗi trang"),
    current_user=Depends(get_current_user),
):
    """
    Lấy danh sách tất cả cuộc hội thoại của người dùng hiện tại (Tối ưu với JOIN query)

    Args:
        page: Trang hiện tại (bắt đầu từ 1)
        page_size: Số lượng hội thoại mỗi trang
        current_user: Thông tin người dùng hiện tại

    Returns:
        Dict: Danh sách hội thoại và thông tin phân trang
    """
    try:
        user_id = current_user.id

        # Tính offset cho phân trang
        offset = (page - 1) * page_size

        # Tối ưu: Sử dụng một query duy nhất với CTE để lấy tất cả thông tin cần thiết
        query = f"""
        WITH conversation_stats AS (
            SELECT 
                c.conversation_id,
                c.user_id,
                c.created_at,
                c.last_updated,
                COUNT(m.id) as message_count,
                (
                    SELECT content 
                    FROM messages m2 
                    WHERE m2.conversation_id = c.conversation_id 
                    AND m2.role = 'user' 
                    ORDER BY m2.sequence ASC 
                    LIMIT 1
                ) as first_message
            FROM conversations c
            LEFT JOIN messages m ON c.conversation_id = m.conversation_id
            WHERE c.user_id = '{user_id}'
            GROUP BY c.conversation_id, c.user_id, c.created_at, c.last_updated
            ORDER BY c.last_updated DESC
            LIMIT {page_size} OFFSET {offset}
        ),
        total_count AS (
            SELECT COUNT(*) as total FROM conversations WHERE user_id = '{user_id}'
        )
        SELECT 
            cs.*,
            tc.total as total_conversations
        FROM conversation_stats cs
        CROSS JOIN total_count tc
        """

        # TẮM RPC EXECUTE_SQL - LUÔN DÙNG FALLBACK METHOD
        # RPC execute_sql đang gây lỗi "string indices must be integers"
        print("Skipping RPC execute_sql - using fallback method directly")
        return await get_user_conversations_fallback(page, page_size, current_user)

        conversations = []
        total_items = 0
        
        try:
            for row in result.data:
                # Kiểm tra xem row có phải là dict không
                if not isinstance(row, dict):
                    print(f"Row is not dict: {type(row)}, {row}")
                    continue
                    
                if 'total_conversations' in row:
                    total_items = row['total_conversations']
                
                conversations.append({
                    "conversation_id": row.get("conversation_id", ""),
                    "user_id": row.get("user_id", ""),
                    "created_at": parse_and_format_vietnam_time(row.get("created_at", "")),
                    "last_updated": parse_and_format_vietnam_time(row.get("last_updated", "")),
                    "first_message": row.get("first_message") or "Hội thoại mới",
                    "message_count": row.get("message_count", 0)
                })
        except Exception as row_error:
            print(f"Error processing rows: {str(row_error)}")
            return await get_user_conversations_fallback(page, page_size, current_user)

        return {
            "status": "success",
            "data": conversations,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": (total_items + page_size - 1) // page_size,
            },
        }
    except Exception as e:
        print(f"Lỗi khi lấy danh sách hội thoại: {str(e)}")
        import traceback
        print(f"Chi tiết lỗi: {traceback.format_exc()}")
        # Fallback về phương pháp cũ
        return await get_user_conversations_fallback(page, page_size, current_user)


async def get_user_conversations_fallback(
    page: int,
    page_size: int,
    current_user,
):
    """
    Phương pháp fallback cho get_user_conversations khi RPC không hoạt động
    TỐI ỦU HÓA: Giảm số lần query xuống còn 4 queries thay vì N+1
    """
    try:
        user_id = current_user.id
        offset = (page - 1) * page_size

        # Query 1: Lấy tổng số hội thoại
        count_result = (
            supabase_client.table("conversations")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .execute()
        )

        total_items = count_result.count if hasattr(count_result, "count") else 0

        # Query 2: Lấy danh sách hội thoại có phân trang
        conversations = (
            supabase_client.table("conversations")
            .select("*")
            .eq("user_id", user_id)
            .order("last_updated", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

        # Kiểm tra conversations.data trước khi xử lý
        if not conversations.data or not isinstance(conversations.data, list):
            return {
                "status": "success",
                "data": [],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_items": 0,
                    "total_pages": 0,
                },
            }

        conversation_ids = [conv.get("conversation_id") for conv in conversations.data if conv.get("conversation_id")]
        
        if conversation_ids:
            try:
                # Query 3: Batch query cho first messages
                first_messages = (
                    supabase_client.table("messages")
                    .select("conversation_id, content, sequence")
                    .in_("conversation_id", conversation_ids)
                    .eq("role", "user")
                    .order("conversation_id, sequence")
                    .execute()
                )
                
                # Query 4: Batch query cho message counts - TỐI ỦU HÓA CHÍNH
                # Thay vì N queries riêng lẻ, dùng 1 query duy nhất với GROUP BY
                message_counts_result = (
                    supabase_client.table("messages")
                    .select("conversation_id")
                    .in_("conversation_id", conversation_ids)
                    .execute()
                )
                
                # Xử lý kết quả first messages
                first_msg_dict = {}
                if hasattr(first_messages, "data") and isinstance(first_messages.data, list):
                    for msg in first_messages.data:
                        if isinstance(msg, dict) and msg.get("conversation_id"):
                            conv_id = msg["conversation_id"]
                            if conv_id not in first_msg_dict:
                                first_msg_dict[conv_id] = msg.get("content", "")
                
                # Xử lý kết quả message counts - đếm trong Python thay vì SQL
                msg_count_dict = {}
                if hasattr(message_counts_result, "data") and isinstance(message_counts_result.data, list):
                    for msg in message_counts_result.data:
                        if isinstance(msg, dict) and msg.get("conversation_id"):
                            conv_id = msg["conversation_id"]
                            msg_count_dict[conv_id] = msg_count_dict.get(conv_id, 0) + 1

                # Gán dữ liệu vào conversations
                for conv in conversations.data:
                    if isinstance(conv, dict) and conv.get("conversation_id"):
                        conv_id = conv["conversation_id"]
                        conv["first_message"] = first_msg_dict.get(conv_id, "Hội thoại mới")
                        conv["message_count"] = msg_count_dict.get(conv_id, 0)
                        
            except Exception as batch_error:
                print(f"Error in batch processing: {batch_error}")
                # Tiếp tục với dữ liệu cơ bản nếu batch processing fail
                for conv in conversations.data:
                    if isinstance(conv, dict):
                        conv["first_message"] = conv.get("first_message", "Hội thoại mới")
                        conv["message_count"] = 0

        return {
            "status": "success",
            "data": conversations.data if conversations.data else [],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": (total_items + page_size - 1) // page_size,
            },
        }
    except Exception as e:
        print(f"Lỗi trong fallback method: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi lấy danh sách hội thoại: {str(e)}"
        )


@app.delete(f"{PREFIX}/conversations/{{conversation_id}}")
async def delete_conversation(
    conversation_id: str = Path(..., description="ID của cuộc hội thoại cần xóa"),
    current_user=Depends(get_current_user),
):
    """
    Xóa một cuộc hội thoại và tất cả tin nhắn của nó

    Args:
        conversation_id: ID của cuộc hội thoại cần xóa
        current_user: Thông tin người dùng hiện tại

    Returns:
        Dict: Kết quả xóa hội thoại
    """
    try:
        user_id = current_user.id

        # Kiểm tra quyền xóa conversation
        conversation = (
            supabase_client.table("conversations")
            .select("*")
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if not conversation.data:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy hội thoại {conversation_id} hoặc bạn không có quyền xóa",
            )

        # Xóa conversation (messages sẽ tự động bị xóa do có ON DELETE CASCADE)
        result = (
            supabase_client.table("conversations")
            .delete()
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Không thể xóa hội thoại",
            )
        print(f"Đã xóa hội thoại {conversation_id}")
        return {
            "status": "success",
            "message": f"Đã xóa hội thoại {conversation_id}",
            "conversation_id": conversation_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Lỗi khi xóa hội thoại: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi xóa hội thoại: {str(e)}",
        )


# Thêm model cho response của API đề xuất câu hỏi
class SuggestionResponse(BaseModel):
    suggestions: List[str]
    conversation_id: Optional[str] = None
    from_history: bool = (
        False  # True nếu đề xuất dựa trên lịch sử hội thoại, False nếu dùng mặc định
    )


# Thêm model cho response của API lấy cuộc hội thoại gần đây
class LatestConversationResponse(BaseModel):
    conversation_info: Dict
    messages: List[Dict]
    found: bool = True  # True nếu tìm thấy cuộc hội thoại, False nếu không


@app.get(f"{PREFIX}/suggestions", response_model=SuggestionResponse)
async def get_question_suggestions(
    num_suggestions: int = Query(
        3, ge=1, le=10, description="Số lượng câu hỏi đề xuất"
    ),
    current_user=Depends(get_current_user),
):
    """
    Lấy đề xuất câu hỏi dựa trên cuộc hội thoại gần đây nhất có tin nhắn
    """
    try:
        # Lấy user_id từ thông tin người dùng hiện tại
        user_id = current_user.id

        # Lấy đề xuất câu hỏi từ cuộc hội thoại gần đây nhất
        suggestions = await suggestion_manager.get_suggestions_from_latest_conversation(
            user_id, conversation_manager, num_suggestions
        )

        # Lấy thông tin về cuộc hội thoại đã được sử dụng (nếu có)
        conversation_data = conversation_manager.get_latest_conversation_with_messages(
            user_id
        )

        # Kiểm tra xem đề xuất có dựa trên lịch sử hội thoại hay không
        from_history = bool(conversation_data and conversation_data.get("messages"))
        conversation_id = (
            conversation_data.get("conversation_info", {}).get("conversation_id")
            if from_history
            else None
        )

        return {
            "suggestions": suggestions,
            "conversation_id": conversation_id,
            "from_history": from_history,
        }
    except Exception as e:
        print(f"Lỗi khi lấy đề xuất câu hỏi: {str(e)}")
        import traceback

        traceback.print_exc()

        # Trả về các đề xuất mặc định nếu có lỗi
        default_suggestions = suggestion_manager._get_default_suggestions()[
            :num_suggestions
        ]
        return {
            "suggestions": default_suggestions,
            "conversation_id": None,
            "from_history": False,
        }


@app.get(f"{PREFIX}/latest-conversation", response_model=LatestConversationResponse)
async def get_latest_conversation(
    current_user=Depends(get_current_user),
):
    """
    Lấy cuộc hội thoại gần đây nhất có tin nhắn
    """
    try:
        # Lấy user_id từ thông tin người dùng hiện tại
        user_id = current_user.id

        # Lấy cuộc hội thoại gần đây nhất có tin nhắn
        conversation_data = conversation_manager.get_latest_conversation_with_messages(
            user_id
        )

        if not conversation_data:
            return {"conversation_info": {}, "messages": [], "found": False}

        return {
            "conversation_info": conversation_data.get("conversation_info", {}),
            "messages": conversation_data.get("messages", []),
            "found": True,
        }
    except Exception as e:
        print(f"Lỗi khi lấy cuộc hội thoại gần đây: {str(e)}")
        import traceback

        traceback.print_exc()

        return {"conversation_info": {}, "messages": [], "found": False}


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for deployment monitoring"""
    try:
        # Check if Qdrant is accessible
        vector_store = rag_system.vector_store
        # Basic connectivity test
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "api": "running",
                "vector_store": "connected" if vector_store else "disconnected"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

# === THÊM MODELS CHO ADMIN USER MANAGEMENT ===
class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = "student"  # Mặc định là student
    metadata: Optional[Dict] = None

class AdminUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None
    metadata: Optional[Dict] = None

class AdminUserResponse(BaseModel):
    id: str
    email: str
    created_at: str
    email_confirmed_at: Optional[str] = None
    last_sign_in_at: Optional[str] = None
    role: Optional[str] = None
    metadata: Optional[Dict] = None
    banned_until: Optional[str] = None

class AdminUserListResponse(BaseModel):
    users: List[AdminUserResponse]
    total_count: int
    page: int
    per_page: int

class BanUserRequest(BaseModel):
    duration: str = "24h"  # Format: "1h", "24h", "7d", etc.
    reason: Optional[str] = None

# === HELPER FUNCTIONS ===
def _raise_if_supabase_error(res):
    """Kiểm tra và raise HTTPException nếu có lỗi từ Supabase"""
    if hasattr(res, 'error') and res.error:
        raise HTTPException(status_code=400, detail=str(res.error))
    return res

async def require_admin_role(current_user=Depends(get_current_user)):
    """Dependency để kiểm tra quyền admin"""
    if not current_user or getattr(current_user, 'role', None) != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin mới có quyền truy cập API này"
        )
    return current_user

def get_service_supabase_client():
    """Lấy Supabase client với service role key"""
    try:
        from backend.supabase.client import SupabaseClient
        service_client = SupabaseClient(use_service_key=True)
        return service_client.get_client()
    except Exception as e:
        print(f"Lỗi khi khởi tạo service client: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Không thể khởi tạo service client"
        )

def calculate_banned_until(user):
    """
    Tính toán thời gian banned_until từ user object
    Lưu ý: Supabase không expose banned_until field qua API, 
    nên phải tính toán dựa trên ban_duration và banned_at
    """
    from datetime import datetime, timedelta
    import re
    
    # Lấy user_metadata để tìm banned_at và ban_duration
    user_metadata = getattr(user, 'user_metadata', {}) or {}
    banned_at_str = user_metadata.get('banned_at')
    ban_duration_meta = user_metadata.get('ban_duration')
    unbanned_at_str = user_metadata.get('unbanned_at')
    
    # Ưu tiên đọc ban_duration từ metadata, fallback về Supabase Auth field
    ban_duration_raw = ban_duration_meta
    if not ban_duration_raw:
        ban_duration_raw = getattr(user, 'ban_duration', None)
    
    # Kiểm tra xem có bị unban hay không dựa trên timestamp
    user_was_unbanned = False
    if unbanned_at_str and banned_at_str:
        try:
            # Sử dụng parse_and_format_vietnam_time để đảm bảo format đúng
            parsed_unbanned = parse_and_format_vietnam_time(unbanned_at_str)
            parsed_banned = parse_and_format_vietnam_time(banned_at_str)
            if parsed_unbanned and parsed_banned:
                unbanned_at = datetime.fromisoformat(parsed_unbanned)
                banned_at = datetime.fromisoformat(parsed_banned)
            # Nếu unbanned_at > banned_at thì user đã được unban sau lần ban cuối
            if unbanned_at > banned_at:
                user_was_unbanned = True
            elif banned_at > unbanned_at:
                user_was_unbanned = False  # User is currently banned
        except Exception:
            pass
    
    # Trường hợp đặc biệt: User bị ban trực tiếp từ Supabase Dashboard
    # Khi đó sẽ không có ban_duration trong metadata, cần kiểm tra Auth field
    if not ban_duration_raw:
        auth_ban_duration = getattr(user, 'ban_duration', None)
        
        # Nếu Supabase Auth có ban_duration, nghĩa là user bị ban manual từ Dashboard
        if auth_ban_duration and auth_ban_duration != "none":
            ban_duration_raw = auth_ban_duration
            
            # Nếu có banned_at trong metadata nhưng là từ lần ban cũ, 
            # và hiện tại user bị ban manual từ Dashboard, 
            # cần sử dụng thời gian hiện tại làm banned_at ước tính
            if user_was_unbanned:
                # Ước tính banned_at dựa trên updated_at của user hoặc thời gian hiện tại
                banned_at_str = None  # Reset để sử dụng current time
        else:
            # Kiểm tra xem có phải Dashboard ban không bằng cách xem updated_at gần đây
            # và không có unban event sau ban event
            updated_at_str = getattr(user, 'updated_at', None)
            current_time = datetime.now()
            
            # Nếu user có banned_at, không có ban_duration, và updated_at gần đây
            # => có thể là Dashboard ban
            # HOẶC user có banned_at sau unbanned_at (ban lại sau khi unban)
            if banned_at_str and updated_at_str:
                try:
                    # Sử dụng parse_and_format_vietnam_time để đảm bảo format đúng
                    parsed_banned = parse_and_format_vietnam_time(banned_at_str)
                    if parsed_banned:
                        banned_at = datetime.fromisoformat(parsed_banned)
                    
                    # Handle different datetime formats for updated_at
                    if isinstance(updated_at_str, str):
                        # Remove timezone info if present and parse
                        updated_at_clean = updated_at_str.replace('+00:00', '').replace('Z', '')
                        updated_at = datetime.fromisoformat(updated_at_clean)
                    else:
                        # If it's already a datetime object, convert to naive
                        updated_at = updated_at_str.replace(tzinfo=None) if updated_at_str.tzinfo else updated_at_str
                    
                    # Kiểm tra nếu banned_at > unbanned_at (ban lại sau khi unban)
                    should_detect_ban = False
                    current_time = datetime.now()
                    
                    # Đảm bảo tất cả datetime đều là naive để tránh lỗi timezone
                    try:
                        time_diff = current_time - updated_at
                        
                        if unbanned_at_str:
                            parsed_unbanned = parse_and_format_vietnam_time(unbanned_at_str)
                            if parsed_unbanned:
                                unbanned_at = datetime.fromisoformat(parsed_unbanned)
                                # Đảm bảo cả banned_at và unbanned_at đều là naive datetime
                                banned_at_naive = banned_at.replace(tzinfo=None) if banned_at.tzinfo else banned_at
                                unbanned_at_naive = unbanned_at.replace(tzinfo=None) if unbanned_at.tzinfo else unbanned_at
                                if banned_at_naive > unbanned_at_naive:
                                    should_detect_ban = True
                        
                        # Hoặc nếu updated_at sau banned_at và trong vòng 24 giờ gần đây
                        if not should_detect_ban:
                            banned_at_naive = banned_at.replace(tzinfo=None) if banned_at.tzinfo else banned_at
                            updated_at_naive = updated_at.replace(tzinfo=None) if updated_at.tzinfo else updated_at
                            if updated_at_naive > banned_at_naive and time_diff.total_seconds() < 86400:  # 24 hours
                                should_detect_ban = True
                    except Exception as tz_error:
                        print(f"⚠️ Lỗi timezone khi so sánh thời gian: {str(tz_error)}")
                        # Fallback: không detect ban nếu có lỗi timezone
                        should_detect_ban = False
                    
                    if should_detect_ban:
                        # Ước tính ban duration dựa trên pattern thông thường
                        # Dashboard thường ban 24h hoặc dài hạn
                        ban_duration_raw = "24h"  # Default estimate
                        
                        # Sử dụng banned_at từ metadata (thời gian ban thực tế)
                        banned_at_str = banned_at.isoformat()
                except Exception:
                    pass
    
    # Nếu user đã được unban (theo metadata) nhưng vẫn có ban_duration, 
    # có thể là do inconsistency - ưu tiên kiểm tra Supabase Auth state trực tiếp
    if user_was_unbanned and ban_duration_raw:
        # Kiểm tra trực tiếp từ Supabase Auth field
        auth_ban_duration = getattr(user, 'ban_duration', None)
        if not auth_ban_duration or auth_ban_duration == "none":
            return None
        else:
            ban_duration_raw = auth_ban_duration
            # Reset banned_at để sử dụng thời gian ước tính cho manual ban
            banned_at_str = None
    
    # Nếu không có ban_duration hoặc ban_duration = "none" -> không bị ban
    if not ban_duration_raw or ban_duration_raw == "none":
        return None
    
    # Nếu có ban_duration hợp lệ, tính toán banned_until
    try:
        # Parse ban duration (format: "24h", "7d", "1h", etc.)
        duration_match = re.match(r'(\d+)([hdm])', str(ban_duration_raw).lower())
        if not duration_match:
            return None
            
        amount = int(duration_match.group(1))
        unit = duration_match.group(2)
        
        # Tìm banned_at - sử dụng thời gian ban cuối cùng
        banned_at = None
        if banned_at_str:
            try:
                parsed_banned = parse_and_format_vietnam_time(banned_at_str)
                if parsed_banned:
                    banned_at = datetime.fromisoformat(parsed_banned)
            except Exception:
                pass
        
        # Nếu không có banned_at trong metadata, sử dụng thời gian hiện tại
        if not banned_at:
            banned_at = datetime.now()
        
        # Tính toán thời gian hết ban
        if unit == 'h':
            ban_until = banned_at + timedelta(hours=amount)
        elif unit == 'd':
            ban_until = banned_at + timedelta(days=amount)
        elif unit == 'm':
            ban_until = banned_at + timedelta(minutes=amount)
        else:
            ban_until = banned_at + timedelta(hours=24)  # Default 24h
        
        # Chỉ return banned_until nếu thời gian ban chưa hết
        current_time = datetime.now()
        # Đảm bảo cả ban_until và current_time đều là naive datetime
        try:
            ban_until_naive = ban_until.replace(tzinfo=None) if ban_until.tzinfo else ban_until
            current_time_naive = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
            if ban_until_naive > current_time_naive:
                return ban_until.isoformat()
            else:
                return None  # Ban đã hết hạn
        except Exception as tz_error:
            print(f"⚠️ Lỗi timezone khi so sánh thời gian ban: {str(tz_error)}")
            # Fallback: return ban_until anyway
            return ban_until.isoformat()
            
    except Exception as calc_error:
        print(f"⚠️ Lỗi khi tính toán ban time: {str(calc_error)}")
        return None

@app.get(f"{PREFIX}/admin/users", response_model=AdminUserListResponse)
async def admin_list_users(
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    per_page: int = Query(50, ge=1, le=100, description="Số người dùng mỗi trang"),
    admin_user=Depends(require_admin_role)
):
    """
    [ADMIN] Liệt kê tất cả người dùng trong hệ thống
    
    - **page**: Trang hiện tại (bắt đầu từ 1)
    - **per_page**: Số người dùng mỗi trang (tối đa 100)
    """
    try:
        service_client = get_service_supabase_client()
        
        # Lấy danh sách người dùng từ Supabase Auth
        result = service_client.auth.admin.list_users(page=page, per_page=per_page)
        _raise_if_supabase_error(result)
        
        # Xử lý response dựa trên cấu trúc thực tế
        users_list = []
        if hasattr(result, 'users') and result.users:
            users_list = result.users
        elif isinstance(result, list):
            users_list = result
        elif hasattr(result, 'data') and result.data:
            users_list = result.data
        else:
            return AdminUserListResponse(
                users=[],
                total_count=0,
                page=page,
                per_page=per_page
            )
        
        if not users_list:
            return AdminUserListResponse(
                users=[],
                total_count=0,
                page=page,
                per_page=per_page
            )
        
        # Lấy roles của tất cả users từ database
        user_ids = [user.id for user in users_list]
        roles_result = service_client.table("user_roles").select("user_id, role").in_("user_id", user_ids).execute()
        
        # Tạo dictionary để lookup role nhanh
        user_roles = {}
        if roles_result.data:
            for role_record in roles_result.data:
                user_roles[role_record["user_id"]] = role_record["role"]
        
        # Format response
        users_response = []
        for user in users_list:
            # Chuyển đổi datetime thành string nếu cần
            created_at = user.created_at
            if hasattr(created_at, "isoformat"):
                created_at = created_at.isoformat()
            
            email_confirmed_at = getattr(user, 'email_confirmed_at', None)
            if email_confirmed_at and hasattr(email_confirmed_at, "isoformat"):
                email_confirmed_at = email_confirmed_at.isoformat()
            
            last_sign_in_at = getattr(user, 'last_sign_in_at', None)
            if last_sign_in_at and hasattr(last_sign_in_at, "isoformat"):
                last_sign_in_at = last_sign_in_at.isoformat()
            
            # Tính toán banned_until từ nhiều nguồn khác nhau
            banned_until = calculate_banned_until(user)
            
            users_response.append(AdminUserResponse(
                id=user.id,
                email=user.email,
                created_at=created_at,
                email_confirmed_at=email_confirmed_at,
                last_sign_in_at=last_sign_in_at,
                role=user_roles.get(user.id, "student"),
                metadata=getattr(user, 'user_metadata', {}),
                banned_until=banned_until
            ))
        
        return AdminUserListResponse(
            users=users_response,
            total_count=len(users_list),  # Supabase không trả về total count, dùng length của current page
            page=page,
            per_page=per_page
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Lỗi khi lấy danh sách người dùng: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Lỗi khi lấy danh sách người dùng: {str(e)}"
        )

@app.post(f"{PREFIX}/admin/users", status_code=201, response_model=AdminUserResponse)
async def admin_create_user(
    body: AdminUserCreate,
    admin_user=Depends(require_admin_role)
):
    """
    [ADMIN] Tạo người dùng mới
    
    - **email**: Email của người dùng
    - **password**: Mật khẩu 
    - **role**: Vai trò (admin/student, mặc định student)
    - **metadata**: Metadata bổ sung (tùy chọn)
    """
    try:
        service_client = get_service_supabase_client()
        
        # Tạo user trong Supabase Auth
        create_params = {
            "email": body.email,
            "password": body.password,
            "email_confirm": True,  # Tự động xác nhận email
        }
        
        if body.metadata:
            create_params["user_metadata"] = body.metadata
            
        result = service_client.auth.admin.create_user(create_params)
        _raise_if_supabase_error(result)
        
        # Xử lý response
        new_user = None
        if hasattr(result, 'user') and result.user:
            new_user = result.user
        elif hasattr(result, 'data') and result.data:
            new_user = result.data
        elif hasattr(result, 'id'):  # Trường hợp result chính là user object
            new_user = result
        
        if not new_user:
            raise HTTPException(status_code=400, detail="Không thể tạo người dùng")
        
        # Thêm role vào bảng user_roles
        try:
            # Kiểm tra xem user đã có role chưa
            existing_role = service_client.table("user_roles").select("role").eq("user_id", new_user.id).execute()
            
            if existing_role.data and len(existing_role.data) > 0:
                # Nếu đã có role, cập nhật role hiện tại
                service_client.table("user_roles").update({
                    "role": body.role or "student",
                    "updated_at": "now()"
                }).eq("user_id", new_user.id).execute()
                print(f"✅ Đã cập nhật role '{body.role or 'student'}' cho user {new_user.email}")
            else:
                # Nếu chưa có role, tạo mới
                service_client.table("user_roles").insert({
                    "id": str(uuid.uuid4()),
                    "user_id": new_user.id,
                    "role": body.role or "student",
                    "created_at": "now()",
                    "updated_at": "now()"
                }).execute()
                print(f"✅ Đã thêm role '{body.role or 'student'}' cho user {new_user.email}")
        except Exception as role_error:
            print(f"⚠️ Lỗi khi thêm/cập nhật role: {str(role_error)}")
            # Không raise exception để không cản trở việc tạo user
        
        # Format response
        created_at = new_user.created_at
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        
        # Format email_confirmed_at    
        email_confirmed_at = getattr(new_user, 'email_confirmed_at', None)
        if email_confirmed_at and hasattr(email_confirmed_at, "isoformat"):
            email_confirmed_at = email_confirmed_at.isoformat()
            
        return AdminUserResponse(
            id=new_user.id,
            email=new_user.email,
            created_at=created_at,
            email_confirmed_at=email_confirmed_at,
            last_sign_in_at=None,
            role=body.role or "student",
            metadata=body.metadata or {},
            banned_until=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        
        # Xử lý các trường hợp lỗi cụ thể
        if "User already registered" in error_message or "already registered" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email này đã được đăng ký"
            )
        elif "Invalid email" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email không hợp lệ"
            )
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Lỗi khi tạo người dùng: {error_message}"
            )

@app.get(f"{PREFIX}/admin/users/{{user_id}}", response_model=AdminUserResponse)
async def admin_get_user(
    user_id: str = Path(..., description="ID của người dùng"),
    admin_user=Depends(require_admin_role)
):
    """
    [ADMIN] Lấy thông tin chi tiết của một người dùng
    
    - **user_id**: ID của người dùng cần lấy thông tin
    """
    try:
        service_client = get_service_supabase_client()
        
        # Lấy user từ Supabase Auth
        result = service_client.auth.admin.get_user_by_id(user_id)
        _raise_if_supabase_error(result)
        
        # Xử lý response
        user = None
        if hasattr(result, 'user') and result.user:
            user = result.user
        elif hasattr(result, 'data') and result.data:
            user = result.data
        elif hasattr(result, 'id'):  # Trường hợp result chính là user object
            user = result
            
        if not user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
        
        # Lấy role từ database
        role_result = service_client.table("user_roles").select("role").eq("user_id", user_id).execute()
        user_role = "student"
        if role_result.data and len(role_result.data) > 0:
            user_role = role_result.data[0].get("role", "student")
        
        # Format response
        created_at = user.created_at
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        
        email_confirmed_at = getattr(user, 'email_confirmed_at', None)
        if email_confirmed_at and hasattr(email_confirmed_at, "isoformat"):
            email_confirmed_at = email_confirmed_at.isoformat()
        
        last_sign_in_at = getattr(user, 'last_sign_in_at', None)
        if last_sign_in_at and hasattr(last_sign_in_at, "isoformat"):
            last_sign_in_at = last_sign_in_at.isoformat()
        
        # Tính toán banned_until từ nhiều nguồn khác nhau
        banned_until = calculate_banned_until(user)
        
        return AdminUserResponse(
            id=user.id,
            email=user.email,
            created_at=created_at,
            email_confirmed_at=email_confirmed_at,
            last_sign_in_at=last_sign_in_at,
            role=user_role,
            metadata=getattr(user, 'user_metadata', {}),
            banned_until=banned_until
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Lỗi khi lấy thông tin người dùng: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Lỗi khi lấy thông tin người dùng: {str(e)}"
        )

@app.put(f"{PREFIX}/admin/users/{{user_id}}", response_model=AdminUserResponse)
async def admin_update_user(
    user_id: str = Path(..., description="ID của người dùng"),
    body: AdminUserUpdate = Body(...),
    admin_user=Depends(require_admin_role)
):
    """
    [ADMIN] Cập nhật thông tin người dùng
    
    - **user_id**: ID của người dùng cần cập nhật
    - **email**: Email mới (tùy chọn)
    - **password**: Mật khẩu mới (tùy chọn)  
    - **role**: Vai trò mới (tùy chọn)
    - **metadata**: Metadata mới (tùy chọn)
    """
    try:
        service_client = get_service_supabase_client()
        
        # Kiểm tra user tồn tại
        existing_user_result = service_client.auth.admin.get_user_by_id(user_id)
        _raise_if_supabase_error(existing_user_result)
        
        # Xử lý response
        existing_user = None
        if hasattr(existing_user_result, 'user') and existing_user_result.user:
            existing_user = existing_user_result.user
        elif hasattr(existing_user_result, 'data') and existing_user_result.data:
            existing_user = existing_user_result.data
        elif hasattr(existing_user_result, 'id'):
            existing_user = existing_user_result
            
        if not existing_user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
        
        # Chuẩn bị payload update cho Supabase Auth
        auth_payload = {}
        if body.email:
            auth_payload["email"] = body.email
        if body.password:
            auth_payload["password"] = body.password
        if body.metadata is not None:
            auth_payload["user_metadata"] = body.metadata
        
        # Cập nhật trong Supabase Auth nếu có thay đổi
        updated_user = existing_user
        if auth_payload:
            result = service_client.auth.admin.update_user_by_id(user_id, auth_payload)
            _raise_if_supabase_error(result)
            # Xử lý response từ update
            if hasattr(result, 'user') and result.user:
                updated_user = result.user
            elif hasattr(result, 'data') and result.data:
                updated_user = result.data
            elif hasattr(result, 'id'):
                updated_user = result
        
        # Cập nhật role trong database nếu có thay đổi
        current_role = "student"
        if body.role:
            try:
                # Kiểm tra role hiện tại
                role_check = service_client.table("user_roles").select("role").eq("user_id", user_id).execute()
                
                if role_check.data and len(role_check.data) > 0:
                    # Update existing role
                    service_client.table("user_roles").update({
                        "role": body.role,
                        "updated_at": "now()"
                    }).eq("user_id", user_id).execute()
                    current_role = body.role
                else:
                    # Insert new role
                    service_client.table("user_roles").insert({
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "role": body.role,
                        "created_at": "now()",
                        "updated_at": "now()"
                    }).execute()
                    current_role = body.role
                    
                print(f"✅ Đã cập nhật role '{body.role}' cho user {updated_user.email}")
            except Exception as role_error:
                print(f"⚠️ Lỗi khi cập nhật role: {str(role_error)}")
        else:
            # Lấy role hiện tại
            role_result = service_client.table("user_roles").select("role").eq("user_id", user_id).execute()
            if role_result.data and len(role_result.data) > 0:
                current_role = role_result.data[0].get("role", "student")
        
        # Format response
        created_at = updated_user.created_at
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        
        email_confirmed_at = getattr(updated_user, 'email_confirmed_at', None)
        if email_confirmed_at and hasattr(email_confirmed_at, "isoformat"):
            email_confirmed_at = email_confirmed_at.isoformat()
        
        last_sign_in_at = getattr(updated_user, 'last_sign_in_at', None)
        if last_sign_in_at and hasattr(last_sign_in_at, "isoformat"):
            last_sign_in_at = last_sign_in_at.isoformat()
        
        # Tính toán banned_until từ nhiều nguồn khác nhau
        banned_until = calculate_banned_until(updated_user)
        
        return AdminUserResponse(
            id=updated_user.id,
            email=updated_user.email,
            created_at=created_at,
            email_confirmed_at=email_confirmed_at,
            last_sign_in_at=last_sign_in_at,
            role=current_role,
            metadata=getattr(updated_user, 'user_metadata', {}),
            banned_until=banned_until
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Lỗi khi cập nhật người dùng: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Lỗi khi cập nhật người dùng: {str(e)}"
        )

@app.delete(f"{PREFIX}/admin/users/{{user_id}}", status_code=204)
async def admin_delete_user(
    user_id: str = Path(..., description="ID của người dùng cần xóa"),
    hard: bool = Query(True, description="True = xóa vĩnh viễn, False = xóa tạm thời"),
    admin_user=Depends(require_admin_role)
):
    """
    [ADMIN] Xóa người dùng khỏi hệ thống
    
    - **user_id**: ID của người dùng cần xóa
    - **hard**: True để xóa vĩnh viễn, False để xóa tạm thời
    """
    try:
        service_client = get_service_supabase_client()
        
        # Kiểm tra user tồn tại
        existing_user_result = service_client.auth.admin.get_user_by_id(user_id)
        _raise_if_supabase_error(existing_user_result)
        
        # Xử lý response
        existing_user = None
        if hasattr(existing_user_result, 'user') and existing_user_result.user:
            existing_user = existing_user_result.user
        elif hasattr(existing_user_result, 'data') and existing_user_result.data:
            existing_user = existing_user_result.data
        elif hasattr(existing_user_result, 'id'):
            existing_user = existing_user_result
            
        if not existing_user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
        
        # Không cho phép admin xóa chính mình
        if user_id == admin_user.id:
            raise HTTPException(
                status_code=400, 
                detail="Không thể xóa chính tài khoản admin đang đăng nhập"
            )
        
        # Xóa user từ Supabase Auth
        service_client.auth.admin.delete_user(user_id, should_soft_delete=not hard)
        
        # Xóa role trong database nếu xóa vĩnh viễn
        if hard:
            try:
                service_client.table("user_roles").delete().eq("user_id", user_id).execute()
                print(f"✅ Đã xóa role cho user {existing_user.email}")
            except Exception as role_error:
                print(f"⚠️ Lỗi khi xóa role: {str(role_error)}")
        
        print(f"✅ Admin {admin_user.email} đã {'xóa vĩnh viễn' if hard else 'xóa tạm thời'} user {existing_user.email}")
        return
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Lỗi khi xóa người dùng: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Lỗi khi xóa người dùng: {str(e)}"
        )

@app.post(f"{PREFIX}/admin/users/{{user_id}}/ban")
async def admin_ban_user(
    user_id: str = Path(..., description="ID của người dùng cần cấm"),
    body: BanUserRequest = Body(...),
    admin_user=Depends(require_admin_role)
):
    """
    [ADMIN] Cấm người dùng trong một khoảng thời gian
    
    - **user_id**: ID của người dùng cần cấm
    - **duration**: Thời gian cấm (format: "1h", "24h", "7d")
    - **reason**: Lý do cấm (tùy chọn)
    """
    try:
        service_client = get_service_supabase_client()
        
        # Kiểm tra user tồn tại
        existing_user_result = service_client.auth.admin.get_user_by_id(user_id)
        _raise_if_supabase_error(existing_user_result)
        
        # Xử lý response
        existing_user = None
        if hasattr(existing_user_result, 'user') and existing_user_result.user:
            existing_user = existing_user_result.user
        elif hasattr(existing_user_result, 'data') and existing_user_result.data:
            existing_user = existing_user_result.data
        elif hasattr(existing_user_result, 'id'):
            existing_user = existing_user_result
            
        if not existing_user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
        
        # Không cho phép admin cấm chính mình
        if user_id == admin_user.id:
            raise HTTPException(
                status_code=400, 
                detail="Không thể cấm chính tài khoản admin đang đăng nhập"
            )
        
        # Cập nhật ban duration trong Supabase Auth
        ban_payload = {"ban_duration": body.duration}
        
        # Thêm reason vào user_metadata nếu có
        current_metadata = getattr(existing_user, 'user_metadata', {}) or {}
        if body.reason:
            current_metadata["ban_reason"] = body.reason
        current_metadata["banned_by"] = admin_user.email
        current_metadata["banned_at"] = datetime.now().isoformat()
        current_metadata["ban_duration"] = body.duration  # Lưu vào metadata để có thể đọc lại
        ban_payload["user_metadata"] = current_metadata
        
        result = service_client.auth.admin.update_user_by_id(user_id, ban_payload)
        _raise_if_supabase_error(result)
        
        return {
            "user_id": user_id,
            "email": existing_user.email,
            "banned_for": body.duration,
            "reason": body.reason,
            "banned_by": admin_user.email,
            "banned_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Lỗi khi cấm người dùng: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Lỗi khi cấm người dùng: {str(e)}"
        )

@app.post(f"{PREFIX}/admin/users/{{user_id}}/unban")
async def admin_unban_user(
    user_id: str = Path(..., description="ID của người dùng cần bỏ cấm"),
    admin_user=Depends(require_admin_role)
):
    """
    [ADMIN] Bỏ cấm người dùng
    
    - **user_id**: ID của người dùng cần bỏ cấm
    """
    try:
        service_client = get_service_supabase_client()
        
        # Kiểm tra user tồn tại
        existing_user_result = service_client.auth.admin.get_user_by_id(user_id)
        _raise_if_supabase_error(existing_user_result)
        
        # Xử lý response
        existing_user = None
        if hasattr(existing_user_result, 'user') and existing_user_result.user:
            existing_user = existing_user_result.user
        elif hasattr(existing_user_result, 'data') and existing_user_result.data:
            existing_user = existing_user_result.data
        elif hasattr(existing_user_result, 'id'):
            existing_user = existing_user_result
            
        if not existing_user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
        
        # Bỏ ban duration - sử dụng "none" theo tài liệu Supabase
        unban_payload = {"ban_duration": "none"}
        
        # Xóa thông tin ban khỏi metadata
        current_metadata = getattr(existing_user, 'user_metadata', {}) or {}
        current_metadata.pop("ban_reason", None)
        current_metadata.pop("banned_by", None)
        current_metadata.pop("banned_at", None)
        current_metadata.pop("ban_duration", None)  # Xóa ban_duration khỏi metadata
        current_metadata["unbanned_by"] = admin_user.email
        current_metadata["unbanned_at"] = datetime.now().isoformat()
        unban_payload["user_metadata"] = current_metadata
        
        result = service_client.auth.admin.update_user_by_id(user_id, unban_payload)
        _raise_if_supabase_error(result)
        
        return {
            "user_id": user_id,
            "email": existing_user.email,
            "unbanned_by": admin_user.email,
            "unbanned_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Lỗi khi bỏ cấm người dùng: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Lỗi khi bỏ cấm người dùng: {str(e)}"
        )

# =====================================================================
# END ADMIN USER MANAGEMENT APIs  
# =====================================================================

# Thêm model cho tìm kiếm hội thoại
class ConversationSearchRequest(BaseModel):
    query: str = ""  # Từ khóa tìm kiếm (tìm trong nội dung tin nhắn)
    date_from: Optional[str] = None  # Tìm từ ngày (YYYY-MM-DD)
    date_to: Optional[str] = None    # Tìm đến ngày (YYYY-MM-DD)
    page: int = Query(1, ge=1, description="Trang hiện tại")
    page_size: int = Query(10, ge=1, le=50, description="Số hội thoại mỗi trang")

class ConversationSearchResponse(BaseModel):
    conversations: List[Dict]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    search_query: str
    search_metadata: Dict

@app.post(f"{PREFIX}/conversations/search", response_model=ConversationSearchResponse)
async def search_conversations(
    query: str = Body("", description="Từ khóa tìm kiếm trong nội dung tin nhắn"),
    date_from: Optional[str] = Body(None, description="Tìm từ ngày (YYYY-MM-DD)"),
    date_to: Optional[str] = Body(None, description="Tìm đến ngày (YYYY-MM-DD)"),
    page: int = Body(1, ge=1, description="Trang hiện tại"),
    page_size: int = Body(10, ge=1, le=50, description="Số hội thoại mỗi trang"),
    current_user=Depends(get_current_user),
):
    """
    Tìm kiếm hội thoại của người dùng dựa trên nội dung tin nhắn và thời gian

    - **query**: Từ khóa tìm kiếm trong nội dung tin nhắn (tìm cả tin nhắn user và assistant)
    - **date_from**: Tìm từ ngày (format: YYYY-MM-DD)
    - **date_to**: Tìm đến ngày (format: YYYY-MM-DD) 
    - **page**: Trang hiện tại (bắt đầu từ 1)
    - **page_size**: Số hội thoại mỗi trang (tối đa 50)
    """
    try:
        user_id = current_user.id
        offset = (page - 1) * page_size
        
        print(f"[SEARCH] User {current_user.email} tìm kiếm: query='{query}', date_from={date_from}, date_to={date_to}")
        
        # Sử dụng phương pháp fallback trực tiếp để tránh lỗi SQL
        try:
            # Fallback: Sử dụng phương pháp đơn giản hơn
            conversations = await search_conversations_fallback(
                user_id, query, date_from, date_to, page_size, offset
            )
            
            # Đếm tổng số kết quả
            all_conversations = await search_conversations_fallback(
                user_id, query, date_from, date_to, 1000, 0  # Lấy tất cả để đếm
            )
            total_count = len(all_conversations)
            
        except Exception as e:
            print(f"[SEARCH] Lỗi trong fallback method: {str(e)}")
            conversations = []
            total_count = 0
        
        # Format kết quả
        formatted_conversations = []
        for conv in conversations:
            formatted_conv = {
                "conversation_id": conv.get("conversation_id", ""),
                "user_id": conv.get("user_id", ""),
                "last_updated": parse_and_format_vietnam_time(conv.get("last_updated", "")),
                "first_message": conv.get("first_message") or "Hội thoại không có tiêu đề",
                "message_count": conv.get("message_count", 0),
                "matching_content": conv.get("matching_content") if query and query.strip() else None
            }
            formatted_conversations.append(formatted_conv)
        
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        
        # Metadata về tìm kiếm
        search_metadata = {
            "has_query": bool(query and query.strip()),
            "has_date_filter": bool(date_from or date_to),
            "date_range": f"{date_from or 'không giới hạn'} đến {date_to or 'không giới hạn'}" if (date_from or date_to) else None,
            "search_time": get_vietnam_time().isoformat()
        }
        
        print(f"[SEARCH] Tìm thấy {total_count} hội thoại, trả về trang {page}/{total_pages}")
        
        return ConversationSearchResponse(
            conversations=formatted_conversations,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            search_query=query,
            search_metadata=search_metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SEARCH] Lỗi khi tìm kiếm hội thoại: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi tìm kiếm hội thoại: {str(e)}"
        )

async def search_conversations_fallback(
    user_id: str, 
    query: str, 
    date_from: Optional[str], 
    date_to: Optional[str], 
    page_size: int, 
    offset: int
) -> List[Dict]:
    """
    Phương pháp fallback tìm kiếm hội thoại khi SQL query phức tạp không hoạt động
    """
    try:
        # Query đơn giản để lấy conversations của user
        query_builder = supabase_client.table("conversations").select("*").eq("user_id", user_id)
        
        # Thêm filter theo thời gian nếu có
        if date_from:
            query_builder = query_builder.gte("last_updated", f"{date_from} 00:00:00")
        if date_to:
            query_builder = query_builder.lte("last_updated", f"{date_to} 23:59:59")
        
        conversations_result = query_builder.order("last_updated", desc=True).execute()
        
        if not conversations_result.data:
            return []
        
        # Lọc theo nội dung tin nhắn nếu có query
        filtered_conversations = []
        
        for conv in conversations_result.data:
            conversation_id = conv["conversation_id"]
            
            # Lấy messages của conversation này
            messages_result = supabase_client.table("messages").select("*").eq("conversation_id", conversation_id).execute()
            
            messages = messages_result.data if messages_result.data else []
            
            # Kiểm tra query match
            if query and query.strip():
                # Tìm trong nội dung tin nhắn
                query_lower = query.lower()
                has_match = any(query_lower in msg.get("content", "").lower() for msg in messages)
                if not has_match:
                    continue
            
            # Lấy first_message và message_count
            first_message = ""
            for msg in messages:
                if msg.get("role") == "user":
                    first_message = msg.get("content", "")
                    break
            
            conv_data = {
                "conversation_id": conversation_id,
                "user_id": conv["user_id"],
                "last_updated": conv["last_updated"],
                "first_message": first_message or "Hội thoại không có tiêu đề",
                "message_count": len(messages),
                "matching_content": None  # Có thể implement later nếu cần
            }
            
            filtered_conversations.append(conv_data)
        
        # Apply pagination
        start_idx = offset
        end_idx = offset + page_size
        return filtered_conversations[start_idx:end_idx]
        
    except Exception as e:
        print(f"[SEARCH] Lỗi trong fallback method: {str(e)}")
        return []

# =====================================================================
# ADMIN CONVERSATION MANAGEMENT APIs  
# =====================================================================

# Models cho Admin Conversation Management
class AdminConversationListResponse(BaseModel):
    conversations: List[Dict]
    total_count: int
    page: int
    per_page: int
    total_pages: int

class AdminMessageListResponse(BaseModel):
    conversation_id: str
    messages: List[Dict]
    total_messages: int
    user_info: Dict

class AdminMessageSearchRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    user_email: Optional[str] = None  # Thay đổi từ user_id sang user_email
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    page: int = 1
    per_page: int = 50

class AdminMessageSearchResponse(BaseModel):
    messages: List[Dict]
    total_count: int
    page: int
    per_page: int
    search_query: str

class AdminConversationStatsResponse(BaseModel):
    total_conversations: int
    total_messages: int
    total_users: int
    conversations_by_date: List[Dict]
    messages_by_role: Dict[str, int]
    top_users: List[Dict]



@app.get(f"{PREFIX}/admin/conversations", response_model=AdminConversationListResponse)
async def admin_list_conversations(
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    per_page: int = Query(20, ge=1, le=100, description="Số conversation mỗi trang"),
    user_email: Optional[str] = Query(None, description="Lọc theo email người dùng (có @ = exact match, không có @ = partial match)"),
    search_message: Optional[str] = Query(None, description="Tìm kiếm trong tin nhắn đầu tiên của conversation"),
    date_from: Optional[str] = Query(None, description="Lọc từ ngày (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Lọc đến ngày (YYYY-MM-DD)"),
    admin_user=Depends(require_admin_role)
):
    """
    [ADMIN] Lấy danh sách tất cả conversations trong hệ thống
    
    - **page**: Trang hiện tại
    - **per_page**: Số conversation mỗi trang
    - **user_email**: Lọc theo email người dùng (tùy chọn)
    - **search_message**: Tìm kiếm trong tin nhắn đầu tiên (tùy chọn)
    - **date_from**: Lọc từ ngày (tùy chọn)
    - **date_to**: Lọc đến ngày (tùy chọn)
    """
    try:
        service_client = get_service_supabase_client()
        offset = (page - 1) * per_page
        
        # Bước 1: Nếu có filter theo email, tìm user_id tương ứng
        target_user_ids = None
        if user_email:
            try:
                # Tìm user theo email
                users_result = service_client.auth.admin.list_users()
                if hasattr(users_result, 'users'):
                    # Nếu có @ thì tìm exact match, không có @ thì tìm partial match
                    if '@' in user_email:
                        matching_users = [user for user in users_result.users if user.email.lower() == user_email.lower()]
                    else:
                        matching_users = [user for user in users_result.users if user_email.lower() in user.email.lower()]
                    
                    if matching_users:
                        target_user_ids = [user.id for user in matching_users]
                    else:
                        # Không tìm thấy user nào có email này
                        return AdminConversationListResponse(
                            conversations=[],
                            total_count=0,
                            page=page,
                            per_page=per_page,
                            total_pages=0
                        )
            except Exception as e:
                print(f"Lỗi khi tìm user theo email: {e}")
                # Nếu có lỗi, trả về kết quả rỗng
                return AdminConversationListResponse(
                    conversations=[],
                    total_count=0,
                    page=page,
                    per_page=per_page,
                    total_pages=0
                )
        
        # Bước 2: Build query cho conversations
        query = service_client.table("conversations").select("*", count="exact")
        
        # Add filters
        if target_user_ids:
            query = query.in_("user_id", target_user_ids)
        if date_from:
            query = query.gte("last_updated", f"{date_from} 00:00:00")
        if date_to:
            query = query.lte("last_updated", f"{date_to} 23:59:59")
        
        # Execute query với pagination
        result = query.order("last_updated", desc=True).range(offset, offset + per_page - 1).execute()
        
        conversations = result.data if result.data else []
        # total_count ban đầu từ database
        db_total_count = result.count if hasattr(result, 'count') else len(conversations)
        
        # Enrich conversations với thông tin user và message count
        enriched_conversations = []
        for conv in conversations:
            # Lấy thông tin user
            user_info = {}
            try:
                user_result = service_client.auth.admin.get_user_by_id(conv["user_id"])
                if hasattr(user_result, 'user') and user_result.user:
                    user_info = {
                        "email": user_result.user.email,
                        "created_at": getattr(user_result.user, 'created_at', '').isoformat() if hasattr(getattr(user_result.user, 'created_at', ''), 'isoformat') else ''
                    }
            except:
                user_info = {"email": "Unknown", "created_at": ""}
            
            # Lấy số lượng messages
            msg_count_result = service_client.table("messages").select("conversation_id", count="exact").eq("conversation_id", conv["conversation_id"]).execute()
            message_count = msg_count_result.count if hasattr(msg_count_result, 'count') else 0
            
            # Lấy first message để hiển thị
            first_msg_result = service_client.table("messages").select("content").eq("conversation_id", conv["conversation_id"]).eq("role", "user").order("created_at").limit(1).execute()
            first_message = first_msg_result.data[0]["content"] if first_msg_result.data else "Không có tin nhắn"
            
            # Bước 3: Filter theo search_message nếu có
            if search_message:
                if search_message.lower() not in first_message.lower():
                    continue  # Bỏ qua conversation này nếu không match
            
            enriched_conversations.append({
                "conversation_id": conv["conversation_id"],
                "user_id": conv["user_id"],
                "user_email": user_info.get("email", "Unknown"),
                "created_at": parse_and_format_vietnam_time(conv.get("created_at", "")),
                "last_updated": parse_and_format_vietnam_time(conv.get("last_updated", "")),
                "message_count": message_count,
                "first_message": first_message[:100] + "..." if len(first_message) > 100 else first_message
            })
        
        # Tính total_count thực tế sau khi filter
        actual_total_count = len(enriched_conversations)
        
        # Nếu có search_message filter, cần tính lại total_count chính xác
        if search_message:
            # Trong trường hợp này, actual_total_count chỉ là số lượng trong trang hiện tại
            # Để có total_count chính xác, cần query tất cả và filter
            # Nhưng để đơn giản, ta sẽ sử dụng số lượng hiện tại
            total_count = actual_total_count
        else:
            total_count = db_total_count
        
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
        
        return AdminConversationListResponse(
            conversations=enriched_conversations,
            total_count=total_count,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        print(f"Lỗi khi lấy danh sách conversations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy danh sách conversations: {str(e)}"
        )

@app.get(f"{PREFIX}/admin/conversations/{{conversation_id}}/messages", response_model=AdminMessageListResponse)
async def admin_get_conversation_messages(
    conversation_id: str = Path(..., description="ID của conversation"),
    admin_user=Depends(require_admin_role)
):
    """
    [ADMIN] Xem chi tiết tin nhắn trong một conversation
    
    - **conversation_id**: ID của conversation cần xem
    """
    try:
        service_client = get_service_supabase_client()
        
        # Kiểm tra conversation tồn tại
        conv_result = service_client.table("conversations").select("*").eq("conversation_id", conversation_id).execute()
        if not conv_result.data:
            raise HTTPException(status_code=404, detail="Không tìm thấy conversation")
        
        conversation = conv_result.data[0]
        
        # Lấy thông tin user
        user_info = {}
        try:
            user_result = service_client.auth.admin.get_user_by_id(conversation["user_id"])
            if hasattr(user_result, 'user') and user_result.user:
                user_info = {
                    "id": user_result.user.id,
                    "email": user_result.user.email,
                    "created_at": getattr(user_result.user, 'created_at', '').isoformat() if hasattr(getattr(user_result.user, 'created_at', ''), 'isoformat') else ''
                }
        except:
            user_info = {
                "id": conversation["user_id"],
                "email": "Unknown",
                "created_at": ""
            }
        
        # Lấy tất cả messages
        messages_result = service_client.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at").execute()
        
        messages = []
        for msg in messages_result.data:
            messages.append({
                "message_id": msg.get("message_id"),
                "role": msg.get("role"),
                "content": msg.get("content"),
                "created_at": parse_and_format_vietnam_time(msg.get("created_at", "")),
                "sequence": msg.get("sequence", 0)
            })
        
        return AdminMessageListResponse(
            conversation_id=conversation_id,
            messages=messages,
            total_messages=len(messages),
            user_info=user_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Lỗi khi lấy messages: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy messages: {str(e)}"
        )

@app.post(f"{PREFIX}/admin/messages/search", response_model=AdminMessageSearchResponse)
async def admin_search_messages(
    request: AdminMessageSearchRequest,
    admin_user=Depends(require_admin_role)
):
    """
    [ADMIN] Tìm kiếm tin nhắn trong toàn hệ thống
    
    - **query**: Từ khóa tìm kiếm
    - **conversation_id**: Lọc theo conversation_id (tùy chọn)
    - **user_email**: Lọc theo email người dùng (tùy chọn)
    - **date_from**: Tìm từ ngày (tùy chọn)
    - **date_to**: Tìm đến ngày (tùy chọn)
    """
    try:
        service_client = get_service_supabase_client()
        offset = (request.page - 1) * request.per_page
        
        # Tìm user_id từ email nếu có
        target_user_ids = None
        if request.user_email:
            try:
                users_result = service_client.auth.admin.list_users()
                if hasattr(users_result, 'users'):
                    # Nếu có @ thì tìm exact match, không có @ thì tìm partial match
                    if '@' in request.user_email:
                        matching_users = [user for user in users_result.users if user.email.lower() == request.user_email.lower()]
                    else:
                        matching_users = [user for user in users_result.users if request.user_email.lower() in user.email.lower()]
                    if matching_users:
                        target_user_ids = [user.id for user in matching_users]
                    else:
                        # Không tìm thấy user nào
                        return AdminMessageSearchResponse(
                            messages=[],
                            total_count=0,
                            page=request.page,
                            per_page=request.per_page,
                            search_query=request.query
                        )
            except Exception as e:
                print(f"Lỗi khi tìm user theo email: {e}")
                return AdminMessageSearchResponse(
                    messages=[],
                    total_count=0,
                    page=request.page,
                    per_page=request.per_page,
                    search_query=request.query
                )
        
        # Build base query
        query = service_client.table("messages").select("*, conversations!inner(user_id)", count="exact")
        
        # Add search filter
        if request.query:
            query = query.ilike("content", f"%{request.query}%")
        
        # Add other filters
        if request.conversation_id:
            query = query.eq("conversation_id", request.conversation_id)
        if target_user_ids:
            query = query.in_("conversations.user_id", target_user_ids)
        if request.date_from:
            query = query.gte("created_at", f"{request.date_from} 00:00:00")
        if request.date_to:
            query = query.lte("created_at", f"{request.date_to} 23:59:59")
        
        # Execute query
        result = query.order("created_at", desc=True).range(offset, offset + request.per_page - 1).execute()
        
        messages = []
        for msg in result.data:
            # Lấy thông tin user
            user_email = "Unknown"
            if msg.get("conversations") and msg["conversations"].get("user_id"):
                try:
                    user_result = service_client.auth.admin.get_user_by_id(msg["conversations"]["user_id"])
                    if hasattr(user_result, 'user') and user_result.user:
                        user_email = user_result.user.email
                except:
                    pass
            
            messages.append({
                "message_id": msg.get("message_id"),
                "conversation_id": msg.get("conversation_id"),
                "user_id": msg["conversations"]["user_id"] if msg.get("conversations") else None,
                "user_email": user_email,
                "role": msg.get("role"),
                "content": msg.get("content"),
                "created_at": parse_and_format_vietnam_time(msg.get("created_at", ""))
            })
        
        total_count = result.count if hasattr(result, 'count') else len(messages)
        
        return AdminMessageSearchResponse(
            messages=messages,
            total_count=total_count,
            page=request.page,
            per_page=request.per_page,
            search_query=request.query
        )
        
    except Exception as e:
        print(f"Lỗi khi tìm kiếm messages: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi tìm kiếm messages: {str(e)}"
        )

@app.delete(f"{PREFIX}/admin/conversations/{{conversation_id}}")
async def admin_delete_conversation(
    conversation_id: str = Path(..., description="ID của conversation cần xóa"),
    admin_user=Depends(require_admin_role)
):
    """
    [ADMIN] Xóa một conversation và tất cả messages liên quan
    
    - **conversation_id**: ID của conversation cần xóa
    """
    try:
        service_client = get_service_supabase_client()
        
        # Kiểm tra conversation tồn tại
        conv_result = service_client.table("conversations").select("*").eq("conversation_id", conversation_id).execute()
        if not conv_result.data:
            raise HTTPException(status_code=404, detail="Không tìm thấy conversation")
        
        # Xóa messages trước (do foreign key constraint)
        service_client.table("messages").delete().eq("conversation_id", conversation_id).execute()
        
        # Xóa conversation
        service_client.table("conversations").delete().eq("conversation_id", conversation_id).execute()
        
        print(f"✅ Admin {admin_user.email} đã xóa conversation {conversation_id}")
        
        return {
            "status": "success",
            "message": f"Đã xóa conversation {conversation_id} và tất cả tin nhắn liên quan"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Lỗi khi xóa conversation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi xóa conversation: {str(e)}"
        )

@app.get(f"{PREFIX}/admin/files/stats")
async def admin_get_files_stats(
    admin_user=Depends(require_admin_role)
):
    """
    [ADMIN] Lấy thống kê về files trong hệ thống
    """
    try:
        service_client = get_service_supabase_client()
        
        # Lấy danh sách file từ database
        try:
            from backend.supabase.files_manager import FilesManager
            from backend.supabase.client import SupabaseClient
            
            supabase_client_with_service_role = SupabaseClient(use_service_key=True)
            client = supabase_client_with_service_role.get_client()
            files_manager = FilesManager(client)
            
            # Lấy tất cả file từ database
            db_files = files_manager.get_all_files(include_deleted=False)
            
            # Thống kê theo loại file
            file_types = {}
            file_categories = {}
            total_size = 0
            upload_trend = {}  # Thêm trend upload theo ngày
            
            for file in db_files:
                # Xử lý extension
                ext = os.path.splitext(file.get("filename", ""))[1].lower()
                if ext:
                    file_types[ext] = file_types.get(ext, 0) + 1
                
                # Xử lý category
                metadata = file.get("metadata", {}) or {}
                category = metadata.get("category", "Không phân loại")
                file_categories[category] = file_categories.get(category, 0) + 1
                
                # Tính tổng dung lượng
                file_size = metadata.get("file_size", 0)
                total_size += file_size
                
                # Thống kê upload trend
                upload_time = file.get("upload_time")
                if upload_time:
                    try:
                        parsed_time = parse_and_format_vietnam_time(upload_time)
                        if parsed_time:
                            upload_date = datetime.fromisoformat(parsed_time).date().isoformat()
                            upload_trend[upload_date] = upload_trend.get(upload_date, 0) + 1
                    except Exception as e:
                        print(f"Lỗi khi parse upload_time '{upload_time}': {e}")
                        pass
            
            # Thống kê theo thời gian upload
            today = datetime.now()
            last_7_days = 0
            last_30_days = 0
            
            for file in db_files:
                upload_time = file.get("upload_time")
                if not upload_time:
                    continue
                
                try:
                    # Sử dụng parse_and_format_vietnam_time để đảm bảo format đúng
                    parsed_time = parse_and_format_vietnam_time(upload_time)
                    if parsed_time:
                        upload_date = datetime.fromisoformat(parsed_time)
                        days_diff = (today - upload_date).days
                        
                        if days_diff <= 7:
                            last_7_days += 1
                        if days_diff <= 30:
                            last_30_days += 1
                except Exception as e:
                    print(f"Lỗi khi parse upload_time '{upload_time}': {e}")
                    pass
            
            return {
                "total_files": len(db_files),
                "total_size": total_size,
                "file_types": file_types,
                "file_categories": file_categories,
                "last_7_days": last_7_days,
                "last_30_days": last_30_days,
                "upload_trend": upload_trend,
                "avg_file_size": total_size / len(db_files) if len(db_files) > 0 else 0
            }
            
        except Exception as e:
            print(f"Lỗi khi lấy thống kê files: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Lỗi khi lấy thống kê files: {str(e)}"
            )
            
    except Exception as e:
        print(f"Lỗi không xác định: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi không xác định: {str(e)}"
        )

@app.get(f"{PREFIX}/admin/system/stats")
async def admin_get_system_stats(
    admin_user=Depends(require_admin_role)
):
    """
    [ADMIN] Lấy thống kê tổng quan hệ thống
    """
    try:
        service_client = get_service_supabase_client()
        
        # Thống kê users
        users_result = service_client.auth.admin.list_users()
        total_users = len(users_result.users) if hasattr(users_result, 'users') else 0
        
        # Thống kê người dùng mới theo ngày (7 ngày gần nhất)
        now = datetime.now()
        user_growth = {}
        banned_users = 0
        active_users = 0
        week_ago = now - timedelta(days=7)
        
        if hasattr(users_result, 'users'):
            for user in users_result.users:
                # Đếm banned users
                if calculate_banned_until(user):
                    banned_users += 1
                
                # Đếm active users (đăng nhập trong 7 ngày qua)
                if hasattr(user, 'last_sign_in_at') and user.last_sign_in_at:
                    try:
                        last_signin = datetime.fromisoformat(str(user.last_sign_in_at).replace('Z', '+00:00'))
                        if last_signin > week_ago:
                            active_users += 1
                    except:
                        pass
                
                # Thống kê user growth
                if hasattr(user, 'created_at') and user.created_at:
                    try:
                        created_date = datetime.fromisoformat(str(user.created_at).replace('Z', '+00:00')).date().isoformat()
                        user_growth[created_date] = user_growth.get(created_date, 0) + 1
                    except:
                        pass
        
        # Thống kê conversations
        conv_result = service_client.table("conversations").select("*", count="exact").execute()
        total_conversations = conv_result.count if hasattr(conv_result, 'count') else 0
        
        # Thống kê messages
        msg_result = service_client.table("messages").select("*", count="exact").execute()
        total_messages = msg_result.count if hasattr(msg_result, 'count') else 0
        
        # Thống kê files
        try:
            from backend.supabase.files_manager import FilesManager
            from backend.supabase.client import SupabaseClient
            
            supabase_client_with_service_role = SupabaseClient(use_service_key=True)
            client = supabase_client_with_service_role.get_client()
            files_manager = FilesManager(client)
            
            db_files = files_manager.get_all_files(include_deleted=False)
            total_files = len(db_files)
            total_storage = sum(file.get("metadata", {}).get("file_size", 0) for file in db_files)
        except:
            total_files = 0
            total_storage = 0
        
        # Tính engagement rate
        engagement_rate = 0
        if total_users > 0:
            engagement_rate = round((active_users / total_users) * 100, 2)
        
        # Tính average messages per conversation
        avg_msg_per_conv = 0
        if total_conversations > 0:
            avg_msg_per_conv = round(total_messages / total_conversations, 2)
        
        return {
            "overview": {
                "total_users": total_users,
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "total_files": total_files,
                "total_storage": total_storage
            },
            "user_metrics": {
                "active_users": active_users,
                "banned_users": banned_users,
                "engagement_rate": engagement_rate,
                "user_growth": user_growth
            },
            "activity_metrics": {
                "avg_messages_per_conversation": avg_msg_per_conv,
                "conversations_per_user": round(total_conversations / total_users, 2) if total_users > 0 else 0,
                "messages_per_user": round(total_messages / total_users, 2) if total_users > 0 else 0
            },
            "storage_metrics": {
                "avg_file_size": round(total_storage / total_files, 2) if total_files > 0 else 0,
                "files_per_user": round(total_files / total_users, 2) if total_users > 0 else 0
            }
        }
        
    except Exception as e:
        print(f"Lỗi khi lấy system stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy system stats: {str(e)}"
        )

@app.get(f"{PREFIX}/admin/conversations/stats", response_model=AdminConversationStatsResponse)
async def admin_get_conversation_stats(
    days: int = Query(7, ge=1, le=365, description="Số ngày thống kê"),
    admin_user=Depends(require_admin_role)
):
    """
    [ADMIN] Lấy thống kê về conversations và messages
    
    - **days**: Số ngày để thống kê (mặc định 7 ngày)
    """
    try:
        service_client = get_service_supabase_client()
        
        # Tính ngày bắt đầu thống kê
        start_date = (get_vietnam_time() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Tổng conversations
        total_conv_result = service_client.table("conversations").select("conversation_id", count="exact").execute()
        total_conversations = total_conv_result.count if hasattr(total_conv_result, 'count') else 0
        
        # Tổng messages
        total_msg_result = service_client.table("messages").select("message_id", count="exact").execute()
        total_messages = total_msg_result.count if hasattr(total_msg_result, 'count') else 0
        
        # Tổng users (có conversation)
        unique_users_result = service_client.table("conversations").select("user_id").execute()
        unique_user_ids = set(conv["user_id"] for conv in unique_users_result.data) if unique_users_result.data else set()
        total_users = len(unique_user_ids)
        
        # Conversations by date (7 ngày gần nhất)
        conv_by_date_result = service_client.table("conversations").select("last_updated").gte("last_updated", start_date).execute()
        
        # Group by date
        date_counts = {}
        for conv in conv_by_date_result.data:
            date_str = conv["last_updated"][:10]  # Lấy YYYY-MM-DD
            date_counts[date_str] = date_counts.get(date_str, 0) + 1
        
        conversations_by_date = [
            {"date": date, "count": count}
            for date, count in sorted(date_counts.items())
        ]
        
        # Messages by role
        user_msg_result = service_client.table("messages").select("role", count="exact").eq("role", "user").execute()
        assistant_msg_result = service_client.table("messages").select("role", count="exact").eq("role", "assistant").execute()
        
        messages_by_role = {
            "user": user_msg_result.count if hasattr(user_msg_result, 'count') else 0,
            "assistant": assistant_msg_result.count if hasattr(assistant_msg_result, 'count') else 0
        }
        
        # Top users (by conversation count)
        top_users = []
        user_conv_counts = {}
        for conv in unique_users_result.data:
            user_id = conv["user_id"]
            user_conv_counts[user_id] = user_conv_counts.get(user_id, 0) + 1
        
        # Sort và lấy top 10
        sorted_users = sorted(user_conv_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        for user_id, conv_count in sorted_users:
            try:
                user_result = service_client.auth.admin.get_user_by_id(user_id)
                if hasattr(user_result, 'user') and user_result.user:
                    email = user_result.user.email
                else:
                    email = "Unknown"
            except:
                email = "Unknown"
            
            top_users.append({
                "user_id": user_id,
                "email": email,
                "conversation_count": conv_count
            })
        
        return AdminConversationStatsResponse(
            total_conversations=total_conversations,
            total_messages=total_messages,
            total_users=total_users,
            conversations_by_date=conversations_by_date,
            messages_by_role=messages_by_role,
            top_users=top_users
        )
        
    except Exception as e:
        print(f"Lỗi khi lấy thống kê: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy thống kê: {str(e)}"
        )



# =====================================================================
# END ADMIN CONVERSATION MANAGEMENT APIs  
# =====================================================================

# ==================== LEARNING ANALYTICS ENDPOINTS ====================

@app.get(f"{PREFIX}/learning/dashboard")
async def get_learning_dashboard(
    weeks: int = Query(4, ge=1, le=12, description="Số tuần để hiển thị"),
    current_user=Depends(get_current_user)
):
    """Dashboard học tập cá nhân"""
    try:
        if not analytics_service:
            raise HTTPException(status_code=503, detail="Learning analytics service không khả dụng")
        
        dashboard_data = await analytics_service.get_dashboard_data(current_user.id, weeks)
        return dashboard_data
        
    except Exception as e:
        print(f"Error getting learning dashboard: {e}")
        raise HTTPException(status_code=500, detail="Lỗi khi lấy dashboard học tập")

@app.post(f"{PREFIX}/learning/recommendations/{{recommendation_id}}/dismiss")
async def dismiss_recommendation(
    recommendation_id: str,
    current_user=Depends(get_current_user)
):
    """Ẩn recommendation"""
    try:
        result = supabase_client.table("learning_recommendations").update({
            "status": "dismissed"
        }).eq("recommendation_id", recommendation_id).eq("user_id", current_user.id).execute()
        
        return {"success": True, "message": "Đã ẩn gợi ý"}
        
    except Exception as e:
        print(f"Error dismissing recommendation: {e}")
        raise HTTPException(status_code=500, detail="Lỗi khi ẩn gợi ý")

@app.get(f"{PREFIX}/learning/analytics/{{user_id}}")
async def get_user_analytics(
    user_id: str,
    days: int = Query(30, ge=7, le=365, description="Số ngày để phân tích"),
    current_user=Depends(get_current_user)
):
    """Lấy analytics chi tiết cho user (chỉ user chính hoặc admin)"""
    # Kiểm tra quyền: user chỉ xem analytics của mình, admin xem được tất cả
    if current_user.id != user_id and getattr(current_user, 'role', 'student') != 'admin':
        raise HTTPException(status_code=403, detail="Không có quyền truy cập analytics của user khác")
    
    try:
        # Lấy message analysis trong khoảng thời gian
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        analyses_result = supabase_client.table("message_analysis").select("*").eq(
            "user_id", user_id
        ).gte("analysis_timestamp", start_date.isoformat()).order("analysis_timestamp", desc=True).execute()
        
        return {
            "user_id": user_id,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat(), "days": days},
            "analyses": analyses_result.data,
            "total_analyses": len(analyses_result.data)
        }
        
    except Exception as e:
        print(f"Error getting user analytics: {e}")
        raise HTTPException(status_code=500, detail="Lỗi khi lấy dữ liệu phân tích")

# ==================== ADMIN LEARNING ANALYTICS ====================

@app.get(f"{PREFIX}/admin/learning/overview")
async def admin_get_learning_overview(
    days: int = Query(30, ge=7, le=365, description="Số ngày thống kê"),
    admin_user=Depends(require_admin_role)
):
    """Tổng quan analytics học tập cho admin"""
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Lấy tất cả phân tích trong khoảng thời gian
        analyses_result = supabase_client.table("message_analysis").select("*").gte(
            "analysis_timestamp", start_date.isoformat()
        ).execute()
        
        analyses = analyses_result.data
        
        # Tính toán metrics tổng quan
        total_questions = len(analyses)
        unique_users = len(set(a["user_id"] for a in analyses)) if analyses else 0
        
        # Bloom distribution
        bloom_counts = {}
        for analysis in analyses:
            bloom = analysis["bloom_level"]
            bloom_counts[bloom] = bloom_counts.get(bloom, 0) + 1
        
        # Topic distribution
        topic_counts = {}
        for analysis in analyses:
            topics = analysis.get("topics_detected", [])
            if isinstance(topics, list):
                for topic in topics:
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # User activity
        user_activity = {}
        for analysis in analyses:
            user_id = analysis["user_id"]
            user_activity[user_id] = user_activity.get(user_id, 0) + 1
        
        top_active_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat(), "days": days},
            "overview": {
                "total_questions": total_questions,
                "unique_users": unique_users,
                "avg_questions_per_user": total_questions / unique_users if unique_users > 0 else 0
            },
            "bloom_distribution": bloom_counts,
            "topic_distribution": dict(sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "top_active_users": top_active_users
        }
        
    except Exception as e:
        print(f"Error getting admin learning overview: {e}")
        raise HTTPException(status_code=500, detail="Lỗi khi lấy tổng quan học tập")

if __name__ == "__main__":
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)
