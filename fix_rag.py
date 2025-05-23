"""
Script để sửa lỗi trong file rag.py
"""
import re

def fix_rag_file():
    """Sửa lỗi trong file rag.py"""
    # Đọc nội dung file rag.py
    with open('src/rag.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Sửa lỗi cú pháp trong phần other_question
    error_pattern = r'"type": "start",\s+"data": \{\s+"query_type": query_type,\s+"search_type": search_type,\s+"alpha": alpha if alpha is not None else self\.default_alpha,\s+"file_id": file_id,\s+"search_type": search_type \+ \("\+gas_fallback" if gas_fallback_used else ""\),\s+"gas_fallback_used": gas_fallback_used,\},'
    
    replacement = '"type": "start",\n                "data": {\n                    "query_type": query_type,\n                    "search_type": search_type,\n                    "alpha": alpha if alpha is not None else self.default_alpha,\n                    "file_id": file_id\n                },'
    
    content = re.sub(error_pattern, replacement, content)
    print("Đã sửa lỗi cú pháp trong phần other_question")
    
    # 2. Sửa lỗi thiếu phần tìm kiếm
    error_pattern2 = r'return# Rerank kết quả nếu có nhiều hơn 1 kết quả'
    replacement2 = '''return

        # Tìm kiếm dựa trên loại tìm kiếm được chỉ định
        if search_type == "semantic":
            search_results = self.semantic_search(
                query_to_use, k=k, sources=sources, file_id=file_id
            )
        elif search_type == "keyword":
            search_results = self.search_manager.keyword_search(
                query_to_use, k=k, sources=sources, file_id=file_id
            )
        else:  # hybrid
            # Sử dụng hybrid_search đồng bộ, không còn gây lỗi asyncio.run
            search_results = self.hybrid_search(
                query_to_use,
                k=k,
                alpha=alpha if alpha is not None else self.default_alpha,
                sources=sources,
                file_id=file_id,
            )
            
        # Fallback mechanism cho streaming
        perform_fallback_stream = not search_results or len(search_results) == 0
        gas_fallback_used = False
        
        if perform_fallback_stream:
            print(f"Không có kết quả RAG (stream). Thực hiện fallback với Google Agent Search cho: '{query_to_use}'")
            fallback_summary, fallback_urls = google_agent_search(query_to_use)
            fallback_content = fallback_summary.content if hasattr(fallback_summary, 'content') else str(fallback_summary)
            
            if fallback_content and fallback_content != "Không tìm thấy thông tin liên quan đến truy vấn này.":
                gas_fallback_used = True
                print(f"Google Agent Search (stream) tìm thấy: {fallback_content[:100]}...")
                
                # Tạo một doc giả cho fallback để đưa vào context LLM
                fallback_doc = {
                    "text": fallback_content,
                    "metadata": {
                        "source": "Google Agent Search",
                        "page": "Web Result",
                        "source_type": "web_search",
                        "urls": fallback_urls
                    },
                    "score": 0.9,
                    "rerank_score": 0.9,
                    "file_id": "web_search_fallback"
                }
                
                # Thêm vào search_results
                search_results = [fallback_doc]
            else:
                print("Google Agent Search (stream) không tìm thấy kết quả fallback.")

        # Nếu không có kết quả tìm kiếm, trả về thông báo không tìm thấy
        if not search_results or len(search_results) == 0:
            # Trả về thông báo bắt đầu
            yield {
                "type": "start",
                "data": {
                    "query_type": "no_results",
                    "search_type": search_type,
                    "alpha": alpha if alpha is not None else self.default_alpha,
                    "file_id": file_id,
                },
            }

            # Trả về nguồn rỗng
            yield {
                "type": "sources",
                "data": {
                    "sources": [],
                    "filtered_sources": [],
                    "filtered_file_id": file_id if file_id else [],
                },
            }

            # Trả về nội dung
            response = "Không tìm thấy thông tin liên quan đến câu hỏi của bạn trong tài liệu. Vui lòng thử lại với câu hỏi khác hoặc điều chỉnh từ khóa tìm kiếm."
            yield {"type": "content", "data": {"content": response}}

            # Trả về kết thúc
            elapsed_time = time.time() - start_time
            yield {
                "type": "end",
                "data": {
                    "processing_time": round(elapsed_time, 2),
                    "query_type": "no_results",
                },
            }
            return
            
        # Rerank kết quả nếu có nhiều hơn 1 kết quả'''
    
    content = content.replace(error_pattern2, replacement2)
    print("Đã thêm phần tìm kiếm bị thiếu")
    
    # 3. Sửa lỗi trong phần start event
    error_pattern3 = r'# Trả về thông báo bắt đầu\s+yield \{\s+"type": "start",\s+"data": \{\s+"query_type": query_type,\s+"search_type": search_type,\s+"alpha": alpha if alpha is not None else self\.default_alpha,\s+"file_id": file_id,\s+"total_results": len\(search_results\),\s+"total_reranked": total_reranked,\s+\},\s+\},'
    
    replacement3 = '''# Trả về thông báo bắt đầu
        yield {
            "type": "start",
            "data": {
                "query_type": query_type,
                "search_type": search_type + ("+gas_fallback" if gas_fallback_used else ""),
                "alpha": alpha if alpha is not None else self.default_alpha,
                "file_id": file_id,
                "total_results": len(search_results),
                "total_reranked": total_reranked,
                "gas_fallback_used": gas_fallback_used
            },
        },'''
    
    content = re.sub(error_pattern3, replacement3, content)
    print("Đã sửa lỗi trong phần start event")
    
    # Lưu nội dung đã sửa
    with open('src/rag.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Đã hoàn thành sửa lỗi file rag.py")

if __name__ == "__main__":
    fix_rag_file() 