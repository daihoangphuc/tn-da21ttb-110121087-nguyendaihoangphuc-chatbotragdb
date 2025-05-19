# Tài liệu API Hệ thống RAG

## Giới thiệu

Đây là tài liệu API cho hệ thống RAG (Retrieval Augmented Generation) được xây dựng bằng FastAPI. Hệ thống này cho phép người dùng đặt câu hỏi, tải lên tài liệu, quản lý cuộc hội thoại và nhiều hơn nữa.

## Prefix API

Tất cả các API đều sử dụng prefix: `/api` (có thể được cấu hình qua biến môi trường `API_PREFIX`).

## Các Model Dữ liệu (Pydantic Models)

Phần này mô tả các model dữ liệu được sử dụng trong các request và response của API.

### `QuestionRequest`

Dùng cho việc đặt câu hỏi.

-   `question` (str): Câu hỏi cần trả lời.
-   `search_type` (Optional[str], default: "hybrid"): Loại tìm kiếm. Các giá trị hợp lệ: "semantic", "keyword", "hybrid".
-   `alpha` (Optional[float], default: 0.7): Hệ số kết hợp giữa semantic và keyword search (ví dụ: 0.7 nghĩa là 70% semantic, 30% keyword).
-   `sources` (Optional[List[str]], default: None): Danh sách các tên file hoặc đường dẫn file nguồn cần tìm kiếm.
-   `file_id` (Optional[List[str]], default: None): Danh sách các `file_id` của tài liệu cần tìm kiếm (sử dụng trong API stream).
-   `session_id` (Optional[str], default: None): ID của phiên hội thoại. Nếu không cung cấp, một ID mới sẽ được tạo tự động.

### `AnswerResponse`

Dùng cho việc trả về câu trả lời cho một câu hỏi.

-   `question_id` (str): ID duy nhất của câu hỏi.
-   `question` (str): Câu hỏi gốc đã được đặt.
-   `answer` (str): Câu trả lời được tạo ra bởi hệ thống.
-   `sources` (List[Dict]): Danh sách các nguồn tài liệu được sử dụng để tạo câu trả lời. Mỗi nguồn bao gồm:
    -   `source` (str): Tên hoặc đường dẫn file nguồn.
    -   `page` (Optional[int]): Số trang (nếu có).
    -   `section` (Optional[str]): Tên section (nếu có).
    -   `score` (float): Điểm relevancy của nguồn.
    -   `content_snippet` (str): Đoạn trích nội dung từ nguồn.
    -   `original_page` (Optional[Any]): Thông tin trang gốc (nếu có).
-   `search_method` (str): Phương pháp tìm kiếm đã được sử dụng.
-   `total_reranked` (Optional[int]): Số lượng kết quả đã được rerank.
-   `filtered_sources` (Optional[List[str]]): Danh sách các file nguồn đã được lọc (nếu có).
-   `reranker_model` (Optional[str]): Tên model reranker đã được sử dụng.
-   `processing_time` (Optional[float]): Thời gian xử lý câu hỏi (tính bằng giây).
-   `debug_info` (Optional[Dict]): Thông tin debug bổ sung.
-   `related_questions` (Optional[List[str]]): Danh sách các câu hỏi liên quan được gợi ý.
-   `is_low_confidence` (Optional[bool]): `True` nếu câu trả lời có độ tin cậy thấp.
-   `confidence_score` (Optional[float]): Điểm tin cậy của câu trả lời.
-   `query_type` (Optional[str]): Loại câu hỏi (ví dụ: "question_from_document", "realtime_question").
-   `session_id` (Optional[str]): ID của phiên hội thoại.

### `FileInfo`

Thông tin chi tiết về một file đã upload.

