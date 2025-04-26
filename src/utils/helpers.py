import os
import time
from typing import List, Dict, Any
from langchain.schema import Document


def get_file_extension(file_path: str) -> str:
    """Lấy phần mở rộng của file"""
    return os.path.splitext(file_path)[1].lower()


def measure_time(func):
    """Decorator để đo thời gian thực thi của hàm"""

    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"✅ {func.__name__} thực thi trong {end_time - start_time:.2f} giây")
        return result

    return wrapper


def print_document_info(docs: List[Document], title: str = "Thông tin tài liệu"):
    """In thông tin các tài liệu"""
    print(f"==== {title} ====")
    print(f"Số lượng: {len(docs)}")
    if docs:
        print(f"Ví dụ tài liệu đầu tiên: {docs[0].page_content[:100]}...")
    print("=" * (len(title) + 12))


def format_context_for_llm(docs: List[Document]) -> str:
    """Format danh sách tài liệu thành văn bản context cho LLM

    Cải tiến:
    - Bảo toàn cấu trúc đoạn văn và danh sách liệt kê
    - Thêm dấu hiệu phân biệt giữa các tài liệu
    - Xử lý đặc biệt với nội dung liệt kê
    """
    # Sắp xếp tài liệu theo mức độ liên quan (giả định là thứ tự trong danh sách)
    formatted_docs = []

    for i, doc in enumerate(docs):
        # Xác định xem tài liệu có chứa nội dung liệt kê hay không
        has_list_content = doc.metadata.get("has_list_content", False)

        # Lấy nguồn (nếu có)
        source = doc.metadata.get("source", f"Document {i+1}")

        # Format tài liệu với tiêu đề nguồn và đảm bảo giữ nguyên cấu trúc đoạn văn
        content = doc.page_content.strip()

        # Đặc biệt xử lý nội dung có danh sách liệt kê
        if has_list_content:
            # Đảm bảo giữ nguyên định dạng xuống dòng của danh sách liệt kê
            formatted_item = f"--- NGUỒN: {source} ---\n{content}\n"
        else:
            # Với nội dung thông thường
            formatted_item = f"--- NGUỒN: {source} ---\n{content}\n"

        formatted_docs.append(formatted_item)

    # Kết hợp tất cả tài liệu với dấu hiệu phân tách rõ ràng
    return "\n\n" + "\n\n".join(formatted_docs)


def extract_source_info(docs: List[Document]) -> List[Dict[str, Any]]:
    """Trích xuất thông tin về nguồn từ danh sách tài liệu

    Args:
        docs: Danh sách tài liệu

    Returns:
        Danh sách các thông tin về nguồn
    """
    sources = []
    for i, doc in enumerate(docs):
        # Lấy thông tin nguồn từ metadata
        source_info = {
            "index": i,
            "source": doc.metadata.get("source", "Unknown"),
            "source_path": doc.metadata.get("source_path", ""),
            "file_type": doc.metadata.get("file_type", ""),
            "chunk_length": doc.metadata.get("chunk_length", 0),
            "chunk_word_count": doc.metadata.get("chunk_word_count", 0),
            "start_index": doc.metadata.get("start_index", 0),
            "chunk_count": doc.metadata.get("chunk_count", 1),
            "has_list_content": doc.metadata.get("has_list_content", False),
            "content_preview": (
                doc.page_content[:200] + "..."
                if len(doc.page_content) > 200
                else doc.page_content
            ),
        }
        sources.append(source_info)

    return sources
