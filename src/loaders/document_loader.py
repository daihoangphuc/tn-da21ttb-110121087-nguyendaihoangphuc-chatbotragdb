import os
import logging
from typing import List, Tuple
from langchain.schema import Document
from langchain_core.documents.base import Blob
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import time

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

        # Tự động tăng số lượng workers nếu CPU có nhiều lõi
        import multiprocessing

        cpu_count = multiprocessing.cpu_count()
        if cpu_count > max_workers * 2:  # Nếu có nhiều CPU hơn gấp đôi max_workers
            max_workers = min(
                cpu_count - 2, 16
            )  # Giới hạn tối đa 16 workers và giữ lại 2 lõi cho hệ thống
            print(
                f"ℹ️ Tự động điều chỉnh số workers lên {max_workers} (CPU cores: {cpu_count})"
            )

        # Thu thập danh sách file cần xử lý
        file_paths = []
        for root, _, files in os.walk(directory_path):
            for fname in files:
                # Lọc các file temporay, cache hoặc không phải là file văn bản thông thường
                if fname.startswith("~$") or fname.startswith("."):
                    continue

                path = os.path.join(root, fname)
                file_paths.append(path)

        print(
            f"🔍 Tìm thấy {len(file_paths)} file cần xử lý (sử dụng {max_workers} workers)."
        )

        # Theo dõi thời gian
        start_time = time.time()
        file_times = {}

        # Xử lý song song với ThreadPoolExecutor
        docs = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit các task với chunksize để tối ưu hóa hiệu suất xử lý
            # Chunksize giúp mỗi worker nhận nhiều task cùng lúc, giảm overhead
            chunksize = max(1, len(file_paths) // (max_workers * 2))
            print(f"ℹ️ Sử dụng chunksize={chunksize} cho ThreadPoolExecutor")

            # Thu thập kết quả với thanh tiến trình tqdm
            progress_bar = tqdm(
                total=len(file_paths), desc="Loading documents", unit="file"
            )

            # Sử dụng map với chunksize thay vì submit từng tác vụ riêng biệt
            # Điều này sẽ hiệu quả hơn với số lượng file lớn
            for file_idx, (path, result_docs) in enumerate(
                zip(
                    file_paths,
                    executor.map(
                        DocumentLoader._load_file_safe, file_paths, chunksize=chunksize
                    ),
                )
            ):
                try:
                    # Tính thời gian xử lý cho file hiện tại
                    file_time = time.time() - start_time
                    start_time = time.time()
                    file_times[path] = file_time

                    # Cập nhật kết quả
                    if result_docs:
                        docs.extend(result_docs)

                    # Tính thời gian xử lý trung bình
                    avg_time = sum(file_times.values()) / len(file_times)
                    progress_bar.set_postfix_str(
                        f"File: {os.path.basename(path)} → {len(result_docs) if result_docs else 0} tài liệu ({file_time:.2f}s, avg: {avg_time:.2f}s/file)"
                    )
                    progress_bar.update(1)
                except Exception as e:
                    progress_bar.set_postfix_str(f"Lỗi: {path} - {str(e)}")
                    progress_bar.update(1)
                    print(f"⚠️ Lỗi khi đọc file {path}: {str(e)}")

            progress_bar.close()

        total_docs = len(docs)
        total_files = len(file_paths)
        docs_per_file = total_docs / total_files if total_files > 0 else 0
        print(
            f"✅ Đã load được {total_docs} tài liệu từ {total_files} file (trung bình: {docs_per_file:.1f} tài liệu/file)."
        )
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

        # Thay vì sử dụng cả hai phương pháp, chỉ sử dụng PDFPlumberLoader vì nhanh hơn
        try:
            plumber_loader = PDFPlumberLoader(path, extract_images=True)
            docs.extend(plumber_loader.load())
            print(f"  - Đã xử lý PDF với PDFPlumberLoader: {len(docs)} trang")
            return docs
        except Exception as e:
            print(
                f"  - Lỗi khi sử dụng PDFPlumberLoader: {str(e)}, thử dùng PDFMinerParser..."
            )
            # Backup: Nếu PDFPlumberLoader thất bại, dùng PDFMinerParser
            try:
                blob = Blob.from_path(path)
                miner_parser = PDFMinerParser(extract_images=True)
                docs.extend(miner_parser.parse(blob))
                print(f"  - Đã xử lý PDF với PDFMinerParser: {len(docs)} trang")
                return docs
            except Exception as e2:
                print(f"  - Lỗi khi sử dụng PDFMinerParser: {str(e2)}")
                raise e2

    @staticmethod
    def _load_image(path: str) -> List[Document]:
        """Load tài liệu ảnh"""
        img_loader = UnstructuredImageLoader(path)
        return img_loader.load()
