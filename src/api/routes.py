from fastapi import (
    APIRouter,
    HTTPException,
    BackgroundTasks,
    UploadFile,
    File,
    Form,
    Path,
    Query,
)
from typing import List, Optional, Dict, Any
import os
import uuid
import shutil
import tempfile
import time
from datetime import datetime
from pydantic import BaseModel
from tqdm import tqdm

from src.app import RAGPipeline
from src.loaders import DocumentLoader


router = APIRouter()

# Khởi tạo RAG Pipeline
pipeline = RAGPipeline()

# Thư mục lưu dữ liệu cố định
DATA_DIR = "D:\\DATN\\V2\\src\\data"

# Trạng thái indexing để theo dõi
indexing_tasks = {}


class QueryRequest(BaseModel):
    query: str


class SourceInfo(BaseModel):
    index: int
    source: str
    source_path: str
    file_type: str
    chunk_length: int
    chunk_word_count: int
    start_index: int
    chunk_count: int
    has_list_content: bool
    content_preview: str
    page_number: Optional[int] = None
    image_paths: Optional[List[str]] = []
    pdf_element_type: Optional[str] = None


class QueryResponse(BaseModel):
    response: str
    sources: List[SourceInfo]
    prompt: str
    model: str
    query: str
    temperature: float
    total_sources: int
    retrieval_time_ms: int
    llm_time_ms: int
    total_tokens: int
    related_images: Optional[List[str]] = []


class IndexResponse(BaseModel):
    task_id: str
    message: str


class DeleteFileResponse(BaseModel):
    deleted_file: str
    deleted_embeddings: int
    success: bool
    message: str


class TaskStatus(BaseModel):
    task_id: str
    status: str
    message: Optional[str] = None


class ProgressDetail(BaseModel):
    step: str
    step_name: str
    completed_steps: int
    total_steps: int
    progress_percent: float
    start_time: float
    current_time: float
    elapsed_time: float
    estimated_time_remaining: Optional[float] = None


class TaskProgress(BaseModel):
    task_id: str
    status: str
    message: str
    progress: Optional[ProgressDetail] = None


class FileInfo(BaseModel):
    name: str
    path: str
    size: int
    last_modified: float


@router.get("/")
async def root():
    return {"message": "API hệ thống RAG đang hoạt động"}


@router.post("/query", response_model=QueryResponse, status_code=200)
async def query(request: QueryRequest):
    """API endpoint cho việc truy vấn"""
    try:
        if not request.query or request.query.strip() == "":
            raise HTTPException(status_code=400, detail="Câu truy vấn không được trống")

        # Gọi pipeline.query để lấy kết quả chi tiết
        result = pipeline.query(request.query)

        # Trích xuất đường dẫn ảnh từ sources
        related_images = []
        for source in result.get("sources", []):
            if "image_paths" in source and source["image_paths"]:
                for img_path in source["image_paths"]:
                    if img_path not in related_images:
                        related_images.append(img_path)
            # Kiểm tra cả image_path (đơn lẻ)
            if "image_path" in source and source["image_path"]:
                if source["image_path"] not in related_images:
                    related_images.append(source["image_path"])

        # Chuyển đổi đường dẫn tương đối thành URL API
        image_urls = [
            f"/images/{os.path.basename(os.path.dirname(img_path))}/{os.path.basename(img_path)}"
            for img_path in related_images
        ]

        # Chuẩn bị response với đầy đủ thông tin
        response = QueryResponse(
            response=result.get("text", ""),
            sources=result.get("sources", []),
            prompt=result.get("prompt", ""),
            model=result.get("model", ""),
            query=result.get("query", request.query),
            temperature=result.get("temperature", 0.0),
            total_sources=result.get("total_sources", 0),
            retrieval_time_ms=round(result.get("retrieval_time", 0) * 1000),
            llm_time_ms=round(result.get("llm_time", 0) * 1000),
            total_tokens=result.get("total_tokens", 0),
            related_images=image_urls,
        )

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý truy vấn: {str(e)}")


