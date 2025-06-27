import os
import logging
import subprocess
import shutil
import re
import uuid
from typing import List, Dict
import asyncio

from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ------------------------------------------------------------
# Logging helpers
# ------------------------------------------------------------
logging.basicConfig(format="[Document Processor] %(message)s", level=logging.INFO)
_original_print = print

def print(*args, **kwargs):
    """Override built‑in print to include a prefix for consistency with logging."""
    prefix = "[Document Processor] "
    _original_print(prefix + " ".join(map(str, args)), **kwargs)


logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# DocumentProcessor
# ------------------------------------------------------------
class DocumentProcessor:
    """Manage loading, normalising, and chunking documents for RAG với hỗ trợ async."""

    # --------------------------------------------------------
    # Construction helpers
    # --------------------------------------------------------
    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None):
        """Initialise with optional overrides for chunk sizing.
        The public API is unchanged so that other modules' imports remain valid.
        """
        default_chunk_size = 800
        default_chunk_overlap = 150

        try:
            chunk_size_env = os.getenv("CHUNK_SIZE")
            chunk_overlap_env = os.getenv("CHUNK_OVERLAP")
            self.chunk_size = int(chunk_size_env) if chunk_size_env else chunk_size or default_chunk_size
            self.chunk_overlap = (
                int(chunk_overlap_env) if chunk_overlap_env else chunk_overlap or default_chunk_overlap
            )
        except ValueError as exc:
            print(
                "Lỗi khi đọc cấu hình chunk từ biến môi trường: "
                f"{exc}.  Sử dụng giá trị mặc định size={default_chunk_size}, overlap={default_chunk_overlap}"
            )
            self.chunk_size = default_chunk_size
            self.chunk_overlap = default_chunk_overlap

        print(f"Cấu hình chunk: size={self.chunk_size}, overlap={self.chunk_overlap}")

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ".", " ", ""],
        )

        # Loader mapping (unchanged)
        self.loaders = {
            ".pdf": PyPDFLoader,
            ".docx": Docx2txtLoader,
            ".txt": TextLoader,
            ".sql": TextLoader,
            ".md": TextLoader,
        }

        # Category keyword map (unchanged)
        self.category_keywords: Dict[str, List[str]] = {
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

        # Toggle for structure‑aware chunking
        self.use_structural_chunking = True

        # Formats eligible for conversion to PDF via LibreOffice
        self.convertible_formats = [
            ".sql",
            ".doc",
            ".docx",
            ".ppt",
            ".pptx",
            ".xls",
            ".xlsx",
            ".odt",
            ".ods",
            ".odp",
        ]

        # Default LibreOffice path – override with env var LIBREOFFICE_PATH if needed
        self.libreoffice_path = self._get_default_libreoffice_path()

    # --------------------------------------------------------
    # Conversion helpers
    # --------------------------------------------------------
    def _get_default_libreoffice_path(self):
        """Tự động detect LibreOffice path theo platform"""
        # Kiểm tra biến môi trường trước
        env_path = os.getenv("LIBREOFFICE_PATH")
        if env_path and os.path.exists(env_path):
            return env_path
        
        import platform
        system = platform.system().lower()
        
        if system == "windows":
            # Các đường dẫn phổ biến trên Windows
            possible_paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                r"C:\Program Files\LibreOffice 7\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice 7\program\soffice.exe",
            ]
        elif system == "darwin":  # macOS
            possible_paths = [
                "/Applications/LibreOffice.app/Contents/MacOS/soffice",
                "/usr/local/bin/soffice",
            ]
        else:  # Linux và Unix-like systems
            possible_paths = [
                "/usr/bin/libreoffice",
                "/usr/local/bin/libreoffice",
                "/snap/bin/libreoffice",
                "/usr/bin/soffice",
                "/usr/local/bin/soffice",
            ]
        
        # Tìm path đầu tiên tồn tại
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Tìm thấy LibreOffice tại: {path}")
                return path
        
        # Nếu không tìm thấy, thử tìm trong PATH
        import shutil
        soffice_in_path = shutil.which("soffice") or shutil.which("libreoffice")
        if soffice_in_path:
            print(f"Tìm thấy LibreOffice trong PATH: {soffice_in_path}")
            return soffice_in_path
        
        # Trường hợp cuối cùng, dùng default của Windows (backward compatibility)
        default_path = r"C:\Program Files\LibreOffice\program\soffice.exe"
        print(f"Không tìm thấy LibreOffice, sử dụng path mặc định: {default_path}")
        return default_path
    def get_converted_path(self, input_path: str) -> str:
        """Return the path to the PDF version of *input_path* if it already exists."""
        file_ext = os.path.splitext(input_path)[1].lower()
        if file_ext == ".pdf" or file_ext not in self.convertible_formats:
            return input_path

        output_dir = os.path.dirname(input_path)
        file_stem = os.path.splitext(os.path.basename(input_path))[0]
        pdf_path = os.path.join(output_dir, f"{file_stem}.pdf")
        return pdf_path if os.path.exists(pdf_path) else input_path

    async def convert_to_pdf(self, input_path: str, *, remove_original: bool = True) -> str:
        """Convert *input_path* to PDF (if recognised format) using LibreOffice (bất đồng bộ)."""
        file_ext = os.path.splitext(input_path)[1].lower()
        
        # If already PDF or not a convertible format, return as-is
        if file_ext == ".pdf" or file_ext not in self.convertible_formats:
            return input_path

        output_dir = os.path.dirname(input_path)
        pdf_path = self.get_converted_path(input_path)

        # If PDF version already exists, return it
        if os.path.exists(pdf_path):
            print(f"PDF version already exists: {pdf_path}")
            if remove_original and input_path != pdf_path:
                os.remove(input_path)
            return pdf_path

        if not os.path.exists(self.libreoffice_path):
            print(f"LibreOffice not found at {self.libreoffice_path}. Returning original file.")
            return input_path

        try:
            print(f"Converting {input_path} to PDF using LibreOffice...")
            
            # Run LibreOffice conversion in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [
                        self.libreoffice_path,
                        "--headless",
                        "--convert-to", "pdf",
                        "--outdir", output_dir,
                        input_path
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            )

            if result.returncode == 0 and os.path.exists(pdf_path):
                print(f"Successfully converted to PDF: {pdf_path}")
                if remove_original:
                    os.remove(input_path)
                return pdf_path
            else:
                print(f"LibreOffice conversion failed: {result.stderr}")
                return input_path

        except subprocess.TimeoutExpired:
            print("LibreOffice conversion timed out")
            return input_path
        except Exception as e:
            print(f"Error during LibreOffice conversion: {str(e)}")
            return input_path

    def convert_to_pdf_sync(self, input_path: str, *, remove_original: bool = True) -> str:
        """Convert *input_path* to PDF (if recognised format) using LibreOffice (đồng bộ)."""
        file_ext = os.path.splitext(input_path)[1].lower()
        
        # If already PDF or not a convertible format, return as-is
        if file_ext == ".pdf" or file_ext not in self.convertible_formats:
            return input_path

        output_dir = os.path.dirname(input_path)
        pdf_path = self.get_converted_path(input_path)

        # If PDF version already exists, return it
        if os.path.exists(pdf_path):
            print(f"PDF version already exists: {pdf_path}")
            if remove_original and input_path != pdf_path:
                os.remove(input_path)
            return pdf_path

        if not os.path.exists(self.libreoffice_path):
            print(f"LibreOffice not found at {self.libreoffice_path}. Returning original file.")
            return input_path

        try:
            print(f"Converting {input_path} to PDF using LibreOffice...")
            result = subprocess.run(
                [
                    self.libreoffice_path,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", output_dir,
                    input_path
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and os.path.exists(pdf_path):
                print(f"Successfully converted to PDF: {pdf_path}")
                if remove_original:
                    os.remove(input_path)
                return pdf_path
            else:
                print(f"LibreOffice conversion failed: {result.stderr}")
                return input_path

        except subprocess.TimeoutExpired:
            print("LibreOffice conversion timed out")
            return input_path
        except Exception as e:
            print(f"Error during LibreOffice conversion: {str(e)}")
            return input_path

    @staticmethod
    def _ensure_page_metadata(docs: List):
        """Ensure each document has page metadata."""
        for i, doc in enumerate(docs):
            if not hasattr(doc, "metadata") or not doc.metadata:
                doc.metadata = {}
            
            # Try to extract page number from existing metadata
            page_num = doc.metadata.get("page", doc.metadata.get("page_number", i + 1))
            doc.metadata["page"] = page_num
            doc.metadata["page_number"] = page_num
            
            # Ensure source is present
            if "source" not in doc.metadata:
                doc.metadata["source"] = "unknown"
        
        return docs

    async def load_documents(self, data_dir: str) -> List[Dict]:
        """Load all documents from a directory (bất đồng bộ)."""
        documents = []
        
        if not os.path.exists(data_dir):
            print(f"Directory không tồn tại: {data_dir}")
            return documents
            
        for filename in os.listdir(data_dir):
            file_path = os.path.join(data_dir, filename)
            if os.path.isfile(file_path):
                try:
                    doc = await self.load_document_with_category(file_path)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    print(f"Lỗi khi load file {filename}: {str(e)}")
                    
        print(f"Đã load {len(documents)} documents từ {data_dir}")
        return documents

    def load_documents_sync(self, data_dir: str) -> List[Dict]:
        """Load all documents from a directory (đồng bộ)."""
        documents = []
        
        if not os.path.exists(data_dir):
            print(f"Directory không tồn tại: {data_dir}")
            return documents
            
        for filename in os.listdir(data_dir):
            file_path = os.path.join(data_dir, filename)
            if os.path.isfile(file_path):
                try:
                    doc = self.load_document_with_category_sync(file_path)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    print(f"Lỗi khi load file {filename}: {str(e)}")
                    
        print(f"Đã load {len(documents)} documents từ {data_dir}")
        return documents

    async def load_document_with_category(self, file_path: str, category: str | None = None):
        """Load a single document with automatic category detection (bất đồng bộ)."""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext not in self.loaders:
            print(f"Không hỗ trợ định dạng file: {file_ext}")
            return None
            
        try:
            # Convert to PDF if needed
            processed_path = await self.convert_to_pdf(file_path, remove_original=False)
            
            # Use appropriate loader
            final_ext = os.path.splitext(processed_path)[1].lower()
            loader_class = self.loaders.get(final_ext, TextLoader)
            
            # Load document in thread pool
            loop = asyncio.get_event_loop()
            docs = await loop.run_in_executor(
                None,
                lambda: loader_class(processed_path).load()
            )
            
            if not docs:
                return None
                
            # Ensure page metadata
            docs = self._ensure_page_metadata(docs)
            
            # Get document content for category detection
            content = " ".join([doc.page_content for doc in docs])
            detected_category = category or self._classify_document_content(content)
            
            return {
                "file_path": file_path,
                "processed_path": processed_path,
                "content": content,
                "category": detected_category,
                "docs": docs,
                "metadata": {
                    "source": os.path.basename(file_path),
                    "category": detected_category,
                    "file_ext": file_ext,
                    "total_pages": len(docs)
                }
            }
            
        except Exception as e:
            print(f"Lỗi khi load document {file_path}: {str(e)}")
            return None

    def load_document_with_category_sync(self, file_path: str, category: str | None = None):
        """Load a single document with automatic category detection (đồng bộ)."""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext not in self.loaders:
            print(f"Không hỗ trợ định dạng file: {file_ext}")
            return None
            
        try:
            # Convert to PDF if needed
            processed_path = self.convert_to_pdf_sync(file_path, remove_original=False)
            
            # Use appropriate loader
            final_ext = os.path.splitext(processed_path)[1].lower()
            loader_class = self.loaders.get(final_ext, TextLoader)
            
            docs = loader_class(processed_path).load()
            
            if not docs:
                return None
                
            # Ensure page metadata
            docs = self._ensure_page_metadata(docs)
            
            # Get document content for category detection
            content = " ".join([doc.page_content for doc in docs])
            detected_category = category or self._classify_document_content(content)
            
            return {
                "file_path": file_path,
                "processed_path": processed_path,
                "content": content,
                "category": detected_category,
                "docs": docs,
                "metadata": {
                    "source": os.path.basename(file_path),
                    "category": detected_category,
                    "file_ext": file_ext,
                    "total_pages": len(docs)
                }
            }
            
        except Exception as e:
            print(f"Lỗi khi load document {file_path}: {str(e)}")
            return None

    # --------------------------------------------------------
    # Chunking helpers
    # --------------------------------------------------------
    async def chunk_documents(self, documents: List[Dict]) -> List[Dict]:
        """Split documents into smaller chunks (bất đồng bộ)."""
        all_chunks = []
        
        for doc_data in documents:
            try:
                docs = doc_data.get("docs", [])
                if not docs:
                    continue
                    
                # Run chunking in thread pool
                loop = asyncio.get_event_loop()
                chunks = await loop.run_in_executor(
                    None,
                    lambda: self.text_splitter.split_documents(docs)
                )
                
                # Process chunks
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_dict = {
                        "text": chunk.page_content,
                        "metadata": chunk.metadata.copy(),
                        "source": chunk.metadata.get("source", "unknown"),
                        "chunk_id": f"{chunk.metadata.get('source', 'unknown')}_{chunk_idx}"
                    }
                    
                    # Add category and other metadata from document
                    chunk_dict["metadata"]["category"] = doc_data.get("category", "unknown")
                    chunk_dict["metadata"]["chunk_index"] = chunk_idx
                    chunk_dict["metadata"]["total_chunks"] = len(chunks)
                    
                    # Add rich metadata for better search
                    chunk_dict["metadata"].update(
                        await self._analyze_chunk_content(chunk.page_content)
                    )
                    
                    all_chunks.append(chunk_dict)
                    
            except Exception as e:
                print(f"Lỗi khi chunk document: {str(e)}")
                continue
                
        print(f"Đã tạo {len(all_chunks)} chunks từ {len(documents)} documents")
        return all_chunks

    def chunk_documents_sync(self, documents: List[Dict]) -> List[Dict]:
        """Split documents into smaller chunks (đồng bộ)."""
        all_chunks = []
        
        for doc_data in documents:
            try:
                docs = doc_data.get("docs", [])
                if not docs:
                    continue
                    
                chunks = self.text_splitter.split_documents(docs)
                
                # Process chunks
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_dict = {
                        "text": chunk.page_content,
                        "metadata": chunk.metadata.copy(),
                        "source": chunk.metadata.get("source", "unknown"),
                        "chunk_id": f"{chunk.metadata.get('source', 'unknown')}_{chunk_idx}"
                    }
                    
                    # Add category and other metadata from document
                    chunk_dict["metadata"]["category"] = doc_data.get("category", "unknown")
                    chunk_dict["metadata"]["chunk_index"] = chunk_idx
                    chunk_dict["metadata"]["total_chunks"] = len(chunks)
                    
                    # Add rich metadata for better search
                    chunk_dict["metadata"].update(
                        self._analyze_chunk_content_sync(chunk.page_content)
                    )
                    
                    all_chunks.append(chunk_dict)
                    
            except Exception as e:
                print(f"Lỗi khi chunk document: {str(e)}")
                continue
                
        print(f"Đã tạo {len(all_chunks)} chunks từ {len(documents)} documents")
        return all_chunks

    async def process_documents(self, data_dir: str) -> List[Dict]:
        """Complete document processing pipeline (bất đồng bộ)."""
        print(f"Bắt đầu xử lý documents từ {data_dir}")
        
        # Load documents
        documents = await self.load_documents(data_dir)
        if not documents:
            print("Không có documents nào để xử lý")
            return []
            
        # Chunk documents
        chunks = await self.chunk_documents(documents)
        return chunks

    def process_documents_sync(self, data_dir: str) -> List[Dict]:
        """Complete document processing pipeline (đồng bộ)."""
        print(f"Bắt đầu xử lý documents từ {data_dir}")
        
        # Load documents
        documents = self.load_documents_sync(data_dir)
        if not documents:
            print("Không có documents nào để xử lý")
            return []
            
        # Chunk documents
        chunks = self.chunk_documents_sync(documents)
        return chunks

    async def _analyze_chunk_content(self, content: str) -> Dict:
        """Analyze chunk content to add rich metadata (bất đồng bộ)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._analyze_chunk_content_sync,
            content
        )

    def _analyze_chunk_content_sync(self, content: str) -> Dict:
        """Analyze chunk content to add rich metadata (đồng bộ)."""
        metadata = {}
        content_lower = content.lower()
        
        # Check for definitions
        definition_patterns = [
            r'(là|is|được định nghĩa|defined as|nghĩa là)',
            r'(khái niệm|concept|definition|định nghĩa)',
        ]
        metadata["chứa_định_nghĩa"] = any(
            re.search(pattern, content_lower) for pattern in definition_patterns
        )
        
        # Check for SQL syntax
        sql_keywords = [
            "select", "insert", "update", "delete", "create", "alter", "drop",
            "join", "where", "group by", "order by", "having", "union"
        ]
        metadata["chứa_cú_pháp"] = any(keyword in content_lower for keyword in sql_keywords)
        
        # Check for specific SQL syntax types
        metadata["chứa_cú_pháp_select"] = "select" in content_lower
        metadata["chứa_cú_pháp_join"] = any(
            join_type in content_lower 
            for join_type in ["join", "inner join", "left join", "right join", "full join"]
        )
        metadata["chứa_cú_pháp_ddl"] = any(
            ddl in content_lower 
            for ddl in ["create", "alter", "drop", "table", "index", "view"]
        )
        
        # Check for examples
        example_patterns = [
            r'(ví dụ|example|minh họa|demonstration)',
            r'(như sau|as follows|for instance)',
            r'(xem xét|consider|let\'s)',
        ]
        metadata["chứa_ví_dụ"] = any(
            re.search(pattern, content_lower) for pattern in example_patterns
        )
        
        # Check for comparisons
        comparison_patterns = [
            r'(so sánh|compare|khác nhau|difference|versus|vs)',
            r'(tốt hơn|better|worse|worse than)',
            r'(ưu điểm|advantage|nhược điểm|disadvantage)',
        ]
        metadata["chứa_so_sánh"] = any(
            re.search(pattern, content_lower) for pattern in comparison_patterns
        )
        
        # Check for error/troubleshooting content
        error_patterns = [
            r'(lỗi|error|bug|issue|problem)',
            r'(không hoạt động|not working|failed|failure)',
            r'(sửa|fix|debug|troubleshoot|resolve)',
        ]
        metadata["chứa_lỗi"] = any(
            re.search(pattern, content_lower) for pattern in error_patterns
        )
        
        # Check for tables/data structures
        metadata["chứa_bảng"] = any(
            table_keyword in content_lower 
            for table_keyword in ["table", "bảng", "column", "cột", "row", "hàng"]
        )
        
        return metadata

    # --------------------------------------------------------
    # Classification helpers  
    # --------------------------------------------------------
    def _classify_document_content(self, content: str) -> str:
        """Classify document content based on keywords."""
        content_lower = content.lower()
        
        # Count keywords for each category
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            category_scores[category] = score
            
        # Return category with highest score, or 'general' if no matches
        if not category_scores or all(score == 0 for score in category_scores.values()):
            return "general"
            
        return max(category_scores.keys(), key=lambda k: category_scores[k])
