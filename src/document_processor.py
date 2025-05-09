import os
import re
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict, Optional, Tuple, Any


class DocumentProcessor:
    """Lớp quản lý việc tải và xử lý tài liệu"""

    def __init__(self, chunk_size=None, chunk_overlap=None):
        """Khởi tạo bộ xử lý tài liệu với kích thước chunk nhỏ hơn để tìm kiếm chính xác hơn"""
        # Đọc cấu hình từ biến môi trường nếu có
        default_chunk_size = 800
        default_chunk_overlap = 150

        # Đọc từ biến môi trường hoặc sử dụng các giá trị được cung cấp
        try:
            chunk_size_env = os.getenv("CHUNK_SIZE")
            if chunk_size_env:
                chunk_size = int(chunk_size_env)
            else:
                chunk_size = chunk_size or default_chunk_size

            chunk_overlap_env = os.getenv("CHUNK_OVERLAP")
            if chunk_overlap_env:
                chunk_overlap = int(chunk_overlap_env)
            else:
                chunk_overlap = chunk_overlap or default_chunk_overlap

            print(f"Cấu hình chunk: size={chunk_size}, overlap={chunk_overlap}")
        except ValueError as e:
            print(f"Lỗi khi đọc cấu hình chunk từ biến môi trường: {e}")
            print(
                f"Sử dụng giá trị mặc định: size={default_chunk_size}, overlap={default_chunk_overlap}"
            )
            chunk_size = default_chunk_size
            chunk_overlap = default_chunk_overlap

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

        # Áp dụng chunking cấu trúc mặc định
        self.use_structural_chunking = True

    def _chunk_by_structure(self, text: str, metadata: Dict) -> List[Dict]:
        """Chia văn bản thành các đoạn theo cấu trúc"""
        chunks = []

        # Phiên bản regex đơn giản hóa để tránh backtracking
        # Tìm các tiêu đề - dòng có ít hơn 100 ký tự, không có dấu chấm câu ở cuối
        # và có dòng trống phía sau
        heading_pattern = r"(?:^|\n)([A-Za-z0-9\u00C0-\u1EF9][^\n.!?]{5,99})\n\s*\n"

        try:
            # Tìm tất cả các tiêu đề với timeout
            import signal

            # Gắn một hàm xử lý timeout (chỉ hoạt động trên hệ điều hành Unix)
            # Trên Windows, sẽ sử dụng cách tiếp cận đơn giản hơn
            if os.name != "nt":  # Không phải Windows

                def timeout_handler(signum, frame):
                    raise TimeoutError("Quá thời gian khi tìm tiêu đề")

                # Đặt tín hiệu timeout
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(5)  # 5 giây

                # Tìm tất cả các tiêu đề
                headings = list(re.finditer(heading_pattern, text, re.MULTILINE))

                # Hủy tín hiệu timeout
                signal.alarm(0)
            else:  # Windows
                # Trên Windows, chỉ đơn giản thực thi regex
                headings = list(re.finditer(heading_pattern, text, re.MULTILINE))

            # Nếu có quá nhiều tiêu đề (có thể là dấu hiệu regex khớp sai),
            # chuyển sang phương pháp chunking theo kích thước
            if len(headings) > 100:
                print(
                    f"Phát hiện {len(headings)} tiêu đề - quá nhiều, chuyển sang chunking theo kích thước"
                )
                return self._chunk_by_size(text, metadata)

            # Các vị trí để chia
            positions = []
            last_index = 0

            for match in headings:
                start_idx = match.start(1)
                if start_idx > last_index:
                    # Thêm vị trí của nội dung trước tiêu đề
                    positions.append((last_index, start_idx, None))

                # Thêm vị trí của tiêu đề
                positions.append((start_idx, match.end(1), match.group(1)))
                last_index = match.end(1)

            # Thêm phần cuối cùng
            if last_index < len(text):
                positions.append((last_index, len(text), None))

        except (TimeoutError, Exception) as e:
            print(
                f"Lỗi khi tìm cấu trúc: {str(e)}. Chuyển sang chunking theo kích thước."
            )
            return self._chunk_by_size(text, metadata)

        # Xử lý từng phần
        try:
            for i, (start, end, heading) in enumerate(positions):
                chunk_text = text[start:end].strip()
                if not chunk_text:
                    continue

                # Phát hiện loại đoạn dựa vào nội dung
                chunk_type = "text"  # Mặc định

                # Đoạn có tiêu đề
                if heading:
                    chunk_type = "heading"
                # Đoạn có bảng - sử dụng regex đơn giản hơn
                elif "|" in chunk_text and "-" in chunk_text and len(chunk_text) < 5000:
                    chunk_type = "table"
                # Đoạn có danh sách
                elif (
                    "* " in chunk_text
                    or "- " in chunk_text
                    or ". " in chunk_text
                    and len(chunk_text) < 3000
                ):
                    chunk_type = "list"
                # Đoạn có code
                elif "```" in chunk_text or chunk_text.count("  ") > 5:
                    chunk_type = "code"

                # Nếu phần này là tiêu đề, ghép nó với nội dung tiếp theo nếu có
                if chunk_type == "heading" and i < len(positions) - 1:
                    next_start, next_end, next_heading = positions[i + 1]
                    if not next_heading:  # Nếu phần tiếp theo không phải là tiêu đề
                        next_text = text[next_start:next_end].strip()
                        # Kết hợp tiêu đề với nội dung tiếp theo
                        chunk_text = f"{chunk_text}\n\n{next_text}"
                        # Bỏ qua phần tiếp theo trong vòng lặp
                        positions[i + 1] = (next_start, next_end, "SKIP")

                # Bỏ qua các phần đã được đánh dấu để bỏ qua
                if heading == "SKIP":
                    continue

                # Tạo metadata cho chunk
                enhanced_metadata = dict(metadata)

                # Thêm thông tin về cấu trúc
                enhanced_metadata["chunk_type"] = chunk_type
                enhanced_metadata["position"] = f"section {i+1} of {len(positions)}"

                # Thêm thông tin về tiêu đề nếu có
                if heading:
                    enhanced_metadata["heading"] = heading

                # Thêm thông tin về trang nếu không có
                if "page" not in enhanced_metadata:
                    enhanced_metadata["page"] = enhanced_metadata.get(
                        "page", f"section_{i+1}"
                    )

                # Phát hiện và thêm metadata phong phú - sử dụng bản sao để tránh thay đổi gốc
                enhanced_metadata = self._enhance_chunk_metadata(
                    chunk_text, enhanced_metadata.copy()
                )

                chunks.append(
                    {
                        "id": str(i),
                        "text": chunk_text,
                        "metadata": enhanced_metadata,
                        "source": enhanced_metadata.get("source", "unknown"),
                    }
                )

            # Nếu không tìm thấy cấu trúc, sử dụng chunking theo kích thước
            if not chunks:
                return self._chunk_by_size(text, metadata)

            return chunks

        except Exception as e:
            print(
                f"Lỗi khi xử lý cấu trúc: {str(e)}. Chuyển sang chunking theo kích thước."
            )
            return self._chunk_by_size(text, metadata)

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

            # Thêm metadata phong phú cho từng chunk
            for chunk in chunks:
                chunk_text = chunk.get("text", "")
                chunk_metadata = chunk.get("metadata", {})
                enhanced_metadata = self._enhance_chunk_metadata(
                    chunk_text, chunk_metadata
                )
                chunk["metadata"] = enhanced_metadata

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

    def _enhance_chunk_metadata(self, text: str, metadata: Dict) -> Dict:
        """Phát hiện và thêm metadata phong phú cho chunk như định nghĩa, cú pháp, mẫu code"""
        enhanced_metadata = dict(metadata)
        text_lower = text.lower()

        # Phát hiện định nghĩa
        definition_patterns = [
            r"\b(là|được định nghĩa là|được hiểu là|có nghĩa là|refers to|is defined as|is)\b",
            r"^(định nghĩa|definition|khái niệm|concept)[\s\:]",
            r"\b(nghĩa là|có nghĩa là|tức là|means|meaning)\b",
        ]

        # Phát hiện cú pháp
        syntax_patterns = [
            r"\b(cú pháp|syntax|format|khai báo|declaration|statement)\b",
            r"(SELECT|CREATE|ALTER|DROP|INSERT|UPDATE|DELETE)[\s\w]+\b(FROM|TABLE|INTO|VALUES|SET|WHERE)\b",
            r"(sử dụng|usage|how to use|cách sử dụng)\s+.+\s+(lệnh|command|statement)",
            r"(general|standard|chuẩn)\s+(format|syntax|form)",
        ]

        # Phát hiện mẫu code
        code_patterns = [
            r"```\w*\n[\s\S]*?\n```",  # Markdown code blocks
            r"(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)[\s\S]*?;",
            r"(?:^|\n)(?:  |\t)[\s\S]+(?:\n|$)",  # Indented code blocks
            r"(?:Ví dụ|Example|For example)[\s\:][\s\S]*?(?:SELECT|INSERT|UPDATE|DELETE)[\s\S]*?;",
        ]

        # Kiểm tra và đánh dấu metadata
        for pattern in definition_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                enhanced_metadata["chứa_định_nghĩa"] = True
                break

        for pattern in syntax_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                enhanced_metadata["chứa_cú_pháp"] = True
                break

        for pattern in code_patterns:
            if re.search(pattern, text, re.MULTILINE):
                enhanced_metadata["chứa_mẫu_code"] = True
                break

        # Phát hiện các từ khóa quan trọng về cú pháp SQL
        if "SELECT" in text and "FROM" in text:
            enhanced_metadata["chứa_cú_pháp_select"] = True

        if "JOIN" in text and ("ON" in text or "USING" in text):
            enhanced_metadata["chứa_cú_pháp_join"] = True

        if ("CREATE" in text and "TABLE" in text) or (
            "ALTER" in text and "TABLE" in text
        ):
            enhanced_metadata["chứa_cú_pháp_ddl"] = True

        if "INSERT" in text or "UPDATE" in text or "DELETE" in text:
            enhanced_metadata["chứa_cú_pháp_dml"] = True

        # Phát hiện các bảng và hình vẽ
        if "|" in text and "-" in text and re.search(r"\|\s*-+\s*\|", text):
            enhanced_metadata["chứa_bảng"] = True

        if re.search(r"!\[.*?\]\(.*?\)", text) or re.search(r"<img.*?>", text):
            enhanced_metadata["chứa_hình_ảnh"] = True

        return enhanced_metadata

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
