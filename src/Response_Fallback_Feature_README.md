# Response-based Fallback Feature

## Tổng quan

Tính năng **Response-based Fallback** là một cải tiến của hệ thống RAG nhằm tự động phát hiện khi trợ lý AI không thể trả lời đầy đủ câu hỏi dựa trên tài liệu có sẵn, và tự động chuyển sang tìm kiếm thông tin bổ sung từ Google Search.

## Cách hoạt động

### 1. Phát hiện Response thiếu thông tin

Hệ thống sẽ phân tích nội dung response từ LLM và tìm kiếm các pattern sau:

**Strong Patterns (Trigger ngay lập tức):**
- "Tôi không thể trả lời đầy đủ câu hỏi này dựa trên tài liệu hiện có"
- "không thể trả lời đầy đủ câu hỏi này dựa trên tài liệu"
- "không được tìm thấy trong tài liệu được cung cấp"
- "Tôi chỉ tìm thấy thông tin giới hạn về chủ đề này trong tài liệu"

**Weak Patterns (Chỉ trigger khi response < 200 ký tự):**
- "không đủ thông tin"
- "thông tin không đầy đủ"
- "không có thông tin chi tiết"
- "tài liệu không đề cập"
- "không được đề cập trong tài liệu"

**Refusal Indicators (Trigger khi có >= 2 indicators và response < 300 ký tự):**
- "tôi không thể"
- "không thể cung cấp"
- "không có thông tin"
- "xin lỗi, tôi"

### 2. Luồng xử lý chi tiết

1. **Normal RAG Processing**: Hệ thống xử lý câu hỏi bằng RAG pipeline thông thường
2. **Response Collection**: Thu thập toàn bộ response từ LLM stream
3. **Pattern Detection**: Phân tích response để tìm các pattern thiếu thông tin
4. **Automatic Fallback**: Nếu phát hiện thiếu thông tin:
   - Thêm separator visual `---`
   - Hiển thị thông báo "Đang tìm kiếm thông tin bổ sung từ web..."
   - Thực hiện Google Search với câu hỏi gốc
   - Stream kết quả bổ sung từ web
5. **Unified Response**: Người dùng nhận được cả response từ tài liệu và thông tin bổ sung từ web

## Cấu hình

### Biến môi trường

```env
# Bật/tắt tính năng Smart Fallback (đánh giá context trước khi xử lý)
ENABLE_SMART_FALLBACK=true

# Bật/tắt tính năng Response-based Fallback
ENABLE_RESPONSE_FALLBACK=true

# Ngưỡng chất lượng context cho Smart Fallback
CONTEXT_QUALITY_THRESHOLD=0.3
```

### Trong code

```python
# Khởi tạo với cấu hình tùy chỉnh
rag = AdvancedDatabaseRAG()

# Kiểm tra trạng thái cấu hình
print(f"Smart Fallback: {rag.enable_smart_fallback}")
print(f"Response Fallback: {rag.enable_response_fallback}")
```

## Ví dụ sử dụng

### Trước khi có tính năng

**User**: "CSDL dạng tệp là gì?"

**Assistant**: "Tôi không thể trả lời đầy đủ câu hỏi này dựa trên tài liệu hiện có. Thông tin về CSDL dạng tệp không được tìm thấy trong tài liệu được cung cấp."

### Sau khi có tính năng

**User**: "CSDL dạng tệp là gì?"

**Assistant**: 
```
Tôi không thể trả lời đầy đủ câu hỏi này dựa trên tài liệu hiện có. Thông tin về CSDL dạng tệp không được tìm thấy trong tài liệu được cung cấp.

---

**Đang tìm kiếm thông tin bổ sung từ web...**

CSDL dạng tệp (File-based Database) là một hệ thống quản lý dữ liệu đơn giản trong đó dữ liệu được lưu trữ trong các tệp tin riêng biệt trên hệ thống tệp của máy tính...

## Nguồn tham khảo
- https://example.com/database-types
- https://tutorial.com/file-database
```

## Lợi ích

1. **Trải nghiệm người dùng tốt hơn**: Không bao giờ để người dùng "treo" với câu trả lời thiếu thông tin
2. **Tự động hóa hoàn toàn**: Không cần can thiệp thủ công từ người dùng
3. **Thông tin đầy đủ**: Kết hợp cả kiến thức từ tài liệu và web
4. **Tùy chỉnh linh hoạt**: Có thể bật/tắt theo nhu cầu
5. **Hiệu suất tối ưu**: Chỉ trigger khi thực sự cần thiết

## Testing

Chạy test để kiểm tra tính năng:

```bash
cd src
python test_response_fallback.py
```

Test sẽ kiểm tra:
- Pattern detection accuracy
- Configuration values
- Edge cases handling

## Logs và Monitoring

Hệ thống ghi log chi tiết cho việc theo dõi:

```
🔍 Detected strong insufficient response pattern: 'Tôi không thể trả lời đầy đủ' in response
🔄 Detected insufficient response, triggering Google search fallback...
✅ Google fallback found results: 3 sources
``` 