@router.post("/upload", response_model=IndexResponse)
async def upload_and_index(
    background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)
):
    """API endpoint để upload tài liệu và index"""
    task_id = str(uuid.uuid4())

    # Tạo thư mục nếu chưa tồn tại
    os.makedirs(DATA_DIR, exist_ok=True)

    # Tạo thư mục con theo thời gian để tránh trùng lặp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_dir = os.path.join(DATA_DIR, f"upload_{timestamp}")
    os.makedirs(upload_dir, exist_ok=True)

    try:
        # Lưu các file được upload vào thư mục dữ liệu
        file_paths = []
        for file in files:
            file_path = os.path.join(upload_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_paths.append(file_path)

        # Khởi tạo trạng thái task với progress chi tiết
        current_time = time.time()
        indexing_tasks[task_id] = {
            "status": "running",
            "message": "Đang lưu file và chuẩn bị xử lý...",
            "files": file_paths,
            "directory": upload_dir,
            "progress": {
                "step": "init",
                "step_name": "Khởi tạo",
                "completed_steps": 0,
                "total_steps": 4,
                "progress_percent": 0.0,
                "start_time": current_time,
                "current_time": current_time,
                "elapsed_time": 0.0,
                "estimated_time_remaining": None,
            },
        }

        # Thực hiện indexing trong background với stream progress
        background_tasks.add_task(
            _process_indexing_with_progress, task_id, upload_dir, False
        )

        return {
            "task_id": task_id,
            "message": f"Đã upload và bắt đầu quá trình indexing {len(files)} file",
        }
    except Exception as e:
        # Xóa thư mục nếu có lỗi
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi xử lý upload và indexing: {str(e)}"
        )


@router.post("/index/files", response_model=IndexResponse)
async def index_files(
    background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)
):
    """API endpoint để index dữ liệu từ các file được upload"""
    task_id = str(uuid.uuid4())
    temp_dir = tempfile.mkdtemp()

    try:
        # Lưu các file được upload vào thư mục tạm
        for file in files:
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

        # Khởi tạo trạng thái task với progress chi tiết
        current_time = time.time()
        indexing_tasks[task_id] = {
            "status": "running",
            "message": "Đang xử lý...",
            "progress": {
                "step": "init",
                "step_name": "Khởi tạo",
                "completed_steps": 0,
                "total_steps": 4,
                "progress_percent": 0.0,
                "start_time": current_time,
                "current_time": current_time,
                "elapsed_time": 0.0,
                "estimated_time_remaining": None,
            },
        }

        # Thực hiện indexing trong background
        background_tasks.add_task(
            _process_indexing_with_progress, task_id, temp_dir, True
        )

        return {
            "task_id": task_id,
            "message": f"Đã bắt đầu quá trình indexing {len(files)} file",
        }
    except Exception as e:
        # Xóa thư mục tạm nếu có lỗi
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý indexing: {str(e)}")


@router.post("/index/path", response_model=IndexResponse)
async def index_directory(
    background_tasks: BackgroundTasks, directory: str = Form(...)
):
    """API endpoint để index dữ liệu từ một thư mục"""
    task_id = str(uuid.uuid4())

    try:
        # Kiểm tra thư mục có tồn tại không
        if not os.path.exists(directory) or not os.path.isdir(directory):
            raise HTTPException(
                status_code=400, detail=f"Thư mục không tồn tại: {directory}"
            )

        # Khởi tạo trạng thái task với progress chi tiết
        current_time = time.time()
        indexing_tasks[task_id] = {
            "status": "running",
            "message": "Đang xử lý...",
            "progress": {
                "step": "init",
                "step_name": "Khởi tạo",
                "completed_steps": 0,
                "total_steps": 4,
                "progress_percent": 0.0,
                "start_time": current_time,
                "current_time": current_time,
                "elapsed_time": 0.0,
                "estimated_time_remaining": None,
            },
        }

        # Thực hiện indexing trong background
        background_tasks.add_task(
            _process_indexing_with_progress, task_id, directory, False
        )

        return {
            "task_id": task_id,
            "message": f"Đã bắt đầu quá trình indexing từ thư mục {directory}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý indexing: {str(e)}")


