import os
import logging
import subprocess
import shutil
import re
import uuid
from typing import List, Dict

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
    """Manage loading, normalising, and chunking documents for RAG."""

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

        # Default LibreOffice path – override with env var LIBREOFFICE_PATH if needed
        self.libreoffice_path = os.getenv(
            "LIBREOFFICE_PATH", r"C:\\Program Files\\LibreOffice\\program\\soffice.exe"
        )

    # --------------------------------------------------------
    # Conversion helpers
    # --------------------------------------------------------
    def get_converted_path(self, input_path: str) -> str:
        """Return the path to the PDF version of *input_path* if it already exists."""
        file_ext = os.path.splitext(input_path)[1].lower()
        if file_ext == ".pdf" or file_ext not in self.convertible_formats:
            return input_path

        output_dir = os.path.dirname(input_path)
        file_stem = os.path.splitext(os.path.basename(input_path))[0]
        pdf_path = os.path.join(output_dir, f"{file_stem}.pdf")
        return pdf_path if os.path.exists(pdf_path) else input_path

    def convert_to_pdf(self, input_path: str, *, remove_original: bool = True) -> str:
        """Convert *input_path* to PDF (if recognised format) using LibreOffice.
        Returns the path to a PDF file if available; otherwise returns the original path.
        """
        file_ext = os.path.splitext(input_path)[1].lower()
        if file_ext == ".pdf" or file_ext not in self.convertible_formats:
            return input_path  # Nothing to do

        output_dir = os.path.dirname(input_path)
        file_stem = os.path.splitext(os.path.basename(input_path))[0]
        pdf_path = os.path.join(output_dir, f"{file_stem}.pdf")

        # Avoid re‑converting if PDF already exists
        if os.path.exists(pdf_path):
            if remove_original and os.path.exists(input_path) and input_path != pdf_path:
                try:
                    os.remove(input_path)
                    print(f"Đã xóa tập tin gốc: {input_path}")
                except OSError as exc:
                    print(f"Không thể xóa tập tin gốc {input_path}: {exc}")
            return pdf_path

        print(f"Đang chuyển đổi {input_path} sang PDF…")
        try:
            subprocess.run(
                [
                    self.libreoffice_path,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    input_path,
                    "--outdir",
                    output_dir,
                ],
                check=True,
                stderr=subprocess.DEVNULL,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"Chuyển đổi sang PDF thất bại ({exc}). Tạm dùng tệp gốc.")
            return input_path

        if os.path.exists(pdf_path):
            print(f"Chuyển đổi thành công: {pdf_path}")
            if remove_original and os.path.exists(input_path):
                try:
                    os.remove(input_path)
                    print(f"Đã xóa tập tin gốc: {input_path}")
                except OSError as exc:
                    print(f"Không thể xóa tập tin gốc {input_path}: {exc}")
            return pdf_path

        print("Không tìm thấy PDF sau khi chuyển đổi – trả về tệp gốc")
        return input_path

    # --------------------------------------------------------
    # Loading helpers
    # --------------------------------------------------------
    @staticmethod
    def _ensure_page_metadata(docs: List):
        """Guarantee each LangChain Document has a numeric 1‑based `page` field.
        If loader already supplies a 0‑based integer, convert to 1‑based; if no page
        info present, default to 1. This is purely additive; existing keys are left
        unchanged except the normalisation from 0→1‑based.
        """
        for d in docs:
            if not hasattr(d, "metadata"):
                continue
            meta = d.metadata
            if "page" not in meta:
                meta["page"] = 1
            else:
                try:
                    # Only convert if int/str representing int
                    page_val = int(meta["page"])
                    if page_val == 0:
                        meta["page"] = 1
                    else:
                        meta["page"] = page_val  # ensure int type
                except (ValueError, TypeError):
                    # leave as‑is if conversion fails (string like "section_1")
                    pass

    def load_documents(self, data_dir: str) -> List[Dict]:
        """Load **all** documents under *data_dir* into LangChain Document objects."""
        documents = []
        for fname in os.listdir(data_dir):
            file_path = os.path.join(data_dir, fname)
            converted_path = self.convert_to_pdf(file_path)
            ext = os.path.splitext(converted_path)[1].lower()

            if ext not in self.loaders:
                print(f"Bỏ qua định dạng không hỗ trợ: {fname}")
                continue

            try:
                loader_cls = self.loaders[ext]
                loaded_docs = loader_cls(converted_path).load()

                # Ensure page metadata exists and is 1‑based
                self._ensure_page_metadata(loaded_docs)

                for doc in loaded_docs:
                    # Basic provenance metadata
                    doc.metadata.setdefault("source", fname)
                    if converted_path != file_path:
                        doc.metadata["original_file"] = fname
                        doc.metadata["converted_from"] = os.path.splitext(fname)[1]
                documents.extend(loaded_docs)
            except Exception as exc:  # noqa: BLE001 – catch‑all acceptable at this layer
                print(f"Error loading {converted_path}: {exc}")
        return documents

    # Single file loader with optional category override (kept for API compatibility)
    def load_document_with_category(self, file_path: str, category: str | None = None):
        converted_path = self.convert_to_pdf(file_path)
        ext = os.path.splitext(converted_path)[1].lower()
        if ext not in self.loaders:
            print(f"Định dạng {ext} không được hỗ trợ")
            return []
        try:
            docs = self.loaders[ext](converted_path).load()
            self._ensure_page_metadata(docs)
            for doc in docs:
                doc.metadata.setdefault("source", os.path.basename(file_path))
                if converted_path != file_path:
                    doc.metadata["original_file"] = os.path.basename(file_path)
                    doc.metadata["converted_from"] = os.path.splitext(file_path)[1]
                if category:
                    doc.metadata["category"] = category
                else:
                    doc.metadata["category"] = self._classify_document_content(doc.page_content)
            return docs
        except Exception as exc:  # noqa: BLE001
            print(f"Lỗi khi tải tài liệu {converted_path}: {exc}")
            return []

    # --------------------------------------------------------
    # Chunking helpers
    # --------------------------------------------------------
    def _chunk_by_size(self, text: str, metadata: Dict) -> List[Dict]:
        """Fallback chunking strategy: fixed size chunks using Recursive splitter."""
        chunks = self.text_splitter.create_documents([text], [metadata])
        output = []
        for i, chunk in enumerate(chunks):
            meta = dict(chunk.metadata)
            if "page" not in meta:
                meta["page"] = 1
            meta.setdefault("chunk_type", "text")
            meta["position"] = f"chunk {i + 1} of {len(chunks)}"
            output.append(
                {
                    "id": str(uuid.uuid4()),
                    "text": chunk.page_content,
                    "metadata": meta,
                    "source": meta.get("source", "unknown"),
                }
            )
        return output

    def _chunk_by_structure(self, text: str, metadata: Dict) -> List[Dict]:
        """Structure‑aware chunking that attempts to keep headings with their content."""
        heading_pattern = r"(?:^|\n)([A-Za-z0-9\u00C0-\u1EF9][^\n.!?]{5,99})\n\s*\n"
        positions: List[tuple[int, int, str | None]] = []
        try:
            # Attempt to find headings; on Unix we can timeout the regex to avoid worst‑case.
            import signal

            def _timeout_handler(_signum, _frame):
                raise TimeoutError("Regex heading detection timed‑out")

            if os.name != "nt":
                signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(5)
            headings = list(re.finditer(heading_pattern, text, re.MULTILINE))
            if os.name != "nt":
                signal.alarm(0)
        except Exception as exc:
            print(f"Heading detection failed ({exc}); dùng chunk theo kích thước")
            return self._chunk_by_size(text, metadata)

        if len(headings) > 100:
            print("Quá nhiều tiêu đề, chuyển sang chunk theo kích thước")
            return self._chunk_by_size(text, metadata)

        # Build positions list
        last_idx = 0
        for m in headings:
            start_idx = m.start(1)
            if start_idx > last_idx:
                positions.append((last_idx, start_idx, None))
            positions.append((start_idx, m.end(1), m.group(1)))
            last_idx = m.end(1)
        if last_idx < len(text):
            positions.append((last_idx, len(text), None))

        results: List[Dict] = []
        skip_next = False
        total = len(positions)
        for i, (start, end, heading) in enumerate(positions):
            if skip_next:
                skip_next = False
                continue
            chunk_text = text[start:end].strip()
            if not chunk_text:
                continue
            chunk_type = "heading" if heading else "text"
            # Simple heuristics
            if not heading and "|" in chunk_text and "-" in chunk_text and len(chunk_text) < 5000:
                chunk_type = "table"
            elif not heading and (
                "* " in chunk_text or "- " in chunk_text or (". " in chunk_text and len(chunk_text) < 3000)
            ):
                chunk_type = "list"
            elif "```" in chunk_text or chunk_text.count("  ") > 5:
                chunk_type = "code"

            # If current is a heading, merge with immediate next block
            if chunk_type == "heading" and i < total - 1 and positions[i + 1][2] is None:
                nxt_start, nxt_end, _ = positions[i + 1]
                chunk_text = f"{chunk_text}\n\n{text[nxt_start:nxt_end].strip()}"
                skip_next = True

            # Metadata copy + enrich
            meta = dict(metadata)
            meta.setdefault("page", metadata.get("page", 1))
            meta["chunk_type"] = chunk_type
            meta["position"] = f"section {i + 1} of {total}"
            if heading:
                meta["heading"] = heading
            meta = self._enhance_chunk_metadata(chunk_text, meta)

            results.append(
                {
                    "id": str(uuid.uuid4()),
                    "text": chunk_text,
                    "metadata": meta,
                    "source": meta.get("source", "unknown"),
                }
            )

        return results if results else self._chunk_by_size(text, metadata)

    # --------------------------------------------------------
    # Public processing entrypoint
    # --------------------------------------------------------
    def process_documents(self, documents: List) -> List[Dict]:
        """Convert LangChain Documents (or raw dicts) into enriched chunk dicts."""
        processed: List[Dict] = []
        for doc in documents:
            if hasattr(doc, "page_content") and hasattr(doc, "metadata"):
                text = doc.page_content
                meta = dict(doc.metadata)
            else:
                text = doc.get("text", doc.get("page_content", ""))
                meta = dict(doc.get("metadata", {}))

            if "category" not in meta:
                meta["category"] = self._classify_document_content(text)

            if self.use_structural_chunking:
                chunks = self._chunk_by_structure(text, meta)
            else:
                chunks = self._chunk_by_size(text, meta)
            processed.extend(chunks)
        return processed

    # --------------------------------------------------------
    # Classification & metadata enrichment helpers
    # --------------------------------------------------------
    def _classify_document_content(self, text: str) -> str:
        text_lower = text.lower()
        scores: Dict[str, float] = {}
        for cat, keywords in self.category_keywords.items():
            score = sum(len(re.findall(r"\b" + re.escape(kw) + r"\b", text_lower)) for kw in keywords)
            scores[cat] = score / (len(text_lower.split()) + 1) * 100
        if scores:
            best_cat, best_score = max(scores.items(), key=lambda x: x[1])
            return best_cat if best_score > 0.5 else "general"
        return "general"

    def _enhance_chunk_metadata(self, text: str, metadata: Dict) -> Dict:
        enhanced = dict(metadata)
        text_lower = text.lower()

        # Quick definition/syntax/code detectors (unchanged)
        definition_patterns = [
            r"\b(là|được định nghĩa là|được hiểu là|có nghĩa là|refers to|is defined as|is)\b",
            r"^(định nghĩa|definition|khái niệm|concept)[\s\:]",
            r"\b(nghĩa là|có nghĩa là|tức là|means|meaning)\b",
        ]
        syntax_patterns = [
            r"\b(cú pháp|syntax|format|khai báo|declaration|statement)\b",
            r"(SELECT|CREATE|ALTER|DROP|INSERT|UPDATE|DELETE)[\s\w]+\b(FROM|TABLE|INTO|VALUES|SET|WHERE)\b",
            r"(sử dụng|usage|how to use|cách sử dụng)\s+.+\s+(lệnh|command|statement)",
            r"(general|standard|chuẩn)\s+(format|syntax|form)",
        ]
        code_patterns = [
            r"```\w*\n[\s\S]*?\n```",
            r"(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)[\s\S]*?;",
            r"(?:^|\n)(?:  |\t)[\s\S]+(?:\n|$)",
            r"(?:Ví dụ|Example|For example)[\s\:][\s\S]*?(?:SELECT|INSERT|UPDATE|DELETE)[\s\S]*?;",
        ]

        example_patterns = [
            r"\b(ví dụ|example|e\.g\.|chẳng hạn)\b",
            r"(for instance|case study|in practice)",
        ]
        
        comparison_patterns = [
            r"\b(so sánh|compare|vs|versus|khác với|tương tự như|different from|similar to)\b",
            r"(ưu điểm|nhược điểm|advantages|disadvantages|pros|cons)\b",
        ]

        error_patterns = [
            r"\b(lỗi|error|exception|ngoại lệ|sự cố|issue|problem)\b",
            r"(troubleshoot|debug|fix|khắc phục|sửa lỗi|gỡ rối)\b",
            r"(common error|known issue|vấn đề thường gặp)",
        ]

        for p in definition_patterns:
            if re.search(p, text, re.IGNORECASE):
                enhanced["chứa_định_nghĩa"] = True
                break
        for p in syntax_patterns:
            if re.search(p, text, re.IGNORECASE):
                enhanced["chứa_cú_pháp"] = True
                break
        for p in code_patterns:
            if re.search(p, text, re.MULTILINE):
                enhanced["chứa_mẫu_code"] = True
                break
        
        # Bổ sung các pattern mới
        for p in example_patterns:
            if re.search(p, text, re.IGNORECASE):
                enhanced["chứa_ví_dụ"] = True
                break

        for p in comparison_patterns:
            if re.search(p, text, re.IGNORECASE):
                enhanced["chứa_so_sánh"] = True
                break
        
        for p in error_patterns:
            if re.search(p, text, re.IGNORECASE):
                enhanced["chứa_lỗi"] = True
                break

        # Specific SQL syntax flags
        if "SELECT" in text and "FROM" in text:
            enhanced["chứa_cú_pháp_select"] = True
        if "JOIN" in text and ("ON" in text or "USING" in text):
            enhanced["chứa_cú_pháp_join"] = True
        if ("CREATE" in text and "TABLE" in text) or ("ALTER" in text and "TABLE" in text):
            enhanced["chứa_cú_pháp_ddl"] = True
        if "INSERT" in text or "UPDATE" in text or "DELETE" in text:
            enhanced["chứa_cú_pháp_dml"] = True

        # Table / image heuristics
        if "|" in text and "-" in text and re.search(r"\|\s*-+\s*\|", text):
            enhanced["chứa_bảng"] = True
        if re.search(r"!\[.*?\]\(.*?\)", text) or re.search(r"<img.*?>", text):
            enhanced["chứa_hình_ảnh"] = True
        return enhanced