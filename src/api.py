from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Form,
    HTTPException,
    BackgroundTasks,
    Depends,
    Query,
)
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import uvicorn
import shutil
from uuid import uuid4
import time
import json
from datetime import datetime
from os import path
from dotenv import load_dotenv

from src.rag import AdvancedDatabaseRAG

# Load biến môi trường từ .env
load_dotenv()

# Thêm prefix API
PREFIX = os.getenv("API_PREFIX", "/api")

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

# Đường dẫn lưu dữ liệu tạm thời
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "src/data")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Đường dẫn lưu phản hồi
FEEDBACK_DIR = os.getenv("FEEDBACK_DIR", "src/feedback")
os.makedirs(FEEDBACK_DIR, exist_ok=True)


# Models cho API
class QuestionRequest(BaseModel):
    question: str
    search_type: Optional[str] = "hybrid"  # "semantic", "keyword", "hybrid"
    alpha: Optional[float] = 0.7  # Hệ số kết hợp giữa semantic và keyword search
    sources: Optional[List[str]] = None  # Danh sách các file nguồn cần tìm kiếm


class AnswerResponse(BaseModel):
    question_id: str
    question: str
    answer: str
    sources: List[Dict]  # Sẽ bao gồm source, page, section, score, content_snippet
    search_method: str
    total_reranked: Optional[int] = None  # Thêm trường hiển thị số lượng kết quả rerank
    filtered_sources: Optional[List[str]] = None  # Danh sách các file nguồn đã được lọc
    reranker_model: Optional[str] = None  # Model reranker được sử dụng
    processing_time: Optional[float] = None  # Thời gian xử lý (giây)
    debug_info: Optional[Dict] = None  # Thông tin debug bổ sung


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


class FileListResponse(BaseModel):
    total_files: int
    files: List[FileInfo]