-   `filename` (str): Tên file.
-   `path` (str): Đường dẫn đến file trên server.
-   `size` (int): Kích thước file (bytes).
-   `upload_date` (Optional[str]): Thời gian upload file (ISO format).
-   `extension` (str): Phần mở rộng của file (ví dụ: ".pdf").
-   `category` (Optional[str]): Danh mục của file (nếu có).
-   `id` (Optional[str]): `file_id` duy nhất của file trong hệ thống (thường là UUID).

### `FileListResponse`

Danh sách các file đã upload.

-   `total_files` (int): Tổng số file.
-   `files` (List[FileInfo]): Danh sách các đối tượng `FileInfo`.

### `FileDeleteResponse`

Kết quả sau khi xóa một file.

-   `filename` (str): Tên file đã bị xóa.
-   `status` (str): Trạng thái xóa ("success" hoặc "error").
-   `message` (str): Thông báo chi tiết về kết quả xóa.
-   `removed_points` (Optional[int]): Số lượng điểm dữ liệu (index) đã bị xóa khỏi vector store.

### `CreateConversationResponse`

Kết quả sau khi tạo một cuộc hội thoại mới.

-   `status` (str): Trạng thái ("success").
-   `message` (str): Thông báo.
-   `conversation_id` (str): ID của cuộc hội thoại vừa được tạo.

### `DeleteConversationResponse` (Không được sử dụng trực tiếp trong response model của API, nhưng cấu trúc tương tự)

Kết quả sau khi xóa một cuộc hội thoại.

-   `status` (str): Trạng thái.
-   `message` (str): Thông báo.
-   `conversation_id` (str): ID của cuộc hội thoại đã bị xóa.

### `UserSignUpRequest`

Dùng cho việc đăng ký tài khoản mới.

-   `email` (EmailStr): Địa chỉ email của người dùng.
-   `password` (str): Mật khẩu.

### `UserLoginRequest`

Dùng cho việc đăng nhập.

-   `email` (EmailStr): Địa chỉ email của người dùng.
-   `password` (str): Mật khẩu.

### `GoogleAuthRequest`

Dùng cho việc đăng nhập/đăng ký bằng Google.

-   `code` (Optional[str]): Authorization code nhận được từ Google OAuth.
-   `access_token` (Optional[str]): Access token Google đã cấp.
-   `provider` (str, default: "google"): OAuth provider (hiện tại chỉ hỗ trợ "google").

### `UserResponse`

Thông tin cơ bản về người dùng.

-   `id` (str): ID duy nhất của người dùng (thường là UUID từ Supabase).
-   `email` (str): Địa chỉ email của người dùng.
-   `created_at` (str): Thời gian tạo tài khoản (ISO format).

### `AuthResponse`

Kết quả sau khi đăng nhập hoặc đăng ký thành công.

-   `user` (UserResponse): Thông tin người dùng.
-   `access_token` (str): JWT access token.
-   `token_type` (str, default: "bearer"): Loại token.
-   `expires_in` (Optional[int]): Thời gian hết hạn của access token (tính bằng giây).

### `SuggestionResponse`

Danh sách các câu hỏi gợi ý.

-   `suggestions` (List[str]): Danh sách các câu hỏi được gợi ý.
-   `conversation_id` (Optional[str]): ID của cuộc hội thoại được sử dụng để tạo gợi ý (nếu có).
-   `from_history` (bool): `True` nếu gợi ý dựa trên lịch sử hội thoại, `False` nếu dùng gợi ý mặc định.

### `LatestConversationResponse`

Thông tin về cuộc hội thoại gần đây nhất.

-   `conversation_info` (Dict): Thông tin chung về cuộc hội thoại (ví dụ: ID, thời gian cập nhật).
-   `messages` (List[Dict]): Danh sách các tin nhắn trong cuộc hội thoại.
-   `found` (bool): `True` nếu tìm thấy cuộc hội thoại, `False` nếu không.

## API Endpoints

### 1. Root

