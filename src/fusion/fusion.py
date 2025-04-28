from typing import List, Dict, Any, Set, Tuple, Optional
import numpy as np
from collections import defaultdict
from langchain.schema import Document

from src.config import (
    QUERY_EXPANSION_ENABLED,
    RERANKER_ENABLED,
    RETRIEVAL_TOP_K,
    FAST_MODE,
    MAX_FUSION_QUERIES,
    RERANK_RETRIEVAL_RESULTS,
)
from src.utils import measure_time
from src.query_expansion import LLMQueryExpander


def reciprocal_rank_fusion(
    ranked_docs_list: List[List[Document]], k: float = 60.0
) -> List[Document]:
    """Thực hiện Reciprocal Rank Fusion trên các danh sách xếp hạng khác nhau

    Args:
        ranked_docs_list: Danh sách các danh sách tài liệu đã được xếp hạng
        k: Hằng số RRF (mặc định là 60.0)

    Returns:
        Danh sách tài liệu đã được fusion
    """
    # Dict để lưu điểm số của mỗi tài liệu
    doc_scores = defaultdict(float)
    # Dict để lưu nội dung của mỗi tài liệu
    doc_contents = {}

    # Tính điểm RRF cho từng tài liệu
    for ranked_docs in ranked_docs_list:
        for rank, doc in enumerate(ranked_docs):
            # Tạo ID duy nhất cho tài liệu dựa trên nội dung
            doc_id = hash(doc.page_content)
            # Formula: 1 / (rank + k)
            doc_scores[doc_id] += 1.0 / (rank + k)
            # Lưu tài liệu
            doc_contents[doc_id] = doc

    # Sắp xếp tài liệu theo điểm số giảm dần
    sorted_doc_ids = sorted(
        doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True
    )

    # Tạo danh sách tài liệu kết quả, thêm thông tin điểm fusion
    result_docs = []
    for doc_id in sorted_doc_ids:
        doc = doc_contents[doc_id]
        # Thêm điểm RRF vào metadata
        doc.metadata["fusion_score"] = doc_scores[doc_id]
        result_docs.append(doc)

    return result_docs


