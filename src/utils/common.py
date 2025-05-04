import time
import functools
import os
from typing import List, Dict, Any, Callable, Union
from langchain.schema import Document


def print_document_info(
    docs: List[Document], title: str = "Thông tin tài liệu"
) -> None:
    """In thông tin về danh sách các Document

    Args:
        docs: Danh sách các Document cần in thông tin
        title: Tiêu đề khi in thông tin
    """
    print(f"\n{'='*20} {title} {'='*20}")
    print(f"Số lượng documents: {len(docs)}")

    for i, doc in enumerate(docs, 1):
        metadata = doc.metadata or {}
        source = metadata.get("source", "Unknown")
        content_length = len(doc.page_content)
        word_count = len(doc.page_content.split())

        print(f"\nDocument {i}:")
        print(f"  - Nguồn: {source}")
        print(f"  - Độ dài: {content_length} ký tự, {word_count} từ")

        # In thêm thông tin về trang nếu có
        if "page_number" in metadata:
            print(f"  - Trang: {metadata['page_number']}")

        # In thêm thông tin về file_type nếu có
        if "file_type" in metadata:
            print(f"  - Loại file: {metadata['file_type']}")

        # In preview nội dung
        preview = (
            doc.page_content[:100] + "..."
            if len(doc.page_content) > 100
            else doc.page_content
        )
        print(f"  - Preview: {preview}")

    print(f"{'='*50}\n")


def get_file_extension(file_path: str) -> str:
    """Lấy phần mở rộng của file từ đường dẫn

    Args:
        file_path: Đường dẫn đến file

    Returns:
        Phần mở rộng của file (không bao gồm dấu chấm)
    """
    _, ext = os.path.splitext(file_path)
    return ext.lower().lstrip(".")


def measure_time(func: Callable) -> Callable:
    """Decorator để đo thời gian thực thi của một hàm

    Args:
        func: Hàm cần đo thời gian

    Returns:
        Hàm wrapper với thời gian thực thi được thêm vào kết quả
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time

        if isinstance(result, dict):
            # Lưu thời gian thực thi vào kết quả nếu là dict
            result[f"{func.__name__}_time"] = execution_time

        print(f"⏱️ Thời gian thực thi {func.__name__}: {execution_time:.2f}s")
        return result

    return wrapper


def format_context_for_llm(docs: List[Document]) -> str:
    """Định dạng danh sách các Document thành string cho LLM

    Args:
        docs: Danh sách Document

    Returns:
        String được định dạng để sử dụng trong prompt
    """
    # Tạo một context tổng hợp từ tất cả tài liệu
    formatted_docs = []

    for i, doc in enumerate(docs, 1):
        # Trích xuất metadata
        metadata = doc.metadata or {}
        source = metadata.get("source", "Unknown")
        page = metadata.get("page_number", "")
        page_info = f" (trang {page})" if page else ""

        # Định dạng các tài liệu
        formatted_doc = f"""--- DOCUMENT {i}: {source}{page_info} ---
{doc.page_content}
"""
        formatted_docs.append(formatted_doc)

    # Kết hợp tất cả các tài liệu
    return "\n\n".join(formatted_docs)


def extract_source_info(docs: List[Document]) -> List[Dict[str, Any]]:
    """Trích xuất thông tin về nguồn từ danh sách các Document

    Args:
        docs: Danh sách Document

    Returns:
        List các dict chứa thông tin về nguồn
    """
    sources = []

    for i, doc in enumerate(docs):
        metadata = doc.metadata or {}
        source_path = metadata.get("source", "Unknown")

        # Trích xuất thông tin từ metadata
        source_info = {
            "index": i,
            "source": source_path.split("/")[-1] if "/" in source_path else source_path,
            "source_path": source_path,
            "file_type": metadata.get("file_type", "unknown"),
            "chunk_length": len(doc.page_content),
            "chunk_word_count": len(doc.page_content.split()),
            "start_index": metadata.get("start_index", 0),
            "chunk_count": metadata.get("chunk_count", 1),
            "has_list_content": bool(metadata.get("has_list_content", False)),
            "content_preview": (
                doc.page_content[:150] + "..."
                if len(doc.page_content) > 150
                else doc.page_content
            ),
        }

        # Thêm các metadata khác nếu có
        if "page_number" in metadata:
            source_info["page_number"] = metadata["page_number"]

        if "image_paths" in metadata:
            source_info["image_paths"] = metadata["image_paths"]

        if "pdf_element_type" in metadata:
            source_info["pdf_element_type"] = metadata["pdf_element_type"]

        sources.append(source_info)

    return sources
