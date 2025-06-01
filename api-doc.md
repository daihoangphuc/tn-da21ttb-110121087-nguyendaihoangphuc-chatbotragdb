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
-   `sources` (Optional[List[str]], default: None): Danh sách các tên file hoặc đường dẫn file nguồn cần tìm kiếm. (Lưu ý: API `/ask/stream` ưu tiên `file_id`).
-   `file_id` (Optional[List[str]], default: None): Danh sách các `file_id` của tài liệu cần tìm kiếm (sử dụng trong API `/ask/stream`).
-   `conversation_id` (Optional[str], default: None): ID của phiên hội thoại. Nếu không cung cấp, một ID mới sẽ được tạo tự động hoặc sử dụng ID của cuộc hội thoại gần nhất nếu có.

### `SQLAnalysisRequest`

Dùng cho việc yêu cầu phân tích một câu lệnh SQL.

- `sql_query` (str): Câu lệnh SQL cần phân tích.
- `database_context` (Optional[str], default: None): Ngữ cảnh của cơ sở dữ liệu (ví dụ: schema, phiên bản).

### `SQLAnalysisResponse`

Kết quả phân tích câu lệnh SQL.

- `query` (str): Câu lệnh SQL gốc.
- `analysis` (str): Kết quả phân tích chi tiết.
- `suggestions` (List[str]): Danh sách các đề xuất cải thiện.
- `optimized_query` (Optional[str], default: None): Câu lệnh SQL đã được tối ưu hóa (nếu có).

### `IndexingStatusResponse`

Thông tin về trạng thái của quá trình indexing tài liệu.

- `status` (str): Trạng thái hiện tại (ví dụ: "idle", "running", "completed", "error").
- `message` (str): Thông báo chi tiết về trạng thái.
- `processed_files` (int): Số lượng file đã được xử lý.

### `CategoryStatsResponse`

Thống kê tài liệu theo danh mục.

- `total_documents` (int): Tổng số tài liệu.
- `documents_by_category` (Dict[str, int]): Số lượng tài liệu theo từng danh mục.
- `categories` (List[str]): Danh sách các danh mục có sẵn.

### `FileInfo`

Thông tin chi tiết về một file đã upload.

-   `filename` (str): Tên file (thường là tên file gốc khi upload).
-   `path` (str): Đường dẫn đến file trên server (có thể là đường dẫn file đã chuyển đổi).
-   `size` (int): Kích thước file (bytes).
-   `upload_date` (Optional[str]): Thời gian upload file (ISO format, lấy từ database hoặc thời gian tạo file).
-   `extension` (str): Phần mở rộng của file (thường là phần mở rộng của file gốc).
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

### `ConversationRequest`
Dùng để truyền ID của một cuộc hội thoại.
- `conversation_id` (str): ID của cuộc hội thoại.


### `CreateConversationResponse`

Kết quả sau khi tạo một cuộc hội thoại mới.

-   `status` (str): Trạng thái ("success").
-   `message` (str): Thông báo.
-   `conversation_id` (str): ID của cuộc hội thoại vừa được tạo.

### `DeleteConversationResponse`

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
    *Validator*: Phải cung cấp một trong hai: `code` hoặc `access_token`.

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

### `ForgotPasswordRequest`
Dùng cho việc yêu cầu gửi email đặt lại mật khẩu.
- `email` (EmailStr): Email của người dùng cần đặt lại mật khẩu.
- `redirect_to` (Optional[str]): URL để chuyển hướng người dùng sau khi họ nhấp vào liên kết trong email (tùy chọn, Supabase sẽ dùng URL mặc định nếu không cung cấp).

### `ResetPasswordRequest`
Dùng cho việc đặt lại mật khẩu bằng token nhận từ email.
- `password` (str): Mật khẩu mới của người dùng.
  *Validator*: Mật khẩu phải có ít nhất 8 ký tự, 1 chữ hoa, 1 chữ thường, 1 chữ số.
- `access_token` (str): Token xác thực nhận được từ email.