class RAGFusion:
    """Lớp thực hiện RAG Fusion với query expansion"""

    def __init__(self, retriever, use_query_expansion: bool = QUERY_EXPANSION_ENABLED):
        """Khởi tạo RAG Fusion với retriever đã cho

        Args:
            retriever: Đối tượng retriever để truy xuất tài liệu
            use_query_expansion: Bật/tắt query expansion
        """
        self.retriever = retriever
        self.use_query_expansion = use_query_expansion
        self.fast_mode = FAST_MODE

        # Khởi tạo query expander nếu bật
        if self.use_query_expansion:
            try:
                self.query_expander = LLMQueryExpander()
                print("✅ Đã khởi tạo Query Expander cho RAG Fusion")
            except Exception as e:
                print(f"⚠️ Lỗi khi khởi tạo Query Expander: {str(e)}")
                print("⚠️ RAG Fusion sẽ hoạt động mà không có query expansion")
                self.use_query_expansion = False

    @measure_time
    def retrieve(self, query: str, top_k: int = RETRIEVAL_TOP_K) -> List[Document]:
        """Thực hiện quá trình RAG Fusion

        Args:
            query: Câu truy vấn gốc
            top_k: Số lượng tài liệu cần trả về

        Returns:
            Danh sách tài liệu đã được fusion
        """
        print(f"⏳ Đang thực hiện RAG Fusion cho truy vấn: '{query}'")

        # Các danh sách tài liệu đã được xếp hạng
        ranked_docs_list = []

        # 1. Thực hiện retrieval với câu truy vấn gốc
        # Trong chế độ nhanh, sử dụng reranking nếu RERANK_RETRIEVAL_RESULTS=True
        # Trong chế độ thường, luôn lấy kết quả không rerank để fusion sau
        use_rerank_for_orig = RERANK_RETRIEVAL_RESULTS and self.fast_mode

        if (
            use_rerank_for_orig
            and hasattr(self.retriever, "reranker")
            and self.retriever.reranker
            and RERANKER_ENABLED
        ):
            # Nếu rerank được bật trong chế độ nhanh, rerank luôn kết quả
            original_docs = self.retriever.reranker.rerank(
                query, self.retriever.retrieve(query)
            )
        else:
            # Trong trường hợp khác, lấy kết quả không rerank
            original_docs = self.retriever.retrieve(query)

        ranked_docs_list.append(original_docs)

        # 2. Thực hiện query expansion nếu được bật
        if self.use_query_expansion and not self.fast_mode:
            print("⏳ Đang thực hiện query expansion...")
            expanded_queries = self.query_expander.expand_query(query)

            # Loại bỏ query gốc từ danh sách expanded_queries (vì đã được xử lý ở trên)
            expanded_queries = [q for q in expanded_queries if q != query]

            # Giới hạn số lượng truy vấn mở rộng theo cấu hình MAX_FUSION_QUERIES
            max_additional_queries = max(0, MAX_FUSION_QUERIES - 1)  # Đã tính query gốc
            if len(expanded_queries) > max_additional_queries:
                expanded_queries = expanded_queries[:max_additional_queries]
                print(f"ℹ️ Giới hạn số truy vấn mở rộng xuống {max_additional_queries}")

            print(f"ℹ️ Các truy vấn mở rộng: {expanded_queries}")

            # Thực hiện retrieval cho mỗi truy vấn mở rộng
            for i, expanded_query in enumerate(expanded_queries):
                print(f"⏳ Đang truy vấn với expanded query {i+1}: '{expanded_query}'")
                # Trong chế độ nhanh, dùng ngay kết quả không rerank
                expanded_docs = self.retriever.retrieve(expanded_query)
                ranked_docs_list.append(expanded_docs)

        # 3. Thực hiện Reciprocal Rank Fusion
        if len(ranked_docs_list) > 1:
            print(
                f"⏳ Đang thực hiện fusion trên {len(ranked_docs_list)} danh sách tài liệu"
            )
            fused_docs = reciprocal_rank_fusion(ranked_docs_list)

            # Lấy top_k tài liệu sau fusion
            result_docs = fused_docs[:top_k]
            print(f"✅ Đã fusion thành công! Kết quả: {len(result_docs)} tài liệu")
            return result_docs
        else:
            # Nếu chỉ có một danh sách, trả về luôn
            print("ℹ️ Chỉ có một danh sách tài liệu, không cần fusion")
            return original_docs[:top_k]

    @measure_time
    def retrieve_and_rerank(
        self, query: str, top_k: int = RETRIEVAL_TOP_K
    ) -> List[Document]:
        """Thực hiện quá trình RAG Fusion với reranking ở bước cuối cùng

        Args:
            query: Câu truy vấn gốc
            top_k: Số lượng tài liệu cần trả về

        Returns:
            Danh sách tài liệu đã được fusion và rerank
        """
        # Kiểm tra chế độ nhanh
        if self.fast_mode:
            print("ℹ️ Sử dụng chế độ nhanh cho RAG Fusion")
            # Trong chế độ nhanh, nếu RERANK_RETRIEVAL_RESULTS=true, kết quả đã được rerank
            # trong hàm retrieve, nên không cần rerank lại nữa
            return self.retrieve(query, top_k=top_k)

        # Lấy các tài liệu từ fusion process mà không gọi rerank
        # Chú ý: Sử dụng fusion_retrieve để tránh gọi rerank lại
        fusion_k = top_k * 2
        fused_docs = self.fusion_retrieve(query, top_k=fusion_k)

        # Kiểm tra xem retriever có reranker không
        if (
            hasattr(self.retriever, "reranker")
            and self.retriever.reranker
            and RERANKER_ENABLED
        ):
            print(f"⏳ Đang rerank {len(fused_docs)} tài liệu sau fusion...")
            reranked_docs = self.retriever.reranker.rerank(
                query, fused_docs, top_k=top_k
            )
            print(f"✅ Đã rerank thành công! Kết quả: {len(reranked_docs)} tài liệu")
            return reranked_docs
        else:
            # Nếu không có reranker, chỉ trả về top_k tài liệu sau fusion
            return fused_docs[:top_k]

    @measure_time
    def fusion_retrieve(
        self, query: str, top_k: int = RETRIEVAL_TOP_K
    ) -> List[Document]:
        """Thực hiện quá trình RAG Fusion mà không rerank kết quả cuối cùng

        Phương thức này giống với retrieve nhưng không gọi reranker ở bước cuối,
        được sử dụng bởi retrieve_and_rerank để tránh rerank hai lần.

        Args:
            query: Câu truy vấn gốc
            top_k: Số lượng tài liệu cần trả về

        Returns:
            Danh sách tài liệu đã được fusion
        """
        print(f"⏳ Đang thực hiện RAG Fusion cho truy vấn: '{query}'")

        # Các danh sách tài liệu đã được xếp hạng
        ranked_docs_list = []

        # 1. Thực hiện retrieval với câu truy vấn gốc
        # Trong chế độ nhanh, sử dụng reranking nếu RERANK_RETRIEVAL_RESULTS=True
        # Trong chế độ thường, luôn lấy kết quả không rerank để fusion sau
        use_rerank_for_orig = RERANK_RETRIEVAL_RESULTS and self.fast_mode

        if (
            use_rerank_for_orig
            and hasattr(self.retriever, "reranker")
            and self.retriever.reranker
            and RERANKER_ENABLED
        ):
            # Nếu rerank được bật trong chế độ nhanh, rerank luôn kết quả
            original_docs = self.retriever.reranker.rerank(
                query, self.retriever.retrieve(query)
            )
        else:
            # Trong trường hợp khác, lấy kết quả không rerank
            original_docs = self.retriever.retrieve(query)

        ranked_docs_list.append(original_docs)

        # 2. Thực hiện query expansion nếu được bật
        if self.use_query_expansion and not self.fast_mode:
            print("⏳ Đang thực hiện query expansion...")
            expanded_queries = self.query_expander.expand_query(query)

            # Loại bỏ query gốc từ danh sách expanded_queries (vì đã được xử lý ở trên)
            expanded_queries = [q for q in expanded_queries if q != query]

            # Giới hạn số lượng truy vấn mở rộng theo cấu hình MAX_FUSION_QUERIES
            max_additional_queries = max(0, MAX_FUSION_QUERIES - 1)  # Đã tính query gốc
            if len(expanded_queries) > max_additional_queries:
                expanded_queries = expanded_queries[:max_additional_queries]
                print(f"ℹ️ Giới hạn số truy vấn mở rộng xuống {max_additional_queries}")

            print(f"ℹ️ Các truy vấn mở rộng: {expanded_queries}")

            # Thực hiện retrieval cho mỗi truy vấn mở rộng
            for i, expanded_query in enumerate(expanded_queries):
                print(f"⏳ Đang truy vấn với expanded query {i+1}: '{expanded_query}'")
                # Trong chế độ nhanh, dùng ngay kết quả không rerank
                expanded_docs = self.retriever.retrieve(expanded_query)
                ranked_docs_list.append(expanded_docs)

        # 3. Thực hiện Reciprocal Rank Fusion
        if len(ranked_docs_list) > 1:
            print(
                f"⏳ Đang thực hiện fusion trên {len(ranked_docs_list)} danh sách tài liệu"
            )
            fused_docs = reciprocal_rank_fusion(ranked_docs_list)

            # Lấy top_k tài liệu sau fusion
            result_docs = fused_docs[:top_k]
            print(f"✅ Đã fusion thành công! Kết quả: {len(result_docs)} tài liệu")
            return result_docs
        else:
            # Nếu chỉ có một danh sách, trả về luôn
            print("ℹ️ Chỉ có một danh sách tài liệu, không cần fusion")
            return original_docs[:top_k]
