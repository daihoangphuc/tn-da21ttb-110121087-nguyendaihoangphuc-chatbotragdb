import numpy as np
from typing import List
from langchain.schema import Document
from tqdm import tqdm

# from langchain_experimental.text_splitter import SemanticChunker
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sklearn.cluster import AgglomerativeClustering

from src.config import (
    CHUNK_BUFFER_SIZE,
    CHUNK_BREAKPOINT_THRESHOLD_TYPE,
    CHUNK_BREAKPOINT_THRESHOLD_AMOUNT,
    CLUSTER_DISTANCE_THRESHOLD,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    CHUNK_SEPARATORS,
    MIN_CHUNK_SIZE,
    MIN_CHUNK_CHARACTERS,
)
from src.utils import measure_time, print_document_info


class DocumentProcessor:
    """Lớp xử lý chunking và clustering tài liệu"""

    def __init__(self, embeddings):
        """Khởi tạo với embedding model đã cho"""
        self.embeddings = embeddings
        # Phương pháp chunking cũ sử dụng SemanticChunker
        # self.chunker = SemanticChunker(
        #     embeddings=self.embeddings,
        #     buffer_size=CHUNK_BUFFER_SIZE,
        #     breakpoint_threshold_type=CHUNK_BREAKPOINT_THRESHOLD_TYPE,
        #     breakpoint_threshold_amount=CHUNK_BREAKPOINT_THRESHOLD_AMOUNT,
        #     add_start_index=True,
        # )
        # Phương pháp chunking mới sử dụng RecursiveCharacterTextSplitter
        self.chunker = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            # separators cho các nguồn chuyên về lĩnh vực cơ sở dữ liệu
            separators=CHUNK_SEPARATORS,
            length_function=len,
        )

    @measure_time
    def chunk_documents(self, docs: List[Document]) -> List[Document]:
        """Chia tài liệu thành các chunk có ngữ cảnh gần nhau"""
        print("⏳ Đang chunk tài liệu...")

        # Kiểm tra số lượng tài liệu và điều chỉnh chunking nếu cần
        doc_count = len(docs)
        print(f"ℹ️ Số lượng tài liệu cần chia: {doc_count}")

        total_text_length = sum(len(doc.page_content) for doc in docs)
        avg_doc_length = total_text_length / doc_count if doc_count > 0 else 0
        print(
            f"ℹ️ Tổng độ dài nội dung: {total_text_length} ký tự (trung bình: {avg_doc_length:.1f} ký tự/tài liệu)"
        )

        # Điều chỉnh cấu hình chunking nếu tài liệu quá dài
        chunk_size = CHUNK_SIZE
        chunk_overlap = CHUNK_OVERLAP

        if avg_doc_length > 10000:  # Điều chỉnh cho tài liệu dài
            chunk_size = min(2000, chunk_size * 1.5)
            chunk_overlap = min(300, chunk_overlap * 1.5)
            print(
                f"ℹ️ Điều chỉnh chunking cho tài liệu dài: chunk_size={chunk_size}, chunk_overlap={chunk_overlap}"
            )
            # Cập nhật lại chunker
            self.chunker = RecursiveCharacterTextSplitter(
                chunk_size=int(chunk_size),
                chunk_overlap=int(chunk_overlap),
                separators=CHUNK_SEPARATORS,
            )

        # Phương pháp chunking mới
        chunks = []
        for doc in tqdm(docs, desc="Chunking documents", unit="doc"):
            # Tách văn bản thành các chunk
            text_chunks = self.chunker.split_text(doc.page_content)

            # Lọc các chunk quá ngắn
            filtered_chunks = []
            for chunk in text_chunks:
                # Lọc dựa trên số từ và số ký tự
                num_words = len(chunk.split())
                num_chars = len(chunk)

                if num_words >= MIN_CHUNK_SIZE and num_chars >= MIN_CHUNK_CHARACTERS:
                    filtered_chunks.append(chunk)

            # Báo cáo thống kê chunking
            if len(text_chunks) > 0:
                filtered_rate = len(filtered_chunks) / len(text_chunks) * 100
                if filtered_rate < 100:
                    print(
                        f"  - Đã lọc chunks cho '{doc.metadata.get('source', 'unknown')}': {len(filtered_chunks)}/{len(text_chunks)} chunks giữ lại ({filtered_rate:.1f}%)"
                    )

            # Chuyển đổi text chunks thành Document objects
            doc_chunks = [
                Document(
                    page_content=chunk,
                    metadata={
                        **doc.metadata,
                        "start_index": doc.page_content.find(chunk),
                        "chunk_length": len(chunk),
                        "chunk_word_count": len(chunk.split()),
                    },
                )
                for chunk in filtered_chunks
            ]
            chunks.extend(doc_chunks)

        # Tính kích thước trung bình của chunks
        avg_chunk_length = (
            sum(len(c.page_content) for c in chunks) / len(chunks) if chunks else 0
        )
        avg_chunk_words = (
            sum(len(c.page_content.split()) for c in chunks) / len(chunks)
            if chunks
            else 0
        )

        print(
            f"ℹ️ Thống kê chunks: {len(chunks)} chunks (trung bình {avg_chunk_length:.1f} ký tự, {avg_chunk_words:.1f} từ/chunk)"
        )
        print_document_info(chunks, "Kết quả chunking")
        return chunks

    @measure_time
    def cluster_and_merge(self, chunks: List[Document]) -> List[Document]:
        """Nhóm và gộp các chunk liên quan lại với nhau"""
        print("⏳ Đang embed & cluster...")

        # Tối ưu kích thước danh sách chunks nếu quá lớn
        if len(chunks) > 1000:
            print(
                f"⚠️ Số lượng chunks quá lớn ({len(chunks)}), chỉ xử lý 1000 chunks đầu tiên"
            )
            chunks = chunks[:1000]

        # Lấy embedding với tqdm để hiển thị tiến trình
        print("⏳ Đang tính toán embeddings...")
        chunk_texts = [c.page_content for c in chunks]

        # Sử dụng batching để tính embeddings hiệu quả hơn - tăng batch_size lên 64
        batch_size = 64  # Tăng từ 32 lên 64
        all_embeddings = []

        for i in tqdm(
            range(0, len(chunk_texts), batch_size),
            desc="Embedding chunks",
            unit="batch",
        ):
            batch = chunk_texts[i : i + batch_size]
            batch_embeddings = self.embeddings.embed_documents(batch)
            all_embeddings.extend(batch_embeddings)

        vecs = np.array(all_embeddings)

        # Clustering với Agglomerative Clustering - giới hạn số lượng clusters
        print("⏳ Đang thực hiện clustering...")
        # Tối ưu clustering threshold nếu số lượng chunks lớn
        threshold = CLUSTER_DISTANCE_THRESHOLD
        if len(chunks) > 500:
            threshold = CLUSTER_DISTANCE_THRESHOLD * 1.2
            print(f"⚠️ Điều chỉnh threshold lên {threshold} do có nhiều chunks")

        labels = AgglomerativeClustering(
            n_clusters=None, distance_threshold=threshold
        ).fit_predict(vecs)

        # Nhóm các chunk theo cluster
        clustered = {}
        for lbl, c in zip(labels, chunks):
            clustered.setdefault(lbl, []).append(c)

        # Kiểm tra và in thông tin về clusters
        print(f"👉 Đã phân thành {len(clustered)} clusters")

        # Lọc bỏ các clusters quá nhỏ (chỉ 1 chunk) nếu có quá nhiều clusters
        if len(clustered) > 200:
            original_count = len(clustered)
            clustered = {k: v for k, v in clustered.items() if len(v) > 1}
            print(
                f"👉 Đã lọc các clusters nhỏ: từ {original_count} xuống {len(clustered)} clusters"
            )

        # Sắp xếp và gộp các chunk trong cùng một cluster
        merged_docs = []
        for group_id in tqdm(clustered.keys(), desc="Merging clusters", unit="cluster"):
            group = clustered[group_id]
            group.sort(key=lambda d: d.metadata.get("start_index", 0))
            merged_content = "\n".join(d.page_content for d in group)

            # Lấy metadata từ phần tử đầu tiên
            merged_metadata = {**group[0].metadata}
            merged_metadata["chunk_count"] = len(group)

            merged_docs.append(
                Document(page_content=merged_content, metadata=merged_metadata)
            )

        print_document_info(merged_docs, "Kết quả sau khi cluster và merge")
        return merged_docs
