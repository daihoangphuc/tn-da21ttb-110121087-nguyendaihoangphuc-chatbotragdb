# Hệ thống Hỏi đáp Thông minh (RAG) cho Cơ sở dữ liệu

## 1. Tổng quan

Đây là một hệ thống Retrieval-Augmented Generation (RAG) được xây dựng để trả lời các câu hỏi phức tạp liên quan đến cơ sở dữ liệu, SQL và các chủ đề liên quan. Hệ thống sử dụng mô hình ngôn ngữ lớn (LLM) và kỹ thuật embedding để cung cấp câu trả lời chính xác, đi kèm với nguồn trích dẫn từ tài liệu của bạn.

Dự án bao gồm:
-   **Backend**: API xây dựng bằng FastAPI (Python).
-   **Frontend**: Giao diện người dùng hiện đại bằng Next.js (TypeScript).
-   **Cơ sở dữ liệu**: Supabase được sử dụng để xác thực, lưu trữ dữ liệu người dùng và file.

## 2. Tính năng chính

-   **Hỏi đáp thông minh**: Trả lời câu hỏi dựa trên nội dung tài liệu được tải lên.
-   **Quản lý hội thoại**: Lưu trữ, xem lại và tìm kiếm lịch sử các cuộc hội thoại.
-   **Quản lý tài liệu (Admin)**: Tải lên, quản lý và xóa các file tài liệu (PDF, DOCX, TXT, SQL).
-   **Quản lý người dùng (Admin)**: Quản lý danh sách người dùng, vai trò và quyền hạn.
-   **Xác thực & Phân quyền**: Hỗ trợ đăng ký/đăng nhập, phân quyền `Admin` và `Student`.
-   **Giao diện hiện đại**: Hỗ trợ Dark/Light mode, responsive và thân thiện với người dùng.

## 3. Yêu cầu cài đặt

Để chạy dự án này, bạn cần cài đặt các công cụ sau trên máy của mình:

-   **Python** (phiên bản 3.9+).
-   **Node.js** (phiên bản 18.x trở lên).
-   **pnpm**: Trình quản lý gói cho Node.js. Cài đặt bằng lệnh:
    ```bash
    npm install -g pnpm
    ```
-   **(Tùy chọn) Docker**: Để chạy ứng dụng thông qua container.

## 4. Hướng dẫn Cài đặt và Chạy thử

### Bước 1: Cấu hình Biến môi trường

Ứng dụng yêu cầu một số biến môi trường để kết nối với các dịch vụ bên ngoài như Supabase và các nhà cung cấp LLM.

1.  Tạo một file tên là `.env` ở thư mục gốc của dự án.
2.  Sao chép nội dung từ file `.env.example` (nếu có) hoặc tự thêm các biến cần thiết. Các biến quan trọng bao như GEMINI_API_KEY, QDRANT_URL, QDRANT_API_KEY, SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY,...

KHI KẾT NỐI MỚI ĐẾN SUPABASE CẦN
1. Lấy các key 
2. Chạy code này để setup các bảng ban đầu (src\scripts\supabase_first_setup.sql)
3. Tắt xác nhận email khi đăng ký tài khoản (để tiện cho test nhanh)
4. Lấy client ID và secret key của google để auth với google (nếu muốn có thể auth với Google)

### Bước 2: Cài đặt và Chạy Backend

Backend được xây dựng bằng Python và FastAPI.

1.  **Mở terminal** và di chuyển đến thư mục gốc của dự án.

2.  **Tạo môi trường ảo** cho Python:
    ```bash
    python -m venv venv
    ```

3.  **Kích hoạt môi trường ảo**:
    -   Trên Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    -   Trên macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

4.  **Cài đặt các thư viện** cần thiết:
    ```bash
    pip install -r requirements.txt
    ```

5.  **Chạy máy chủ API**:
    ```bash
    uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
    ```
    API backend bây giờ sẽ chạy tại `http://localhost:8000`.

### Bước 3: Cài đặt và Chạy Frontend

Frontend được xây dựng bằng Next.js.

1.  **Mở một terminal mới** và di chuyển vào thư mục `frontend`:
    ```bash
    cd frontend
    ```

2.  **Cài đặt các dependencies** bằng `pnpm`:
    ```bash
    pnpm install
    ```

3.  **Chạy ứng dụng frontend** ở chế độ development:
    ```bash
    pnpm dev
    ```
    Giao diện người dùng bây giờ sẽ có thể truy cập tại `http://localhost:3000`.

## 5. Hướng dẫn sử dụng Demo

Sau khi đã khởi động thành công cả backend và frontend, bạn có thể bắt đầu trải nghiệm ứng dụng.

### Đăng ký tài khoản

1.  Truy cập `http://localhost:3000`.
2.  Nhấn vào nút "Đăng ký" và tạo một tài khoản mới bằng email và mật khẩu.
3.  Sau khi đăng ký, bạn sẽ được tự động đăng nhập với vai trò mặc định là `Student`.

### Cấp quyền Admin

Để sử dụng các tính năng quản trị như tải lên tài liệu và quản lý người dùng, bạn cần có vai trò `Admin`.

1.  **Đăng ký một tài khoản** mà bạn muốn cấp quyền admin (ví dụ: `admin@example.com`).
2.  **Cách 1: Sử dụng SQL trong Supabase Studio**:
    -   Truy cập vào Supabase project của bạn.
    -   Đi đến mục **SQL Editor**.
    -   Chạy câu lệnh sau để cấp quyền admin cho email đã đăng ký:
        ```sql
        SELECT public.create_admin_from_email('admin@example.com');
        ```
        Thay `'admin@example.com'` bằng email của bạn.

3.  Đăng xuất và đăng nhập lại để hệ thống cập nhật vai trò mới. Giao diện Admin sẽ xuất hiện trong sidebar.

### Các tính năng chính để Demo

-   **Hỏi đáp**:
    -   Vào trang chủ, nhập câu hỏi vào ô chat và nhấn gửi.
    -   Hệ thống sẽ trả về câu trả lời cùng với các nguồn đã trích dẫn.

-   **Quản lý tài liệu (Admin)**:
    -   Trong giao diện Admin, điều hướng đến mục "Quản lý tài liệu".
    -   Nhấn nút "Tải lên" để thêm các file tài liệu mới (PDF, DOCX, TXT). Hệ thống sẽ tự động xử lý và index chúng.
    -   Bạn cũng có thể xóa các tài liệu đã tải lên.

-   **Tìm kiếm hội thoại**:
    -   Sử dụng tab "Tìm kiếm" trong sidebar để tìm kiếm nội dung trong các cuộc hội thoại cũ theo từ khóa hoặc khoảng thời gian.