@router.get("/index/status/{task_id}", response_model=TaskStatus)
async def get_index_status(task_id: str):
    """Lấy trạng thái của task indexing"""
    if task_id not in indexing_tasks:
        raise HTTPException(status_code=404, detail="Task không tồn tại")

    return {
        "task_id": task_id,
        "status": indexing_tasks[task_id]["status"],
        "message": indexing_tasks[task_id]["message"],
    }


@router.get("/index/progress/{task_id}", response_model=TaskProgress)
async def get_index_progress(task_id: str):
    """Lấy thông tin chi tiết về tiến trình xử lý"""
    if task_id not in indexing_tasks:
        raise HTTPException(status_code=404, detail="Task không tồn tại")

    task = indexing_tasks[task_id]

    # Cập nhật thời gian hiện tại và tính toán thời gian đã trôi qua
    if "progress" in task:
        current_time = time.time()
        task["progress"]["current_time"] = current_time
        task["progress"]["elapsed_time"] = current_time - task["progress"]["start_time"]

    return {
        "task_id": task_id,
        "status": task["status"],
        "message": task["message"],
        "progress": task.get("progress"),
    }


@router.delete("/index")
async def delete_index():
    """API endpoint để xóa index"""
    try:
        pipeline.delete_index()
        return {"message": "Đã xóa index thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa index: {str(e)}")


@router.get("/uploads")
async def list_uploads():
    """API endpoint để liệt kê các thư mục upload"""
    try:
        if not os.path.exists(DATA_DIR):
            return {"uploads": []}

        # Lấy danh sách thư mục upload
        uploads = []
        for item in os.listdir(DATA_DIR):
            item_path = os.path.join(DATA_DIR, item)
            if os.path.isdir(item_path) and item.startswith("upload_"):
                # Lấy thông tin thư mục
                files = [
                    f
                    for f in os.listdir(item_path)
                    if os.path.isfile(os.path.join(item_path, f))
                ]
                uploads.append(
                    {
                        "name": item,
                        "path": item_path,
                        "files": files,
                        "file_count": len(files),
                    }
                )

        return {"uploads": uploads}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi liệt kê uploads: {str(e)}"
        )


@router.get("/files", response_model=List[FileInfo])
async def list_files():
    """API endpoint để liệt kê các file trong tất cả thư mục upload"""
    try:
        if not os.path.exists(DATA_DIR):
            return []

        # Danh sách file
        files_info = []

        # Duyệt qua các thư mục upload
        for folder in os.listdir(DATA_DIR):
            folder_path = os.path.join(DATA_DIR, folder)

            if os.path.isdir(folder_path) and folder.startswith("upload_"):
                # Duyệt qua các file trong thư mục
                for file_name in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, file_name)

                    if os.path.isfile(file_path):
                        # Lấy thông tin file
                        file_stat = os.stat(file_path)

                        files_info.append(
                            FileInfo(
                                name=file_name,
                                path=file_path,
                                size=file_stat.st_size,
                                last_modified=file_stat.st_mtime,
                            )
                        )

        # Sắp xếp theo thời gian sửa đổi mới nhất
        files_info.sort(key=lambda x: x.last_modified, reverse=True)

        return files_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi liệt kê files: {str(e)}")


