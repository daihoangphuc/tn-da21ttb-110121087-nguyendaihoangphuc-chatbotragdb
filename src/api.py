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
from datetime import datetime
from os import path
from dotenv import load_dotenv
import supabase
import re
import asyncio

from src.rag import AdvancedDatabaseRAG
from src.supabase.conversation_manager import SupabaseConversationManager

# Load biến môi trường từ .env
load_dotenv()

# Thêm prefix API
PREFIX = os.getenv("API_PREFIX", "/api")
from src.suggestion_manager import SuggestionManager

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

# Khởi tạo hệ thống RAG
rag_system = AdvancedDatabaseRAG()

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

# Đường dẫn lưu dữ liệu tạm thời
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "src/data")
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
    sources: Optional[List[str]] = None  # Danh sách các file nguồn cần tìm kiếm
    file_id: Optional[List[str]] = None  # Danh sách các file_id cần tìm kiếm
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
    - **file_id**: Danh sách các file_id của tài liệu cần tìm kiếm (thay thế sources)
    - **current_conversation_id**: ID phiên hội thoại để duy trì ngữ cảnh cuộc hội thoại
    - **max_sources**: Số lượng nguồn tham khảo tối đa trả về (query parameter)
    """
    try:
        # Lấy hoặc tạo ID phiên hội thoại

        user_id = current_user.id

        # Đặt collection_name cho vector store
        rag_system.vector_store.collection_name = "user_" + str(user_id)
        # Cập nhật user_id cho vector_store trong SearchManager
        rag_system.vector_store.user_id = user_id
        # # QUAN TRỌNG: Cập nhật SearchManager.vector_store và tải BM25 index cho user hiện tại
        # rag_system.search_manager.set_vector_store_and_reload_bm25(rag_system.vector_store)
        # print(f"Đã cập nhật SearchManager vector_store và BM25 index cho user_id={user_id}")

        # Kiểm tra xem người dùng đã chọn file_id hay chưa
        if (
            not hasattr(request, "file_id")
            or not request.file_id
            or len(request.file_id) == 0
        ):
            # Lấy danh sách các file_id có sẵn từ bảng document_files
            try:
                from src.supabase.files_manager import FilesManager
                from src.supabase.client import SupabaseClient

                client = SupabaseClient().get_client()
                files_manager = FilesManager(client)

                # Lấy danh sách file của người dùng
                files = files_manager.get_files_by_user(
                    current_user.id, include_deleted=False
                )
                available_file_ids = [file.get("file_id") for file in files]
                available_filenames = [
                    (file.get("filename"), file.get("file_id")) for file in files
                ]

                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Vui lòng chọn ít nhất một file_id để tìm kiếm.",
                        "available_file_ids": available_file_ids,
                        "available_files": available_filenames,
                    },
                )
            except Exception as e:
                print(f"Lỗi khi lấy danh sách file_id: {str(e)}")
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Vui lòng chọn ít nhất một file_id để tìm kiếm.",
                    },
                )

        # Tạo ID cho câu hỏi
        question_id = f"q_{uuid4().hex[:8]}"

        # Thêm tin nhắn người dùng vào bộ nhớ hội thoại
        conversation_manager.add_user_message(
            conversation_manager.get_current_conversation_id(),
            request.question,
            user_id=user_id,
        )

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
                # Gọi RAG để lấy kết quả dạng stream với file_id thay vì sources
                stream_generator = rag_system.query_with_sources_streaming(
                    request.question,
                    file_id=request.file_id,  # Sử dụng file_id thay cho sources
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
                                "file_id": request.file_id,  # Lưu file_id thay vì sources
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
    Upload tài liệu và index vào vector database

    - **file**: File cần upload (PDF, DOCX, TXT)
    - **category**: Danh mục của tài liệu (tùy chọn)
    """
    try:
        # Tạo thư mục upload cho user nếu chưa tồn tại
        user_id = current_user.id
        upload_dir = os.getenv("UPLOAD_DIR", "src/data")
        user_dir = os.path.join(upload_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)

        # Lưu file vào thư mục uploads
        file_name = file.filename
        original_file_name = file_name  # Lưu tên file gốc
        file_path = os.path.join(user_dir, file_name)
        original_file_path = file_path  # Lưu đường dẫn file gốc
        
        # Cập nhật user_id cho vector_store
        rag_system.vector_store.user_id = user_id
        # Đặt collection_name cho vector store
        rag_system.vector_store.collection_name = "user_" + str(user_id)
        
        # Lưu ý: Không cập nhật SearchManager.vector_store ở đây
        # Sẽ cập nhật sau khi đã index dữ liệu thành công

        with open(file_path, "wb+") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"[UPLOAD] Đã lưu file {file_name} vào {file_path}")

        # Xác định loại file
        file_extension = os.path.splitext(file_name)[1].lower()
        original_file_extension = file_extension  # Lưu phần mở rộng file gốc
        file_type = None
        
        # Đọc nội dung file và xử lý
        documents = None
        try:
            # Sử dụng DocumentProcessor thay vì các hàm riêng lẻ
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

        # Index lên vector store
        if processed_chunks:
            # Tạo embeddings cho các chunks
            texts = [chunk["text"] for chunk in processed_chunks]
            embeddings = rag_system.embedding_model.encode(texts)

            # Đảm bảo collection đã tồn tại với kích thước vector đúng
            rag_system.vector_store.ensure_collection_exists(len(embeddings[0]))

            # Index embeddings với user_id của người dùng hiện tại
            print(
                f"[UPLOAD] Đang index {len(processed_chunks)} chunks với user_id='{current_user.id}'"
            )
            file_id = str(uuid.uuid4())
            rag_system.vector_store.index_documents(
                processed_chunks,
                embeddings,
                user_id=current_user.id,
                file_id=file_id,
            )
            
            # Lưu thông tin file vào bảng document_files trong Supabase
            try:
                from src.supabase.files_manager import FilesManager
                from src.supabase.client import SupabaseClient
                
                # Lấy kích thước file gốc
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                if file_size == 0 and os.path.exists(original_file_path):
                    file_size = os.path.getsize(original_file_path)
                
                # Tạo metadata
                metadata = {
                    "category": category,
                    "file_size": file_size,
                    "chunks_count": len(processed_chunks),
                    "is_indexed": True,
                    "last_indexed": datetime.now().isoformat(),
                    "original_file_name": original_file_name,
                    "original_extension": original_file_extension,
                    "converted_to_pdf": original_file_extension != ".pdf" and file_extension == ".pdf"
                }
                
                # Lưu thông tin file vào Supabase
                client = SupabaseClient().get_client()
                files_manager = FilesManager(client)
                
                # Lưu metadata vào Supabase - sử dụng tên file gốc
                save_result = files_manager.save_file_metadata(
                    file_id=file_id,
                    filename=original_file_name,  # Sử dụng tên file gốc
                    file_path=file_path,  # Vẫn lưu đường dẫn file đã chuyển đổi để xử lý
                    user_id=user_id,
                    file_type=file_type,  # Loại file gốc
                    metadata=metadata
                )
                
                print(f"[UPLOAD] Đã lưu thông tin file vào Supabase với file_id={file_id}")
            except Exception as e:
                print(f"[UPLOAD] Lỗi khi lưu thông tin file vào Supabase: {str(e)}")
                # Không dừng quá trình nếu lưu vào Supabase thất bại

        return {
            "filename": original_file_name,  # Trả về tên file gốc
            "status": "success",
            "message": f"Đã tải lên và index thành công {len(processed_chunks)} chunks từ tài liệu",
            "chunks_count": len(processed_chunks),
            "category": category,
            "file_id": file_id,
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
        sample_embedding = rag_system.embedding_model.encode(["Sample text"])
        vector_size = len(sample_embedding[0])

        # Tạo lại collection mới
        rag_system.vector_store.ensure_collection_exists(vector_size)

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
    Lấy danh sách các file đã upload của người dùng hiện tại

    Returns:
        Danh sách các file đã upload
    """
    try:
        files = []
        user_id = current_user.id

        # Lấy danh sách file từ database
        try:
            from src.supabase.files_manager import FilesManager
            from src.supabase.client import SupabaseClient

            client = SupabaseClient().get_client()
            files_manager = FilesManager(client)

            # Lấy danh sách file từ database
            db_files = files_manager.get_files_by_user(user_id)
            print(f"[FILES] Tìm thấy {len(db_files)} file của user {user_id} trong database")
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
            # Fallback: Nếu không có dữ liệu trong database, đọc từ filesystem
            print(f"[FILES] Không tìm thấy dữ liệu trong database, đọc từ filesystem")
            user_upload_dir = get_user_upload_dir(current_user.id)

            # Kiểm tra thư mục có tồn tại không
            if os.path.exists(user_upload_dir):
                for filename in os.listdir(user_upload_dir):
                    file_path = os.path.join(user_upload_dir, filename)

                    # Bỏ qua các thư mục
                    if os.path.isdir(file_path):
                        continue

                    # Lấy thông tin file
                    file_stats = os.stat(file_path)
                    extension = os.path.splitext(filename)[1].lower()

                    # Lấy thời gian tạo file
                    created_time = datetime.fromtimestamp(
                        file_stats.st_ctime
                    ).isoformat()

                    # Thêm vào danh sách
                    files.append(
                        FileInfo(
                            filename=filename,
                            path=file_path,
                            size=file_stats.st_size,
                            upload_date=created_time,
                            extension=extension,
                            category=None,
                            id=None,
                        )
                    )

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
    Xóa file đã upload và các index liên quan trong vector store
    """
    try:
        # Lấy thư mục upload của user
        user_upload_dir = get_user_upload_dir(current_user.id)
        
        # **LOGIC MỚI: Chuyển đổi tên file sang PDF nếu cần**
        original_ext = os.path.splitext(filename)[1].lower()
        
        if original_ext == ".pdf":
            # File gốc đã là PDF
            actual_filename = filename
        else:
            # File gốc không phải PDF, chuyển sang tên file PDF
            base_name = os.path.splitext(filename)[0]
            actual_filename = f"{base_name}.pdf"
            print(f"[DELETE] Chuyển đổi tên file từ {filename} thành {actual_filename}")
        
        # Sử dụng file thực tế để kiểm tra và xóa
        file_path = os.path.join(user_upload_dir, actual_filename)
        print(f"[DELETE] Bắt đầu xóa file: {filename}, đường dẫn thực tế: {file_path}")

        # Kiểm tra file có tồn tại không
        if not os.path.exists(file_path):
            print(f"[DELETE] Lỗi: File {actual_filename} không tồn tại")
            raise HTTPException(
                status_code=404, detail=f"File {filename} không tồn tại"
            )

        print(f"[DELETE] Đang xóa các điểm dữ liệu liên quan đến file: {filename}")

        # **CẬP NHẬT: Tạo danh sách các biến thể với cả tên gốc và tên PDF**
        file_paths = [
            file_path,  # Đường dẫn file thực tế (PDF)
            file_path.replace("\\", "/"),  # Đường dẫn với dấu /
            os.path.join(user_upload_dir, actual_filename).replace("\\", "/"),  # Đường dẫn đầy đủ với dấu /
            f"src/data/{current_user.id}/{actual_filename}",  # Tiền tố src/data/user_id/ với file PDF
            f"src/data\\{current_user.id}\\{actual_filename}",  # Tiền tố src/data\user_id\ với backslash
            # Thêm các biến thể cho tên file gốc (trong trường hợp vector store lưu tên gốc)
            os.path.join(user_upload_dir, filename),
            os.path.join(user_upload_dir, filename).replace("\\", "/"),
            f"src/data/{current_user.id}/{filename}",
            f"src/data\\{current_user.id}\\{filename}",
        ]

        # Khởi tạo biến để lưu số lượng điểm đã xóa
        deleted_points_count = 0
        deletion_success = False

        # Thử xóa với từng đường dẫn
        for path in file_paths:
            print(f"[DELETE] Thử xóa với đường dẫn: {path}")
            try:
                # Sử dụng phương thức delete_by_file_path
                success, message = rag_system.vector_store.delete_by_file_path(
                    path, user_id=current_user.id
                )

                if success:
                    # Phân tích số lượng điểm đã xóa từ message
                    import re

                    match = re.search(r"Đã xóa (\d+) điểm", message)
                    if match:
                        deleted_points_count = int(match.group(1))
                    print(f"[DELETE] Xóa thành công với đường dẫn {path}: {message}")
                    deletion_success = True
                    break
            except Exception as e:
                print(f"[DELETE] Lỗi khi xóa với đường dẫn {path}: {str(e)}")
                continue

        # **CẬP NHẬT: Thử xóa với cả tên file gốc và tên file PDF**
        if not deletion_success:
            filenames_to_try = [filename, actual_filename]  # Thử cả tên gốc và tên PDF
            
            for fname in filenames_to_try:
                print(f"[DELETE] Thử xóa với tên file: {fname}")
                try:
                    # Sử dụng phương thức delete_by_file_path với tên file
                    success, message = rag_system.vector_store.delete_by_file_path(
                        fname, user_id=current_user.id
                    )

                    if success:
                        # Phân tích số lượng điểm đã xóa từ message
                        import re

                        match = re.search(r"Đã xóa (\d+) điểm", message)
                        if match:
                            deleted_points_count = int(match.group(1))
                        print(f"[DELETE] Xóa thành công với tên file: {message}")
                        deletion_success = True
                        break
                except Exception as e:
                    print(f"[DELETE] Lỗi khi xóa với tên file {fname}: {str(e)}")
                    continue

        # Nếu vẫn không thành công, thử xóa bằng phương thức cũ
        if not deletion_success:
            print(f"[DELETE] Thử xóa bằng phương thức cũ...")

            # Tìm tất cả tài liệu khớp với đường dẫn hoặc tên file
            all_docs = rag_system.vector_store.get_all_documents(
                user_id=current_user.id
            )
            related_docs = []

            for doc in all_docs:
                # Kiểm tra trong metadata.source và source trực tiếp
                meta_source = doc.get("metadata", {}).get("source", "unknown")
                direct_source = doc.get("source", "unknown")

                # So sánh với tất cả các biến thể của đường dẫn
                for path in file_paths:
                    if meta_source == path or direct_source == path:
                        related_docs.append(doc)
                        break

                # **CẬP NHẬT: So sánh với cả tên file gốc và tên file PDF**
                if meta_source == filename or direct_source == filename or \
                   meta_source == actual_filename or direct_source == actual_filename:
                    related_docs.append(doc)

            # Nếu tìm thấy tài liệu liên quan, xóa chúng
            if related_docs:
                print(f"[DELETE] Tìm thấy {len(related_docs)} tài liệu liên quan")

                # Thử xóa bằng filter
                filter_conditions = []

                # Thêm điều kiện cho source
                for path in file_paths:
                    filter_conditions.append(
                        {"key": "source", "match": {"value": path}}
                    )
                    filter_conditions.append(
                        {"key": "metadata.source", "match": {"value": path}}
                    )

                # **CẬP NHẬT: Thêm điều kiện cho cả tên file gốc và tên file PDF**
                for fname in [filename, actual_filename]:
                    filter_conditions.append(
                        {"key": "source", "match": {"value": fname}}
                    )
                    filter_conditions.append(
                        {"key": "metadata.source", "match": {"value": fname}}
                    )

                filter_request = {"filter": {"should": filter_conditions}}

                try:
                    success, message = rag_system.vector_store.delete_points_by_filter(
                        filter_request, user_id=current_user.id
                    )

                    if success:
                        # Phân tích số lượng điểm đã xóa từ message
                        import re

                        match = re.search(r"Đã xóa (\d+) điểm", message)
                        if match:
                            deleted_points_count = int(match.group(1))
                        print(f"[DELETE] Xóa thành công bằng filter: {message}")
                        deletion_success = True
                except Exception as e:
                    print(f"[DELETE] Lỗi khi xóa bằng filter: {str(e)}")

                    # Nếu không thành công với filter, thử xóa bằng ID
                    try:
                        point_ids = [
                            doc.get("id")
                            for doc in related_docs
                            if doc.get("id") is not None
                        ]
                        if point_ids:
                            delete_result = rag_system.vector_store.delete_points(
                                point_ids, user_id=current_user.id
                            )
                            if delete_result:
                                deleted_points_count = len(point_ids)
                                print(
                                    f"[DELETE] Đã xóa {deleted_points_count} điểm dữ liệu bằng ID"
                                )
                                deletion_success = True
                    except Exception as e2:
                        print(f"[DELETE] Lỗi khi xóa bằng ID: {str(e2)}")

        # **XÓA FILE VẬT LÝ - Sử dụng đường dẫn file thực tế**
        print(f"[DELETE] Đang xóa file vật lý: {file_path}")
        os.remove(file_path)
        print(f"[DELETE] Đã xóa file vật lý thành công")

        # Đánh dấu file đã xóa trong bảng document_files (sử dụng tên file gốc)
        try:
            from src.supabase.files_manager import FilesManager
            from src.supabase.client import SupabaseClient

            client = SupabaseClient().get_client()
            files_manager = FilesManager(client)

            # Tìm file trong database theo tên gốc và user_id
            files = files_manager.get_file_by_name_and_user(filename, current_user.id)
            if files and len(files) > 0:
                # Lấy file_id từ kết quả tìm kiếm
                file_id = files[0].get("file_id")
                if file_id:
                    # Xóa vĩnh viễn file khỏi database thay vì chỉ đánh dấu đã xóa
                    files_manager.delete_file_permanently(file_id)
                    print(
                        f"[DELETE] Đã xóa vĩnh viễn file {filename} (ID: {file_id}) khỏi database"
                    )
        except Exception as e:
            print(f"[DELETE] Lỗi khi đánh dấu file đã xóa trong database: {str(e)}")

        return {
            "filename": filename,  # Trả về tên file gốc
            "status": "success",
            "message": f"Đã xóa file {filename} và {deleted_points_count} index liên quan",
            "removed_points": deleted_points_count,
        }
    except HTTPException as e:
        print(f"[DELETE] HTTP Exception: {e.detail}")
        raise e
    except Exception as e:
        print(f"[DELETE] Lỗi không xác định: {str(e)}")
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


@app.get(f"{PREFIX}/conversations")
async def get_all_conversations(
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    page_size: int = Query(10, ge=1, le=50, description="Số lượng hội thoại mỗi trang"),
    current_user=Depends(get_current_user),
):
    """
    Lấy danh sách tất cả các hội thoại đã lưu trữ

    Trả về danh sách các phiên hội thoại với thông tin cơ bản, có hỗ trợ phân trang
    """
    try:
        user_id = current_user.id

        # Sử dụng SupabaseConversationManager để lấy danh sách hội thoại
        all_conversations = conversation_manager.get_conversations(user_id)

        # Kiểm tra nếu không có hội thoại nào
        if not all_conversations:
            return {
                "status": "success",
                "message": "Không có hội thoại nào",
                "data": [],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_items": 0,
                    "total_pages": 0,
                },
            }

        # Thêm user_id vào từng hội thoại để client có thể lọc
        for conv in all_conversations:
            conv["user_id"] = user_id

        # Thực hiện phân trang
        total_items = len(all_conversations)
        total_pages = (total_items + page_size - 1) // page_size

        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_items)

        conversations = all_conversations[start_idx:end_idx]

        return {
            "status": "success",
            "message": f"Đã tìm thấy {total_items} hội thoại",
            "data": conversations,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi lấy danh sách hội thoại: {str(e)}"
        )