### `ForgotPasswordResponse`
Phản hồi sau khi yêu cầu quên mật khẩu.
- `status` (str): Trạng thái ("success").
- `message` (str): Thông báo.


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
-   **Xác thực:** Không yêu cầu.
-   **Đầu vào:** Không có.
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "message": "Chào mừng đến với API của hệ thống RAG. Truy cập /docs để xem tài liệu API."
    }
    ```

### 2. Đặt câu hỏi (Stream)

-   **Endpoint:** `POST /ask/stream`
-   **Mô tả:** Đặt một câu hỏi và nhận câu trả lời dưới dạng Server-Sent Events (SSE). API này sử dụng `file_id` để xác định tài liệu cần tìm kiếm trong collection của người dùng hiện tại.
-   **Xác thực:** Yêu cầu (Bearer Token - `get_current_user`).
-   **Đầu vào:**
    -   **Query Parameters:**
        -   `max_sources` (Optional[int], default: None, min: 1, max: 50): Số lượng nguồn tham khảo tối đa trả về.
    -   **Request Body:** `QuestionRequest` (trong đó `file_id` là bắt buộc nếu người dùng chưa có file nào được upload hoặc không có file_id nào được chọn).
-   **Đầu ra (Thành công - 200):** `StreamingResponse` (media type: `text/event-stream`).
    Các sự kiện SSE có thể bao gồm:
    -   `event: start`: Bắt đầu quá trình trả lời. Dữ liệu là JSON object chứa `question_id`, `conversation_id`.
    -   `event: sources`: Thông tin về các nguồn tài liệu. Dữ liệu là JSON object chứa `sources`, `question_id`, `conversation_id`.
    -   `event: content`: Một phần của nội dung câu trả lời. Dữ liệu là JSON object chứa `content`.
    -   `event: end`: Kết thúc quá trình trả lời. Dữ liệu là JSON object chứa thông tin tổng kết như `question_id`, `conversation_id`, `processing_time`, `related_questions`.
    -   `event: error`: Nếu có lỗi xảy ra trong quá trình stream. Dữ liệu là JSON object chứa `error: true`, `message`, `question_id`, `conversation_id`.
-   **Lỗi có thể xảy ra (Trước khi stream bắt đầu):**
    -   `400 Bad Request`: Nếu không cung cấp `file_id` và không có file nào khả dụng cho user. Nội dung response:
        ```json
        {
            "status": "error",
            "message": "Vui lòng chọn ít nhất một file_id để tìm kiếm.",
            "available_file_ids": ["uuid1", "uuid2"], // Danh sách file_id có sẵn của user
            "available_files": [["filename1.pdf", "uuid1"], ["filename2.txt", "uuid2"]] // Danh sách (tên file, file_id)
        }
        ```
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `500 Internal Server Error`: Lỗi xử lý câu hỏi ban đầu.
    -   `503 Service Unavailable`: Dịch vụ xác thực chưa được cấu hình.

### 3. Tải lên Tài liệu (Upload Document)

-   **Endpoint:** `POST /upload`
-   **Mô tả:** Tải lên một tài liệu để thêm vào hệ thống. Tài liệu sẽ được tự động xử lý và index vào collection của người dùng hiện tại.
-   **Xác thực:** Yêu cầu (Bearer Token - `get_current_user`).
-   **Đầu vào:**
    -   **Form Data:**
        -   `file` (UploadFile): File tài liệu cần tải lên (Hỗ trợ: .pdf, .docx, .txt, .sql, .md).
        -   `category` (Optional[str]): Danh mục cho tài liệu.
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "filename": "example.pdf", // Tên file gốc đã upload
        "status": "success",
        "message": "Đã tải lên và index thành công X chunks từ tài liệu", // X là số chunks
        "chunks_count": X, // Số chunks
        "category": "general", // Danh mục (nếu có)
        "file_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" // file_id của tài liệu trong hệ thống
    }
    ```
    Hoặc nếu lỗi:
    ```json
    {
        "filename": "unsupported.zip",
        "status": "error",
        "message": "Không hỗ trợ định dạng file .zip" // Hoặc lỗi đọc file, lỗi index
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Định dạng file không được hỗ trợ hoặc lỗi đọc file.
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `500 Internal Server Error`: Lỗi khi xử lý hoặc index tài liệu.
    -   `503 Service Unavailable`: Dịch vụ xác thực chưa được cấu hình.

### 4. Reset Collection (Của User hiện tại)

-   **Endpoint:** `DELETE /collection/reset`
-   **Mô tả:** Xóa toàn bộ dữ liệu đã index trong collection của người dùng hiện tại (ví dụ: `user_xxxxxxxx-xxxx`) và tạo lại collection mới.
-   **Xác thực:** Yêu cầu (Bearer Token - `get_current_user` sẽ được sử dụng để xác định collection của user, mặc dù không được truyền trực tiếp vào hàm `reset_collection`).
-   **Đầu vào:** Không có.
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "status": "success",
        "message": "Đã xóa và tạo lại collection YOUR_USER_SPECIFIC_COLLECTION_NAME",
        "vector_size": 768 // Kích thước vector của collection
    }
    ```
    Hoặc nếu collection không tồn tại trước đó:
     ```json
    {
        "status": "warning",
        "message": "Collection YOUR_USER_SPECIFIC_COLLECTION_NAME không tồn tại"
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Xác thực thất bại.
    -   `500 Internal Server Error`: Lỗi khi reset collection.
    -   `503 Service Unavailable`: Dịch vụ xác thực chưa được cấu hình.

### 5. Lấy Danh sách Files Đã Upload

-   **Endpoint:** `GET /files`
-   **Mô tả:** Lấy danh sách các file đã được người dùng hiện tại upload vào hệ thống. Thông tin được lấy từ database (Supabase).
-   **Xác thực:** Yêu cầu (Bearer Token - `get_current_user`).
-   **Đầu vào:** Không có.
-   **Đầu ra (Thành công - 200):** `FileListResponse`
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `500 Internal Server Error`: Lỗi khi lấy danh sách file.
    -   `503 Service Unavailable`: Dịch vụ xác thực chưa được cấu hình.

### 6. Xóa File

-   **Endpoint:** `DELETE /files/{filename}`
-   **Mô tả:** Xóa một file đã upload (xóa file vật lý, các index liên quan trong vector store của người dùng, và thông tin file trong database).
-   **Xác thực:** Yêu cầu (Bearer Token - `get_current_user`).
-   **Đầu vào:**
    -   **Path Parameters:**
        -   `filename` (str): Tên file cần xóa (tên file gốc khi upload).
-   **Đầu ra (Thành công - 200):** `FileDeleteResponse`
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `404 Not Found`: Nếu file không tồn tại trong thư mục của người dùng hoặc trong database.
    -   `500 Internal Server Error`: Lỗi khi xóa file hoặc index.
    -   `503 Service Unavailable`: Dịch vụ xác thực chưa được cấu hình.

### 7. Xóa Điểm Dữ liệu theo Filter (Trong Collection của User hiện tại)

-   **Endpoint:** `POST /collections/delete-by-filter`
-   **Mô tả:** Xóa các điểm dữ liệu trong collection của người dùng hiện tại dựa trên một bộ lọc (filter).
-   **Xác thực:** Yêu cầu (Bearer Token - `get_current_user` sẽ được sử dụng để xác định collection của user, mặc dù không được truyền trực tiếp vào hàm `delete_points_by_filter`).
-   **Đầu vào:**
    -   **Request Body:** (Dict)
        ```json
        {
          "filter": {
            "must": [ // Hoặc "should", "must_not"
              {
                "key": "metadata.source", // Hoặc "source", "metadata.file_id", ...
                "match": {
                  "value": "tên_file.pdf" // Hoặc file_id
                }
              }
              // , { ... } // Các điều kiện khác
            ]
            // Filter sẽ tự động được áp dụng thêm điều kiện user_id của người dùng hiện tại.
          }
        }
        ```
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "status": "success",
        "message": "Đã xóa X điểm dữ liệu thành công." // X là số điểm đã xóa
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Filter không hợp lệ hoặc lỗi khi thực hiện xóa.
    -   `401 Unauthorized`: Xác thực thất bại.
    -   `500 Internal Server Error`: Lỗi không xác định.
    -   `503 Service Unavailable`: Dịch vụ xác thực chưa được cấu hình.

### 8. Lấy Danh sách Cuộc Hội thoại (của User hiện tại)

-   **Endpoint:** `GET /conversations`
-   **Mô tả:** Lấy danh sách tất cả các cuộc hội thoại của người dùng hiện tại, có phân trang. Thông tin bao gồm tin nhắn đầu tiên và số lượng tin nhắn.
-   **Xác thực:** Yêu cầu (Bearer Token - `get_current_user`).
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
                "user_id": "user_id_1", // Luôn là user_id của người dùng hiện tại
                "created_at": "2023-10-27T10:00:00Z",
                "last_updated": "2023-10-27T10:05:00Z",
                "title": null, // Hiện tại không có title trong DB, sẽ là null
                "first_message": "Xin chào, tôi cần giúp đỡ về...", // Nội dung tin nhắn đầu tiên (user)
                "message_count": 5 // Tổng số tin nhắn trong hội thoại
            }
            // ... các hội thoại khác
        ],
        "pagination": {
            "page": 1,
            "page_size": 10,
            "total_items": 25, // Tổng số hội thoại của user
            "total_pages": 3
        }
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `500 Internal Server Error`: Lỗi khi lấy danh sách hội thoại.
    -   `503 Service Unavailable`: Dịch vụ xác thực chưa được cấu hình.

### 9. Lấy Chi tiết Cuộc Hội thoại

-   **Endpoint:** `GET /conversations/{conversation_id}`
-   **Mô tả:** Lấy chi tiết tin nhắn của một cuộc hội thoại cụ thể, thuộc về người dùng hiện tại.
-   **Xác thực:** Yêu cầu (Bearer Token - `get_current_user`).
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
            "last_updated": "2023-10-27T10:00:00Z", // Thời gian cuộc hội thoại được cập nhật lần cuối (lấy từ DB hoặc now())
            "messages": [
                // Danh sách các tin nhắn (role, content, sequence, created_at, ...)
            ]
        }
    }
    ```
    Hoặc nếu không tìm thấy tin nhắn/hội thoại:
    ```json
    {
        "status": "success",
        "message": "Không tìm thấy hội thoại với ID XXXXX", // Hoặc "Không tìm thấy tin nhắn cho hội thoại..."
        "conversation_id": "XXXXX" // Có thể không có messages trong data
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ, hoặc hội thoại không thuộc user.
    -   `404 Not Found`: Nếu hội thoại không tồn tại.
    -   `500 Internal Server Error`: Lỗi khi lấy chi tiết hội thoại.
    -   `503 Service Unavailable`: Dịch vụ xác thực chưa được cấu hình.

### 10. Đăng ký Tài khoản (Sign Up)

-   **Endpoint:** `POST /auth/signup`
-   **Mô tả:** Đăng ký tài khoản mới bằng email và mật khẩu.
-   **Xác thực:** Không yêu cầu.
-   **Đầu vào:**
    -   **Request Body:** `UserSignUpRequest`
-   **Đầu ra (Thành công - 200):** `AuthResponse` (lưu ý: `access_token` có thể rỗng nếu Supabase yêu cầu xác thực email).
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Đăng ký thất bại (ví dụ: email đã tồn tại, mật khẩu không đủ mạnh theo rule của Supabase, hoặc lỗi từ Supabase).
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 11. Đăng nhập (Login)

-   **Endpoint:** `POST /auth/login`
-   **Mô tả:** Đăng nhập bằng email và mật khẩu.
-   **Xác thực:** Không yêu cầu.
-   **Đầu vào:**
    -   **Request Body:** `UserLoginRequest`
-   **Đầu ra (Thành công - 200):** `AuthResponse`
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request` / `401 Unauthorized` / `429 Too Many Requests`:
        -   "Email hoặc mật khẩu không chính xác" (401)
        -   "Email chưa được xác nhận. Vui lòng kiểm tra hộp thư để xác nhận email" (401)
        -   "Không tìm thấy tài khoản với email này" (401)
        -   "Email không hợp lệ" (400)
        -   "Quá nhiều lần đăng nhập thất bại. Vui lòng thử lại sau" (429)
        -   Hoặc lỗi chung: "Lỗi đăng nhập: [chi tiết lỗi từ Supabase]" (400)
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 12. Đăng xuất (Logout)

