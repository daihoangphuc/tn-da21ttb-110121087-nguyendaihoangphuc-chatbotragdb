import re
import os
from typing import List, Dict, Any, Optional, Tuple
from langchain.schema import Document
from tqdm import tqdm
import fitz  # PyMuPDF
from PIL import Image
import numpy as np
import io
import tempfile
import cv2

from src.config import (
    CHUNK_SIZE_SPECIALIZED,
    CHUNK_OVERLAP_SPECIALIZED,
    MIN_CHUNK_SIZE,
    MIN_CHUNK_CHARACTERS,
)

from src.utils import measure_time, print_document_info

try:
    import pytesseract

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("⚠️ pytesseract không được cài đặt. Nhận dạng OCR sẽ bị vô hiệu hóa.")


class PDFDocumentProcessor:
    """Lớp xử lý chunking đặc biệt cho PDF phức tạp với bảng, hình ảnh và định dạng"""

    def __init__(self, embeddings):
        """Khởi tạo với embedding model đã cho"""
        self.embeddings = embeddings
        self.min_table_rows = 3  # Số dòng tối thiểu để được coi là bảng
        self.min_table_cols = 2  # Số cột tối thiểu để được coi là bảng
        self.image_resolution_threshold = 100  # Ngưỡng độ phân giải cho OCR (DPI)

    @measure_time
    def process_pdf_documents(self, docs: List[Document]) -> List[Document]:
        """Xử lý tài liệu PDF với phương pháp chunking đặc biệt

        Args:
            docs: Danh sách tài liệu PDF cần xử lý

        Returns:
            Danh sách tài liệu đã được chunk
        """
        print("⏳ Đang xử lý tài liệu PDF phức tạp...")
        pdf_chunks = []

        for doc in tqdm(docs, desc="Processing PDF documents", unit="doc"):
            source_path = doc.metadata.get("source_path", "unknown")

            # Kiểm tra xem file có phải là PDF không
            if not source_path.lower().endswith(".pdf"):
                continue

            # Kiểm tra xem file có tồn tại không
            if not os.path.exists(source_path):
                print(f"⚠️ File không tồn tại: {source_path}")
                continue

            # Thêm loại tài liệu vào metadata
            metadata = {**doc.metadata, "pdf_document": True}

            # Xử lý PDF
            try:
                # Mở PDF với PyMuPDF
                pdf_doc = fitz.open(source_path)

                # Xử lý metadata của PDF
                pdf_info = self._extract_pdf_metadata(pdf_doc)
                metadata.update(pdf_info)

                # Tạo chunk metadata riêng
                metadata_chunk = self._create_metadata_chunk(pdf_doc, metadata)
                pdf_chunks.append(metadata_chunk)

                # Xử lý từng trang
                for page_num, page in enumerate(pdf_doc):
                    page_chunks = self._process_page(page, page_num, metadata)
                    pdf_chunks.extend(page_chunks)

            except Exception as e:
                print(f"⚠️ Lỗi khi xử lý PDF {source_path}: {str(e)}")
                continue

        # Thêm thông tin về loại chunker đã sử dụng
        for chunk in pdf_chunks:
            if "processor" not in chunk.metadata:
                chunk.metadata["processor"] = "pdf_processor"

        print(f"✅ Đã xử lý tài liệu PDF: {len(pdf_chunks)} chunks")
        print_document_info(pdf_chunks, "Kết quả PDF processor")
        return pdf_chunks

    def _extract_pdf_metadata(self, pdf_doc: fitz.Document) -> Dict[str, Any]:
        """Trích xuất metadata từ tài liệu PDF

        Args:
            pdf_doc: Đối tượng fitz.Document

        Returns:
            Dict chứa metadata
        """
        metadata = {}
        try:
            # Lấy metadata cơ bản
            metadata["pdf_pages"] = len(pdf_doc)
            metadata["pdf_title"] = pdf_doc.metadata.get("title", "")
            metadata["pdf_author"] = pdf_doc.metadata.get("author", "")
            metadata["pdf_subject"] = pdf_doc.metadata.get("subject", "")
            metadata["pdf_keywords"] = pdf_doc.metadata.get("keywords", "")
            metadata["pdf_creator"] = pdf_doc.metadata.get("creator", "")
            metadata["pdf_producer"] = pdf_doc.metadata.get("producer", "")

            # Kiểm tra xem PDF có được bảo vệ không
            metadata["pdf_encrypted"] = pdf_doc.is_encrypted

            # Kích thước tài liệu
            if len(pdf_doc) > 0:
                first_page = pdf_doc[0]
                metadata["pdf_width"] = first_page.rect.width
                metadata["pdf_height"] = first_page.rect.height

        except Exception as e:
            print(f"⚠️ Lỗi khi trích xuất metadata PDF: {str(e)}")

        return metadata

    def _create_metadata_chunk(
        self, pdf_doc: fitz.Document, metadata: Dict[str, Any]
    ) -> Document:
        """Tạo chunk chứa thông tin metadata của PDF

        Args:
            pdf_doc: Đối tượng fitz.Document
            metadata: Metadata đã trích xuất

        Returns:
            Document chứa thông tin metadata
        """
        # Tạo nội dung văn bản từ metadata
        content = "PDF Document Information:\n\n"

        # Thêm thông tin cơ bản
        if metadata.get("pdf_title"):
            content += f"Title: {metadata['pdf_title']}\n"
        if metadata.get("pdf_author"):
            content += f"Author: {metadata['pdf_author']}\n"
        if metadata.get("pdf_subject"):
            content += f"Subject: {metadata['pdf_subject']}\n"
        if metadata.get("pdf_keywords"):
            content += f"Keywords: {metadata['pdf_keywords']}\n"

        # Thêm thông tin kỹ thuật
        content += f"Total Pages: {metadata['pdf_pages']}\n"
        if "pdf_width" in metadata and "pdf_height" in metadata:
            content += f"Page Size: {metadata['pdf_width']:.1f} x {metadata['pdf_height']:.1f} points\n"

        # Thêm thông tin về cấu trúc tài liệu
        content += "\nDocument Structure:\n"

        # Trich xuất và thêm mục lục nếu có
        toc = pdf_doc.get_toc()
        if toc:
            content += "Table of Contents:\n"
            for level, title, page in toc:
                indent = "  " * (level - 1)
                content += f"{indent}- {title} (page {page})\n"

        # Tạo metadata cho chunk
        chunk_metadata = {**metadata, "pdf_element_type": "metadata"}

        return Document(page_content=content, metadata=chunk_metadata)

    def _process_page(
        self, page: fitz.Page, page_num: int, metadata: Dict[str, Any]
    ) -> List[Document]:
        """Xử lý một trang PDF

        Args:
            page: Đối tượng fitz.Page
            page_num: Số trang
            metadata: Metadata của tài liệu gốc

        Returns:
            Danh sách Document đã được chunk
        """
        page_chunks = []

        # Thêm thông tin trang vào metadata
        page_metadata = {
            **metadata,
            "pdf_page": page_num + 1,
            "page_width": page.rect.width,
            "page_height": page.rect.height,
        }

        # 1. Trích xuất và xử lý các bảng trong trang
        tables = self._extract_tables(page)
        for i, table in enumerate(tables):
            table_metadata = {
                **page_metadata,
                "pdf_element_type": "table",
                "table_index": i,
                "table_rows": len(table),
                "table_cols": len(table[0]) if table else 0,
            }

            table_content = self._format_table(table)
            page_chunks.append(
                Document(page_content=table_content, metadata=table_metadata)
            )

        # 2. Trích xuất và xử lý các hình ảnh trong trang
        images = self._extract_images(page)
        image_paths = []  # Danh sách các đường dẫn ảnh trong trang

        for i, (pix, bbox, image_path) in enumerate(images):
            # Thêm đường dẫn vào danh sách
            if image_path:
                image_paths.append(image_path)

            # OCR hình ảnh nếu có thể
            if TESSERACT_AVAILABLE:
                image_text = self._perform_ocr(pix)
                if image_text.strip():  # Nếu OCR trả về kết quả
                    image_metadata = {
                        **page_metadata,
                        "pdf_element_type": "image",
                        "image_index": i,
                        "bbox": [bbox.x0, bbox.y0, bbox.x1, bbox.y1],
                        "image_width": pix.width,
                        "image_height": pix.height,
                        "ocr_applied": True,
                        "image_path": image_path,
                        "image_paths": [
                            image_path
                        ],  # Thêm vào dạng mảng để phù hợp với schema
                    }

                    image_content = f"Image content (OCR):\n{image_text}"
                    page_chunks.append(
                        Document(page_content=image_content, metadata=image_metadata)
                    )

        # 3. Trích xuất và xử lý văn bản
        text_blocks = self._extract_text_blocks(page)

        # Loại bỏ các vùng văn bản đã được xử lý ở trong bảng hoặc hình ảnh
        filtered_blocks = []
        table_image_regions = []

        # Thu thập vùng bảng
        for table_info in tables:
            if hasattr(table_info, "rect"):  # Nếu có thông tin vùng
                table_image_regions.append(table_info.rect)

        # Thu thập vùng hình ảnh
        for _, bbox, _ in images:
            table_image_regions.append(bbox)

        # Lọc các block văn bản không nằm trong vùng bảng hoặc hình ảnh
        for block in text_blocks:
            block_rect = fitz.Rect(block[0], block[1], block[2], block[3])
            overlap = False

            for region in table_image_regions:
                if (
                    block_rect.intersects(region)
                    and self._calc_overlap_percent(block_rect, region) > 0.5
                ):
                    overlap = True
                    break

            if not overlap:
                filtered_blocks.append(block)

        # Xử lý các đoạn văn bản thành các chunk
        if filtered_blocks:
            current_text = ""
            current_size = 0

            for block in filtered_blocks:
                block_text = block[4]

                # Nếu thêm block mới vượt quá kích thước và đã có nội dung
                if (
                    current_size + len(block_text) > CHUNK_SIZE_SPECIALIZED
                    and current_text
                ):
                    # Tạo chunk từ văn bản hiện tại
                    if len(current_text) >= MIN_CHUNK_CHARACTERS:
                        text_metadata = {
                            **page_metadata,
                            "pdf_element_type": "text",
                            "image_paths": (
                                image_paths if image_paths else []
                            ),  # Thêm tất cả đường dẫn ảnh vào metadata
                        }
                        page_chunks.append(
                            Document(page_content=current_text, metadata=text_metadata)
                        )

                    # Reset văn bản hiện tại
                    current_text = ""
                    current_size = 0

                # Thêm block vào văn bản hiện tại
                current_text += block_text + "\n"
                current_size += len(block_text) + 1

            # Xử lý chunk cuối cùng
            if current_text and len(current_text) >= MIN_CHUNK_CHARACTERS:
                text_metadata = {
                    **page_metadata,
                    "pdf_element_type": "text",
                    "image_paths": (
                        image_paths if image_paths else []
                    ),  # Thêm tất cả đường dẫn ảnh vào metadata
                }
                page_chunks.append(
                    Document(page_content=current_text, metadata=text_metadata)
                )

        return page_chunks

    def _extract_tables(self, page: fitz.Page) -> List[List[List[str]]]:
        """Trích xuất các bảng từ trang PDF

        Args:
            page: Đối tượng fitz.Page

        Returns:
            Danh sách các bảng, mỗi bảng là một list 2D
        """
        tables = []

        # Phương pháp 1: Sử dụng PyMuPDF để trích xuất bảng
        try:
            # Tìm các bảng bằng phương pháp phát hiện đường kẻ
            tab = page.find_tables()
            if tab and tab.tables:
                for idx, table in enumerate(tab.tables):
                    rows = []
                    for row_idx in range(table.row_count):
                        row = []
                        for col_idx in range(table.col_count):
                            cell = table.cells[row_idx * table.col_count + col_idx]
                            cell_text = page.get_text("text", clip=cell.rect).strip()
                            row.append(cell_text)
                        rows.append(row)

                    # Chỉ thêm bảng nếu nó đủ lớn
                    if (
                        len(rows) >= self.min_table_rows
                        and len(rows[0]) >= self.min_table_cols
                    ):
                        table.rect = table.bbox  # Lưu bbox của bảng
                        tables.append(rows)
        except Exception as e:
            print(f"⚠️ Lỗi khi trích xuất bảng từ trang {page.number+1}: {str(e)}")

        # Phương pháp 2: Phát hiện bảng từ cấu trúc văn bản (phòng trường hợp PyMuPDF không tìm được)
        if not tables:
            try:
                # Trích xuất cấu trúc văn bản dạng dict
                page_dict = page.get_text("dict")

                # Tìm các khối văn bản có dấu hiệu của bảng
                potential_tables = []
                for block in page_dict["blocks"]:
                    if "lines" in block:
                        # Tìm các dòng có cùng số lượng từ và khoảng cách đều nhau
                        lines = block["lines"]
                        if len(lines) >= self.min_table_rows:
                            # Tính khoảng cách giữa các từ trong mỗi dòng
                            spans_per_line = [len(line["spans"]) for line in lines]

                            # Nếu các dòng có số lượng spans tương tự nhau
                            if (
                                len(set(spans_per_line)) <= 3
                                and min(spans_per_line) >= self.min_table_cols
                            ):
                                # Trích xuất văn bản từ các spans
                                table_rows = []
                                for line in lines:
                                    row = [span["text"] for span in line["spans"]]
                                    table_rows.append(row)

                                # Chuẩn hóa bảng (đảm bảo tất cả các dòng có cùng số cột)
                                max_cols = max(len(row) for row in table_rows)
                                for row in table_rows:
                                    row.extend([""] * (max_cols - len(row)))

                                potential_tables.append(table_rows)

                # Thêm các bảng tiềm năng đã tìm thấy
                for table in potential_tables:
                    if (
                        len(table) >= self.min_table_rows
                        and len(table[0]) >= self.min_table_cols
                    ):
                        tables.append(table)
            except Exception as e:
                print(f"⚠️ Lỗi khi phát hiện bảng bằng phương pháp 2: {str(e)}")

        return tables

    def _extract_images(
        self, page: fitz.Page
    ) -> List[Tuple[fitz.Pixmap, fitz.Rect, str]]:
        """Trích xuất các hình ảnh từ trang PDF và lưu vào thư mục

        Args:
            page: Đối tượng fitz.Page

        Returns:
            Danh sách các bộ (pixmap, bbox, image_path)
        """
        images = []

        # Tạo thư mục lưu ảnh nếu chưa tồn tại
        images_dir = os.path.join(os.getcwd(), "src", "data", "images")
        os.makedirs(images_dir, exist_ok=True)

        # Tạo thư mục con theo document_id và trang
        doc_id = os.path.basename(page.parent.name).split(".")[0]
        page_num = page.number + 1
        doc_images_dir = os.path.join(images_dir, f"{doc_id}")
        os.makedirs(doc_images_dir, exist_ok=True)

        try:
            # Phương pháp 1: Sử dụng page.get_images()
            for img_idx, img_info in enumerate(page.get_images(full=True)):
                try:
                    # Lấy hình ảnh từ xref
                    xref = img_info[0]
                    base_image = page.parent.extract_image(xref)

                    if base_image:
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        # Lưu hình ảnh vào file
                        image_filename = f"page{page_num}_img{img_idx}.{image_ext}"
                        image_path = os.path.join(doc_images_dir, image_filename)

                        with open(image_path, "wb") as imgfile:
                            imgfile.write(image_bytes)

                        # Tạo đối tượng Pixmap
                        pix = fitz.Pixmap(image_bytes)

                        # Tìm bounding box của hình ảnh trên trang
                        bbox = None
                        for item in page.get_drawings():
                            if item["type"] == "image" and item["xref"] == xref:
                                bbox = item["rect"]
                                break

                        # Nếu không tìm thấy bbox, sử dụng một giá trị mặc định
                        if not bbox:
                            bbox = fitz.Rect(0, 0, 100, 100)

                        # Chỉ xử lý hình ảnh có kích thước đủ lớn
                        if pix.width >= 100 and pix.height >= 100:
                            # Tạo đường dẫn tương đối để dễ truy cập từ API
                            relative_path = os.path.join(
                                "data", "images", doc_id, image_filename
                            )
                            images.append((pix, bbox, relative_path))
                except Exception as e:
                    print(f"⚠️ Lỗi khi trích xuất hình ảnh {xref}: {str(e)}")

            # Phương pháp 2: Trích xuất tất cả hình ảnh từ trang
            if not images:
                # Tạo một pixmap từ trang
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

                # Chuyển đổi pixmap thành hình ảnh PIL
                img = Image.open(io.BytesIO(pix.tobytes()))

                # Lưu hình ảnh vào tập tin tạm thời để sử dụng với OpenCV
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    img.save(tmp.name)
                    tmp_path = tmp.name

                # Sử dụng OpenCV để phát hiện các vùng hình ảnh
                try:
                    cv_img = cv2.imread(tmp_path)
                    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

                    # Tìm các contour
                    contours, _ = cv2.findContours(
                        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                    )

                    # Lọc các contour lớn (có thể là hình ảnh)
                    min_area = pix.width * pix.height * 0.01  # 1% diện tích trang
                    for img_idx, contour in enumerate(contours):
                        area = cv2.contourArea(contour)
                        if area >= min_area:
                            # Tính toán bounding box
                            x, y, w, h = cv2.boundingRect(contour)

                            # Điều chỉnh tỷ lệ để phù hợp với tọa độ trang gốc
                            x0 = x / 2
                            y0 = y / 2
                            x1 = (x + w) / 2
                            y1 = (y + h) / 2

                            bbox = fitz.Rect(x0, y0, x1, y1)

                            # Trích xuất phần hình ảnh
                            img_region = img.crop((x, y, x + w, y + h))

                            # Lưu hình ảnh vào file
                            image_filename = f"page{page_num}_contour{img_idx}.png"
                            image_path = os.path.join(doc_images_dir, image_filename)
                            img_region.save(image_path)

                            # Tạo Pixmap từ region
                            img_bytes = io.BytesIO()
                            img_region.save(img_bytes, format="PNG")
                            img_bytes.seek(0)
                            img_pix = fitz.Pixmap(img_bytes.read())

                            # Tạo đường dẫn tương đối
                            relative_path = os.path.join(
                                "data", "images", doc_id, image_filename
                            )

                            # Thêm vào danh sách hình ảnh
                            images.append((img_pix, bbox, relative_path))

                except Exception as e:
                    print(f"⚠️ Lỗi khi sử dụng OpenCV để phát hiện hình ảnh: {str(e)}")

                # Xóa file tạm
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        except Exception as e:
            print(f"⚠️ Lỗi khi trích xuất hình ảnh từ trang {page.number+1}: {str(e)}")

        return images

    def _extract_text_blocks(self, page: fitz.Page) -> List[List]:
        """Trích xuất các khối văn bản từ trang PDF

        Args:
            page: Đối tượng fitz.Page

        Returns:
            Danh sách các khối văn bản
        """
        try:
            # Sử dụng API blocks để lấy các khối văn bản
            blocks = page.get_text("blocks")
            return blocks
        except Exception as e:
            print(
                f"⚠️ Lỗi khi trích xuất khối văn bản từ trang {page.number+1}: {str(e)}"
            )
            return []

    def _format_table(self, table: List[List[str]]) -> str:
        """Định dạng bảng thành văn bản có cấu trúc

        Args:
            table: Bảng dưới dạng list 2D

        Returns:
            Chuỗi văn bản biểu diễn bảng
        """
        if not table or not table[0]:
            return ""

        content = "Table:\n\n"

        # Xác định độ rộng cần thiết cho mỗi cột
        col_widths = []
        for col_idx in range(len(table[0])):
            max_width = 0
            for row_idx in range(len(table)):
                if col_idx < len(table[row_idx]):
                    cell_content = str(table[row_idx][col_idx])
                    # Tìm độ dài của từ dài nhất trong ô
                    max_word_len = max(
                        [len(word) for word in cell_content.split()] or [0]
                    )
                    # Sử dụng độ dài từ dài nhất hoặc độ dài chuỗi nếu ngắn hơn
                    max_width = max(
                        max_width, min(len(cell_content), max(max_word_len, 15))
                    )
            col_widths.append(min(max_width, 30))  # Giới hạn độ rộng tối đa là 30 ký tự

        # Điều chỉnh chiều rộng tổng thể để đảm bảo bảng không quá rộng
        total_width = sum(col_widths) + len(col_widths) * 3 + 1  # +3 cho "| " và " "
        if total_width > 100:  # Giới hạn chiều rộng bảng là 100 ký tự
            scale_factor = 100 / total_width
            col_widths = [
                max(5, int(w * scale_factor)) for w in col_widths
            ]  # Chiều rộng tối thiểu 5

        # Tạo header
        header = "| "
        for col_idx, width in enumerate(col_widths):
            if col_idx < len(table[0]):
                cell_text = str(table[0][col_idx])
                # Đảm bảo cell_text không vượt quá chiều rộng
                if len(cell_text) > width:
                    cell_text = cell_text[: width - 3] + "..."
                header += cell_text.ljust(width) + " | "
        content += header + "\n"

        # Tạo separator
        separator = "| "
        for width in col_widths:
            separator += "-" * width + " | "
        content += separator + "\n"

        # Tạo nội dung các dòng
        for row_idx in range(1, len(table)):
            row = "| "
            for col_idx, width in enumerate(col_widths):
                if col_idx < len(table[row_idx]):
                    cell_text = str(table[row_idx][col_idx])
                    # Nếu cell_text vượt quá chiều rộng, chia thành nhiều dòng
                    if len(cell_text) > width:
                        # Chia cell_text thành các dòng
                        wrapped_text = self._wrap_text(cell_text, width)
                        row += wrapped_text[0].ljust(width) + " | "
                    else:
                        row += cell_text.ljust(width) + " | "
                else:
                    row += " " * width + " | "
            content += row + "\n"

            # Xử lý các dòng bổ sung cho cell nhiều dòng
            max_lines = 1
            for col_idx, width in enumerate(col_widths):
                if col_idx < len(table[row_idx]):
                    cell_text = str(table[row_idx][col_idx])
                    if len(cell_text) > width:
                        wrapped_text = self._wrap_text(cell_text, width)
                        max_lines = max(max_lines, len(wrapped_text))

            # Thêm các dòng bổ sung nếu cần
            for line_idx in range(1, max_lines):  # Bắt đầu từ dòng thứ 2
                extra_row = "| "
                for col_idx, width in enumerate(col_widths):
                    if col_idx < len(table[row_idx]):
                        cell_text = str(table[row_idx][col_idx])
                        if len(cell_text) > width:
                            wrapped_text = self._wrap_text(cell_text, width)
                            if line_idx < len(wrapped_text):
                                extra_row += wrapped_text[line_idx].ljust(width) + " | "
                            else:
                                extra_row += " " * width + " | "
                        else:
                            extra_row += " " * width + " | "
                    else:
                        extra_row += " " * width + " | "
                content += extra_row + "\n"

        return content

    def _wrap_text(self, text: str, width: int) -> List[str]:
        """Chia một chuỗi thành các dòng theo độ rộng cho trước

        Args:
            text: Chuỗi cần chia
            width: Độ rộng tối đa của mỗi dòng

        Returns:
            Danh sách các dòng
        """
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            # Nếu thêm từ mới vào dòng hiện tại sẽ vượt quá độ rộng
            if len(current_line) + len(word) + 1 > width:
                # Thêm dòng hiện tại vào kết quả và bắt đầu dòng mới
                if current_line:
                    lines.append(current_line)

                # Nếu từ dài hơn độ rộng, cần chia nhỏ
                if len(word) > width:
                    # Chia từ thành các phần có độ dài width
                    for i in range(0, len(word), width):
                        part = word[i : i + width]
                        if i + width < len(word):
                            lines.append(part + "-")
                        else:
                            current_line = part
                else:
                    current_line = word
            else:
                # Thêm từ vào dòng hiện tại
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word

        # Thêm dòng cuối cùng nếu có
        if current_line:
            lines.append(current_line)

        # Nếu không có dòng nào, thêm một dòng trống
        if not lines:
            lines.append("")

        return lines

    def _perform_ocr(self, pix: fitz.Pixmap) -> str:
        """Thực hiện OCR trên hình ảnh

        Args:
            pix: Đối tượng fitz.Pixmap

        Returns:
            Văn bản đã được OCR
        """
        if not TESSERACT_AVAILABLE:
            return ""

        try:
            # Chuyển đổi Pixmap thành hình ảnh PIL
            img_bytes = pix.tobytes()
            img = Image.open(io.BytesIO(img_bytes))

            # Thực hiện OCR
            text = pytesseract.image_to_string(img, lang="eng+vie")
            return text
        except Exception as e:
            print(f"⚠️ Lỗi khi thực hiện OCR: {str(e)}")
            return ""

    def _calc_overlap_percent(self, rect1: fitz.Rect, rect2: fitz.Rect) -> float:
        """Tính toán phần trăm chồng lấp giữa hai hình chữ nhật

        Args:
            rect1: Hình chữ nhật thứ nhất
            rect2: Hình chữ nhật thứ hai

        Returns:
            Phần trăm chồng lấp
        """
        # Tính diện tích giao nhau
        inter_rect = rect1 & rect2  # Phép toán & là phép giao trong fitz.Rect
        inter_area = inter_rect.width * inter_rect.height

        # Tính diện tích rect1
        rect1_area = rect1.width * rect1.height

        # Tính phần trăm chồng lấp
        if rect1_area == 0:
            return 0

        return inter_area / rect1_area
