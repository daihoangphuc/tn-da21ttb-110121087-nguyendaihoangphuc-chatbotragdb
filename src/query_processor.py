from typing import Dict, List, Optional
import re
import os
import json
from sentence_transformers import SentenceTransformer, util
from dotenv import load_dotenv
import numpy as np

# Load biến môi trường từ .env
load_dotenv()


class QueryProcessor:
    """Module xử lý và cải thiện câu truy vấn trước khi thực hiện tìm kiếm"""

    def __init__(self, synonyms_file: str = None, use_model: bool = True):
        """Khởi tạo processor với synonyms và model để tạo các câu truy vấn thay thế"""
        # Từ điển đồng nghĩa và viết tắt
        self.synonyms = {}

        # Mặc định tìm file synonyms từ biến môi trường
        if synonyms_file is None:
            synonyms_file = os.getenv(
                "SYNONYMS_FILE",
                os.path.join(
                    os.getenv("UPLOAD_DIR", "src/data"), "synonyms", "synonyms.json"
                ),
            )

        # Tải từ điển đồng nghĩa nếu có
        if os.path.exists(synonyms_file):
            try:
                with open(synonyms_file, "r", encoding="utf-8") as f:
                    self.synonyms = json.load(f)
                print(
                    f"Đã tải {len(self.synonyms)} bộ từ đồng nghĩa từ {synonyms_file}"
                )
            except Exception as e:
                print(f"Lỗi khi tải file synonyms: {str(e)}")
                # Tạo synonyms mặc định nếu không tải được
                self._create_default_synonyms()
        else:
            # Tạo synonyms mặc định
            self._create_default_synonyms()

        # Tải model cho query expansion nếu được yêu cầu
        self.use_model = use_model
        self.model = None
        if use_model:
            try:
                print("Đang tải mô hình cho query expansion...")
                # Sử dụng mô hình đa ngôn ngữ để hỗ trợ cả tiếng Việt
                expansion_model = os.getenv(
                    "QUERY_EXPANSION_MODEL", "paraphrase-multilingual-mpnet-base-v2"
                )
                self.model = SentenceTransformer(expansion_model)
                print(f"Đã tải xong mô hình query expansion: {expansion_model}")
            except Exception as e:
                print(f"Không thể tải mô hình: {str(e)}")
                self.use_model = False

        # Cấu hình cho query compression
        self.use_query_compression = os.getenv(
            "USE_QUERY_COMPRESSION", "True"
        ).lower() in ["true", "1", "yes"]
        self.max_query_length = int(os.getenv("MAX_QUERY_LENGTH", "250"))
        self.compression_ratio = float(os.getenv("QUERY_COMPRESSION_RATIO", "0.5"))

    def _create_default_synonyms(self):
        """Tạo từ điển đồng nghĩa mặc định về CSDL và công nghệ liên quan"""
        self.synonyms = {
            # Viết tắt và từ đầy đủ
            "csdl": ["cơ sở dữ liệu", "database", "db"],
            "database": ["cơ sở dữ liệu", "csdl", "db"],
            "sql": ["structured query language", "ngôn ngữ truy vấn có cấu trúc"],
            "nosql": ["not only sql", "phi quan hệ", "cơ sở dữ liệu phi quan hệ"],
            "dbms": [
                "database management system",
                "hệ quản trị cơ sở dữ liệu",
                "hqtcsdl",
            ],
            "hqtcsdl": [
                "hệ quản trị cơ sở dữ liệu",
                "dbms",
                "database management system",
            ],
            # Thuật ngữ CSDL
            "khóa chính": ["primary key", "khóa gốc"],
            "khóa ngoại": ["foreign key", "khóa phụ"],
            "bảng": ["table", "relation"],
            "cột": ["column", "attribute", "thuộc tính"],
            "hàng": ["row", "record", "tuple", "bản ghi"],
            "chỉ mục": ["index", "indices"],
            "view": ["khung nhìn", "bảng ảo"],
            "transaction": ["giao dịch"],
            "join": ["kết nối", "ghép bảng"],
            "query": ["truy vấn", "câu hỏi", "câu truy vấn"],
            # Loại CSDL
            "quan hệ": ["relational", "rdbms"],
            "phi quan hệ": ["non-relational", "nosql"],
            "mongodb": ["csdl tài liệu", "nosql"],
            "redis": ["csdl key-value", "nosql"],
            "neo4j": ["csdl đồ thị", "graph database"],
            # Mô hình và thiết kế
            "er": ["entity-relationship", "thực thể kết hợp", "mô hình er"],
            "normalization": ["chuẩn hóa"],
            "denormalization": ["phi chuẩn hóa"],
            # Thuật ngữ về tối ưu và hiệu suất
            "tối ưu": ["optimization", "tối ưu hóa"],
            "hiệu suất": ["performance", "performance tuning"],
            "deadlock": ["bế tắc", "khóa chết"],
        }

        print(f"Đã tạo từ điển đồng nghĩa mặc định với {len(self.synonyms)} bộ từ")

    def save_synonyms(self, file_path: str):
        """Lưu từ điển đồng nghĩa ra file"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.synonyms, f, ensure_ascii=False, indent=4)
            print(f"Đã lưu từ điển đồng nghĩa vào {file_path}")
            return True
        except Exception as e:
            print(f"Lỗi khi lưu từ điển đồng nghĩa: {str(e)}")
            return False

    def add_synonym(self, term: str, synonyms: List[str]):
        """Thêm từ đồng nghĩa mới vào từ điển"""
        term = term.lower().strip()
        if term in self.synonyms:
            # Thêm vào danh sách đã có
            for syn in synonyms:
                if syn.lower().strip() not in self.synonyms[term]:
                    self.synonyms[term].append(syn.lower().strip())
        else:
            # Tạo danh sách mới
            self.synonyms[term] = [syn.lower().strip() for syn in synonyms]

    def compress_query(self, query: str) -> str:
        """
        Nén query dài thành phiên bản ngắn gọn hơn nhưng vẫn giữ nguyên ngữ nghĩa chính.
        Sử dụng kỹ thuật trích xuất từ khóa và tóm tắt để giảm độ dài của query.

        Args:
            query: Query gốc cần nén

        Returns:
            Phiên bản ngắn gọn của query giữ được ý nghĩa chính
        """
        # Nếu query đã đủ ngắn hoặc không bật tính năng nén, trả về nguyên bản
        if (
            len(query) <= self.max_query_length
            or not self.use_query_compression
            or not self.use_model
        ):
            return query

        try:
            print(f"Thực hiện nén query dài ({len(query)} ký tự)")

            # Chia query thành các câu
            sentences = re.split(r"[.!?]+", query)
            sentences = [s.strip() for s in sentences if s.strip()]

            if len(sentences) <= 1:
                return query  # Không đủ câu để nén

            # Nhúng từng câu
            sentence_embeddings = self.model.encode(sentences)

            # Tính độ quan trọng của từng câu dựa trên tương quan với toàn bộ query
            query_embedding = self.model.encode([query])[0]

            # Tính điểm tương đồng
            similarities = []
            for emb in sentence_embeddings:
                similarity = util.cos_sim(query_embedding, emb)
                similarities.append(float(similarity[0][0]))

            # Sắp xếp câu theo độ tương đồng và lấy các câu quan trọng nhất
            sentence_importance = [
                (sentences[i], similarities[i]) for i in range(len(sentences))
            ]
            sentence_importance.sort(key=lambda x: x[1], reverse=True)

            # Xác định số câu cần giữ lại
            num_sentences_to_keep = max(1, int(len(sentences) * self.compression_ratio))

            # Lấy các câu quan trọng nhất
            top_sentences = [
                item[0] for item in sentence_importance[:num_sentences_to_keep]
            ]

            # Khôi phục thứ tự ban đầu của các câu
            compressed_sentences = []
            for s in sentences:
                if s in top_sentences:
                    compressed_sentences.append(s)

            # Ghép lại thành query ngắn gọn
            compressed_query = ". ".join(compressed_sentences)

            print(f"Đã nén query từ {len(query)} xuống {len(compressed_query)} ký tự")
            return compressed_query

        except Exception as e:
            print(f"Lỗi khi nén query: {str(e)}")
            return query  # Trả về query gốc nếu có lỗi

    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Trích xuất từ khóa quan trọng từ một đoạn văn bản

        Args:
            text: Văn bản cần trích xuất từ khóa
            max_keywords: Số lượng từ khóa tối đa cần trích xuất

        Returns:
            Danh sách các từ khóa được trích xuất
        """
        if not self.use_model:
            # Trích xuất đơn giản dựa trên tần suất từ nếu không có model
            words = re.findall(r"\b\w{3,}\b", text.lower())
            word_freq = {}
            for word in words:
                if word not in word_freq:
                    word_freq[word] = 0
                word_freq[word] += 1

            # Loại bỏ các từ dừng phổ biến (có thể mở rộng)
            stop_words = {
                "và",
                "hoặc",
                "là",
                "của",
                "trong",
                "trên",
                "dưới",
                "có",
                "được",
                "cho",
                "này",
                "những",
            }
            word_freq = {k: v for k, v in word_freq.items() if k not in stop_words}

            # Sắp xếp theo tần suất
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            return [word for word, freq in sorted_words[:max_keywords]]

        try:
            # Phương pháp 1: Tạo n-grams từ văn bản
            sentences = re.split(r"[.!?]+", text)
            sentences = [s.strip() for s in sentences if s.strip()]

            # Tạo các n-gram (1-gram, 2-gram)
            ngrams = []
            for sentence in sentences:
                words = sentence.lower().split()
                # 1-gram
                for word in words:
                    if len(word) > 3:  # Chỉ lấy từ có ít nhất 3 ký tự
                        ngrams.append(word)

                # 2-gram
                for i in range(len(words) - 1):
                    if len(words[i]) > 2 and len(words[i + 1]) > 2:  # Từ có ý nghĩa
                        ngrams.append(f"{words[i]} {words[i+1]}")

            # Mã hóa n-grams và text
            ngram_embeddings = self.model.encode(ngrams)
            text_embedding = self.model.encode([text])[0]

            # Tính điểm tương quan
            scores = []
            for idx, embedding in enumerate(ngram_embeddings):
                score = util.cos_sim(text_embedding, embedding)
                scores.append((ngrams[idx], float(score[0][0])))

            # Loại bỏ từ dừng và sắp xếp
            stop_words = {
                "và",
                "hoặc",
                "là",
                "của",
                "trong",
                "trên",
                "dưới",
                "có",
                "được",
                "cho",
                "này",
                "những",
            }
            filtered_scores = [
                (term, score) for term, score in scores if term not in stop_words
            ]
            filtered_scores.sort(key=lambda x: x[1], reverse=True)

            # Loại bỏ trùng lặp (nếu 2-gram chứa 1-gram đã được chọn)
            unique_keywords = []
            selected_terms = set()

            for term, score in filtered_scores:
                is_subset = False
                for selected in selected_terms:
                    if term in selected or selected in term:
                        is_subset = True
                        break

                if not is_subset:
                    unique_keywords.append(term)
                    selected_terms.add(term)

                if len(unique_keywords) >= max_keywords:
                    break

            return unique_keywords

        except Exception as e:
            print(f"Lỗi khi trích xuất từ khóa: {str(e)}")
            return []

    def expand_query(self, query: str) -> List[str]:
        """Mở rộng câu truy vấn với các từ đồng nghĩa và biến thể khác"""
        # Chuẩn hóa query
        original_query = query.strip()
        query = query.lower().strip()

        # Danh sách các câu truy vấn mở rộng
        expanded_queries = [original_query]  # Luôn giữ truy vấn gốc

        # Giới hạn số lượng biến thể tạo ra là 3 (bao gồm cả truy vấn gốc)
        max_variations = 3

        # 1. Xử lý từ đồng nghĩa và viết tắt
        for term, syns in self.synonyms.items():
            # Kiểm tra xem term có nằm trong query không
            if re.search(r"\b" + re.escape(term) + r"\b", query):
                for syn in syns:
                    # Tạo biến thể bằng cách thay thế term bằng synonym
                    new_query = re.sub(r"\b" + re.escape(term) + r"\b", syn, query)
                    if new_query != query and new_query not in expanded_queries:
                        expanded_queries.append(new_query)
                        # Kiểm tra xem đã đủ số lượng biến thể chưa
                        if len(expanded_queries) >= max_variations:
                            break
                # Nếu đã đủ số lượng biến thể, dừng luôn vòng lặp ngoài
                if len(expanded_queries) >= max_variations:
                    break

        # 2. Sử dụng model để tạo các biến thể dựa trên ngữ nghĩa
        # Chỉ thực hiện nếu chưa đủ số lượng biến thể
        if len(expanded_queries) < max_variations and self.use_model and self.model:
            try:
                # Lấy embedding của truy vấn gốc
                query_embedding = self.model.encode(query)

                # Tạo các biến thể dựa trên mẫu
                variations = [
                    f"Định nghĩa {query}",
                    f"{query} là gì",
                    f"Khái niệm {query}",
                    f"Ý nghĩa của {query}",
                    f"Giải thích {query}",
                ]

                # Tính toán độ tương đồng và chỉ giữ lại các biến thể có nghĩa gần với truy vấn gốc
                variation_embeddings = self.model.encode(variations)
                similarities = util.cos_sim(query_embedding, variation_embeddings)[0]

                # Sắp xếp các biến thể theo độ tương đồng
                sorted_variations = [
                    (variations[i], similarities[i]) for i in range(len(variations))
                ]
                sorted_variations.sort(key=lambda x: x[1], reverse=True)

                # Chỉ lấy đủ số biến thể còn thiếu
                for variation, similarity in sorted_variations:
                    if (
                        similarity > 0.7 and variation not in expanded_queries
                    ):  # Ngưỡng tương đồng
                        expanded_queries.append(variation)
                        # Kiểm tra xem đã đủ số lượng biến thể chưa
                        if len(expanded_queries) >= max_variations:
                            break

            except Exception as e:
                print(f"Lỗi khi tạo biến thể bằng model: {str(e)}")

        # Cắt bớt nếu vượt quá số lượng quy định
        if len(expanded_queries) > max_variations:
            expanded_queries = expanded_queries[:max_variations]

        return expanded_queries

    def hybrid_search_with_expansion(self, search_func, query: str, **kwargs) -> Dict:
        """
        Thực hiện tìm kiếm mở rộng sử dụng nhiều biến thể của truy vấn

        Tham số:
            search_func: Hàm tìm kiếm cần gọi
            query: Câu truy vấn gốc
            **kwargs: Các tham số bổ sung cho hàm tìm kiếm

        Trả về:
            Kết quả tìm kiếm hợp nhất từ các truy vấn mở rộng
        """
        # Nén query nếu quá dài
        compressed_query = self.compress_query(query)

        # Sử dụng query đã nén nếu khác query gốc
        if compressed_query != query:
            print(f"Sử dụng query đã nén: '{compressed_query}'")
            query_to_use = compressed_query
        else:
            query_to_use = query

        # Mở rộng truy vấn
        expanded_queries = self.expand_query(query_to_use)

        # Lưu lại dạng query gốc
        original_query = query

        # Tìm kiếm với từng query mở rộng
        all_results = {}
        results_by_query = {}

        for exp_query in expanded_queries:
            try:
                # Gọi hàm tìm kiếm với query mở rộng
                results = search_func(exp_query, **kwargs)

                # Lưu kết quả tìm kiếm theo query
                results_by_query[exp_query] = results

                # Lưu tất cả kết quả vào dict để xử lý
                for res in results:
                    doc_id = res.get("id", res.get("text", ""))
                    if doc_id in all_results:
                        # Nếu đã có kết quả này, cập nhật điểm số nếu cao hơn
                        if res.get("score", 0) > all_results[doc_id].get("score", 0):
                            all_results[doc_id] = res
                    else:
                        all_results[doc_id] = res
            except Exception as e:
                print(f"Lỗi khi tìm kiếm với query '{exp_query}': {str(e)}")

        # Chuyển đổi kết quả từ dict sang list
        combined_results = list(all_results.values())

        # Sắp xếp kết quả theo điểm số từ cao đến thấp
        combined_results.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Thêm từ khóa được trích xuất từ query
        keywords = self.extract_keywords(original_query)

        return {
            "results": combined_results,
            "original_query": original_query,
            "compressed_query": compressed_query if compressed_query != query else None,
            "expanded_queries": expanded_queries,
            "queries_used": list(results_by_query.keys()),
            "extracted_keywords": keywords,
        }