-   **Endpoint:** `POST /auth/logout`
-   **Mô tả:** Đăng xuất khỏi hệ thống, vô hiệu hóa token hiện tại của người dùng.
-   **Xác thực:** Yêu cầu (Bearer Token - `auth_bearer`).
-   **Đầu vào:** Không có.
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "message": "Đăng xuất thành công"
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Lỗi khi đăng xuất từ Supabase.
    -   `401 Unauthorized`: Yêu cầu xác thực token (nếu `credentials` không được cung cấp hoặc không hợp lệ).
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 13. Lấy Thông tin Người dùng Hiện tại

-   **Endpoint:** `GET /auth/user`
-   **Mô tả:** Lấy thông tin của người dùng đang đăng nhập (dựa trên token).
-   **Xác thực:** Yêu cầu (Bearer Token - `get_current_user`).
-   **Đầu vào:** Không có.
-   **Đầu ra (Thành công - 200):** `UserResponse`
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 14. Kiểm tra Thông tin Phiên Hiện tại

-   **Endpoint:** `GET /auth/session`
-   **Mô tả:** Kiểm tra thông tin phiên đăng nhập hiện tại dựa trên token (nếu được cung cấp).
-   **Xác thực:** Tùy chọn (Bearer Token - `auth_bearer`).
-   **Đầu vào:** Không có.
-   **Đầu ra (Thành công - 200 nếu xác thực thành công):**
    ```json
    {
        "is_authenticated": true,
        "user_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "email": "user@example.com",
        "created_at": "2023-10-27T10:00:00Z"
    }
    ```