class FileDeleteResponse(BaseModel):
    filename: str
    status: str
    message: str
    removed_points: Optional[int] = None


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
):
    """
    Đặt câu hỏi và nhận câu trả lời từ hệ thống RAG

    - **question**: Câu hỏi cần trả lời
    - **search_type**: Loại tìm kiếm ("semantic", "keyword", "hybrid")
    - **alpha**: Hệ số kết hợp giữa semantic và keyword search (0.7 = 70% semantic + 30% keyword)
    - **sources**: Danh sách các file nguồn cần tìm kiếm, có thể là tên file đơn thuần hoặc đường dẫn đầy đủ
    - **max_sources**: Số lượng nguồn tham khảo tối đa trả về (query parameter)
    """
    try:
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

        # Gọi RAG để lấy kết quả
        result = rag_system.query_with_sources(
            request.question,
            search_type=request.search_type,
            alpha=request.alpha,
            sources=request.sources,
        )

        # Kết thúc đo thời gian
        elapsed_time = time.time() - start_time

        # Thêm question_id và thông tin reranker vào kết quả
        result["question_id"] = question_id
        result["reranker_model"] = reranker_info
        result["processing_time"] = round(elapsed_time, 2)

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
):
    """
    Đặt câu hỏi và nhận câu trả lời từ hệ thống RAG dưới dạng stream

    - **question**: Câu hỏi cần trả lời
    - **search_type**: Loại tìm kiếm ("semantic", "keyword", "hybrid")
    - **alpha**: Hệ số kết hợp giữa semantic và keyword search (0.7 = 70% semantic + 30% keyword)
    - **sources**: Danh sách các file nguồn cần tìm kiếm, có thể là tên file đơn thuần hoặc đường dẫn đầy đủ
    - **max_sources**: Số lượng nguồn tham khảo tối đa trả về (query parameter)
    """
    try:
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
            available_filenames = set()  # Tập hợp tên file không có đường dẫn

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

        # Hàm generator để cung cấp dữ liệu cho SSE
        async def generate_response_stream():
            try:
                # Gọi RAG để lấy kết quả dạng stream
                async for chunk in rag_system.query_with_sources_streaming(
                    request.question,
                    search_type=request.search_type,
                    alpha=request.alpha,
                    sources=request.sources,
                ):
                    # Xử lý chunk tùy theo loại
                    if chunk["type"] == "sources":
                        # Giới hạn số lượng nguồn trả về theo tham số nếu người dùng yêu cầu
                        if (
                            max_sources
                            and chunk["data"]["sources"]
                            and len(chunk["data"]["sources"]) > max_sources
                        ):
                            chunk["data"]["sources"] = chunk["data"]["sources"][
                                :max_sources
                            ]

                        # Thêm question_id vào kết quả
                        chunk["data"]["question_id"] = question_id

                        # Trả về nguồn dưới dạng SSE
                        yield f"event: sources\ndata: {json.dumps(chunk['data'])}\n\n"

                    elif chunk["type"] == "content":
                        # Trả về từng đoạn nội dung
                        yield f"event: content\ndata: {json.dumps({'content': chunk['data']})}\n\n"

                    elif chunk["type"] == "end":
                        # Khi kết thúc, thêm thông tin bổ sung
                        chunk["data"]["question_id"] = question_id

                        # Lưu vào lịch sử nếu đã có đủ dữ liệu
                        if hasattr(generate_response_stream, "full_answer"):
                            questions_history[question_id] = {
                                "question": request.question,
                                "search_type": request.search_type,
                                "alpha": request.alpha,
                                "sources": request.sources,
                                "timestamp": datetime.now().isoformat(),
                                "answer": generate_response_stream.full_answer,
                                "processing_time": chunk["data"]["processing_time"],
                            }

                        # Trả về sự kiện kết thúc
                        yield f"event: end\ndata: {json.dumps(chunk['data'])}\n\n"

                    # Thu thập toàn bộ nội dung để lưu lịch sử
                    if chunk["type"] == "content":
                        if not hasattr(generate_response_stream, "full_answer"):
                            generate_response_stream.full_answer = chunk["data"]
                        else:
                            generate_response_stream.full_answer += chunk["data"]

            except Exception as e:
                # Trả về lỗi dưới dạng SSE
                error_data = {
                    "error": True,
                    "message": str(e),
                    "question_id": question_id,
                }
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                print(f"Lỗi khi xử lý stream: {str(e)}")

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
    file: UploadFile = File(...), category: Optional[str] = Form(None)
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

        # Lưu file
        file_location = os.path.join(UPLOAD_DIR, file.filename)
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

            # Index embeddings với user_id mặc định
            print(
                f"[UPLOAD] Đang index {len(processed_chunks)} chunks với user_id='default_user'"
            )
            rag_system.vector_store.index_documents(
                processed_chunks, embeddings, user_id="default_user"
            )

            return {
                "filename": file.filename,
                "status": "success",
                "message": f"Đã tải lên và index thành công {len(processed_chunks)} chunks từ tài liệu",
                "chunks_count": len(processed_chunks),
                "category": category,
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


@app.post(f"{PREFIX}/index")
async def index_documents(background_tasks: BackgroundTasks):
    """
    Index các tài liệu đã tải lên và chuẩn bị hệ thống để tìm kiếm/trả lời
    """
    if indexing_status["is_running"]:
        return {
            "status": "running",
            "message": "Đang trong quá trình indexing, vui lòng đợi",
        }

    background_tasks.add_task(indexing_documents)

    return {"status": "started", "message": "Đã bắt đầu quá trình indexing"}


@app.get(f"{PREFIX}/index/status", response_model=IndexingStatusResponse)
async def get_indexing_status():
    """
    Kiểm tra trạng thái của quá trình indexing
    """
    return {
        "status": indexing_status["status"],
        "message": indexing_status["message"],
        "processed_files": indexing_status["processed_files"],
    }


@app.get(f"{PREFIX}/collection/info")
async def get_collection_info():
    """
    Lấy thông tin về collection trong vector store
    """
    try:
        info = rag_system.get_collection_info()
        return info
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi lấy thông tin collection: {str(e)}"
        )


