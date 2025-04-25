import uvicorn
import argparse
import os
import time

from src.api import app
from src.embeddings import initialize_embeddings
from src.vectorstore import VectorStoreManager
from src.config import (
    EMBEDDING_MODEL,
    DOCUMENT_LOADER_MAX_WORKERS,
    QDRANT_BATCH_SIZE,
    CLUSTERING_BATCH_SIZE,
    QDRANT_URL,
)


def check_system_ready():
    """Kiểm tra tất cả thành phần cần thiết trước khi khởi động hệ thống"""
    print("\n🔍 Đang kiểm tra trạng thái hệ thống...")

    # Kiểm tra cấu hình
    print(f"📋 Thông tin cấu hình:")
    print(f"  - Embedding model: {EMBEDDING_MODEL}")
    print(f"  - Document loader workers: {DOCUMENT_LOADER_MAX_WORKERS}")
    print(f"  - Clustering batch size: {CLUSTERING_BATCH_SIZE}")
    print(f"  - Qdrant batch size: {QDRANT_BATCH_SIZE}")

    # Tải và kiểm tra embedding model
    print(f"\n⏳ Đang tải embedding model: {EMBEDDING_MODEL}...")
    start_time = time.time()
    try:
        embeddings = initialize_embeddings()
        embedding_size = len(embeddings.embed_query("Test embedding system"))
        print(
            f"✅ Embedding model đã sẵn sàng! (kích thước vector: {embedding_size}, thời gian: {time.time() - start_time:.2f}s)"
        )
    except Exception as e:
        print(f"❌ Lỗi khi tải embedding model: {str(e)}")
        raise e

    # Kiểm tra kết nối Qdrant
    print(f"\n⏳ Đang kiểm tra kết nối đến Qdrant: {QDRANT_URL}...")
    try:
        vector_store = VectorStoreManager(embeddings)
        # Thử khởi tạo collection để kiểm tra kết nối
        vector_store.initialize_collection()
        print(f"✅ Kết nối đến Qdrant thành công!")
    except Exception as e:
        print(f"❌ Lỗi khi kết nối đến Qdrant: {str(e)}")
        raise e

    print("\n✅ Tất cả hệ thống đã sẵn sàng!")
    return True


def parse_args():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description="API cho RAG Pipeline")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host để chạy API")
    parser.add_argument("--port", type=int, default=8000, help="Port để chạy API")
    parser.add_argument(
        "--reload", action="store_true", help="Tự động reload khi code thay đổi"
    )
    return parser.parse_args()


def main():
    """Hàm main để chạy API"""
    args = parse_args()

    # Kiểm tra trạng thái hệ thống trước khi khởi động API
    check_system_ready()

    # In thông tin về API
    print(f"\n🚀 Đang khởi động API tại http://{args.host}:{args.port}")
    print("📚 Các API có sẵn:")
    print("  - GET /           : Kiểm tra trạng thái API")
    print("  - POST /query     : Truy vấn hệ thống với một câu hỏi")
    print("  - POST /upload    : Upload và index tài liệu (lưu vào thư mục cố định)")
    print("  - POST /index/files : Index dữ liệu từ các file (thư mục tạm)")
    print("  - POST /index/path : Index dữ liệu từ một thư mục")
    print("  - GET /index/status/{task_id} : Kiểm tra trạng thái của task indexing")
    print("  - GET /index/progress/{task_id} : Kiểm tra tiến trình chi tiết của task")
    print("  - GET /files      : Liệt kê tất cả các file đã upload")
    print("  - DELETE /files/{file_name} : Xóa file và embedding tương ứng")
    print("  - GET /uploads    : Liệt kê các thư mục upload")
    print("  - DELETE /index   : Xóa toàn bộ index")
    print("📖 Truy cập API docs tại: http://localhost:8000/docs")

    # Chạy API với Uvicorn
    uvicorn.run("src.api:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