-   **Đầu ra (Thất bại - 401 nếu không xác thực được hoặc token không hợp lệ/hết hạn):**
    ```json
    {
        "is_authenticated": false,
        "message": "Không có thông tin xác thực" // Hoặc "Phiên không hợp lệ hoặc đã hết hạn" hoặc lỗi khác
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 15. Đăng nhập/Đăng ký với Google

-   **Endpoint:** `POST /auth/google`
-   **Mô tả:** Xử lý đăng nhập hoặc đăng ký người dùng thông qua Google OAuth. Cần cung cấp `code` (authorization code) hoặc `access_token` từ Google.
-   **Xác thực:** Không yêu cầu.
-   **Đầu vào:**
    -   **Request Body:** `GoogleAuthRequest`
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "user": {
            "id": "google_user_id_from_supabase",
            "email": "user@gmail.com",
            "name": "User Name", // Lấy từ user_metadata
            "avatar_url": "url_to_avatar.jpg" // Lấy từ user_metadata
        },
        "access_token": "supabase_access_token",
        "refresh_token": "supabase_refresh_token", // Nếu có
        "provider": "google"
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Thiếu `code` hoặc `access_token`, hoặc lỗi xác thực với Google/Supabase (ví dụ: "Không thể xác thực với code: ...", "Không thể tạo phiên đăng nhập").
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 16. Lấy URL Đăng nhập Google

-   **Endpoint:** `GET /auth/google/url`
-   **Mô tả:** Lấy URL để chuyển hướng người dùng đến trang đăng nhập của Google.
-   **Xác thực:** Không yêu cầu.
-   **Đầu vào:**
    -   **Query Parameters:**
        -   `redirect_url` (str): URL mà Google sẽ chuyển hướng về sau khi người dùng đăng nhập thành công (callback URL của bạn). **Bắt buộc.**
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "url": "https://accounts.google.com/o/oauth2/v2/auth?..."
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Thiếu `redirect_url` hoặc lỗi khi tạo URL từ Supabase ("Không thể lấy URL xác thực").
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 17. Xử lý Callback từ Google OAuth

-   **Endpoint:** `GET /auth/callback`
-   **Mô tả:** Endpoint này được Google chuyển hướng về sau khi người dùng xác thực. Nó nhận `code` từ Google và đổi lấy session/token từ Supabase.
-   **Xác thực:** Không yêu cầu.
-   **Đầu vào:**
    -   **Query Parameters:**
        -   `code` (Optional[str]): Authorization code được trả về từ Google. **Bắt buộc nếu không có `error`.**
        -   `error` (Optional[str]): Thông báo lỗi từ Google (nếu có).
        -   `provider` (str, default: "google"): OAuth provider.
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "user": {
            "id": "supabase_user_id",
            "email": "user@gmail.com",
            "name": "User Name", // Lấy từ user_metadata
            "avatar_url": "url_to_avatar.jpg" // Lấy từ user_metadata
        },
        "access_token": "supabase_access_token",
        "refresh_token": "supabase_refresh_token", // Nếu có
        "provider": "google"
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Nếu có `error` từ Google, thiếu `code`, hoặc lỗi khi trao đổi code với Supabase ("Lỗi xác thực OAuth: ...").
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 18. Tạo Cuộc Hội thoại Mới

-   **Endpoint:** `POST /conversations/create`
-   **Mô tả:** Tạo một cuộc hội thoại mới cho người dùng hiện tại.
-   **Xác thực:** Yêu cầu (Bearer Token - `get_current_user`).
-   **Đầu vào:** Không có.
-   **Đầu ra (Thành công - 200):** `CreateConversationResponse`
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `500 Internal Server Error`: Không thể tạo hội thoại mới.
    -   `503 Service Unavailable`: Dịch vụ xác thực chưa được cấu hình.

### 19. Xóa Cuộc Hội thoại

-   **Endpoint:** `DELETE /conversations/{conversation_id}`
-   **Mô tả:** Xóa một cuộc hội thoại và tất cả các tin nhắn liên quan của nó, thuộc về người dùng hiện tại.
-   **Xác thực:** Yêu cầu (Bearer Token - `get_current_user`).
-   **Đầu vào:**
    -   **Path Parameters:**
        -   `conversation_id` (str): ID của cuộc hội thoại cần xóa.
-   **Đầu ra (Thành công - 200):** `DeleteConversationResponse`
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `404 Not Found`: Không tìm thấy hội thoại hoặc người dùng không có quyền xóa.
    -   `500 Internal Server Error`: Không thể xóa hội thoại.
    -   `503 Service Unavailable`: Dịch vụ xác thực chưa được cấu hình.

### 20. Lấy Gợi ý Câu hỏi

-   **Endpoint:** `GET /suggestions`
-   **Mô tả:** Lấy các câu hỏi gợi ý dựa trên cuộc hội thoại gần đây nhất có tin nhắn của người dùng, hoặc trả về các gợi ý mặc định nếu không có hội thoại phù hợp.
-   **Xác thực:** Yêu cầu (Bearer Token - `get_current_user`).
-   **Đầu vào:**
    -   **Query Parameters:**
        -   `num_suggestions` (int, default: 3, min: 1, max: 10): Số lượng câu hỏi gợi ý muốn nhận.
-   **Đầu ra (Thành công - 200):** `SuggestionResponse`
    Ví dụ (nếu có lịch sử và hội thoại):
    ```json
    {
        "suggestions": [
            "Câu hỏi gợi ý 1 dựa trên lịch sử?",
            "Câu hỏi gợi ý 2 dựa trên lịch sử?"
        ],
        "conversation_id": "conv_id_xyz", // ID của hội thoại dùng để tạo gợi ý
        "from_history": true
    }
    ```
    Ví dụ (nếu không có lịch sử hoặc lỗi, trả về mặc định):
    ```json
    {
        "suggestions": [
            "Gợi ý mặc định 1?",
            "Gợi ý mặc định 2?",
            "Gợi ý mặc định 3?"
        ],
        "conversation_id": null,
        "from_history": false
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `503 Service Unavailable`: Dịch vụ xác thực chưa được cấu hình.
    -   (Nếu có lỗi khác, API sẽ cố gắng trả về các gợi ý mặc định)

### 21. Lấy Cuộc Hội thoại Gần đây Nhất

-   **Endpoint:** `GET /latest-conversation`
-   **Mô tả:** Lấy thông tin và tin nhắn của cuộc hội thoại gần đây nhất có tin nhắn của người dùng hiện tại.
-   **Xác thực:** Yêu cầu (Bearer Token - `get_current_user`).
-   **Đầu vào:** Không có.
-   **Đầu ra (Thành công - 200):** `LatestConversationResponse`
    Ví dụ (nếu tìm thấy):
    ```json
    {
        "conversation_info": {
            "conversation_id": "conv_id_recent",
            "user_id": "user_id_1",
            "last_updated": "2023-10-28T12:00:00Z"
            // ... các thông tin khác của conversation
        },
        "messages": [
            {"role": "user", "content": "Câu hỏi cuối cùng của tôi là gì?", "sequence": 1 /* ... các trường khác */},
            {"role": "ai", "content": "Đây là câu trả lời...", "sequence": 2 /* ... các trường khác */}
        ],
        "found": true
    }
    ```
    Ví dụ (nếu không tìm thấy hoặc có lỗi):
    ```json
    {
        "conversation_info": {},
        "messages": [],
        "found": false
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `401 Unauthorized`: Nếu không có thông tin xác thực hoặc token không hợp lệ.
    -   `503 Service Unavailable`: Dịch vụ xác thực chưa được cấu hình.
    -   (Nếu có lỗi khác, API sẽ trả về `found: false`)

### 22. Quên Mật khẩu (Forgot Password)

-   **Endpoint:** `POST /auth/forgot-password`
-   **Mô tả:** Gửi email đặt lại mật khẩu cho người dùng. Người dùng sẽ nhận email chứa liên kết để đặt lại mật khẩu.
-   **Xác thực:** Không yêu cầu.
-   **Đầu vào:**
    -   **Request Body:** `ForgotPasswordRequest`
-   **Đầu ra (Thành công - 200):** `ForgotPasswordResponse` (hoặc JSON tương tự)
    ```json
    {
        "status": "success",
        "message": "Yêu cầu đặt lại mật khẩu đã được gửi đến email của bạn."
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Lỗi khi gửi email (ví dụ: email không hợp lệ).
    -   `500 Internal Server Error`: Lỗi từ Supabase khi gửi email (ví dụ: "Error sending reset password email...").
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.

### 23. Đặt lại mật khẩu (Reset Password - Qua Email Token)

-   **Endpoint:** `POST /auth/reset-password`
-   **Mô tả:** Đặt lại mật khẩu mới cho người dùng sử dụng token xác thực nhận được từ email (sau khi yêu cầu qua `/auth/forgot-password`).
-   **Xác thực:** Không yêu cầu trực tiếp, nhưng `access_token` trong body phải hợp lệ.
-   **Đầu vào:**
    -   **Request Body:** `ResetPasswordRequest`
-   **Đầu ra (Thành công - 200):**
    ```json
    {
        "status": "success",
        "message": "Mật khẩu đã được đặt lại thành công"
        // "user": { ... } // API hiện tại không trả về thông tin user ở đây
    }
    ```
-   **Lỗi có thể xảy ra:**
    -   `400 Bad Request`: Không thể đặt lại mật khẩu. Các lý do có thể bao gồm:
        -   "Mật khẩu mới phải khác mật khẩu cũ"
        -   "Lỗi: [chi tiết lỗi từ Supabase, ví dụ: Invalid token, Password should be at least 6 characters, etc.]"
        -   "Mật khẩu phải có ít nhất 8 ký tự" (Validator của Pydantic)
        -   "Mật khẩu phải có ít nhất một chữ cái viết hoa" (Validator của Pydantic)
        -   ... (các validator khác của Pydantic cho mật khẩu)
    -   `401 Unauthorized`: Nếu `access_token` không hợp lệ hoặc đã hết hạn (ví dụ: "Token không hợp lệ hoặc đã hết hạn").
    -   `500 Internal Server Error`: Lỗi không xác định khi đặt lại mật khẩu.
    -   `503 Service Unavailable`: Dịch vụ xác thực (Supabase) chưa được cấu hình.


---
Lưu ý:
- Endpoint `/conversations` (GET) hiện tại có 2 định nghĩa trong `src/api.py`. Tài liệu này mô tả phiên bản `get_user_conversations` (lấy hội thoại của user hiện tại với phân trang, tin nhắn đầu tiên và số lượng tin nhắn). Phiên bản `get_all_conversations` cũng lấy của user hiện tại nhưng cách phân trang và lấy dữ liệu hơi khác. Cần làm rõ hoặc hợp nhất hai endpoint này trong code. Hiện tại, tài liệu ưu tiên mô tả `get_user_conversations` vì có vẻ đầy đủ hơn.
- Các model như `SQLAnalysisRequest`, `SQLAnalysisResponse`, `IndexingStatusResponse`, `CategoryStatsResponse`, `ConversationRequest` tuy được định nghĩa trong `src/api.py` nhưng không có endpoint nào sử dụng chúng trực tiếp như request body hoặc response model chính thức, nên chúng không được đưa vào phần "API Endpoints" chi tiết, chỉ được liệt kê trong "Các Model Dữ liệu".
- Các mô tả lỗi đã được cập nhật để phản ánh các thông báo lỗi chi tiết hơn từ API và các validator của Pydantic.
- Endpoint "Reset Collection" và "Xóa Điểm Dữ liệu theo Filter" đã được làm rõ là chúng hoạt động trên collection của người dùng hiện tại, được xác định thông qua `get_current_user`.