@app.post(f"{PREFIX}/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    Nhận phản hồi của người dùng về câu trả lời
    """
    try:
        # Kiểm tra question_id có tồn tại không
        if feedback.question_id not in questions_history:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy câu hỏi với ID {feedback.question_id}",
            )

        # Chuẩn bị dữ liệu feedback
        feedback_data = {
            "question_id": feedback.question_id,
            "question": questions_history[feedback.question_id]["question"],
            "answer": questions_history[feedback.question_id]["answer"],
            "rating": feedback.rating,
            "is_helpful": feedback.is_helpful,
            "comment": feedback.comment,
            "specific_feedback": feedback.specific_feedback,
        }

        # Lưu phản hồi
        save_success = save_feedback(feedback_data)

        if save_success:
            return {"status": "success", "message": "Đã lưu phản hồi của bạn. Cảm ơn!"}
        else:
            return {
                "status": "warning",
                "message": "Đã ghi nhận phản hồi nhưng có lỗi khi lưu",
            }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý phản hồi: {str(e)}")


@app.post(f"{PREFIX}/analyze/sql", response_model=SQLAnalysisResponse)
async def analyze_sql_query(request: SQLAnalysisRequest):
    """
    Phân tích và đề xuất cải tiến cho truy vấn SQL
    """
    try:
        # Tìm kiếm tài liệu liên quan đến SQL và mô hình dữ liệu
        search_query = "SQL query optimization performance index"
        context_docs = rag_system.hybrid_search(search_query)

        # Tạo prompt cho phân tích SQL
        sql_prompt = rag_system.prompt_manager.templates["sql_analysis"].format(
            context="\n\n".join([doc["text"] for doc in context_docs[:3]]),
            query=request.sql_query,
        )

        # Phân tích SQL
        analysis_result = rag_system.llm.invoke(sql_prompt)

        # Xử lý kết quả
        analysis_text = analysis_result.content

        # Tìm các đề xuất trong kết quả
        suggestions = []
        for line in analysis_text.split("\n"):
            if line.strip().startswith("- "):
                suggestions.append(line.strip()[2:])

        # Tìm truy vấn đã tối ưu (nếu có)
        optimized_query = rag_system.prompt_manager.extract_sql_query(analysis_text)

        return {
            "query": request.sql_query,
            "analysis": analysis_text,
            "suggestions": suggestions[:5],  # Giới hạn số lượng đề xuất
            "optimized_query": optimized_query if optimized_query else None,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi phân tích SQL: {str(e)}")


@app.get(f"{PREFIX}/categories", response_model=CategoryStatsResponse)
async def get_categories_stats():
    """
    Lấy thống kê về các danh mục tài liệu
    """
    try:
        # Lấy tất cả tài liệu
        all_docs = rag_system.vector_store.get_all_documents()

        if not all_docs:
            return {"total_documents": 0, "documents_by_category": {}, "categories": []}

        # Thống kê theo danh mục
        categories = {}
        for doc in all_docs:
            category = doc["metadata"].get("category", "general")
            if category in categories:
                categories[category] += 1
            else:
                categories[category] = 1

        return {
            "total_documents": len(all_docs),
            "documents_by_category": categories,
            "categories": list(categories.keys()),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi lấy thống kê danh mục: {str(e)}"
        )


# Thêm endpoint ngữ nghĩa
@app.post(f"{PREFIX}/search/semantic")
async def semantic_search(
    request: QuestionRequest, k: int = Query(5, description="Số lượng kết quả trả về")
):
    """
    Tìm kiếm ngữ nghĩa theo câu truy vấn
    """
    try:
        # Kiểm tra xem sources có tồn tại không nếu đã chỉ định
        if request.sources and len(request.sources) > 0:
            # Lấy danh sách các nguồn có sẵn
            all_docs = rag_system.vector_store.get_all_documents(limit=1000)
            available_sources = set()
            available_filenames = (
                set()
            )  # Thêm tập hợp để lưu tên file không có đường dẫn

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

        results = rag_system.semantic_search(
            request.question, k=k, sources=request.sources
        )
        return {
            "query": request.question,
            "results": results,
            "filtered_sources": request.sources if request.sources else [],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi tìm kiếm ngữ nghĩa: {str(e)}"
        )


@app.post(f"{PREFIX}/search/hybrid")
async def hybrid_search(
    request: QuestionRequest,
    k: int = Query(5, description="Số lượng kết quả trả về"),
    alpha: float = Query(
        0.7, description="Hệ số kết hợp (0.7 = 70% semantic + 30% keyword)"
    ),
):
    """
    Thực hiện tìm kiếm kết hợp (hybrid search) vừa ngữ nghĩa vừa keyword
    """
    try:
        # Kiểm tra xem sources có tồn tại không nếu đã chỉ định
        if request.sources and len(request.sources) > 0:
            # Lấy danh sách các nguồn có sẵn
            all_docs = rag_system.vector_store.get_all_documents(limit=1000)
            available_sources = set()
            available_filenames = (
                set()
            )  # Thêm tập hợp để lưu tên file không có đường dẫn

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

        # Cập nhật alpha từ request nếu được cung cấp
        if hasattr(request, "alpha") and request.alpha is not None:
            alpha = request.alpha

        results = rag_system.hybrid_search(
            request.question, k=k, alpha=alpha, sources=request.sources
        )

        return {
            "results": results,
            "count": len(results),
            "filtered_sources": request.sources if request.sources else [],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi thực hiện hybrid search: {str(e)}"
        )


@app.get(f"{PREFIX}/feedback/stats", response_model=dict)
async def get_feedback_stats():
    """
    Trả về thống kê từ các phản hồi người dùng
    """
    FEEDBACK_DIR = os.path.join(os.path.dirname(__file__), "feedback")

    if not os.path.exists(FEEDBACK_DIR):
        return {
            "status": "error",
            "message": "Chưa có dữ liệu phản hồi",
            "total_feedback": 0,
            "average_rating": 0,
            "helpful_percentage": 0,
            "ratings_distribution": {},
        }

    feedback_files = [f for f in os.listdir(FEEDBACK_DIR) if f.endswith(".json")]

    if not feedback_files:
        return {
            "status": "success",
            "message": "Chưa có phản hồi nào",
            "total_feedback": 0,
            "average_rating": 0,
            "helpful_percentage": 0,
            "ratings_distribution": {},
        }

    total_feedback = len(feedback_files)
    total_rating = 0
    helpful_count = 0
    ratings_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    for file in feedback_files:
        file_path = os.path.join(FEEDBACK_DIR, file)
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                feedback = json.load(f)
                rating = feedback.get("rating", 0)
                total_rating += rating

                if rating in ratings_distribution:
                    ratings_distribution[rating] += 1

                if feedback.get("is_helpful", False):
                    helpful_count += 1
            except json.JSONDecodeError:
                continue

    average_rating = (
        round(total_rating / total_feedback, 2) if total_feedback > 0 else 0
    )
    helpful_percentage = (
        round((helpful_count / total_feedback) * 100, 1) if total_feedback > 0 else 0
    )

    return {
        "status": "success",
        "message": "Thống kê phản hồi",
        "total_feedback": total_feedback,
        "average_rating": average_rating,
        "helpful_percentage": helpful_percentage,
        "ratings_distribution": ratings_distribution,
    }


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
async def get_uploaded_files():
    """
    Lấy danh sách các file đã được upload vào hệ thống
    """
    try:
        files = []
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)

            # Bỏ qua các thư mục
            if os.path.isdir(file_path):
                continue

            # Lấy thông tin file
            file_stats = os.stat(file_path)
            extension = os.path.splitext(filename)[1].lower()

            # Lấy thời gian tạo file
            created_time = datetime.fromtimestamp(file_stats.st_ctime).isoformat()

            # Thêm vào danh sách
            files.append(
                FileInfo(
                    filename=filename,
                    path=file_path,
                    size=file_stats.st_size,
                    upload_date=created_time,
                    extension=extension,
                    category=None,  # Có thể cần truy vấn metadata từ vector store
                )
            )

        # Sắp xếp theo thời gian tạo mới nhất
        files.sort(key=lambda x: x.upload_date, reverse=True)

        return {"total_files": len(files), "files": files}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi lấy danh sách file: {str(e)}"
        )


# Thêm API endpoint xóa file và index liên quan
@app.delete(f"{PREFIX}/files/{{filename}}", response_model=FileDeleteResponse)
async def delete_file(filename: str):
    """
    Xóa file đã upload và các index liên quan trong vector store
    """
    try:
        file_path = os.path.join(UPLOAD_DIR, filename)
        print(f"[DELETE] Bắt đầu xóa file: {filename}, đường dẫn: {file_path}")

        # Kiểm tra file có tồn tại không
        if not os.path.exists(file_path):
            print(f"[DELETE] Lỗi: File {filename} không tồn tại")
            raise HTTPException(
                status_code=404, detail=f"File {filename} không tồn tại"
            )

        print(f"[DELETE] Đang tìm kiếm các điểm dữ liệu liên quan đến file: {filename}")
        # Đếm số lượng điểm trong vector store liên quan đến file này trước khi xóa
        all_docs = rag_system.vector_store.get_all_documents()
        print(f"[DELETE] Tổng số documents trong vector store: {len(all_docs)}")

        # Tạo danh sách các biến thể của tên file để tìm kiếm
        file_path_variants = [
            filename,  # Tên file đơn thuần
            file_path,  # Đường dẫn đầy đủ
            file_path.replace("\\", "/"),  # Đường dẫn với dấu /
            os.path.join(UPLOAD_DIR, filename).replace(
                "\\", "/"
            ),  # Đường dẫn đầy đủ với dấu /
            f"src/data/{filename}",  # Thêm tiền tố src/data/
            f"src/data\\{filename}",  # Thêm tiền tố src/data\ với backslash
        ]

        print(f"[DELETE] Tìm kiếm với các biến thể: {file_path_variants}")

        # Tìm tất cả tài liệu khớp với bất kỳ biến thể nào của tên file
        related_docs = []
        for doc in all_docs:
            # Kiểm tra trong metadata.source
            meta_source = doc.get("metadata", {}).get("source", "unknown")
            # Kiểm tra trong source trực tiếp
            direct_source = doc.get("source", "unknown")

            # So sánh với các biến thể
            for variant in file_path_variants:
                if meta_source == variant or direct_source == variant:
                    related_docs.append(doc)
                    print(
                        f"[DELETE] Tìm thấy document với source={meta_source if meta_source != 'unknown' else direct_source}"
                    )
                    break

        points_count = len(related_docs)
        print(f"[DELETE] Số lượng điểm dữ liệu liên quan đến file: {points_count}")

        # Xóa các index liên quan đến file này trong vector store
        if points_count > 0:
            print(f"[DELETE] Bắt đầu xóa {points_count} điểm dữ liệu liên quan")
            point_ids = [
                doc.get("id") for doc in related_docs if doc.get("id") is not None
            ]
            if point_ids:
                delete_result = rag_system.vector_store.delete_points(point_ids)
                print(f"[DELETE] Kết quả xóa điểm dữ liệu: {delete_result}")
            else:
                print(
                    f"[DELETE] Không thể xóa vì không tìm thấy ID cho các điểm dữ liệu"
                )

            # Thêm xóa theo filter dựa trên tên file
            try:
                print(f"[DELETE] Thử xóa theo filter với tên file...")
                for variant in file_path_variants:
                    filter_request = {
                        "filter": {
                            "must": [{"key": "source", "match": {"value": variant}}]
                        }
                    }
                    print(f"[DELETE] Xóa filter với variant: {variant}")
                    success, message = rag_system.vector_store.delete_points_by_filter(
                        filter_request
                    )
                    print(
                        f"[DELETE] Kết quả xóa theo filter (source={variant}): {success}, {message}"
                    )

                    # Thử xóa theo metadata.source
                    filter_request = {
                        "filter": {
                            "must": [
                                {"key": "metadata.source", "match": {"value": variant}}
                            ]
                        }
                    }
                    print(f"[DELETE] Xóa filter với metadata.source={variant}")
                    success, message = rag_system.vector_store.delete_points_by_filter(
                        filter_request
                    )
                    print(
                        f"[DELETE] Kết quả xóa theo filter (metadata.source={variant}): {success}, {message}"
                    )
            except Exception as e:
                print(f"[DELETE] Lỗi khi xóa theo filter: {str(e)}")
        else:
            print(f"[DELETE] Không có điểm dữ liệu nào liên quan đến file {filename}")

        # Xóa file vật lý
        print(f"[DELETE] Đang xóa file vật lý: {file_path}")
        os.remove(file_path)
        print(f"[DELETE] Đã xóa file vật lý thành công")

        return {
            "filename": filename,
            "status": "success",
            "message": f"Đã xóa file {filename} và {points_count} index liên quan",
            "removed_points": points_count,
        }
    except HTTPException as e:
        print(f"[DELETE] HTTP Exception: {str(e)}")
        raise e
    except Exception as e:
        print(f"[DELETE] Lỗi không xác định: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa file: {str(e)}")


@app.get(f"{PREFIX}/files/sources")
async def get_available_sources():
    """
    Lấy danh sách các file nguồn có thể sử dụng để tìm kiếm
    """
    try:
        # Lấy tất cả tài liệu từ vector store
        all_docs = rag_system.vector_store.get_all_documents()

        # Trích xuất danh sách nguồn duy nhất
        sources = set()
        filenames = set()  # Thêm tập hợp để lưu tên file không có đường dẫn
        sources_location = []  # Để debug xem source nằm ở đâu

        for doc in all_docs:
            # Kiểm tra cả trong metadata.source và source trực tiếp
            meta_source = doc.get("metadata", {}).get("source", None)
            direct_source = doc.get("source", None)

            if meta_source:
                sources.add(meta_source)
                # Thêm tên file đơn thuần
                if os.path.sep in meta_source:
                    filenames.add(os.path.basename(meta_source))
                else:
                    filenames.add(meta_source)
                sources_location.append({"location": "metadata", "source": meta_source})

            if direct_source and direct_source != meta_source:
                sources.add(direct_source)
                # Thêm tên file đơn thuần
                if os.path.sep in direct_source:
                    filenames.add(os.path.basename(direct_source))
                else:
                    filenames.add(direct_source)
                sources_location.append({"location": "direct", "source": direct_source})

        # Log 10 mẫu đầu tiên để debug
        samples = all_docs[:5] if len(all_docs) > 5 else all_docs
        sample_structures = []
        for doc in samples:
            # Tính toán filenames
            meta_source = doc.get("metadata", {}).get("source", "not_found")
            direct_source = doc.get("source", "not_found")
            meta_filename = (
                os.path.basename(meta_source)
                if meta_source != "not_found" and os.path.sep in meta_source
                else meta_source
            )
            direct_filename = (
                os.path.basename(direct_source)
                if direct_source != "not_found" and os.path.sep in direct_source
                else direct_source
            )

            sample_structures.append(
                {
                    "metadata_keys": list(doc.get("metadata", {}).keys()),
                    "top_level_keys": list(doc.keys()),
                    "has_source_in_metadata": "source" in doc.get("metadata", {}),
                    "has_direct_source": "source" in doc,
                    "metadata_source": meta_source,
                    "direct_source": direct_source,
                    "metadata_filename": meta_filename,
                    "direct_filename": direct_filename,
                }
            )

        # Trả về danh sách nguồn
        return {
            "total_sources": len(sources),
            "sources": sorted(list(sources)),
            "filenames": sorted(
                list(filenames)
            ),  # Thêm danh sách các tên file đơn thuần
            "recommendation": "Bạn có thể sử dụng sources là tên file đơn thuần hoặc đường dẫn đầy đủ",
            "debug_info": {
                "sample_count": len(samples),
                "sample_structures": sample_structures,
                "sources_location": sources_location[:10],  # Chỉ trả về 10 mẫu đầu
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi lấy danh sách nguồn: {str(e)}"
        )


@app.get(f"{PREFIX}/files/sources/details")
async def get_source_details(
    source_name: Optional[str] = Query(
        None, description="Tên file nguồn cụ thể cần kiểm tra"
    )
):
    """
    Lấy thông tin chi tiết về một nguồn tài liệu cụ thể hoặc tất cả các nguồn

    - **source_name**: (Tùy chọn) Tên file nguồn cần kiểm tra chi tiết
    """
    try:
        # Lấy tất cả tài liệu từ vector store
        all_docs = rag_system.vector_store.get_all_documents(limit=5000)

        # Nếu không chỉ định nguồn cụ thể, trả về thống kê tổng hợp
        if not source_name:
            source_stats = {}
            for doc in all_docs:
                # Lấy nguồn từ cả metadata và trực tiếp
                meta_source = doc.get("metadata", {}).get("source", "unknown")
                direct_source = doc.get("source", "unknown")

                # Ưu tiên source từ metadata nếu có
                source = meta_source if meta_source != "unknown" else direct_source

                if source not in source_stats:
                    source_stats[source] = {
                        "count": 0,
                        "categories": set(),
                    }

                source_stats[source]["count"] += 1

                # Thêm category vào set nếu có
                category = doc.get("metadata", {}).get("category", "unknown")
                if category != "unknown":
                    source_stats[source]["categories"].add(category)

            # Chuyển đổi set thành list cho JSON serialization
            for source in source_stats:
                source_stats[source]["categories"] = list(
                    source_stats[source]["categories"]
                )

            return {"total_sources": len(source_stats), "sources": source_stats}

        # Nếu chỉ định nguồn cụ thể, trả về thông tin chi tiết về nguồn đó
        source_chunks = []
        for doc in all_docs:
            meta_source = doc.get("metadata", {}).get("source", "unknown")
            direct_source = doc.get("source", "unknown")

            if meta_source == source_name or direct_source == source_name:
                source_chunks.append(
                    {
                        "text": doc["text"][:200] + "...",  # Chỉ trả về preview
                        "category": doc.get("metadata", {}).get("category", "unknown"),
                        "full_length": len(doc["text"]),
                    }
                )

        if not source_chunks:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"Không tìm thấy nguồn '{source_name}'",
                    "available_sources": sorted(
                        list(
                            set(
                                [
                                    doc.get("metadata", {}).get(
                                        "source", doc.get("source", "unknown")
                                    )
                                    for doc in all_docs
                                    if doc.get("metadata", {}).get(
                                        "source", doc.get("source", "unknown")
                                    )
                                    != "unknown"
                                ]
                            )
                        )
                    ),
                },
            )

        return {
            "source_name": source_name,
            "total_chunks": len(source_chunks),
            "chunks": source_chunks,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi lấy thông tin chi tiết nguồn: {str(e)}"
        )


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


if __name__ == "__main__":
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