-   **Endpoint:** `GET /`
-   **Mô tả:** Trả về thông báo chào mừng.
-   **Đầu vào:** Không có.
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "message": "Chào mừng đến với API của hệ thống RAG. Truy cập /docs để xem tài liệu API."
    }
    ```

### 2. Đặt câu hỏi (Ask Question)

-   **Endpoint:** `POST /ask`
-   **Mô tả:** Đặt một câu hỏi và nhận câu trả lời từ hệ thống RAG. Yêu cầu xác thực.
-   **Đầu vào:**
    -   **Query Parameters:**
        -   `max_sources` (Optional[int], default: None, min: 1, max: 50): Số lượng nguồn tham khảo tối đa trả về.
    -   **Request Body:** `QuestionRequest`
-   **Đầu ra (Thành công - 200):** `AnswerResponse`
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`:
        -   Nếu không chọn nguồn tài liệu (`request.sources` rỗng). Nội dung response:
            ```json
            {
                "status": "error",
                "message": "Vui lòng chọn ít nhất một nguồn tài liệu để tìm kiếm.",
                "available_sources": ["source1.pdf", "source2.txt"],
                "available_filenames": ["source1.pdf", "source2.txt"],
                "note": "Bạn có thể dùng tên file đơn thuần hoặc đường dẫn đầy đủ"
            }
            ```
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `404 Not Found`: Nếu một hoặc nhiều nguồn tài liệu trong `request.sources` không tồn tại. Nội dung response:
        ```json
        {
            "status": "error",
            "message": "Không tìm thấy các nguồn: missing_source.pdf",
            "available_sources": ["source1.pdf", "source2.txt"],
            "available_filenames": ["source1.pdf", "source2.txt"],
            "note": "Bạn có thể dùng tên file đơn thuần hoặc đường dẫn đầy đủ"
        }
        ```
    -   `500 Internal Server Error`: Lỗi xử lý câu hỏi.

### 3. Đặt câu hỏi (Stream)

-   **Endpoint:** `POST /ask/stream`
-   **Mô tả:** Đặt một câu hỏi và nhận câu trả lời dưới dạng Server-Sent Events (SSE). Yêu cầu xác thực. API này sử dụng `file_id` thay vì `sources`.
-   **Đầu vào:**
    -   **Query Parameters:**
        -   `max_sources` (Optional[int], default: None, min: 1, max: 50): Số lượng nguồn tham khảo tối đa trả về.
    -   **Request Body:** `QuestionRequest` (trong đó `file_id` được ưu tiên sử dụng thay vì `sources`).
-   **Đầu ra (Thành công - 200):** `StreamingResponse` (media type: `text/event-stream`).
    Các sự kiện SSE có thể bao gồm:
    -   `event: start`: Bắt đầu quá trình trả lời. Dữ liệu là JSON object chứa `question_id`, `session_id`.
    -   `event: sources`: Thông tin về các nguồn tài liệu. Dữ liệu là JSON object chứa `sources`, `question_id`, `session_id`.
    -   `event: content`: Một phần của nội dung câu trả lời. Dữ liệu là JSON object chứa `content`.
    -   `event: end`: Kết thúc quá trình trả lời. Dữ liệu là JSON object chứa thông tin tổng kết như `question_id`, `session_id`, `processing_time`, `related_questions`.
    -   `event: error`: Nếu có lỗi xảy ra trong quá trình stream. Dữ liệu là JSON object chứa `error: true`, `message`, `question_id`, `session_id`.
-   **Lỗi có thể xảy ra (Trước khi stream bắt đầu):**
    -   `400 Bad Request`: Nếu không cung cấp `file_id`. Nội dung response:
        ```json
        {
            "status": "error",
            "message": "Vui lòng chọn ít nhất một file_id để tìm kiếm.",
            "available_file_ids": ["uuid1", "uuid2"],
            "available_files": [["filename1.pdf", "uuid1"], ["filename2.txt", "uuid2"]]
        }
        ```
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `500 Internal Server Error`: Lỗi xử lý câu hỏi ban đầu.

### 4. Tải lên Tài liệu (Upload Document)

