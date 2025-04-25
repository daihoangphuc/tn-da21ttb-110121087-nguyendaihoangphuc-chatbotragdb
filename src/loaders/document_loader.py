import os
import logging
from typing import List, Tuple
from langchain.schema import Document
from langchain_core.documents.base import Blob
from concurrent.futures import ThreadPoolExecutor

# Loader & Parser cho PDF và Image
from langchain_community.document_loaders.pdf import PDFPlumberLoader
from langchain_community.document_loaders.parsers.pdf import PDFMinerParser
from langchain_community.document_loaders import UnstructuredImageLoader

# Các loader khác
from langchain_community.document_loaders import (
    UnstructuredMarkdownLoader,
    UnstructuredHTMLLoader,
    UnstructuredExcelLoader,
    CSVLoader,
    JSONLoader,
    TextLoader,
    Docx2txtLoader,
)

from src.utils import get_file_extension, measure_time
from src.config import DOCUMENT_LOADER_MAX_WORKERS

# Cấu hình logging
logging.getLogger("pdfminer").setLevel(logging.ERROR)
logging.getLogger("PIL").setLevel(logging.ERROR)


class DocumentLoader:
    """Lớp xử lý việc load tài liệu từ nhiều định dạng"""

    @staticmethod
    @measure_time
    def load_documents(directory_path: str, max_workers=None) -> List[Document]:
        """Load tất cả tài liệu từ thư mục đã cho sử dụng đa luồng

        Args:
            directory_path: Đường dẫn đến thư mục chứa tài liệu
            max_workers: Số lượng luồng tối đa, mặc định lấy từ cấu hình DOCUMENT_LOADER_MAX_WORKERS

        Returns:
            Danh sách các tài liệu đã load
        """
        # Sử dụng giá trị từ cấu hình nếu không chỉ định max_workers
        if max_workers is None:
            max_workers = DOCUMENT_LOADER_MAX_WORKERS

        # Thu thập danh sách file cần xử lý
        file_paths = []
        for root, _, files in os.walk(directory_path):
            for fname in files:
                path = os.path.join(root, fname)
                file_paths.append(path)

        print(
            f"🔍 Tìm thấy {len(file_paths)} file cần xử lý (sử dụng {max_workers} workers)."
        )

        # Xử lý song song với ThreadPoolExecutor
        docs = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit các task
            future_to_path = {
                executor.submit(DocumentLoader._load_file_safe, path): path
                for path in file_paths
            }

            # Thu thập kết quả
            for i, future in enumerate(future_to_path):
                path = future_to_path[future]
                try:
                    result_docs = future.result()
                    docs.extend(result_docs)
                    print(
                        f"✓ [{i+1}/{len(file_paths)}] Đã xử lý: {path} → {len(result_docs)} tài liệu"
                    )
                except Exception as e:
                    print(
                        f"⚠️ [{i+1}/{len(file_paths)}] Lỗi khi đọc file {path}: {str(e)}"
                    )

        print(f"✅ Đã load được {len(docs)} tài liệu từ {len(file_paths)} file.")
        return docs

    @staticmethod
    def _load_file_safe(path: str) -> List[Document]:
        """Phiên bản an toàn của _load_file để dùng với executor"""
        try:
            return DocumentLoader._load_file(path)
        except Exception as e:
            print(f"⚠️ Lỗi khi đọc file {path}: {str(e)}")
            return []

    @staticmethod
    def _load_file(path: str) -> List[Document]:
        """Load một file cụ thể dựa trên định dạng"""
        ext = get_file_extension(path)

        # Lấy tên file và đường dẫn tuyệt đối để lưu vào metadata
        file_name = os.path.basename(path)
        abs_path = os.path.abspath(path)

        # Load document dựa trên định dạng
        docs = []
        if ext == ".pdf":
            docs = DocumentLoader._load_pdf(path)
        elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"]:
            docs = DocumentLoader._load_image(path)
        elif ext == ".md":
            docs = UnstructuredMarkdownLoader(path, mode="elements").load()
        elif ext == ".html":
            docs = UnstructuredHTMLLoader(path, mode="elements").load()
        elif ext in [".xlsx", ".xls"]:
            docs = UnstructuredExcelLoader(path, mode="elements").load()
        elif ext == ".csv":
            docs = CSVLoader(path, csv_args={"delimiter": ","}).load()
        elif ext == ".tsv":
            docs = CSVLoader(path, csv_args={"delimiter": "\t"}).load()
        elif ext == ".json":
            docs = JSONLoader(path).load()
        elif ext == ".docx":
            docs = Docx2txtLoader(path).load()
        else:
            docs = TextLoader(path).load()

        # Thêm thông tin nguồn gốc vào metadata của mỗi document
        for doc in docs:
            # Đảm bảo metadata tồn tại
            if doc.metadata is None:
                doc.metadata = {}

            # Bổ sung thông tin nguồn gốc
            doc.metadata["source"] = file_name
            doc.metadata["source_path"] = path  # Đường dẫn tương đối
            doc.metadata["file_path"] = abs_path  # Đường dẫn tuyệt đối
            doc.metadata["file_type"] = ext

        return docs

    @staticmethod
    def _load_pdf(path: str) -> List[Document]:
        """Load tài liệu PDF kết hợp nhiều phương pháp"""
        docs = []

        # — Thứ tự: PDFPlumberLoader (text + images) → PDFMinerParser (bảng, hình ảnh nhúng)
        plumber_loader = PDFPlumberLoader(path, extract_images=True)
        docs.extend(plumber_loader.load())

        blob = Blob.from_path(path)
        miner_parser = PDFMinerParser(extract_images=True)
        docs.extend(miner_parser.parse(blob))

        return docs

    @staticmethod
    def _load_image(path: str) -> List[Document]:
        """Load tài liệu ảnh"""
        img_loader = UnstructuredImageLoader(path)
        return img_loader.load()
