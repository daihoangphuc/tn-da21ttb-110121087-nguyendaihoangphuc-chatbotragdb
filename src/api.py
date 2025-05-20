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
from pydantic import BaseModel, EmailStr, validator
from typing import List, Dict, Optional
import os
import uvicorn
import shutil
from uuid import uuid4
import time
import uuid
import json
from datetime import datetime
from os import path
from dotenv import load_dotenv
import supabase

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

# Đường dẫn lưu phản hồi
FEEDBACK_DIR = os.getenv("FEEDBACK_DIR", "src/feedback")
os.makedirs(FEEDBACK_DIR, exist_ok=True)


# Hàm để lấy đường dẫn thư mục của user
def get_user_upload_dir(user_id: str) -> str:
    """Tạo và trả về đường dẫn thư mục upload cho user cụ thể"""
    user_dir = os.path.join(UPLOAD_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


# Models cho API
class QuestionRequest(BaseModel):
    question: str
    search_type: Optional[str] = "hybrid"  # "semantic", "keyword", "hybrid"
    alpha: Optional[float] = 0.7  # Hệ số kết hợp giữa semantic và keyword search
    sources: Optional[List[str]] = None  # Danh sách các file nguồn cần tìm kiếm
    file_id: Optional[List[str]] = None  # Danh sách các file_id cần tìm kiếm
    conversation_id: Optional[str] = (
        None  # ID phiên hội thoại, tự động tạo nếu không có
    )


class AnswerResponse(BaseModel):
    question_id: str
    question: str
    answer: str
    sources: List[
        Dict
    ]  # Sẽ bao gồm source, page, section, score, content_snippet, original_page
    search_method: str
    total_reranked: Optional[int] = None  # Thêm trường hiển thị số lượng kết quả rerank
    filtered_sources: Optional[List[str]] = None  # Danh sách các file nguồn đã được lọc
    reranker_model: Optional[str] = None  # Model reranker được sử dụng
    processing_time: Optional[float] = None  # Thời gian xử lý (giây)
    debug_info: Optional[Dict] = None  # Thông tin debug bổ sung
    related_questions: Optional[List[str]] = None  # Danh sách các câu hỏi liên quan
    is_low_confidence: Optional[bool] = None  # Trạng thái độ tin cậy thấp
    confidence_score: Optional[float] = None  # Điểm tin cậy của câu trả lời
    query_type: Optional[str] = (
        None  # Loại câu hỏi: question_from_document, realtime_question, other_question
    )


class SQLAnalysisRequest(BaseModel):
    sql_query: str
    database_context: Optional[str] = None


class SQLAnalysisResponse(BaseModel):
    query: str
    analysis: str
    suggestions: List[str]
    optimized_query: Optional[str] = None


class FeedbackRequest(BaseModel):
    question_id: str
    rating: int  # 1-5
    comment: Optional[str] = None
    is_helpful: bool
    specific_feedback: Optional[Dict] = None


class IndexingStatusResponse(BaseModel):
    status: str
    message: str
    processed_files: int


class CategoryStatsResponse(BaseModel):
    total_documents: int
    documents_by_category: Dict[str, int]
    categories: List[str]


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

        # Cập nhật BM25 index sau khi đã index xong tài liệu
        indexing_status["message"] = "Đang cập nhật BM25 index..."
        rag_system.search_manager.update_bm25_index()

        indexing_status["status"] = "completed"
        indexing_status["message"] = (
            f"Đã hoàn thành index {len(processed_chunks)} chunks từ {len(documents)} tài liệu"
        )
    except Exception as e:
        indexing_status["status"] = "error"
        indexing_status["message"] = f"Lỗi khi indexing: {str(e)}"
    finally:
        indexing_status["is_running"] = False


# Lưu phản hồi người dùng
def save_feedback(feedback: Dict):
    try:
        # Tạo tên file dựa vào question_id và timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{feedback['question_id']}_{timestamp}.json"
        filepath = os.path.join(FEEDBACK_DIR, filename)

        # Thêm timestamp vào feedback
        feedback["timestamp"] = datetime.now().isoformat()

        # Lưu feedback vào file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(feedback, f, ensure_ascii=False, indent=4)

        return True
    except Exception as e:
        print(f"Lỗi khi lưu phản hồi: {str(e)}")
        return False


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

    @validator("code", "access_token")
    def check_auth_method(cls, v, values, **kwargs):
        if (
            not any([values.get("code"), values.get("access_token")])
            and len(values) == 2
        ):
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


@app.post(f"{PREFIX}/ask", response_model=AnswerResponse)
async def ask_question(
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
    Đặt câu hỏi và nhận câu trả lời từ hệ thống RAG

    - **question**: Câu hỏi cần trả lời
    - **search_type**: Loại tìm kiếm ("semantic", "keyword", "hybrid")
    - **alpha**: Hệ số kết hợp giữa semantic và keyword search (0.7 = 70% semantic + 30% keyword)
    - **sources**: Danh sách các file nguồn cần tìm kiếm
    - **conversation_id**: ID phiên hội thoại để duy trì ngữ cảnh cuộc hội thoại
    """
    try:
        # Lấy hoặc tạo ID phiên hội thoại
        conversation_id = request.conversation_id
        user_id = current_user.id

        if not conversation_id:
            # Tạo ID phiên mới nếu không có
            conversation_id = f"session_{uuid4().hex[:8]}"

        # Kiểm tra xem người dùng đã chọn nguồn hay chưa
        if not request.sources or len(request.sources) == 0:
            # Lấy danh sách các nguồn có sẵn
            all_docs = rag_system.vector_store.get_all_documents(limit=1000)
            available_sources = set()
            available_filenames = set()  # Tập hợp tên file không có đường dẫn

            for doc in all_docs:
                source = doc.get("metadata", {}).get(
                    "source", doc.get("source", "unknown")
                )
                if source != "unknown":
                    available_sources.add(source)
                    # Thêm tên file đơn thuần
                    if os.path.sep in source:
                        available_filenames.add(os.path.basename(source))
                    else:
                        available_filenames.add(source)

            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Vui lòng chọn ít nhất một nguồn tài liệu để tìm kiếm.",
                    "available_sources": sorted(list(available_sources)),
                    "available_filenames": sorted(list(available_filenames)),
                    "note": "Bạn có thể dùng tên file đơn thuần hoặc đường dẫn đầy đủ",
                },
            )

        # Kiểm tra xem sources có tồn tại không nếu đã chỉ định
        if request.sources and len(request.sources) > 0:
            # Lấy danh sách các nguồn có sẵn
            all_docs = rag_system.vector_store.get_all_documents(limit=1000)
            available_sources = set()
            available_filenames = (
                set()
            )  # Thêm tập hợp để lưu tên file không có đường dẫn

            for doc in all_docs:
                # Lấy nguồn từ cả metadata và direct
                source = doc.get("metadata", {}).get(
                    "source", doc.get("source", "unknown")
                )
                if source != "unknown":
                    available_sources.add(source)
                    # Thêm tên file đơn thuần
                    if os.path.sep in source:
                        available_filenames.add(os.path.basename(source))
                    else:
                        available_filenames.add(source)

            # Kiểm tra xem các nguồn được yêu cầu có tồn tại không (tính cả tên file đơn thuần)
            missing_sources = []
            for s in request.sources:
                # Kiểm tra cả đường dẫn đầy đủ và tên file đơn thuần
                filename = os.path.basename(s) if os.path.sep in s else s
                if s not in available_sources and filename not in available_filenames:
                    missing_sources.append(s)

            if missing_sources:
                return JSONResponse(
                    status_code=404,
                    content={
                        "status": "error",
                        "message": f"Không tìm thấy các nguồn: {', '.join(missing_sources)}",
                        "available_sources": sorted(list(available_sources)),
                        "available_filenames": sorted(list(available_filenames)),
                        "note": "Bạn có thể dùng tên file đơn thuần hoặc đường dẫn đầy đủ",
                    },
                )

        # Tạo ID cho câu hỏi
        question_id = f"q_{uuid4().hex[:8]}"

        # Gọi hệ thống RAG với số lượng kết quả tăng lên
        print(f"Xử lý câu hỏi: '{request.question}'")
        print(f"Phương pháp tìm kiếm: {request.search_type}")
        print(f"Alpha: {request.alpha}")

        # Lấy thông tin model reranker đang sử dụng
        reranker_info = getattr(
            rag_system.search_manager, "reranker_model_name", "unknown"
        )

        # Bắt đầu đo thời gian xử lý
        start_time = time.time()

        # Thêm tin nhắn người dùng vào bộ nhớ hội thoại
        conversation_manager.add_user_message(
            conversation_id, request.question, user_id=user_id
        )

        # Lấy lịch sử hội thoại để sử dụng trong prompt
        conversation_history = conversation_manager.format_for_prompt(conversation_id)
        print(f"Lịch sử hội thoại: {conversation_history}")

        # Gọi RAG để lấy kết quả, kèm theo lịch sử hội thoại
        result = rag_system.query_with_sources(
            request.question,
            search_type=request.search_type,
            alpha=request.alpha,
            sources=request.sources,
            conversation_history=conversation_history,
        )

        # Thêm câu trả lời của AI vào bộ nhớ hội thoại
        conversation_manager.add_ai_message(
            conversation_id, result["answer"], user_id=user_id
        )

        # Tạo các câu hỏi liên quan sau khi có kết quả
        related_questions = await rag_system.generate_related_questions(
            request.question, result["answer"]
        )

        # Thêm các câu hỏi liên quan vào kết quả
        result["related_questions"] = related_questions

        # Kết thúc đo thời gian
        elapsed_time = time.time() - start_time

        # Thêm question_id và thông tin reranker vào kết quả
        result["question_id"] = question_id
        result["reranker_model"] = reranker_info
        result["processing_time"] = round(elapsed_time, 2)
        result["conversation_id"] = conversation_id  # Trả về conversation_id cho client

        # Thêm thông tin số lượng kết quả được rerank vào debug info
        debug_info = {
            "search_type": request.search_type,
            "alpha": request.alpha,
            "reranker_model": reranker_info,
            "total_reranked": result.get("total_reranked", 0),
            "elapsed_time_seconds": round(elapsed_time, 2),
        }
        result["debug_info"] = debug_info

        # Giới hạn số lượng nguồn trả về theo tham số nếu người dùng yêu cầu
        if max_sources and result["sources"] and len(result["sources"]) > max_sources:
            result["sources"] = result["sources"][:max_sources]

        # Lưu vào lịch sử
        questions_history[question_id] = {
            "question": request.question,
            "search_type": request.search_type,
            "alpha": request.alpha,
            "sources": request.sources,
            "timestamp": datetime.now().isoformat(),
            "answer": result["answer"],
            "debug_info": debug_info,
            "conversation_id": conversation_id,  # Lưu conversation_id vào lịch sử
        }

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý câu hỏi: {str(e)}")


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
    - **search_type**: Loại tìm kiếm ("semantic", "keyword", "hybrid")
    - **alpha**: Hệ số kết hợp giữa semantic và keyword search (0.7 = 70% semantic + 30% keyword)
    - **file_id**: Danh sách các file_id của tài liệu cần tìm kiếm (thay thế sources)
    - **current_conversation_id**: ID phiên hội thoại để duy trì ngữ cảnh cuộc hội thoại
    - **max_sources**: Số lượng nguồn tham khảo tối đa trả về (query parameter)
    """
    try:
        # Lấy hoặc tạo ID phiên hội thoại

        user_id = current_user.id

        # Đặt collection_name cho vector store
        rag_system.vector_store.collection_name = "user_" + str(user_id)

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
                    search_type=request.search_type,
                    alpha=request.alpha,
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
                                "search_type": request.search_type,
                                "alpha": request.alpha,
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
    Tải lên một tài liệu để thêm vào hệ thống và tự động xử lý/index
    """
    try:
        # Kiểm tra phần mở rộng file
        ext = os.path.splitext(file.filename)[1].lower()
        allowed_extensions = [".pdf", ".docx", ".txt", ".sql"]

        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Định dạng file không được hỗ trợ. Chấp nhận: {', '.join(allowed_extensions)}",
            )

        # Lấy thư mục upload của user
        user_upload_dir = get_user_upload_dir(current_user.id)

        # Lưu file vào thư mục của user
        file_location = os.path.join(user_upload_dir, file.filename)
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Xử lý metadata bổ sung (nếu có)
        metadata = {}
        if category:
            metadata["category"] = category

        # Xử lý file vừa tải lên
        print(f"Bắt đầu xử lý file {file.filename}...")

        # Tải tài liệu bằng loader thích hợp
        if category:
            documents = rag_system.document_processor.load_document_with_category(
                file_location, category
            )
        else:
            ext = os.path.splitext(file_location)[1].lower()
            if ext in rag_system.document_processor.loaders:
                loader = rag_system.document_processor.loaders[ext](file_location)
                documents = loader.load()
            else:
                return {
                    "filename": file.filename,
                    "status": "error",
                    "message": f"Không hỗ trợ định dạng {ext}",
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

            # Lưu thông tin file vào bảng document_files
            try:
                from src.supabase.files_manager import FilesManager
                from src.supabase.client import SupabaseClient

                client = SupabaseClient().get_client()
                files_manager = FilesManager(client)

                # Lấy kích thước file
                file_stats = os.stat(file_location)

                # Lưu metadata
                file_metadata = {
                    "category": category,
                    "chunks_count": len(processed_chunks),
                    "file_size": file_stats.st_size,  # Đưa kích thước file vào metadata thay vì trường riêng
                }

                # Lưu thông tin file vào database
                files_manager.save_file_metadata(
                    file_id=file_id,
                    filename=file.filename,
                    file_path=file_location,
                    user_id=current_user.id,
                    file_type=ext,
                    metadata=file_metadata,
                )
                print(
                    f"[UPLOAD] Đã lưu thông tin file {file.filename} vào bảng document_files"
                )
            except Exception as e:
                print(f"[UPLOAD] Lỗi khi lưu thông tin file vào database: {str(e)}")

            return {
                "filename": file.filename,
                "status": "success",
                "message": f"Đã tải lên và index thành công {len(processed_chunks)} chunks từ tài liệu",
                "chunks_count": len(processed_chunks),
                "category": category,
                "file_id": file_id,
            }
        else:
            return {
                "filename": file.filename,
                "status": "warning",
                "message": "Tài liệu đã được tải lên nhưng không thể tạo chunks",
                "category": category,
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
    Lấy danh sách các file đã được upload vào hệ thống
    """
    try:
        from src.supabase.files_manager import FilesManager
        from src.supabase.client import SupabaseClient

        # Sử dụng FilesManager để lấy danh sách file từ database
        client = SupabaseClient().get_client()
        files_manager = FilesManager(client)

        # Lấy danh sách file của người dùng hiện tại từ bảng document_files
        db_files = files_manager.get_files_by_user(
            current_user.id, include_deleted=False
        )
        print(
            f"[FILES] Tìm thấy {len(db_files)} file của user {current_user.id} trong database"
        )

        files = []

        if db_files:
            for file_record in db_files:
                # Convert từ dữ liệu database sang model FileInfo
                file_path = file_record.get("file_path", "")
                filename = file_record.get("filename", "")
                extension = os.path.splitext(filename)[1].lower() if filename else ""
                upload_time = file_record.get("upload_time", "")

                # Lấy metadata
                metadata = file_record.get("metadata", {}) or {}
                category = metadata.get("category", None)
                # Lấy kích thước file từ metadata hoặc mặc định là 0
                file_size = metadata.get("file_size", 0)

                files.append(
                    FileInfo(
                        filename=filename,
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
        file_path = os.path.join(user_upload_dir, filename)
        print(f"[DELETE] Bắt đầu xóa file: {filename}, đường dẫn: {file_path}")

        # Kiểm tra file có tồn tại không
        if not os.path.exists(file_path):
            print(f"[DELETE] Lỗi: File {filename} không tồn tại")
            raise HTTPException(
                status_code=404, detail=f"File {filename} không tồn tại"
            )

        print(f"[DELETE] Đang xóa các điểm dữ liệu liên quan đến file: {filename}")

        # Tạo danh sách các biến thể của đường dẫn file để thử xóa
        file_paths = [
            file_path,  # Đường dẫn đầy đủ
            file_path.replace("\\", "/"),  # Đường dẫn với dấu /
            os.path.join(user_upload_dir, filename).replace(
                "\\", "/"
            ),  # Đường dẫn đầy đủ với dấu /
            f"src/data/{current_user.id}/{filename}",  # Thêm tiền tố src/data/user_id/
            f"src/data\\{current_user.id}\\{filename}",  # Thêm tiền tố src/data\user_id\ với backslash
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

        # Nếu không thành công với tất cả các đường dẫn, thử xóa bằng filename
        if not deletion_success:
            print(f"[DELETE] Thử xóa với tên file: {filename}")
            try:
                # Sử dụng phương thức delete_by_file_path với tên file
                success, message = rag_system.vector_store.delete_by_file_path(
                    filename, user_id=current_user.id
                )

                if success:
                    # Phân tích số lượng điểm đã xóa từ message
                    import re

                    match = re.search(r"Đã xóa (\d+) điểm", message)
                    if match:
                        deleted_points_count = int(match.group(1))
                    print(f"[DELETE] Xóa thành công với tên file: {message}")
                    deletion_success = True
            except Exception as e:
                print(f"[DELETE] Lỗi khi xóa với tên file: {str(e)}")

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

                # So sánh với tên file
                if meta_source == filename or direct_source == filename:
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

                # Thêm điều kiện cho filename
                filter_conditions.append(
                    {"key": "source", "match": {"value": filename}}
                )
                filter_conditions.append(
                    {"key": "metadata.source", "match": {"value": filename}}
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

        # Xóa file vật lý
        print(f"[DELETE] Đang xóa file vật lý: {file_path}")
        os.remove(file_path)
        print(f"[DELETE] Đã xóa file vật lý thành công")

        # Đánh dấu file đã xóa trong bảng document_files
        try:
            from src.supabase.files_manager import FilesManager
            from src.supabase.client import SupabaseClient

            client = SupabaseClient().get_client()
            files_manager = FilesManager(client)

            # Tìm file trong database theo tên và user_id
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
            "filename": filename,
            "status": "success",
            "message": f"Đã xóa file {filename} và {deleted_points_count} index liên quan",
            "removed_points": deleted_points_count,
        }
    except HTTPException as e:
        print(f"[DELETE] HTTP Exception: {str(e)}")
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lỗi khi đăng nhập: {str(e)}",
        )


@app.post(f"{PREFIX}/auth/logout")
async def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_bearer),
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


if __name__ == "__main__":
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
