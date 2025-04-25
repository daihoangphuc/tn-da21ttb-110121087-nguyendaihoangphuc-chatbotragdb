import numpy as np
from typing import List
from langchain.schema import Document

# from langchain_experimental.text_splitter import SemanticChunker
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sklearn.cluster import AgglomerativeClustering

from src.config import (
    CHUNK_BUFFER_SIZE,
    CHUNK_BREAKPOINT_THRESHOLD_TYPE,
    CHUNK_BREAKPOINT_THRESHOLD_AMOUNT,
    CLUSTER_DISTANCE_THRESHOLD,
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
            chunk_size=1000,
            chunk_overlap=200,
            # separators cho các nguồn chuyên về lĩnh vực cơ sở dữ liệu
            separators=["\n\n", "\n", "; ", " "],
        )

    @measure_time
    def chunk_documents(self, docs: List[Document]) -> List[Document]:
        """Chia tài liệu thành các chunk có ngữ cảnh gần nhau"""
        print("⏳ Đang chunk tài liệu...")
        # Phương pháp chunking cũ
        # chunks = self.chunker.split_documents(docs)

        # Phương pháp chunking mới
        chunks = []
        for doc in docs:
            # Tách văn bản thành các chunk
            text_chunks = self.chunker.split_text(doc.page_content)
            # Lọc các chunk có ít hơn 20 từ
            text_chunks = [c for c in text_chunks if len(c.split()) > 15]
            # Chuyển đổi text chunks thành Document objects
            doc_chunks = [
                Document(
                    page_content=chunk,
                    metadata={
                        **doc.metadata,
                        "start_index": doc.page_content.find(chunk),
                    },
                )
                for chunk in text_chunks
            ]
            chunks.extend(doc_chunks)

        print_document_info(chunks, "Kết quả chunking")
        return chunks

    @measure_time
    def cluster_and_merge(self, chunks: List[Document]) -> List[Document]:
        """Nhóm và gộp các chunk liên quan lại với nhau"""
        print("⏳ Đang embed & cluster...")

        # Lấy embedding
        vecs = np.array(
            self.embeddings.embed_documents([c.page_content for c in chunks])
        )

        # Clustering với Agglomerative Clustering
        labels = AgglomerativeClustering(
            n_clusters=None, distance_threshold=CLUSTER_DISTANCE_THRESHOLD
        ).fit_predict(vecs)

        # Nhóm các chunk theo cluster
        clustered = {}
        for lbl, c in zip(labels, chunks):
            clustered.setdefault(lbl, []).append(c)

        # Sắp xếp và gộp các chunk trong cùng một cluster
        merged_docs = []
        for group in clustered.values():
            group.sort(key=lambda d: d.metadata.get("start_index", 0))
            merged_docs.append(
                Document(page_content="\n".join(d.page_content for d in group))
            )

        print_document_info(merged_docs, "Kết quả sau khi cluster và merge")
        return merged_docs
