import os
import re
import layoutparser as lp
import numpy as np
import cv2
from PIL import Image
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict, Optional, Tuple, Any


class DocumentProcessor:
    """Lớp quản lý việc tải và xử lý tài liệu"""

    def __init__(self, chunk_size=800, chunk_overlap=150, enable_layout_detection=True):
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

        # Khởi tạo mô hình nhận dạng bố cục (layout) lazy loading
        self._layout_model = None
        self.layout_model_name = "lp://EfficientDete/PubLayNet"
        self.enable_layout_detection = enable_layout_detection

        # Kiểm tra và cấu hình đường dẫn cho Poppler và Tesseract
        if (
            os.name == "nt" and enable_layout_detection
        ):  # Windows và layout detection được bật
            print(f"=== Kiểm tra cấu hình layout detection ===")
            # Cấu hình Poppler
            poppler_paths = [
                r"C:\Program Files\poppler\bin",
                r"C:\Program Files\poppler\Library\bin",
                r"C:\poppler\bin",
                r"C:\poppler\Library\bin",
            ]

            poppler_found = False
            for path in poppler_paths:
                if os.path.exists(path):
                    print(f"Tìm thấy Poppler tại: {path}")
                    os.environ["POPPLER_PATH"] = path
                    poppler_found = True
                    break

            if not poppler_found:
                print("Cảnh báo: Không tìm thấy Poppler trong các đường dẫn phổ biến.")

            # Cấu hình Tesseract
            tesseract_paths = [
                r"C:\Program Files\Tesseract-OCR",
                r"C:\Tesseract-OCR",
            ]

            tesseract_found = False
            for path in tesseract_paths:
                if os.path.exists(path):
                    print(f"Tìm thấy Tesseract tại: {path}")
                    tessdata_path = os.path.join(path, "tessdata")
                    if os.path.exists(tessdata_path):
                        os.environ["TESSDATA_PREFIX"] = tessdata_path
                        print(f"Đặt TESSDATA_PREFIX = {tessdata_path}")

                        # Kiểm tra tesseract.exe
                        tesseract_exe = os.path.join(path, "tesseract.exe")
                        if os.path.exists(tesseract_exe):
                            print(f"Tìm thấy tesseract.exe tại: {tesseract_exe}")

                            # Cấu hình pytesseract nếu đã import
                            try:
                                import pytesseract

                                pytesseract.pytesseract.tesseract_cmd = tesseract_exe
                                print(
                                    f"Đã cấu hình pytesseract.tesseract_cmd = {tesseract_exe}"
                                )
                            except ImportError:
                                print("Cảnh báo: Không thể import pytesseract")

                        tesseract_found = True
                        break

            if not tesseract_found:
                print(
                    "Cảnh báo: Không tìm thấy Tesseract OCR trong các đường dẫn phổ biến."
                )

        # Nếu không bật layout detection, không cần load mô hình
        if not enable_layout_detection:
            print("Layout detection bị tắt. Sử dụng phương pháp chunking thông thường")
            self.use_structural_chunking = True
            return

        # Cấu hình cho layout analysis
        self.max_tokens_per_chunk = 512  # Giới hạn token cho mỗi chunk
        self.min_paragraph_length = (
            50  # Độ dài tối thiểu của paragraph để không bị coi là noise
        )

        # Áp dụng chunking cấu trúc mặc định
        self.use_structural_chunking = True

        # Kiểm tra cài đặt cần thiết
        self._check_requirements()

    def _get_layout_model(self):
        """Lazy loading cho mô hình layout detection"""
        # Kiểm tra xem layout detection có được bật hay không
        if not self.enable_layout_detection:
            print("Layout detection bị tắt")
            return None

        if self._layout_model is None:
            try:
                print("Đang tải mô hình layout detection...")
                self._layout_model = lp.AutoLayoutModel(self.layout_model_name)
                print(f"Đã tải xong mô hình layout detection: {self.layout_model_name}")

                # Xác minh mô hình có khả dụng không bằng cách kiểm tra các thuộc tính
                if hasattr(self._layout_model, "detect") and callable(
                    self._layout_model.detect
                ):
                    print("Mô hình layout detection đã sẵn sàng sử dụng")
                    return self._layout_model
                else:
                    print("Mô hình đã tải nhưng không có phương thức detect")
                    self._layout_model = None
                    return None
            except Exception as e:
                print(f"Lỗi khi tải mô hình layout: {str(e)}")
                print("Sử dụng phương pháp chunking thông thường")
                self._layout_model = None
                self.use_structural_chunking = False
                return None
        else:
            print("Đã có mô hình layout detection trong bộ nhớ")
            return self._layout_model

    def detect_layout(self, image_path: str) -> Optional[List[Dict]]:
        """Phát hiện bố cục (layout) từ ảnh tài liệu"""
        try:
            # Đảm bảo mô hình được tải
            model = self._get_layout_model()
            if model is None:
                print("Mô hình layout detection không khả dụng")
                return None

            # Đọc ảnh với OpenCV
            image = cv2.imread(image_path)
            if image is None:
                print(f"Không thể đọc ảnh từ {image_path}")
                return None

            print(f"Đã đọc ảnh thành công từ {image_path}, kích thước: {image.shape}")

            # Chuyển đổi từ BGR sang RGB (OpenCV đọc theo BGR)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Phát hiện layout
            print("Bắt đầu phát hiện layout...")
            layout = model.detect(image)
            print(f"Đã phát hiện {len(layout)} vùng layout")

            # Chuyển đổi kết quả thành list các dict
            result = []
            for i, block in enumerate(layout):
                result.append(
                    {
                        "type": block.type,  # title, text, figure, table, list
                        "bbox": [
                            block.block.x_1,
                            block.block.y_1,
                            block.block.x_2,
                            block.block.y_2,
                        ],
                        "score": block.score,
                        "text": "",  # OCR sẽ điền vào sau
                    }
                )
                if i < 3:  # In chi tiết 3 vùng đầu tiên để debug
                    print(
                        f"Vùng {i}: {block.type}, Score: {block.score:.2f}, Bbox: {block.block}"
                    )

            return result

        except Exception as e:
            print(f"Lỗi khi phát hiện layout: {str(e)}")
            import traceback

            traceback.print_exc()  # In stack trace để dễ debug
            return None

    def extract_text_from_regions(self, image, regions, ocr_engine=None):
        """Trích xuất văn bản từ các vùng đã phát hiện"""
        try:
            # Sử dụng OCR mặc định nếu không cung cấp
            if ocr_engine is None:
                try:
                    import pytesseract

                    # Cấu hình Tesseract trên Windows
                    if os.name == "nt":  # Windows
                        tesseract_paths = [
                            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                            r"C:\Tesseract-OCR\tesseract.exe",
                        ]

                        # Tìm đường dẫn tesseract.exe
                        for path in tesseract_paths:
                            if os.path.exists(path):
                                print(f"Tìm thấy tesseract.exe tại: {path}")
                                pytesseract.pytesseract.tesseract_cmd = path
                                break

                    ocr_engine = pytesseract
                    print(
                        f"Đường dẫn Tesseract: {pytesseract.pytesseract.tesseract_cmd}"
                    )
                except ImportError:
                    print(
                        "Không thể import pytesseract. Vui lòng cài đặt: pip install pytesseract"
                    )
                    return regions

            # Trích xuất văn bản cho từng vùng
            for region in regions:
                x1, y1, x2, y2 = region["bbox"]
                # Lấy vùng ảnh
                region_image = image[int(y1) : int(y2), int(x1) : int(x2)]

                # Áp dụng OCR
                try:
                    region_text = ocr_engine.image_to_string(
                        Image.fromarray(region_image)
                    )
                    region["text"] = region_text.strip()
                    # In debug cho vùng đầu tiên
                    if region == regions[0]:
                        print(
                            f"Đã trích xuất text từ vùng đầu tiên: {region['text'][:50]}..."
                        )
                except Exception as e:
                    print(f"Lỗi OCR: {str(e)}")
                    region["text"] = ""

            return regions

        except Exception as e:
            print(f"Lỗi khi trích xuất văn bản từ vùng: {str(e)}")
            return regions

    def filter_and_group_regions(self, regions: List[Dict]) -> List[Dict]:
        """Lọc và nhóm các vùng layout theo cấu trúc"""
        if not regions:
            return []

        # Sắp xếp các vùng theo thứ tự đọc (từ trên xuống, trái sang phải)
        sorted_regions = sorted(regions, key=lambda r: (r["bbox"][1], r["bbox"][0]))

        # Lọc các header/footer (thường nằm ở phần trên cùng hoặc dưới cùng và lặp lại)
        # và các vùng có nội dung quá ngắn
        filtered_regions = []
        headers_footers = set()

        for region in sorted_regions:
            # Bỏ qua các vùng không có text
            if not region.get("text", "").strip():
                continue

            # Kiểm tra xem có phải header/footer
            text = region["text"].strip()
            is_header_footer = False

            # Header/footer thường ngắn và có thể chứa số trang
            if len(text) < 50 and (
                re.search(r"\d+\s*\/\s*\d+", text)
                or re.search(r"page\s*\d+", text, re.IGNORECASE)
            ):
                headers_footers.add(text)
                is_header_footer = True

            # Kiểm tra xem text có trùng với header/footer đã biết
            if text in headers_footers:
                is_header_footer = True

            # Chỉ giữ lại các vùng không phải header/footer và đủ dài
            if not is_header_footer and len(text) >= self.min_paragraph_length:
                filtered_regions.append(region)

        # Nhóm các vùng theo cấu trúc
        structured_chunks = []
        current_heading = None
        current_content = []

        for region in filtered_regions:
            if region["type"].lower() in ("title", "heading", "header"):
                # Nếu có heading mới, lưu chunk cũ và bắt đầu chunk mới
                if current_heading and current_content:
                    structured_chunks.append(
                        {
                            "heading": current_heading.get("text", ""),
                            "content": "\n".join(
                                [r.get("text", "") for r in current_content]
                            ),
                            "type": "heading_group",
                        }
                    )

                # Bắt đầu nhóm mới
                current_heading = region
                current_content = []
            elif region["type"].lower() in ("table", "figure"):
                # Tables và figures là chunk riêng
                structured_chunks.append(
                    {
                        "heading": "",
                        "content": region.get("text", ""),
                        "type": region["type"].lower(),
                    }
                )
            else:
                # Thêm nội dung vào nhóm hiện tại
                if current_heading:
                    current_content.append(region)
                else:
                    # Nếu không có heading trước đó, tạo chunk text đơn
                    structured_chunks.append(
                        {
                            "heading": "",
                            "content": region.get("text", ""),
                            "type": "text",
                        }
                    )

        # Thêm nhóm cuối cùng nếu còn
        if current_heading and current_content:
            structured_chunks.append(
                {
                    "heading": current_heading.get("text", ""),
                    "content": "\n".join([r.get("text", "") for r in current_content]),
                    "type": "heading_group",
                }
            )

        return structured_chunks

    def _chunk_by_structure(self, text: str, metadata: Dict) -> List[Dict]:
        """Chia văn bản thành các đoạn theo cấu trúc"""
        chunks = []

        # Tách theo các tiêu đề và đoạn văn
        # Mẫu: Một dòng ngắn, không có dấu chấm, và có một dòng trống phía sau
        # regex để nhận dạng tiêu đề
        heading_pattern = r"(?:^|\n)((?:[A-Za-z0-9\u00C0-\u1EF9]+[^.!?]*){1,60})\n\s*\n"

        # Tìm tất cả các tiêu đề
        headings = re.finditer(heading_pattern, text, re.MULTILINE)

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

        # Xử lý từng phần
        for i, (start, end, heading) in enumerate(positions):
            chunk_text = text[start:end].strip()
            if not chunk_text:
                continue

            # Phát hiện loại đoạn dựa vào nội dung
            chunk_type = "text"  # Mặc định

            # Đoạn có tiêu đề
            if heading:
                chunk_type = "heading"
            # Đoạn có bảng
            elif re.search(r"\|\s*-+\s*\|", chunk_text) or re.search(
                r"\|\s*:?-+:?\s*\|", chunk_text
            ):
                chunk_type = "table"
            # Đoạn có danh sách
            elif re.search(r"(?:^|\n)(?:[\*\-\+]|\d+\.)\s+", chunk_text):
                chunk_type = "list"
            # Đoạn có code
            elif re.search(r"```|(?:^|\n)(?:  |\t)", chunk_text):
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
        """Xử lý tài liệu PDF sử dụng layout detection"""
        print(
            f"\n=== Bắt đầu xử lý {os.path.basename(pdf_path)} với layout detection ==="
        )
        print(f"  - Layout detection enabled: {self.enable_layout_detection}")
        print(f"  - Layout model name: {self.layout_model_name}")

        # Kiểm tra xem layout detection có được bật hay không
        if not self.enable_layout_detection:
            print("Layout detection bị tắt. Sử dụng phương pháp tải thông thường.")
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
            return processed_chunks

        try:
            # Cấu hình đường dẫn cho Poppler và Tesseract trên Windows
            if os.name == "nt":  # Windows
                # Thêm đường dẫn Poppler
                poppler_paths = [
                    r"C:\Program Files\poppler\bin",
                    r"C:\Program Files\poppler\Library\bin",
                    r"C:\poppler\bin",
                    r"C:\poppler\Library\bin",
                ]

                # Kiểm tra và đặt POPPLER_PATH
                for path in poppler_paths:
                    if os.path.exists(path):
                        print(f"Tìm thấy Poppler tại: {path}")
                        os.environ["POPPLER_PATH"] = path
                        break

            # Kiểm tra xem có thể sử dụng layout detection không và lưu kết quả vào biến
            layout_model = self._get_layout_model()
            print(f"Kết quả kiểm tra model layout: {layout_model is not None}")

            if layout_model is None:
                print(
                    "Mô hình layout detection không khả dụng. Chuyển sang phương pháp tải thông thường."
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

            # Sử dụng thư viện để chuyển PDF thành ảnh
            try:
                from pdf2image import convert_from_path

                print(
                    f"Đường dẫn POPPLER_PATH: {os.environ.get('POPPLER_PATH', 'Không cấu hình')}"
                )

                # Kiểm tra lại poppler trước khi chuyển đổi
                installation_check = self.check_layoutparser_installation()
                if not installation_check["status"]["poppler"]:
                    print(
                        f"Poppler không khả dụng: {installation_check['missing_components']}"
                    )
                    raise Exception("Poppler không khả dụng cho layout detection")

                # Truyền đường dẫn poppler_path trực tiếp nếu có
                poppler_path = os.environ.get("POPPLER_PATH", None)
                if poppler_path:
                    images = convert_from_path(pdf_path, poppler_path=poppler_path)
                    print(
                        f"Đã chuyển đổi PDF thành {len(images)} ảnh sử dụng poppler_path"
                    )
                else:
                    images = convert_from_path(pdf_path)
                    print(
                        f"Đã chuyển đổi PDF thành {len(images)} ảnh không dùng poppler_path"
                    )

            except ImportError as e:
                print(f"ImportError: {str(e)}")
                print(
                    "Không thể import pdf2image. Vui lòng cài đặt: pip install pdf2image"
                )
                return self.load_document_with_category(pdf_path, category)
            except Exception as e:
                print(f"Lỗi khi chuyển đổi PDF thành ảnh: {str(e)}")
                return self.load_document_with_category(pdf_path, category)

            all_regions = []

            # Xử lý từng trang
            for i, image in enumerate(images):
                # Lưu ảnh tạm thời
                temp_img_path = f"temp_page_{i}.jpg"
                image.save(temp_img_path)

                try:
                    print(
                        f"Xử lý trang {i+1}/{len(images)} của {os.path.basename(pdf_path)}"
                    )
                    # Phát hiện layout
                    regions = self.detect_layout(temp_img_path)

                    if regions is not None and len(regions) > 0:
                        print(
                            f"Đã phát hiện {len(regions)} vùng layout trên trang {i+1}"
                        )
                        # Trích xuất văn bản từ các vùng
                        regions = self.extract_text_from_regions(
                            np.array(image), regions
                        )

                        # Thêm thông tin trang vào regions
                        for region in regions:
                            region["page"] = i + 1

                        all_regions.extend(regions)
                    else:
                        print(
                            f"Không tìm thấy regions cho trang {i+1}, regions={regions}"
                        )
                except Exception as e:
                    print(f"Lỗi khi xử lý trang {i+1}: {str(e)}")
                    import traceback

                    traceback.print_exc()

                # Xóa file tạm
                if os.path.exists(temp_img_path):
                    os.remove(temp_img_path)

            # Kiểm tra xem có regions không
            if not all_regions:
                print(
                    "Không tìm thấy regions nào. Sử dụng phương pháp tải thông thường."
                )
                documents = self.load_document_with_category(pdf_path, category)
                # Chuyển đổi documents
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
                return processed_chunks

            # Lọc và nhóm các vùng layout
            structured_chunks = self.filter_and_group_regions(all_regions)

            # Chuyển đổi structured_chunks thành định dạng document
            processed_chunks = []
            base_metadata = {
                "source": os.path.basename(pdf_path),
                "category": category
                or self._classify_document_content(
                    "\n".join([chunk.get("content", "") for chunk in structured_chunks])
                ),
            }

            for i, chunk in enumerate(structured_chunks):
                # Tạo văn bản có cấu trúc
                if chunk["heading"]:
                    text = f"{chunk['heading']}\n\n{chunk['content']}"
                else:
                    text = chunk["content"]

                # Thêm metadata bổ sung
                chunk_metadata = {
                    **base_metadata,
                    "chunk_type": chunk["type"],
                }

                processed_chunks.append(
                    {
                        "id": str(i),
                        "text": text,
                        "metadata": chunk_metadata,
                        "source": base_metadata["source"],
                        "category": base_metadata["category"],
                    }
                )

            print(f"Đã xử lý {len(processed_chunks)} chunks với layout detection")
            return processed_chunks

        except Exception as e:
            print(f"Lỗi khi xử lý PDF với layout detection: {str(e)}")
            # Fallback to standard loading
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
        """Kiểm tra xem các thư viện layout parser đã được cài đặt chưa"""
        missing_components = []
        installation_tips = {
            "windows": """
            # Cài đặt cho Windows:
            1. Cài đặt Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
            2. Cài đặt Poppler: https://github.com/oschwartz10612/poppler-windows/releases
            3. Thêm đường dẫn vào PATH hoặc cấu hình biến môi trường:
               - POPPLER_PATH = C:\\Program Files\\poppler\\bin
               - TESSDATA_PREFIX = C:\\Program Files\\Tesseract-OCR\\tessdata
            4. pip install layoutparser pdf2image pytesseract torch torchvision
            5. Thử endpoint /api/check/layoutparser/reset để tự động cấu hình lại đường dẫn
            """,
            "linux": """
            # Cài đặt cho Linux:
            sudo apt-get update
            sudo apt-get install -y poppler-utils tesseract-ocr libtesseract-dev
            pip install layoutparser pdf2image pytesseract torch torchvision
            """,
            "docker": """
            # Sử dụng Docker để tránh vấn đề cài đặt:
            docker pull layoutparser/layoutparser:latest
            """,
        }

        # Kiểm tra các thư viện cần thiết
        try:
            import layoutparser

            layoutparser_installed = True
        except ImportError:
            layoutparser_installed = False
            missing_components.append("layoutparser")

        try:
            import cv2

            opencv_installed = True
        except ImportError:
            opencv_installed = False
            missing_components.append("opencv-python")

        try:
            from pdf2image import convert_from_path

            pdf2image_installed = True
        except ImportError:
            pdf2image_installed = False
            missing_components.append("pdf2image")

        # Kiểm tra Tesseract OCR
        try:
            import pytesseract
            from PIL import Image

            tesseract_installed = True

            # Kiểm tra khả năng chạy Tesseract
            try:
                tesseract_path = pytesseract.pytesseract.tesseract_cmd
                tesseract_version = pytesseract.get_tesseract_version()
                tesseract_working = True
                tesseract_info = {
                    "version": str(tesseract_version),
                    "path": tesseract_path,
                }
            except Exception as e:
                tesseract_working = False
                tesseract_info = {"error": str(e)}
                missing_components.append("tesseract-config")

        except ImportError:
            tesseract_installed = False
            tesseract_working = False
            tesseract_info = {"error": "pytesseract not installed"}
            missing_components.append("pytesseract")

        # Kiểm tra Poppler
        poppler_installed = False
        poppler_info = {}

        # Kiểm tra POPPLER_PATH
        poppler_path = os.environ.get("POPPLER_PATH", None)

        # Kiểm tra các đường dẫn phổ biến nếu POPPLER_PATH chưa được thiết lập
        if poppler_path:
            poppler_info["path"] = poppler_path
            if os.path.exists(poppler_path):
                # Kiểm tra sự tồn tại của các file thực thi
                exes = ["pdftoppm", "pdftoppm.exe", "pdfinfo", "pdfinfo.exe"]
                for exe in exes:
                    exe_path = os.path.join(poppler_path, exe)
                    if os.path.exists(exe_path):
                        poppler_installed = True
                        poppler_info["executable"] = exe_path
                        break
            else:
                poppler_info["error"] = (
                    f"Path exists but directory not found: {poppler_path}"
                )
        else:
            # Tìm kiếm các đường dẫn phổ biến
            common_paths = [
                r"C:\Program Files\poppler\bin",
                r"C:\Program Files\poppler\Library\bin",
                r"C:\poppler\bin",
                r"C:\poppler\Library\bin",
            ]

            for path in common_paths:
                if os.path.exists(path):
                    poppler_info["detected_path"] = path
                    # Kiểm tra sự tồn tại của các file thực thi
                    exes = ["pdftoppm", "pdftoppm.exe", "pdfinfo", "pdfinfo.exe"]
                    for exe in exes:
                        exe_path = os.path.join(path, exe)
                        if os.path.exists(exe_path):
                            poppler_installed = True
                            poppler_info["executable"] = exe_path
                            # Tự động đặt POPPLER_PATH
                            os.environ["POPPLER_PATH"] = path
                            poppler_info["path"] = path
                            break
                    if poppler_installed:
                        break

            if not poppler_installed:
                poppler_info["error"] = "Poppler not found in common paths"
                missing_components.append("poppler")

        # Nếu tất cả các thành phần cần thiết đều được cài đặt
        all_components_installed = (
            layoutparser_installed
            and opencv_installed
            and pdf2image_installed
            and tesseract_installed
            and tesseract_working
            and poppler_installed
        )

        # Tạo phản hồi
        return {
            "ready": all_components_installed,
            "status": {
                "layoutparser": layoutparser_installed,
                "opencv": opencv_installed,
                "pdf2image": pdf2image_installed,
                "tesseract": tesseract_installed and tesseract_working,
                "poppler": poppler_installed,
            },
            "details": {
                "tesseract": tesseract_info,
                "poppler": poppler_info,
            },
            "missing_components": missing_components,
            "installation_tips": installation_tips,
        }

    def _check_requirements(self):
        """Kiểm tra các yêu cầu cài đặt cho layout detection"""
        try:
            import layoutparser as lp
        except ImportError:
            print(
                "Cảnh báo: Không thể import layoutparser. Layout detection sẽ bị tắt."
            )
            print("Hãy cài đặt: pip install layoutparser[effdet]")
            self.enable_layout_detection = False
            self.use_structural_chunking = True
            return

        try:
            import cv2
        except ImportError:
            print("Cảnh báo: Không thể import cv2. Layout detection sẽ bị tắt.")
            print("Hãy cài đặt: pip install opencv-python")
            self.enable_layout_detection = False
            return

        try:
            import pdf2image
        except ImportError:
            print("Cảnh báo: Không thể import pdf2image. Layout detection sẽ bị tắt.")
            print("Hãy cài đặt: pip install pdf2image")
            self.enable_layout_detection = False
            return

        # Kiểm tra engine backend cho layoutparser
        try:
            # Thử import cả hai backend
            backend_available = False

            try:
                import detectron2

                backend_available = True
            except ImportError:
                pass

            try:
                import effdet

                backend_available = True
            except ImportError:
                pass

            if not backend_available:
                print(
                    "Cảnh báo: Không tìm thấy backend cho layoutparser (detectron2 hoặc effdet)."
                )
                print("Hãy cài đặt: pip install layoutparser[effdet]")
                self.enable_layout_detection = False
        except:
            self.enable_layout_detection = False
