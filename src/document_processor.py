import os
import re
import numpy as np
import cv2
from PIL import Image
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict, Optional, Tuple, Any


class DocumentProcessor:
    """Lớp quản lý việc tải và xử lý tài liệu"""

    def __init__(
        self, chunk_size=800, chunk_overlap=150, enable_layout_detection=False
    ):
        """Khởi tạo bộ xử lý tài liệu với kích thước chunk nhỏ hơn để tìm kiếm chính xác hơn"""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ".", " ", ""],
        )

        # Khởi tạo các loader cho từng loại tài liệu
        self.loaders = {
            ".pdf": PyPDFLoader,
            ".docx": Docx2txtLoader,
            ".txt": TextLoader,
            ".sql": TextLoader,
        }

        # Định nghĩa các từ khóa để phân loại tài liệu
        self.category_keywords = {
            "sql": [
                "sql",
                "select",
                "insert",
                "update",
                "delete",
                "join",
                "where",
                "group by",
                "order by",
                "index",
                "primary key",
                "foreign key",
                "constraint",
                "view",
                "stored procedure",
                "trigger",
                "transaction",
            ],
            "nosql": [
                "nosql",
                "mongodb",
                "redis",
                "cassandra",
                "neo4j",
                "dynamodb",
                "firebase",
                "couchbase",
                "document store",
                "key-value",
                "graph database",
                "column family",
            ],
            "database_design": [
                "schema",
                "normalization",
                "denormalization",
                "entity relationship",
                "er diagram",
                "data modeling",
                "logical design",
                "physical design",
                "cardinality",
                "attribute",
                "primary key",
                "foreign key",
                "dbms",
                "database management system",
            ],
            "database_administration": [
                "backup",
                "restore",
                "replication",
                "high availability",
                "disaster recovery",
                "performance tuning",
                "user management",
                "permission",
                "monitor",
                "security",
                "maintenance",
                "optimization",
                "audit",
            ],
            "data_warehouse": [
                "data warehouse",
                "olap",
                "oltp",
                "star schema",
                "snowflake schema",
                "fact table",
                "dimension table",
                "etl",
                "extract transform load",
                "bi",
                "business intelligence",
                "reporting",
                "analytics",
            ],
        }

        # Đặt layout detection luôn là False
        self.enable_layout_detection = False
        self.use_structural_chunking = True
        print("Layout detection bị tắt. Sử dụng phương pháp chunking thông thường")

        # Cấu hình cho chunking
        self.max_tokens_per_chunk = 512  # Giới hạn token cho mỗi chunk
        self.min_paragraph_length = (
            50  # Độ dài tối thiểu của paragraph để không bị coi là noise
        )

        # Áp dụng chunking cấu trúc mặc định
        self.use_structural_chunking = True

    def detect_layout(self, image_path: str) -> Optional[List[Dict]]:
        """Phương thức giả lấp, không còn sử dụng layout detection"""
        print("Layout detection đã bị vô hiệu hóa")
        return None

    def extract_text_from_regions(self, image, regions, ocr_engine=None):
        """Phương thức giả lấp, không còn sử dụng layout detection"""
        print("Layout detection đã bị vô hiệu hóa")
        return regions

    def filter_and_group_regions(self, regions: List[Dict]) -> List[Dict]:
        """Phương thức giả lấp, không còn sử dụng layout detection"""
        print("Layout detection đã bị vô hiệu hóa")
        return []

    def _chunk_by_structure(self, text: str, metadata: Dict) -> List[Dict]:
        """Chia nhỏ văn bản theo cấu trúc"""
        # Xác định các tiêu đề qua pattern dùng regex
        heading_patterns = [
            r"^#+\s+(.+)$",  # Markdown headings
            r"^(\d+\.)\s+(.+)$",  # Numbered headings like "1. Title"
            r"^(Chapter|Section|Phần|Chương)\s+\d+:?\s*(.+)$",  # Chapter/Section headings
            r"^([A-Z][A-Z\s]+)$",  # ALL CAPS HEADINGS
        ]

        # Chia văn bản thành các đoạn
        paragraphs = re.split(r"\n\s*\n", text)
        if not paragraphs:
            return []

        # Xác định các đoạn văn là tiêu đề
        structured_chunks = []
        current_heading = None
        current_content = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Kiểm tra xem đoạn hiện tại có phải là tiêu đề không
            is_heading = False
            for pattern in heading_patterns:
                if re.match(pattern, para, re.MULTILINE):
                    is_heading = True
                    break

            # Nếu là tiêu đề hoặc độ dài ngắn và kết thúc mà không có dấu chấm cuối
            if is_heading or (
                len(para) < 100
                and not para.endswith(".")
                and not para.endswith("?")
                and not para.endswith("!")
            ):
                # Lưu nội dung trước đó nếu có
                if current_content:
                    chunk_text = "\n\n".join(current_content)
                    structured_chunks.append(
                        {
                            "heading": current_heading if current_heading else "",
                            "content": chunk_text,
                            "type": "section",
                        }
                    )

                # Bắt đầu chunk mới
                current_heading = para
                current_content = []
            else:
                # Thêm đoạn văn vào nội dung hiện tại
                current_content.append(para)

        # Thêm chunk cuối cùng nếu có
        if current_content:
            chunk_text = "\n\n".join(current_content)
            structured_chunks.append(
                {
                    "heading": current_heading if current_heading else "",
                    "content": chunk_text,
                    "type": "section",
                }
            )

        # Chuyển đổi cấu trúc thành các document
        documents = []
        for i, chunk in enumerate(structured_chunks):
            # Tạo văn bản có cấu trúc
            if chunk["heading"]:
                chunk_text = f"{chunk['heading']}\n\n{chunk['content']}"
            else:
                chunk_text = chunk["content"]

            # Thêm metadata
            chunk_metadata = {
                **metadata,
                "chunk_id": i,
                "chunk_type": chunk["type"],
            }

            documents.append(
                {"text": chunk_text, "id": f"{i}", "metadata": chunk_metadata}
            )

        return documents

    def _chunk_by_size(self, text: str, metadata: Dict) -> List[Dict]:
        """Chia văn bản thành các đoạn có kích thước cố định"""
        # Sử dụng RecursiveCharacterTextSplitter để chia đều văn bản
        chunks = self.text_splitter.create_documents([text], [metadata])

        # Chuyển đổi LangChain Document thành định dạng dict
        results = []
        for i, chunk in enumerate(chunks):
            # Tạo metadata bổ sung cho chunk khi chia theo kích thước
            enhanced_metadata = dict(chunk.metadata)

            # Thêm thông tin về vị trí và loại chunk
            if "page" not in enhanced_metadata:
                # Nếu không có thông tin trang, đánh số chunk
                enhanced_metadata["chunk_index"] = i
                enhanced_metadata["page"] = enhanced_metadata.get(
                    "page", f"chunk_{i+1}"
                )

            # Thêm thông tin về loại chunk (mặc định là text khi chia theo kích thước)
            enhanced_metadata["chunk_type"] = enhanced_metadata.get(
                "chunk_type", "text"
            )
            enhanced_metadata["position"] = f"chunk {i+1} of {len(chunks)}"

            results.append(
                {
                    "id": str(i),
                    "text": chunk.page_content,
                    "metadata": enhanced_metadata,
                    "source": enhanced_metadata.get("source", "unknown"),
                }
            )

        return results

    def load_documents(self, data_dir: str) -> List[Dict]:
        """Tải đa dạng loại tài liệu từ thư mục"""
        documents = []
        for file in os.listdir(data_dir):
            file_path = os.path.join(data_dir, file)
            ext = os.path.splitext(file)[1].lower()

            if ext in self.loaders:
                try:
                    loader = self.loaders[ext](file_path)
                    loaded_docs = loader.load()

                    # Thêm tên tập tin vào metadata nếu chưa có
                    for doc in loaded_docs:
                        if "source" not in doc.metadata:
                            doc.metadata["source"] = file

                    documents.extend(loaded_docs)
                except Exception as e:
                    print(f"Error loading {file_path}: {str(e)}")

        return documents

    def process_documents(self, documents: List[Dict]) -> List[Dict]:
        """Xử lý và chia nhỏ tài liệu"""
        processed_chunks = []

        for doc in documents:
            # Xử lý đối tượng Document từ LangChain
            if hasattr(doc, "page_content") and hasattr(doc, "metadata"):
                # Đây là LangChain Document
                text = doc.page_content
                metadata = doc.metadata or {}
            else:
                # Nếu là dict hoặc định dạng khác
                text = doc.get("text", doc.get("page_content", ""))
                metadata = doc.get("metadata", {})

            # Phân loại tài liệu theo nội dung nếu chưa có category
            if "category" not in metadata:
                category = self._classify_document_content(text)
                metadata["category"] = category

            # Phương pháp chunking phụ thuộc vào cấu hình
            if self.use_structural_chunking:
                chunks = self._chunk_by_structure(text, metadata)
            else:
                chunks = self._chunk_by_size(text, metadata)

            processed_chunks.extend(chunks)

        return processed_chunks

    def _classify_document_content(self, text: str) -> str:
        """Phân loại nội dung tài liệu dựa trên từ khóa"""
        text_lower = text.lower()

        # Đếm số lượng từ khóa khớp với mỗi loại
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                # Đếm số lần từ khóa xuất hiện trong văn bản
                matches = len(
                    re.findall(r"\b" + re.escape(keyword) + r"\b", text_lower)
                )
                score += matches

            # Chuẩn hóa điểm số theo độ dài của văn bản
            category_scores[category] = score / (len(text_lower.split()) + 1) * 100

        # Lựa chọn loại có điểm cao nhất
        if category_scores:
            max_category = max(category_scores.items(), key=lambda x: x[1])

            # Nếu điểm số quá thấp, coi như không phân loại được
            if max_category[1] > 0.5:  # Ngưỡng phân loại
                return max_category[0]

        # Mặc định nếu không phân loại được
        return "general"

    def load_document_with_category(
        self, file_path: str, category: str = None
    ) -> List[Dict]:
        """Tải một tài liệu với danh mục được chỉ định trước"""
        ext = os.path.splitext(file_path)[1].lower()

        if ext not in self.loaders:
            print(f"Định dạng {ext} không được hỗ trợ")
            return []

        try:
            loader = self.loaders[ext](file_path)
            documents = loader.load()

            # Thêm metadata và category
            for doc in documents:
                if not hasattr(doc, "metadata"):
                    # Nếu không phải Document object, bỏ qua
                    continue

                if "source" not in doc.metadata:
                    doc.metadata["source"] = os.path.basename(file_path)

                # Gán category nếu được chỉ định, ngược lại tự động phân loại
                if category:
                    doc.metadata["category"] = category
                else:
                    doc.metadata["category"] = self._classify_document_content(
                        doc.page_content
                    )

            return documents

        except Exception as e:
            print(f"Lỗi khi tải tài liệu {file_path}: {str(e)}")
            return []

    def process_pdf_with_layout(
        self, pdf_path: str, category: str = None
    ) -> List[Dict]:
        """Xử lý tài liệu PDF không sử dụng layout detection"""
        print(
            f"\n=== Bắt đầu xử lý {os.path.basename(pdf_path)} không sử dụng layout detection ==="
        )

        documents = self.load_document_with_category(pdf_path, category)
        # Chuyển đổi documents từ LangChain sang định dạng dict
        processed_chunks = []
        for idx, doc in enumerate(documents):
            processed_chunks.append(
                {
                    "id": str(idx),
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                    "source": doc.metadata.get("source", "unknown"),
                    "category": doc.metadata.get("category", "general"),
                }
            )
        print(
            f"Đã xử lý {len(processed_chunks)} chunks với phương pháp tải thông thường"
        )
        return processed_chunks

    def check_layoutparser_installation(self) -> Dict:
        """Hàm giả lập kiểm tra layoutparser luôn trả về False vì không dùng layout detection nữa"""
        return {
            "ready": False,
            "status": {
                "layoutparser": False,
                "opencv": True,
                "pdf2image": True,
                "tesseract": False,
                "poppler": False,
            },
            "details": {
                "tesseract": {"error": "Layout detection has been disabled"},
                "poppler": {"error": "Layout detection has been disabled"},
            },
            "missing_components": ["Layout detection has been disabled"],
            "installation_tips": {
                "message": "Layout detection đã bị vô hiệu hóa trong hệ thống này."
            },
        }

    def _check_requirements(self):
        """Kiểm tra các yêu cầu cài đặt, luôn tắt layout detection"""
        self.enable_layout_detection = False
        self.use_structural_chunking = True
        return
