import re
from typing import List, Dict, Any, Optional, Pattern
from langchain.schema import Document
import os
from tqdm import tqdm

from src.config import (
    CHUNK_SIZE_SPECIALIZED,
    CHUNK_OVERLAP_SPECIALIZED,
    MIN_CHUNK_SIZE,
    MIN_CHUNK_CHARACTERS,
)

from src.utils import measure_time, print_document_info


class CodeDocumentProcessor:
    """Lớp xử lý chunking đặc biệt cho tài liệu code"""

    def __init__(self, embeddings):
        """Khởi tạo với embedding model đã cho"""
        self.embeddings = embeddings
        # Định nghĩa các regex pattern để nhận diện các phần quan trọng trong code
        self._init_patterns()

    def _init_patterns(self):
        """Khởi tạo các regex pattern cho việc xử lý code"""
        # Pattern cho các phần quan trọng của code
        self.language_patterns = {
            "python": {
                "function": re.compile(
                    r"def\s+(\w+)\s*\(([^)]*)\)(?:\s*->.*?)?:", re.MULTILINE
                ),
                "class": re.compile(r"class\s+(\w+)\s*(?:\([^)]*\))?:", re.MULTILINE),
                "import": re.compile(r"(?:import|from)\s+[^;]+", re.MULTILINE),
            },
            "javascript": {
                "function": re.compile(
                    r"(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:function|\([^)]*\)\s*=>))",
                    re.MULTILINE,
                ),
                "class": re.compile(
                    r"class\s+(\w+)\s*(?:extends\s+\w+)?\s*{", re.MULTILINE
                ),
                "import": re.compile(r"(?:import|export)\s+[^;]+", re.MULTILINE),
            },
            "java": {
                "function": re.compile(
                    r"(?:public|private|protected|static|\s) +[\w\<\>\[\]]+\s+(\w+) *\([^\)]*\) *(?:\{|throws [^;{]+)",
                    re.MULTILINE,
                ),
                "class": re.compile(
                    r"class\s+(\w+)\s*(?:extends\s+\w+)?(?:implements\s+[^{]+)?\s*\{",
                    re.MULTILINE,
                ),
                "import": re.compile(r"import\s+[^;]+;", re.MULTILINE),
            },
            "csharp": {
                "function": re.compile(
                    r"(?:public|private|protected|internal|static|\s)+[\w\<\>\[\]]+\s+(\w+)\s*\([^\)]*\)\s*(?:\{|where\s+[^{]+\{)",
                    re.MULTILINE,
                ),
                "class": re.compile(
                    r"class\s+(\w+)\s*(?::\s*[^{]+)?\s*\{", re.MULTILINE
                ),
                "using": re.compile(r"using\s+[^;]+;", re.MULTILINE),
            },
        }

        # Pattern cho comments
        self.comment_patterns = {
            "python": [
                re.compile(r"#.*"),
                re.compile(r'""".*?"""', re.DOTALL),
                re.compile(r"'''.*?'''", re.DOTALL),
            ],
            "javascript": [re.compile(r"//.*"), re.compile(r"/\*.*?\*/", re.DOTALL)],
            "java": [re.compile(r"//.*"), re.compile(r"/\*.*?\*/", re.DOTALL)],
            "csharp": [re.compile(r"//.*"), re.compile(r"/\*.*?\*/", re.DOTALL)],
        }

    def _detect_language(self, file_path: str, content: str) -> str:
        """Phát hiện ngôn ngữ lập trình dựa trên đuôi file và nội dung

        Args:
            file_path: Đường dẫn file
            content: Nội dung file

        Returns:
            Tên ngôn ngữ: "python", "javascript", "java", "csharp", hoặc "unknown"
        """
        _, ext = os.path.splitext(file_path.lower())

        if ext in [".py", ".pyw"]:
            return "python"
        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
            return "javascript"
        elif ext in [".java"]:
            return "java"
        elif ext in [".cs"]:
            return "csharp"

        # Nếu không thể xác định từ đuôi file, thử phát hiện từ nội dung
        if "def " in content and "import " in content:
            return "python"
        elif "function " in content or "=>" in content:
            return "javascript"
        elif "public class " in content or "private class " in content:
            return "java"
        elif "namespace " in content or "using " in content:
            return "csharp"

        return "unknown"

    @measure_time
    def process_code_documents(self, docs: List[Document]) -> List[Document]:
        """Xử lý tài liệu code với phương pháp chunking đặc biệt

        Args:
            docs: Danh sách tài liệu code cần xử lý

        Returns:
            Danh sách tài liệu đã được chunk theo cấu trúc code
        """
        print("⏳ Đang xử lý tài liệu code...")
        code_chunks = []

        for doc in tqdm(docs, desc="Processing code documents", unit="doc"):
            source_path = doc.metadata.get("source_path", "unknown")
            language = self._detect_language(source_path, doc.page_content)

            # Thêm loại tài liệu vào metadata
            metadata = {**doc.metadata, "code_language": language}

            if language != "unknown":
                chunks = self._process_code_by_language(
                    doc.page_content, metadata, language
                )
            else:
                # Nếu không xác định được ngôn ngữ, sử dụng phương pháp chunk dòng đơn giản
                chunks = self._chunk_by_lines(doc.page_content, metadata)

            code_chunks.extend(chunks)

        # Thêm thông tin về loại chunker đã sử dụng
        for chunk in code_chunks:
            if "processor" not in chunk.metadata:
                chunk.metadata["processor"] = "code_processor"

        print(f"✅ Đã xử lý tài liệu code: {len(code_chunks)} chunks")
        print_document_info(code_chunks, "Kết quả Code processor")
        return code_chunks

    def _process_code_by_language(
        self, content: str, metadata: Dict[str, Any], language: str
    ) -> List[Document]:
        """Xử lý code theo ngôn ngữ cụ thể

        Args:
            content: Nội dung code
            metadata: Metadata của tài liệu gốc
            language: Ngôn ngữ lập trình

        Returns:
            Danh sách Document đã được chunk theo cấu trúc của ngôn ngữ
        """
        chunks = []

        # Tách các phần quan trọng
        functions = []
        classes = []
        imports = []

        # Thu thập các phần theo patterns
        if language in self.language_patterns:
            patterns = self.language_patterns[language]

            # Tìm tất cả các functions
            for match in patterns["function"].finditer(content):
                start = match.start()
                func_name = match.group(1)
                # Tìm phạm vi của function (từ định nghĩa đến kết thúc)
                func_content = self._extract_block(content, start)

                functions.append(
                    {
                        "name": func_name,
                        "content": func_content,
                        "start": start,
                        "end": start + len(func_content),
                    }
                )

            # Tìm tất cả các classes
            for match in patterns["class"].finditer(content):
                start = match.start()
                class_name = match.group(1)
                # Tìm phạm vi của class
                class_content = self._extract_block(content, start)

                classes.append(
                    {
                        "name": class_name,
                        "content": class_content,
                        "start": start,
                        "end": start + len(class_content),
                    }
                )

            # Tìm tất cả imports
            if "import" in patterns:
                for match in patterns["import"].finditer(content):
                    import_stmt = match.group(0)
                    imports.append(import_stmt)

        # Tạo chunks cho imports (gộp imports thành một chunk)
        if imports:
            import_content = "\n".join(imports)
            import_metadata = {
                **metadata,
                "code_element_type": "imports",
                "code_language": language,
            }
            chunks.append(
                Document(page_content=import_content, metadata=import_metadata)
            )

        # Tạo chunks cho classes
        for class_info in classes:
            class_metadata = {
                **metadata,
                "code_element_type": "class",
                "code_language": language,
                "element_name": class_info["name"],
            }
            chunks.append(
                Document(page_content=class_info["content"], metadata=class_metadata)
            )

        # Tạo chunks cho functions (không nằm trong class)
        for func_info in functions:
            # Kiểm tra xem function có nằm trong class nào không
            is_in_class = False
            for class_info in classes:
                if (
                    class_info["start"] <= func_info["start"]
                    and func_info["end"] <= class_info["end"]
                ):
                    is_in_class = True
                    break

            # Chỉ thêm function không nằm trong class
            if not is_in_class:
                func_metadata = {
                    **metadata,
                    "code_element_type": "function",
                    "code_language": language,
                    "element_name": func_info["name"],
                }
                chunks.append(
                    Document(page_content=func_info["content"], metadata=func_metadata)
                )

        # Nếu không có chunks nào được tạo, sử dụng phương pháp chunk dòng
        if not chunks:
            return self._chunk_by_lines(content, metadata)

        return chunks

    def _extract_block(self, content: str, start_pos: int) -> str:
        """Trích xuất một block code hoàn chỉnh từ vị trí bắt đầu

        Args:
            content: Nội dung code
            start_pos: Vị trí bắt đầu của block

        Returns:
            Nội dung block code
        """
        # Tìm vị trí của dấu { đầu tiên sau start_pos
        open_brace_pos = content.find("{", start_pos)

        # Nếu không tìm thấy dấu {, trả về từ start_pos đến cuối dòng
        if open_brace_pos == -1:
            end_line = content.find("\n", start_pos)
            if end_line == -1:
                return content[start_pos:]
            return content[start_pos:end_line]

        # Đếm số dấu ngoặc mở và đóng để xác định phạm vi đúng
        open_count = 1
        pos = open_brace_pos + 1

        while pos < len(content) and open_count > 0:
            if content[pos] == "{":
                open_count += 1
            elif content[pos] == "}":
                open_count -= 1
            pos += 1

        # Nếu đã tìm thấy dấu } cuối cùng đóng block
        if open_count == 0:
            return content[start_pos:pos]

        # Nếu không tìm thấy dấu } khớp, trả về đến cuối nội dung
        return content[start_pos:]

    def _chunk_by_lines(self, content: str, metadata: Dict[str, Any]) -> List[Document]:
        """Chia code thành chunks theo dòng với độ dài phù hợp

        Args:
            content: Nội dung code
            metadata: Metadata của tài liệu gốc

        Returns:
            Danh sách Document đã được chunk theo dòng
        """
        chunks = []
        lines = content.splitlines()

        current_chunk = []
        current_chunk_size = 0

        for line in lines:
            # Nếu thêm dòng mới vào chunk hiện tại sẽ vượt quá kích thước tối đa
            if (
                current_chunk_size + len(line) > CHUNK_SIZE_SPECIALIZED
                and current_chunk
            ):
                # Tạo chunk mới từ các dòng đã thu thập
                chunk_content = "\n".join(current_chunk)
                if len(chunk_content) >= MIN_CHUNK_CHARACTERS:
                    chunk_metadata = {
                        **metadata,
                        "code_element_type": "lines",
                    }
                    chunks.append(
                        Document(page_content=chunk_content, metadata=chunk_metadata)
                    )

                # Reset chunk hiện tại
                current_chunk = []
                current_chunk_size = 0

            # Thêm dòng vào chunk hiện tại
            current_chunk.append(line)
            current_chunk_size += len(line) + 1  # +1 cho ký tự xuống dòng

        # Xử lý chunk cuối cùng
        if current_chunk:
            chunk_content = "\n".join(current_chunk)
            if len(chunk_content) >= MIN_CHUNK_CHARACTERS:
                chunk_metadata = {
                    **metadata,
                    "code_element_type": "lines",
                }
                chunks.append(
                    Document(page_content=chunk_content, metadata=chunk_metadata)
                )

        return chunks
