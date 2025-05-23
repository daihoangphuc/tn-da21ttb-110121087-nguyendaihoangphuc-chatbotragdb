"""
Script để cập nhật file rag.py với hỗ trợ Google Agent Search
"""
import re

def update_rag_file():
    """Cập nhật file rag.py với hỗ trợ Google Agent Search"""
    # Đọc nội dung file rag.py
    with open('src/rag.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Thêm import Google Agent Search nếu chưa có
    import_pattern = r"from src\.tools\.Google_Agents_Search import run_query_with_sources as google_agent_search"
    if import_pattern not in content:
        import_position = content.find("# Load biến môi trường từ .env")
        if import_position != -1:
            content = content[:import_position] + "# Import Google Agent Search\nfrom src.tools.Google_Agents_Search import run_query_with_sources as google_agent_search\n\n" + content[import_position:]
            print("Đã thêm import Google Agent Search")
    # Kiểm tra import trùng lặp
    elif content.count(import_pattern) > 1:
        # Xóa import trùng lặp
        first_import_idx = content.find(import_pattern)
        second_import_start = content.find("# Import Google Agent Search", first_import_idx + 1)
        if second_import_start != -1:
            second_import_end = content.find("\n\n", second_import_start) + 2
            if second_import_end != -1:
                content = content[:second_import_start] + content[second_import_end:]
                print("Đã xóa import trùng lặp")
    
    # 2. Cập nhật hàm query_with_sources_streaming để xử lý realtime_question
    realtime_pattern = r'# Trả về ngay nếu là câu hỏi thời gian thực\s+if query_type == "realtime_question":'
    realtime_match = re.search(realtime_pattern, content)
    
    if realtime_match:
        # Tìm vị trí để thay thế
        start_idx = realtime_match.start()
        # Tìm vị trí kết thúc của khối mã xử lý realtime_question (tìm tới return)
        end_pattern = r'return\s+'
        end_match = re.search(end_pattern, content[start_idx:])
        
        if end_match:
            end_idx = start_idx + end_match.end()
            
            # Mã thay thế
            replacement_code = '''# Trả về ngay nếu là câu hỏi thời gian thực
        if query_type == "realtime_question":
            # Trả về thông báo bắt đầu
            yield {
                "type": "start",
                "data": {
                    "query_type": query_type,
                    "search_type": "google_agent_search",
                    "alpha": alpha if alpha is not None else self.default_alpha,
                    "file_id": file_id,
                },
            }

            # Sử dụng Google Agent Search để tìm kiếm
            gas_summary, gas_urls = google_agent_search(query_to_use)
            
            # Chuẩn bị danh sách nguồn từ Google Agent Search
            gas_sources_list = []
            if gas_urls:
                for url_idx, url in enumerate(gas_urls):
                    gas_sources_list.append({
                        "source": "Google Agent Search",
                        "page": "Web Search",
                        "section": f"Web Source {url_idx+1}",
                        "score": 1.0,
                        "content_snippet": f"Thông tin từ web: {url}",
                        "file_id": "web_search",
                        "is_web_search": True
                    })
            
            # Trả về nguồn
            yield {
                "type": "sources",
                "data": {
                    "sources": gas_sources_list,
                    "filtered_sources": [],
                    "filtered_file_id": file_id if file_id else [],
                },
            }

            # Trả về nội dung
            gas_content = gas_summary.content if hasattr(gas_summary, 'content') else str(gas_summary)
            if gas_content and gas_content != "Không tìm thấy thông tin liên quan đến truy vấn này.":
                yield {"type": "content", "data": {"content": gas_content}}
            else:
                yield {"type": "content", "data": {"content": "Không tìm thấy thông tin từ Google Agent Search."}}

            # Trả về kết thúc
            elapsed_time = time.time() - start_time
            yield {
                "type": "end",
                "data": {
                    "processing_time": round(elapsed_time, 2),
                    "query_type": query_type,
                },
            }
            return'''
            
            # Thay thế mã
            content = content[:start_idx] + replacement_code + content[end_idx:]
            print("Đã cập nhật xử lý realtime_question trong query_with_sources_streaming")
    
    # 3. Thêm fallback mechanism cho streaming
    no_results_pattern = r'# Nếu không có kết quả tìm kiếm, trả về thông báo không tìm thấy\s+if not search_results or len\(search_results\) == 0:'
    no_results_match = re.search(no_results_pattern, content)
    
    if no_results_match:
        # Tìm vị trí để chèn fallback mechanism
        insert_idx = no_results_match.start()
        
        # Mã để chèn
        fallback_code = '''        # Fallback mechanism cho streaming
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

'''
        # Chèn mã
        content = content[:insert_idx] + fallback_code + content[insert_idx:]
        print("Đã thêm fallback mechanism cho streaming")
    
    # 4. Cập nhật sources_list để hỗ trợ nguồn từ Google Agent Search
    sources_list_pattern = r'# Chuẩn bị danh sách nguồn tham khảo\s+sources_list = \[\]\s+for i, doc in enumerate\(reranked_results\):'
    sources_list_match = re.search(sources_list_pattern, content)
    
    if sources_list_match:
        # Tìm vị trí để chèn sau dòng "# Trích xuất thông tin từ metadata"
        metadata_pattern = r'# Trích xuất thông tin từ metadata\s+metadata = doc\.get\("metadata", {}\)'
        metadata_match = re.search(metadata_pattern, content[sources_list_match.end():])
        
        if metadata_match:
            insert_idx = sources_list_match.end() + metadata_match.end()
            
            # Mã để chèn
            source_type_code = '''
            
            # Kiểm tra nếu là nguồn từ Google Agent Search
            if metadata.get("source_type") == "web_search":
                urls_from_gas = metadata.get("urls", [])
                snippet = doc["text"]
                if urls_from_gas:
                    snippet += "\\n\\nNguồn tham khảo từ web:\\n" + "\\n".join([f"- {url}" for url in urls_from_gas])
                
                sources_list.append({
                    "source": "Google Agent Search",
                    "page": "Web Search Result",
                    "section": "Web Content",
                    "score": doc.get("score", 0.9),
                    "content_snippet": snippet,
                    "file_id": doc.get("file_id", "web_search"),
                    "is_web_search": True
                })
            else:
                # Nguồn từ RAG thông thường'''
            
            # Tìm vị trí để thay thế phần còn lại của đoạn code
            remaining_code_pattern = r'source = metadata\.get\("source", "unknown"\)'
            remaining_code_match = re.search(remaining_code_pattern, content[insert_idx:])
            
            if remaining_code_match:
                remaining_code_idx = insert_idx + remaining_code_match.start()
                
                # Mã thay thế
                replacement_code = '''                source = metadata.get("source", "unknown")
                page = metadata.get("page", "N/A")
                section = metadata.get("section", "N/A")
                result_file_id = doc.get("file_id", "unknown")  # Lấy file_id từ kết quả

                # Tạo snippet từ nội dung
                content = doc["text"]
                snippet = content

                # Thêm vào danh sách nguồn
                sources_list.append(
                    {
                        "source": source,
                        "page": page,
                        "section": section,
                        "score": doc.get("score", 0.0),
                        "content_snippet": snippet,
                        "file_id": result_file_id,
                        "is_web_search": False
                    }
                )'''
                
                # Tìm phần kết thúc của đoạn code nguồn
                end_pattern = r'sources_list\.append\('
                end_match = re.search(end_pattern, content[remaining_code_idx:])
                
                if end_match:
                    end_idx = remaining_code_idx + end_match.start() + len('sources_list.append(')
                    # Tìm dấu ngoặc đóng tương ứng
                    closing_idx = end_idx
                    bracket_count = 1
                    while bracket_count > 0 and closing_idx < len(content):
                        if content[closing_idx] == '(':
                            bracket_count += 1
                        elif content[closing_idx] == ')':
                            bracket_count -= 1
                        closing_idx += 1
                    
                    if closing_idx < len(content):
                        # Thay thế mã
                        content = content[:insert_idx] + source_type_code + '\n' + replacement_code + content[closing_idx:]
                        print("Đã cập nhật sources_list để hỗ trợ nguồn từ Google Agent Search")
    
    # 5. Cập nhật thông tin "start" event
    start_event_pattern = r'# Trả về thông báo bắt đầu\s+yield \{\s+"type": "start",'
    start_event_match = re.search(start_event_pattern, content)
    
    if start_event_match:
        # Tìm dòng "gas_fallback_used" trong data
        gas_fallback_pattern = r'"gas_fallback_used": gas_fallback_used'
        if gas_fallback_pattern not in content[start_event_match.start():start_event_match.start() + 500]:
            # Tìm vị trí để thêm thông tin gas_fallback_used
            data_pattern = r'"data": \{\s+"query_type": query_type,'
            data_match = re.search(data_pattern, content[start_event_match.start():])
            
            if data_match:
                end_data_idx = start_event_match.start() + data_match.end()
                
                # Tìm dấu đóng của object data
                data_closing_pattern = r'},\s+'
                data_closing_match = re.search(data_closing_pattern, content[end_data_idx:])
                
                if data_closing_match:
                    insert_idx = end_data_idx + data_closing_match.start()
                    
                    # Thêm thông tin gas_fallback_used
                    updated_content = content[:insert_idx] + '"search_type": search_type + ("+gas_fallback" if gas_fallback_used else ""),\n                "gas_fallback_used": gas_fallback_used,' + content[insert_idx:]
                    
                    # Cập nhật content nếu không có lỗi
                    content = updated_content
                    print("Đã cập nhật thông tin gas_fallback_used trong start event")
    
    # 6. Sửa lỗi indentation
    error_pattern = r'# Nguồn từ RAG thông thườngsource = metadata\.get\("source", "unknown"\)'
    if error_pattern in content:
        # Thay thế bằng đoạn code có indentation đúng
        content = content.replace(
            '# Nguồn từ RAG thông thườngsource = metadata.get("source", "unknown")',
            '# Nguồn từ RAG thông thường\n                source = metadata.get("source", "unknown")'
        )
        print("Đã sửa lỗi indentation")
    
    # Lưu nội dung đã cập nhật
    with open('src/rag.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Đã hoàn thành cập nhật file rag.py")

if __name__ == "__main__":
    update_rag_file() 