@app.get(f"{PREFIX}/conversations/{{conversation_id}}")
async def get_conversation_detail(
    conversation_id: str = Path(..., description="ID phiên hội thoại cần lấy chi tiết"),
    current_user=Depends(get_current_user),
):
    """
    Lấy chi tiết hội thoại cho một phiên cụ thể

    - **conversation_id**: ID phiên hội thoại cần lấy chi tiết
    """
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
            "last_updated": datetime.now().isoformat(),
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
            },
            "access_token": result.session.access_token if result.session else "",
            "expires_in": result.session.expires_in if result.session else None,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lỗi khi đăng ký tài khoản: {str(e)}",
        )


@app.post(f"{PREFIX}/auth/login", response_model=AuthResponse)
async def login(request: UserLoginRequest, response: Response):
    """
    Đăng nhập với email và mật khẩu

    - **email**: Email đăng nhập
    - **password**: Mật khẩu đăng nhập
    """
    if not supabase_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ xác thực chưa được cấu hình",
        )

    try:
        print(f"Đang đăng nhập với email: {request.email}")
        result = supabase_client.auth.sign_in_with_password(
            {"email": request.email, "password": request.password}
        )

        if not result.user or not result.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Đăng nhập thất bại, kiểm tra lại email và mật khẩu",
            )

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
            },
            "access_token": result.session.access_token,
            "expires_in": result.session.expires_in,
        }
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
    Lấy danh sách tất cả cuộc hội thoại của người dùng hiện tại

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

        # Lấy tổng số hội thoại
        count_result = (
            await supabase_client.table("conversations")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .execute()
        )

        total_items = count_result.count if hasattr(count_result, "count") else 0

        # Lấy danh sách hội thoại có phân trang
        conversations = (
            await supabase_client.table("conversations")
            .select("*")
            .eq("user_id", user_id)
            .order("last_updated", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )

        # Lấy tin nhắn đầu tiên cho mỗi hội thoại
        for conv in conversations.data:
            first_message = (
                await supabase_client.table("messages")
                .select("content")
                .eq("conversation_id", conv["conversation_id"])
                .eq("role", "user")
                .order("sequence")
                .limit(1)
                .execute()
            )

            conv["first_message"] = (
                first_message.data[0]["content"] if first_message.data else ""
            )

            # Đếm số tin nhắn trong hội thoại
            message_count = (
                await supabase_client.table("messages")
                .select("*", count="exact")
                .eq("conversation_id", conv["conversation_id"])
                .execute()
            )

            conv["message_count"] = (
                message_count.count if hasattr(message_count, "count") else 0
            )

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
        print(f"Lỗi khi lấy danh sách hội thoại: {str(e)}")
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
        suggestions = suggestion_manager.get_suggestions_from_latest_conversation(
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

if __name__ == "__main__":
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