-   **Endpoint:** `POST /upload`
-   **Mô tả:** Tải lên một tài liệu để thêm vào hệ thống. Tài liệu sẽ được tự động xử lý và index. Yêu cầu xác thực.
-   **Đầu vào:**
    -   **Form Data:**
        -   `file` (UploadFile): File tài liệu cần tải lên (Hỗ trợ: .pdf, .docx, .txt, .sql).
        -   `category` (Optional[str]): Danh mục cho tài liệu.
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "filename": "example.pdf",
        "status": "success", // hoặc "warning", "error"
        "message": "Đã tải lên và index thành công 10 chunks từ tài liệu",
        "chunks_count": 10,
        "category": "general", // (nếu có)
        "file_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" // UUID của file
    }
    ```
    Hoặc nếu lỗi:
    ```json
    {
        "filename": "unsupported.zip",
        "status": "error",
        "message": "Không hỗ trợ định dạng .zip"
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Định dạng file không được hỗ trợ.
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `500 Internal Server Error`: Lỗi khi xử lý tài liệu.

### 5. Reset Collection

-   **Endpoint:** `DELETE /collection/reset`
-   **Mô tả:** Xóa toàn bộ dữ liệu đã index trong collection hiện tại của vector store và tạo lại collection mới. Endpoint này **không** yêu cầu xác thực người dùng.
-   **Đầu vào:** Không có.
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "status": "success", // hoặc "warning"
        "message": "Đã xóa và tạo lại collection my_collection",
        "vector_size": 768 // (nếu thành công)
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `500 Internal Server Error`: Lỗi khi reset collection.

### 6. Lấy Danh sách Files Đã Upload

-   **Endpoint:** `GET /files`
-   **Mô tả:** Lấy danh sách các file đã được người dùng hiện tại upload vào hệ thống. Yêu cầu xác thực.
-   **Đầu vào:** Không có.
-   **Đầu ra (Thành công - 200):** `FileListResponse`
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `500 Internal Server Error`: Lỗi khi lấy danh sách file.

### 7. Xóa File

-   **Endpoint:** `DELETE /files/{filename}`
-   **Mô tả:** Xóa một file đã upload (cả file vật lý và các index liên quan trong vector store). Yêu cầu xác thực.
-   **Đầu vào:**
    -   **Path Parameters:**
        -   `filename` (str): Tên file cần xóa.
-   **Đầu ra (Thành công - 200):** `FileDeleteResponse`
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `404 Not Found`: Nếu file không tồn tại.
    -   `500 Internal Server Error`: Lỗi khi xóa file.

### 8. Xóa Điểm Dữ liệu theo Filter

-   **Endpoint:** `POST /collections/delete-by-filter`
-   **Mô tả:** Xóa các điểm dữ liệu trong collection của vector store dựa trên một bộ lọc (filter) được cung cấp. Endpoint này **không** yêu cầu xác thực người dùng.
-   **Đầu vào:**
    -   **Request Body:** (Dict)
        ```json
        {
          "filter": {
            "must": [ // Hoặc "should"
              {
                "key": "metadata.source", // Hoặc "source", "user_id", ...
                "match": {
                  "value": "tên_file.pdf"
                }
              }
              // , { ... } // Các điều kiện khác
            ]
          }
        }
        ```
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "status": "success",
        "message": "Đã xóa 5 điểm dữ liệu thành công."
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Filter không hợp lệ hoặc lỗi khi thực hiện xóa.
    -   `500 Internal Server Error`: Lỗi không xác định.

### 9. Lấy Danh sách Tất cả Cuộc Hội thoại (Phiên bản cũ, có thể bị ghi đè)

-   **Endpoint:** `GET /conversations` (Endpoint này bị định nghĩa 2 lần, phiên bản này có thể không được FastAPI ưu tiên)
-   **Mô tả:** Lấy danh sách tất cả các cuộc hội thoại đã lưu trữ cho người dùng hiện tại, có phân trang. Yêu cầu xác thực.
-   **Đầu vào:**
    -   **Query Parameters:**
        -   `page` (int, default: 1, min: 1): Trang hiện tại.
        -   `page_size` (int, default: 10, min: 1, max: 50): Số lượng hội thoại mỗi trang.
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "status": "success",
        "message": "Đã tìm thấy 25 hội thoại",
        "data": [
            // Danh sách các object hội thoại, mỗi object có thể chứa user_id và các thông tin khác từ SupabaseConversationManager
        ],
        "pagination": {
            "page": 1,
            "page_size": 10,
            "total_items": 25,
            "total_pages": 3
        }
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `500 Internal Server Error`: Lỗi khi lấy danh sách hội thoại.

### 10. Lấy Chi tiết Cuộc Hội thoại

-   **Endpoint:** `GET /conversations/{conversation_id}`
-   **Mô tả:** Lấy chi tiết tin nhắn của một cuộc hội thoại cụ thể. Yêu cầu xác thực.
-   **Đầu vào:**
    -   **Path Parameters:**
        -   `conversation_id` (str): ID của cuộc hội thoại.
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "status": "success",
        "message": "Đã tìm thấy chi tiết hội thoại cho phiên XXXXX",
        "data": {
            "conversation_id": "XXXXX",
            "last_updated": "2023-10-27T10:00:00Z",
            "messages": [
                // Danh sách các tin nhắn (mỗi tin nhắn là một dict)
            ]
        }
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `404 Not Found`: Nếu không tìm thấy hội thoại với ID cung cấp.
    -   `500 Internal Server Error`: Lỗi khi lấy chi tiết hội thoại.

### 11. Đăng ký Tài khoản (Sign Up)

-   **Endpoint:** `POST /auth/signup`
-   **Mô tả:** Đăng ký tài khoản mới bằng email và mật khẩu.
-   **Đầu vào:**
    -   **Request Body:** `UserSignUpRequest`
-   **Đầu ra (Thành công - 200):** `AuthResponse`
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Đăng ký thất bại (ví dụ: email đã tồn tại, mật khẩu không đủ mạnh theo rule của Supabase).
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 12. Đăng nhập (Login)

-   **Endpoint:** `POST /auth/login`
-   **Mô tả:** Đăng nhập bằng email và mật khẩu.
-   **Đầu vào:**
    -   **Request Body:** `UserLoginRequest`
-   **Đầu ra (Thành công - 200):** `AuthResponse`
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Lỗi khi đăng nhập (thường là do `401` từ Supabase).
    -   `401 Unauthorized`: Sai email hoặc mật khẩu.
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 13. Đăng xuất (Logout)

-   **Endpoint:** `POST /auth/logout`
-   **Mô tả:** Đăng xuất khỏi hệ thống, vô hiệu hóa token hiện tại của người dùng. Yêu cầu xác thực (token trong header).
-   **Đầu vào:**
    -   **Headers:** `Authorization: Bearer <your_access_token>` (Không bắt buộc, nếu không có token thì trả về "Đã đăng xuất")
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "message": "Đăng xuất thành công" // hoặc "Đã đăng xuất" nếu không có token
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Lỗi khi đăng xuất từ Supabase.
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 14. Lấy Thông tin Người dùng Hiện tại

-   **Endpoint:** `GET /auth/user`
-   **Mô tả:** Lấy thông tin của người dùng đang đăng nhập (dựa trên token). Yêu cầu xác thực.
-   **Đầu vào:**
    -   **Headers:** `Authorization: Bearer <your_access_token>`
-   **Đầu ra (Thành công - 200):** `UserResponse`
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 15. Kiểm tra Thông tin Phiên Hiện tại

-   **Endpoint:** `GET /auth/session`
-   **Mô tả:** Kiểm tra thông tin phiên đăng nhập hiện tại dựa trên token. Yêu cầu xác thực.
-   **Đầu vào:**
    -   **Headers:** `Authorization: Bearer <your_access_token>`
-   **Đầu ra (Thành công - 200 nếu xác thực thành công):**
    ```json
    {
        "is_authenticated": true,
        "user_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "email": "user@example.com",
        "created_at": "2023-10-27T10:00:00Z"
    }
    ```
-   **Đầu ra (Thất bại - 401 nếu không xác thực được):**
    ```json
    {
        "is_authenticated": false,
        "message": "Không có thông tin xác thực" // hoặc "Phiên không hợp lệ hoặc đã hết hạn"
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 16. Đăng nhập/Đăng ký với Google

-   **Endpoint:** `POST /auth/google`
-   **Mô tả:** Xử lý đăng nhập hoặc đăng ký người dùng thông qua Google OAuth. Cần cung cấp `code` (authorization code) hoặc `access_token` từ Google.
-   **Đầu vào:**
    -   **Request Body:** `GoogleAuthRequest`
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "user": {
            "id": "google_user_id_from_supabase",
            "email": "user@gmail.com",
            "name": "User Name",
            "avatar_url": "url_to_avatar.jpg"
        },
        "access_token": "supabase_access_token",
        "refresh_token": "supabase_refresh_token",
        "provider": "google"
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Thiếu `code` hoặc `access_token`, hoặc lỗi xác thực với Google/Supabase.
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 17. Lấy URL Đăng nhập Google

-   **Endpoint:** `GET /auth/google/url`
-   **Mô tả:** Lấy URL để chuyển hướng người dùng đến trang đăng nhập của Google.
-   **Đầu vào:**
    -   **Query Parameters:**
        -   `redirect_url` (str): URL mà Google sẽ chuyển hướng về sau khi người dùng đăng nhập thành công (callback URL của bạn).
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "url": "https://accounts.google.com/o/oauth2/v2/auth?..." // URL đăng nhập Google
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Thiếu `redirect_url` hoặc lỗi khi tạo URL từ Supabase.
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 18. Xử lý Callback từ Google OAuth

-   **Endpoint:** `GET /auth/callback`
-   **Mô tả:** Endpoint này được Google chuyển hướng về sau khi người dùng xác thực. Nó nhận `code` từ Google và đổi lấy session/token từ Supabase.
-   **Đầu vào:**
    -   **Query Parameters:**
        -   `code` (Optional[str]): Authorization code được trả về từ Google.
        -   `error` (Optional[str]): Thông báo lỗi từ Google (nếu có).
        -   `provider` (str, default: "google"): OAuth provider.
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "user": {
            "id": "supabase_user_id",
            "email": "user@gmail.com",
            "name": "User Name",
            "avatar_url": "url_to_avatar.jpg"
        },
        "access_token": "supabase_access_token",
        "refresh_token": "supabase_refresh_token",
        "provider": "google"
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Nếu có `error` từ Google, thiếu `code`, hoặc lỗi khi trao đổi code với Supabase.
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 19. Tạo Cuộc Hội thoại Mới

-   **Endpoint:** `POST /conversations/create`
-   **Mô tả:** Tạo một cuộc hội thoại mới cho người dùng hiện tại. Yêu cầu xác thực.
-   **Đầu vào:** Không có.
-   **Đầu ra (Thành công - 200):** `CreateConversationResponse`
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `500 Internal Server Error`: Không thể tạo hội thoại mới.

### 20. Lấy Danh sách Cuộc Hội thoại của Người dùng (Phiên bản được ưu tiên)

-   **Endpoint:** `GET /conversations`
-   **Mô tả:** Lấy danh sách tất cả các cuộc hội thoại của người dùng hiện tại, có phân trang và thông tin tin nhắn đầu tiên. Yêu cầu xác thực. (Endpoint này có vẻ được ưu tiên hơn so với mục 9 do vị trí trong code và logic chi tiết hơn).
-   **Đầu vào:**
    -   **Query Parameters:**
        -   `page` (int, default: 1, min: 1): Trang hiện tại.
        -   `page_size` (int, default: 10, min: 1, max: 50): Số lượng hội thoại mỗi trang.
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "status": "success",
        "data": [
            {
                "conversation_id": "conv_id_1",
                "user_id": "user_id_1",
                "created_at": "2023-10-27T10:00:00Z",
                "last_updated": "2023-10-27T10:05:00Z",
                "first_message": "Xin chào, tôi cần giúp đỡ về...", // Tin nhắn đầu tiên của người dùng
                "message_count": 5 // Tổng số tin nhắn trong hội thoại
            }
            // ... các hội thoại khác
        ],
        "pagination": {
            "page": 1,
            "page_size": 10,
            "total_items": 25,
            "total_pages": 3
        }
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `500 Internal Server Error`: Lỗi khi lấy danh sách hội thoại.

### 21. Xóa Cuộc Hội thoại

-   **Endpoint:** `DELETE /conversations/{conversation_id}`
-   **Mô tả:** Xóa một cuộc hội thoại và tất cả các tin nhắn liên quan của nó. Yêu cầu xác thực.
-   **Đầu vào:**
    -   **Path Parameters:**
        -   `conversation_id` (str): ID của cuộc hội thoại cần xóa.
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "status": "success",
        "message": "Đã xóa hội thoại conv_id_1",
        "conversation_id": "conv_id_1"
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `404 Not Found`: Không tìm thấy hội thoại hoặc người dùng không có quyền xóa.
    -   `500 Internal Server Error`: Không thể xóa hội thoại.

### 22. Lấy Gợi ý Câu hỏi

-   **Endpoint:** `GET /suggestions`
-   **Mô tả:** Lấy các câu hỏi gợi ý dựa trên cuộc hội thoại gần đây nhất có tin nhắn của người dùng, hoặc trả về các gợi ý mặc định nếu không có hội thoại phù hợp. Yêu cầu xác thực.
-   **Đầu vào:**
    -   **Query Parameters:**
        -   `num_suggestions` (int, default: 3, min: 1, max: 10): Số lượng câu hỏi gợi ý muốn nhận.
-   **Đầu ra (Thành công - 200):** `SuggestionResponse`
    Ví dụ:
    ```json
    {
        "suggestions": [
            "Câu hỏi gợi ý 1?",
            "Câu hỏi gợi ý 2?",
            "Câu hỏi gợi ý 3?"
        ],
        "conversation_id": "conv_id_xyz", // (nếu from_history là true)
        "from_history": true // hoặc false
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `500 Internal Server Error`: Lỗi khi lấy gợi ý (sẽ trả về gợi ý mặc định).

### 23. Lấy Cuộc Hội thoại Gần đây Nhất

-   **Endpoint:** `GET /latest-conversation`
-   **Mô tả:** Lấy thông tin và tin nhắn của cuộc hội thoại gần đây nhất có tin nhắn của người dùng hiện tại. Yêu cầu xác thực.
-   **Đầu vào:** Không có.
-   **Đầu ra (Thành công - 200):** `LatestConversationResponse`
    Ví dụ (nếu tìm thấy):
    ```json
    {
        "conversation_info": {
            "conversation_id": "conv_id_recent",
            "user_id": "user_id_1",
            "last_updated": "2023-10-28T12:00:00Z"
            // ... các thông tin khác của hội thoại
        },
        "messages": [
            {"role": "user", "content": "Câu hỏi cuối cùng của tôi là gì?"},
            {"role": "ai", "content": "Đây là câu trả lời..."}
            // ... các tin nhắn khác
        ],
        "found": true
    }
    ```
    Ví dụ (nếu không tìm thấy):
    ```json
    {
        "conversation_info": {},
        "messages": [],
        "found": false
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `500 Internal Server Error`: Lỗi khi lấy hội thoại (sẽ trả về `found: false`).
