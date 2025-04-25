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
    """Format danh sách tài liệu thành văn bản context cho LLM"""
    return "\n\n".join(d.page_content for d in docs)
