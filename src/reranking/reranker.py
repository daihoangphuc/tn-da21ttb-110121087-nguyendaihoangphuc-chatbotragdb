from typing import List, Dict, Any, Optional, Union, Callable
from abc import ABC, abstractmethod
import numpy as np
import time
from langchain.schema import Document

# Sử dụng typing Protocol cho duck-typing
from typing_extensions import Protocol

from src.config import (
    RERANKER_MODEL,
    RERANKER_DEVICE,
    RERANKER_BATCH_SIZE,
    RERANKER_USE_FP16,
)
from src.utils import measure_time


class Reranker(ABC):
    """Lớp trừu tượng cho reranker"""

    @abstractmethod
    def rerank(
        self, query: str, documents: List[Document], top_k: Optional[int] = None
    ) -> List[Document]:
        """Rerank danh sách tài liệu dựa trên query

        Args:
            query: Câu truy vấn
            documents: Danh sách tài liệu cần rerank
            top_k: Số lượng tài liệu cần trả về, mặc định là tất cả

        Returns:
            Danh sách tài liệu đã được sắp xếp lại theo điểm số rerank
        """
        pass


class HFReranker(Reranker):
    """Reranker sử dụng mô hình từ HuggingFace"""

    def __init__(
        self,
        model_name: str = RERANKER_MODEL,
        device: str = RERANKER_DEVICE,
        batch_size: int = RERANKER_BATCH_SIZE,
        use_fp16: bool = RERANKER_USE_FP16,
    ):
        """Khởi tạo reranker với mô hình từ HuggingFace

        Args:
            model_name: Tên mô hình HuggingFace
            device: Thiết bị để chạy mô hình (cpu hoặc cuda)
            batch_size: Kích thước batch
            use_fp16: Sử dụng precision fp16 hay không
        """
        from sentence_transformers import CrossEncoder

        print(f"⏳ Đang tải mô hình reranker: {model_name} trên {device}...")

        # Nếu thiết bị là cuda nhưng không có GPUs, sử dụng CPU
        if device == "cuda":
            import torch

            if not torch.cuda.is_available():
                print("⚠️ CUDA không khả dụng, sử dụng CPU thay thế")
                device = "cpu"

        start_time = time.time()
        self.model = CrossEncoder(
            model_name_or_path=model_name,
            device=device,
            max_length=512,
        )

        print(f"✅ Đã tải mô hình reranker trong {time.time() - start_time:.2f}s")
        self.batch_size = batch_size
        self.use_fp16 = use_fp16

    @measure_time
    def rerank(
        self, query: str, documents: List[Document], top_k: Optional[int] = None
    ) -> List[Document]:
        """Rerank danh sách tài liệu dựa trên query

        Args:
            query: Câu truy vấn
            documents: Danh sách tài liệu cần rerank
            top_k: Số lượng tài liệu cần trả về, mặc định là tất cả

        Returns:
            Danh sách tài liệu đã được sắp xếp lại theo điểm số rerank
        """
        if not documents:
            return []

        # Nếu không chỉ định top_k, sử dụng tất cả
        if top_k is None:
            top_k = len(documents)
        else:
            top_k = min(top_k, len(documents))

        # Tạo các cặp (query, doc) để đưa vào mô hình
        doc_texts = [doc.page_content for doc in documents]
        query_doc_pairs = [(query, text) for text in doc_texts]

        # Thực hiện cross-encoding để tính điểm tương đồng
        scores = self.model.predict(
            query_doc_pairs,
            batch_size=self.batch_size,
            show_progress_bar=len(documents) > 10,
        )

        # Tạo danh sách các cặp (điểm số, tài liệu, index)
        scored_documents = [
            (score, doc, i) for i, (score, doc) in enumerate(zip(scores, documents))
        ]

        # Sắp xếp theo điểm số giảm dần
        scored_documents.sort(key=lambda x: x[0], reverse=True)

        # Lấy top_k tài liệu
        reranked_docs = []
        for score, doc, original_idx in scored_documents[:top_k]:
            # Thêm thông tin reranking vào metadata
            doc.metadata["reranker_score"] = float(score)
            doc.metadata["original_retrieval_rank"] = original_idx
            reranked_docs.append(doc)

        print(f"✅ Đã rerank {len(documents)} tài liệu, lấy top {top_k}")
        return reranked_docs


class RerankerFactory:
    """Factory để tạo ra các loại reranker khác nhau"""

    @staticmethod
    def create_reranker(reranker_type: str = "hf", **kwargs) -> Reranker:
        """Tạo một reranker dựa trên loại

        Args:
            reranker_type: Loại reranker ("hf" cho HuggingFace)
            **kwargs: Các tham số bổ sung cho reranker

        Returns:
            Đối tượng Reranker
        """
        if reranker_type.lower() == "hf":
            return HFReranker(**kwargs)
        else:
            raise ValueError(f"Không hỗ trợ loại reranker: {reranker_type}")