@router.delete("/files/{file_name:path}", response_model=DeleteFileResponse)
async def delete_file(
    file_name: str = Path(
        ..., description="Tên file cần xóa (có phân biệt chữ hoa/thường)"
    ),
    upload_dir: Optional[str] = Query(
        None, description="Thư mục upload cụ thể (nếu có)"
    ),
):
    """API endpoint để xóa file và embedding tương ứng"""
    try:
        # Tìm file trong thư mục dữ liệu
        file_path = None

        if upload_dir:
            # Nếu chỉ định thư mục upload cụ thể
            dir_path = os.path.join(DATA_DIR, upload_dir)
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                temp_path = os.path.join(dir_path, file_name)
                if os.path.exists(temp_path) and os.path.isfile(temp_path):
                    file_path = temp_path
        else:
            # Duyệt qua tất cả thư mục upload
            for folder in os.listdir(DATA_DIR):
                folder_path = os.path.join(DATA_DIR, folder)

                if os.path.isdir(folder_path) and folder.startswith("upload_"):
                    temp_path = os.path.join(folder_path, file_name)
                    if os.path.exists(temp_path) and os.path.isfile(temp_path):
                        file_path = temp_path
                        break

        if not file_path:
            raise HTTPException(
                status_code=404, detail=f"Không tìm thấy file: {file_name}"
            )

        # Xóa các embedding liên quan trong vectorstore
        deleted_count = pipeline.delete_file(file_path)

        # Xóa file thực tế
        os.remove(file_path)

        return {
            "deleted_file": file_path,
            "deleted_embeddings": deleted_count,
            "success": True,
            "message": f"Đã xóa file: {file_name} và {deleted_count} embedding liên quan",
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy file: {file_name}")
    except PermissionError:
        raise HTTPException(
            status_code=403, detail=f"Không có quyền xóa file: {file_name}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa file: {str(e)}")


@router.post("/reindex", response_model=IndexResponse)
async def reindex_all_documents(background_tasks: BackgroundTasks):
    """API endpoint để tái chỉ mục toàn bộ tài liệu hiện có"""
    task_id = str(uuid.uuid4())

    try:
        # Kiểm tra có dữ liệu không
        if not os.path.exists(DATA_DIR):
            raise HTTPException(
                status_code=400, detail="Không tìm thấy thư mục dữ liệu"
            )

        # Tìm tất cả thư mục upload
        upload_dirs = []
        for item in os.listdir(DATA_DIR):
            item_path = os.path.join(DATA_DIR, item)
            if os.path.isdir(item_path) and item.startswith("upload_"):
                upload_dirs.append(item_path)

        if not upload_dirs:
            raise HTTPException(
                status_code=400, detail="Không tìm thấy thư mục upload nào"
            )

        # Khởi tạo trạng thái task với progress chi tiết
        current_time = time.time()
        indexing_tasks[task_id] = {
            "status": "running",
            "message": "Đang chuẩn bị xóa index hiện tại và tái chỉ mục...",
            "progress": {
                "step": "init",
                "step_name": "Khởi tạo",
                "completed_steps": 0,
                "total_steps": 4,
                "progress_percent": 0.0,
                "start_time": current_time,
                "current_time": current_time,
                "elapsed_time": 0.0,
                "estimated_time_remaining": None,
            },
        }

        # Thực hiện xóa index hiện tại và tái chỉ mục trong background
        async def _reindex_all():
            try:
                # 1. Xóa index hiện tại
                _update_progress(
                    task_id,
                    "delete_index",
                    "Xóa index hiện tại",
                    1,
                    "Đang xóa index hiện tại...",
                    0.1,
                )
                pipeline.delete_index()

                # 2. Lặp qua từng thư mục upload để index lại
                for i, upload_dir in enumerate(upload_dirs):
                    progress = 0.1 + 0.8 * (i / len(upload_dirs))
                    _update_progress(
                        task_id,
                        "indexing",
                        f"Index thư mục {i+1}/{len(upload_dirs)}",
                        2,
                        f"Đang index thư mục: {os.path.basename(upload_dir)}",
                        progress,
                    )
                    await _process_indexing_with_progress(
                        f"{task_id}_{i}", upload_dir, False
                    )

                # 3. Hoàn thành
                _update_progress(
                    task_id,
                    "completed",
                    "Hoàn thành",
                    4,
                    "Đã tái chỉ mục tất cả tài liệu",
                    1.0,
                )
                indexing_tasks[task_id]["status"] = "completed"
                indexing_tasks[task_id][
                    "message"
                ] = "Đã tái chỉ mục thành công tất cả tài liệu"

            except Exception as e:
                error_message = f"Lỗi khi tái chỉ mục: {str(e)}"
                print(f"❌ {error_message}")
                indexing_tasks[task_id]["status"] = "failed"
                indexing_tasks[task_id]["message"] = error_message

        # Thực hiện tái chỉ mục trong background
        background_tasks.add_task(_reindex_all)

        return {
            "task_id": task_id,
            "message": f"Đã bắt đầu tái chỉ mục tất cả tài liệu từ {len(upload_dirs)} thư mục upload",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tái chỉ mục: {str(e)}")


async def _process_indexing_with_progress(
    task_id: str, data_dir: str, is_temp_dir: bool = True
):
    """Hàm xử lý indexing trong background với cập nhật tiến trình chi tiết"""
    try:
        # Đảm bảo task đã được khởi tạo
        if task_id not in indexing_tasks:
            indexing_tasks[task_id] = {
                "status": "running",
                "message": "Đang xử lý...",
                "progress": {
                    "step": "init",
                    "step_name": "Khởi tạo",
                    "completed_steps": 0,
                    "total_steps": 4,
                    "progress_percent": 0.0,
                    "start_time": time.time(),
                    "current_time": time.time(),
                    "elapsed_time": 0.0,
                    "estimated_time_remaining": None,
                },
            }

        # In thông tin cấu hình
        from src.config import (
            EMBEDDING_MODEL,
            DOCUMENT_LOADER_MAX_WORKERS,
            QDRANT_BATCH_SIZE,
            CLUSTERING_BATCH_SIZE,
        )

        print(f"📄 Cấu hình xử lý:")
        print(f"  - Model embedding: {EMBEDDING_MODEL}")
        print(f"  - Document loader workers: {DOCUMENT_LOADER_MAX_WORKERS}")
        print(f"  - Clustering batch size: {CLUSTERING_BATCH_SIZE}")
        print(f"  - Qdrant batch size: {QDRANT_BATCH_SIZE}")

        # Tạo thanh tiến trình tổng thể
        overall_progress = tqdm(total=100, desc="Tổng quá trình xử lý", unit="%")

        # Bước 1: Load tài liệu (25%)
        _update_progress(
            task_id, "loading", "Load tài liệu", 0, "Đang load tài liệu...", 0.1
        )
        overall_progress.update(5)

        documents = DocumentLoader.load_documents(data_dir)

        _update_progress(
            task_id,
            "loading",
            "Load tài liệu",
            1,
            f"Đã load {len(documents)} tài liệu",
            0.25,
        )
        overall_progress.update(20)

        # Phân loại tài liệu theo loại
        from src.config import SQL_FILE_EXTENSIONS
        from src.utils import get_file_extension

        # Phân chia tài liệu theo loại
        sql_docs = []
        regular_docs = []

        for doc in documents:
            # Phát hiện tài liệu SQL dựa trên phần mở rộng file
            ext = get_file_extension(doc.metadata.get("source_path", ""))
            if ext in SQL_FILE_EXTENSIONS:
                sql_docs.append(doc)
            else:
                regular_docs.append(doc)

        print(
            f"ℹ️ Tổng số tài liệu: {len(documents)} (SQL: {len(sql_docs)}, Thông thường: {len(regular_docs)})"
        )

        # Bước 2: Chunking (25%)
        _update_progress(
            task_id,
            "chunking",
            "Chia nhỏ tài liệu",
            1,
            "Đang chia nhỏ tài liệu...",
            0.3,
        )
        overall_progress.update(5)

        # Xử lý tài liệu thông thường
        chunks = []
        if regular_docs:
            regular_chunks = pipeline.document_processor.chunk_documents(regular_docs)
            chunks.extend(regular_chunks)

        # Xử lý tài liệu SQL nếu có
        if sql_docs:
            sql_chunks = pipeline.sql_processor.process_sql_documents(sql_docs)
            chunks.extend(sql_chunks)

        _update_progress(
            task_id,
            "chunking",
            "Chia nhỏ tài liệu",
            2,
            f"Đã chia thành {len(chunks)} chunks",
            0.5,
        )
        overall_progress.update(15)

        # Bước 3: Clustering & merging (25%)
        _update_progress(
            task_id,
            "clustering",
            "Phân cụm và gộp chunks",
            2,
            "Đang phân cụm và gộp chunks...",
            0.6,
        )
        overall_progress.update(10)

        # Chỉ áp dụng clustering cho tài liệu thông thường
        merged_docs = []
        if regular_docs:
            regular_chunks_to_merge = [
                chunk for chunk in chunks if "sql_type" not in chunk.metadata
            ]
            if regular_chunks_to_merge:
                merged_regular_docs = pipeline.document_processor.cluster_and_merge(
                    regular_chunks_to_merge
                )
                merged_docs.extend(merged_regular_docs)

        # Thêm các chunk SQL (không cần clustering)
        sql_chunks_to_add = [chunk for chunk in chunks if "sql_type" in chunk.metadata]
        merged_docs.extend(sql_chunks_to_add)

        _update_progress(
            task_id,
            "clustering",
            "Phân cụm và gộp chunks",
            3,
            f"Đã gộp thành {len(merged_docs)} tài liệu",
            0.75,
        )
        overall_progress.update(15)

        # Bước 4: Upload vào vector database (25%)
        _update_progress(
            task_id,
            "vectorizing",
            "Upload vào vector database",
            3,
            "Đang upload vào vector database...",
            0.8,
        )
        overall_progress.update(15)

        pipeline.vector_store_manager.upload_documents(merged_docs)

        # Hoàn thành
        _update_progress(
            task_id, "completed", "Hoàn thành", 4, "Đã hoàn thành indexing", 1.0
        )

        # Khởi tạo lại vectorstore để áp dụng thay đổi
        pipeline._reinitialize_vectorstore()

        # Cập nhật phần còn lại của thanh tiến trình (đảm bảo không vượt quá 100%)
        current_progress = overall_progress.n
        if current_progress < 100:
            overall_progress.update(100 - current_progress)

        overall_progress.close()

        # Cập nhật trạng thái task
        indexing_tasks[task_id]["status"] = "completed"
        indexing_tasks[task_id]["message"] = "Đã hoàn thành indexing"

        # Xóa thư mục tạm nếu cần
        if is_temp_dir:
            shutil.rmtree(data_dir, ignore_errors=True)

    except Exception as e:
        error_message = f"Lỗi khi indexing: {str(e)}"
        print(f"❌ {error_message}")
        if task_id in indexing_tasks:
            indexing_tasks[task_id]["status"] = "failed"
            indexing_tasks[task_id]["message"] = error_message

        # Xóa thư mục tạm nếu có lỗi và là thư mục tạm
        if is_temp_dir:
            shutil.rmtree(data_dir, ignore_errors=True)


def _update_progress(
    task_id: str,
    step: str,
    step_name: str,
    completed_steps: int,
    message: str,
    progress_percent: float,
):
    """Cập nhật thông tin tiến trình"""
    if task_id not in indexing_tasks:
        return

    task = indexing_tasks[task_id]
    current_time = time.time()

    # Nếu progress chưa được khởi tạo
    if "progress" not in task:
        task["progress"] = {
            "step": step,
            "step_name": step_name,
            "completed_steps": completed_steps,
            "total_steps": 4,
            "progress_percent": progress_percent,
            "start_time": current_time,
            "current_time": current_time,
            "elapsed_time": 0.0,
            "estimated_time_remaining": None,
        }
    else:
        # Cập nhật thông tin tiến trình
        elapsed_time = current_time - task["progress"]["start_time"]

        # Ước tính thời gian còn lại (nếu tiến độ > 0)
        estimated_remaining = None
        if progress_percent > 0:
            estimated_remaining = (elapsed_time / progress_percent) * (
                1 - progress_percent
            )

        task["progress"].update(
            {
                "step": step,
                "step_name": step_name,
                "completed_steps": completed_steps,
                "progress_percent": progress_percent,
                "current_time": current_time,
                "elapsed_time": elapsed_time,
                "estimated_time_remaining": estimated_remaining,
            }
        )

    # Cập nhật thông điệp
    task["message"] = message
