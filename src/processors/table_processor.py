import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from langchain.schema import Document
from tqdm import tqdm
import json
import os

from src.config import (
    CHUNK_SIZE_SPECIALIZED,
    CHUNK_OVERLAP_SPECIALIZED,
    MIN_CHUNK_SIZE,
    MIN_CHUNK_CHARACTERS,
)

from src.utils import measure_time, print_document_info


class TableDocumentProcessor:
    """Lớp xử lý chunking đặc biệt cho dữ liệu dạng bảng (CSV, Excel)"""

    def __init__(self, embeddings):
        """Khởi tạo với embedding model đã cho"""
        self.embeddings = embeddings
        self.max_rows_per_chunk = 100  # Số dòng tối đa trong một chunk
        self.supported_extensions = [".csv", ".xlsx", ".xls", ".json", ".tsv"]

    def _can_process(self, file_path: str) -> bool:
        """Kiểm tra xem file có phải là định dạng bảng được hỗ trợ hay không"""
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.supported_extensions

    @measure_time
    def process_table_documents(self, docs: List[Document]) -> List[Document]:
        """Xử lý tài liệu dạng bảng với phương pháp chunking đặc biệt

        Args:
            docs: Danh sách tài liệu dạng bảng cần xử lý

        Returns:
            Danh sách tài liệu đã được chunk theo cấu trúc bảng
        """
        print("⏳ Đang xử lý tài liệu dạng bảng...")
        table_chunks = []

        for doc in tqdm(docs, desc="Processing table documents", unit="doc"):
            source_path = doc.metadata.get("source_path", "unknown")

            # Kiểm tra xem đã có nội dung bảng trong metadata chưa
            if "table_content" in doc.metadata:
                # Đã được xử lý bởi loader, sử dụng dữ liệu có sẵn
                if isinstance(
                    doc.metadata["table_content"], (pd.DataFrame, dict, list)
                ):
                    df = pd.DataFrame(doc.metadata["table_content"])
                else:
                    # Trích xuất DataFrame từ nội dung văn bản
                    df = self._extract_dataframe_from_text(
                        doc.page_content, source_path
                    )
            else:
                # Nội dung văn bản thông thường, thử chuyển đổi
                df = self._extract_dataframe_from_text(doc.page_content, source_path)

            # Nếu không thể chuyển đổi, bỏ qua
            if df is None or df.empty:
                continue

            # Thêm loại tài liệu vào metadata
            metadata = {
                **doc.metadata,
                "table_document": True,
                "table_rows": len(df),
                "table_columns": len(df.columns),
                "column_names": df.columns.tolist(),
            }

            # Xử lý bảng
            chunks = self._process_dataframe(df, metadata)
            table_chunks.extend(chunks)

        # Thêm thông tin về loại chunker đã sử dụng
        for chunk in table_chunks:
            if "processor" not in chunk.metadata:
                chunk.metadata["processor"] = "table_processor"

        print(f"✅ Đã xử lý tài liệu dạng bảng: {len(table_chunks)} chunks")
        print_document_info(table_chunks, "Kết quả Table processor")
        return table_chunks

    def _extract_dataframe_from_text(
        self, content: str, file_path: str
    ) -> Optional[pd.DataFrame]:
        """Cố gắng chuyển đổi nội dung văn bản thành DataFrame

        Args:
            content: Nội dung văn bản
            file_path: Đường dẫn file gốc

        Returns:
            DataFrame hoặc None nếu không thể chuyển đổi
        """
        if not self._can_process(file_path):
            return None

        try:
            _, ext = os.path.splitext(file_path.lower())

            # Thử đọc trực tiếp từ file nếu tồn tại
            if os.path.exists(file_path):
                if ext == ".csv":
                    return pd.read_csv(file_path)
                elif ext in [".xlsx", ".xls"]:
                    return pd.read_excel(file_path)
                elif ext == ".json":
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return pd.DataFrame(data)
                elif ext == ".tsv":
                    return pd.read_csv(file_path, sep="\t")

            # Nếu không thể đọc file trực tiếp, thử phân tích từ nội dung
            if content:
                # Thử phân tích CSV từ nội dung văn bản
                try:
                    from io import StringIO

                    return pd.read_csv(StringIO(content))
                except:
                    # Thử phân tích JSON
                    try:
                        data = json.loads(content)
                        if isinstance(data, list):
                            return pd.DataFrame(data)
                        else:
                            return pd.DataFrame([data])
                    except:
                        pass
        except Exception as e:
            print(f"⚠️ Lỗi khi chuyển đổi sang DataFrame: {str(e)}")

        return None

    def _process_dataframe(
        self, df: pd.DataFrame, metadata: Dict[str, Any]
    ) -> List[Document]:
        """Xử lý DataFrame thành các chunks có ý nghĩa

        Args:
            df: DataFrame cần xử lý
            metadata: Metadata của tài liệu gốc

        Returns:
            Danh sách Document đã được chunk
        """
        chunks = []

        # 1. Tạo chunk cho metadata của bảng
        table_info = {
            "columns": df.columns.tolist(),
            "shape": df.shape,
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "summary": df.describe().to_dict() if df.shape[0] > 5 else {},
        }

        metadata_content = f"Table Information:\n"
        metadata_content += f"- Total rows: {df.shape[0]}\n"
        metadata_content += f"- Total columns: {df.shape[1]}\n"
        metadata_content += f"- Column names: {', '.join(df.columns)}\n\n"
        metadata_content += f"Column Data Types:\n"
        for col, dtype in df.dtypes.items():
            metadata_content += f"- {col}: {dtype}\n"

        # Thêm thông tin tóm tắt cho dữ liệu số
        if df.shape[0] > 5:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                metadata_content += "\nNumeric Column Statistics:\n"
                stats = df[numeric_cols].describe()
                for col in numeric_cols:
                    metadata_content += f"- {col}: min={stats[col]['min']:.2f}, max={stats[col]['max']:.2f}, avg={stats[col]['mean']:.2f}\n"

        chunks.append(
            Document(
                page_content=metadata_content,
                metadata={
                    **metadata,
                    "table_element_type": "metadata",
                    "table_info": table_info,
                },
            )
        )

        # 2. Tạo chunks cho dữ liệu bảng
        total_rows = df.shape[0]

        # Xác định cách chunking dựa trên kích thước bảng
        if total_rows <= self.max_rows_per_chunk:
            # Bảng nhỏ, giữ nguyên
            chunks.append(self._create_table_chunk(df, 0, total_rows - 1, metadata))
        else:
            # Bảng lớn, chia thành các chunk nhỏ hơn
            for start_idx in range(0, total_rows, self.max_rows_per_chunk):
                end_idx = min(start_idx + self.max_rows_per_chunk - 1, total_rows - 1)
                chunks.append(
                    self._create_table_chunk(df, start_idx, end_idx, metadata)
                )

        return chunks

    def _create_table_chunk(
        self, df: pd.DataFrame, start_idx: int, end_idx: int, metadata: Dict[str, Any]
    ) -> Document:
        """Tạo chunk từ một phần của DataFrame

        Args:
            df: DataFrame gốc
            start_idx: Chỉ số dòng bắt đầu
            end_idx: Chỉ số dòng kết thúc
            metadata: Metadata của tài liệu gốc

        Returns:
            Document chứa chunk
        """
        # Lấy phần dữ liệu cần thiết
        subset_df = df.iloc[start_idx : end_idx + 1]

        # Tạo nội dung văn bản từ dữ liệu
        content = f"Table Data (Rows {start_idx+1}-{end_idx+1} of {df.shape[0]}):\n\n"

        # Thêm tên cột
        content += "| " + " | ".join(str(col) for col in df.columns) + " |\n"
        content += "| " + " | ".join("-" * len(str(col)) for col in df.columns) + " |\n"

        # Thêm dữ liệu từng dòng
        for _, row in subset_df.iterrows():
            content += "| " + " | ".join(str(row[col]) for col in df.columns) + " |\n"

        # Thêm thông tin tóm tắt nếu chunk đủ lớn
        if len(subset_df) > 5:
            content += "\nSummary for this section:\n"
            numeric_cols = subset_df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                for col in numeric_cols:
                    content += f"- {col}: min={subset_df[col].min():.2f}, max={subset_df[col].max():.2f}, avg={subset_df[col].mean():.2f}\n"

        # Tạo metadata cho chunk
        chunk_metadata = {
            **metadata,
            "table_element_type": "data",
            "row_range": (start_idx, end_idx),
            "row_count": end_idx - start_idx + 1,
        }

        return Document(page_content=content, metadata=chunk_metadata)
