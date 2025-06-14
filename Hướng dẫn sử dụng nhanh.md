# Hướng dẫn sử dụng Chatbot Cơ sở dữ liệu

Chào mừng bạn đến với Chatbot Cơ sở dữ liệu! Chatbot này được thiết kế để giúp bạn tìm kiếm thông tin và trả lời các câu hỏi liên quan đến môn học Cơ sở dữ liệu, dựa trên tài liệu được cung cấp.

## 1. Truy cập Chatbot

*   Bạn có thể truy cập chatbot qua đường dẫn sau: [http://34.30.191.213:3000](http://34.30.191.213:3000)
    *   *(Hình ảnh minh họa: Trang chủ của chatbot - tương tự #README.md dòng 153)*

## 2. Tải và Chọn Tài liệu Nguồn

Chatbot sẽ trả lời câu hỏi dựa trên nội dung của các tài liệu bạn cung cấp và lựa chọn.

*   **Đối với buổi thử nghiệm này:** Chúng ta sẽ tập trung vào tài liệu **"Hệ_QT_CSDl.pdf"**.
    *   **Trường hợp 1: Tài liệu đã được nạp sẵn:** Nếu tài liệu "Hệ_QT_CSDl.pdf" đã có sẵn trong danh sách "Nguồn tài liệu" ở cột bên trái, bạn chỉ cần **đánh dấu tick** vào tài liệu đó để chatbot sử dụng làm cơ sở kiến thức.
    *   **Trường hợp 2: Tải tài liệu mới:**
        1.  Trong panel "Nguồn tài liệu" (thường ở bên trái giao diện), nhấn vào nút **"Thêm"** hoặc biểu tượng tương tự để mở hộp thoại tải lên tài liệu.
            *   *(Hình ảnh minh họa: Panel Nguồn và nút Thêm - dựa trên #README.md dòng 133, 159)*
        2.  Chọn file **"Hệ_QT_CSDl.pdf"** từ máy tính của bạn và tải lên.
        3.  Sau khi tải lên thành công, tài liệu sẽ xuất hiện trong danh sách. Hãy **đánh dấu tick** vào tài liệu "Hệ_QT_CSDl.pdf" để chatbot sử dụng.

*   **Lưu ý:** Bạn có thể chọn một hoặc nhiều tài liệu để chatbot sử dụng. Câu trả lời sẽ được tổng hợp từ các tài liệu được chọn.

## 3. Đặt câu hỏi

*   Sau khi đã chọn tài liệu nguồn, bạn có thể bắt đầu đặt câu hỏi.
*   Nhập câu hỏi của bạn vào ô văn bản ở phía dưới cùng của khu vực hội thoại.
*   Nhấn phím **Enter** hoặc nhấp vào nút **"Gửi"** (hoặc biểu tượng tương tự) để gửi câu hỏi.
    *   *(Hình ảnh minh họa: Khu vực hội thoại với ô nhập câu hỏi - tương tự #README.md dòng 156)*

## 4. Xem Câu trả lời và Nguồn trích dẫn

*   Chatbot sẽ xử lý câu hỏi và hiển thị câu trả lời trong khu vực hội thoại.
*   **Nguồn trích dẫn:**
    *   Trong câu trả lời, bạn sẽ thấy các thông tin được trích dẫn nguồn cụ thể. Thông thường, trích dẫn sẽ có dạng `(trang X, Tên_File.pdf)`. Ví dụ: "... SQL Server là một hệ quản trị cơ sở dữ liệu quan hệ (trang 20, Hệ_QT_CSDl.pdf)."
    *   Một số câu trả lời có thể hiển thị danh sách các nguồn tham khảo ở cuối, bao gồm tên file, số trang và mức độ liên quan. Bạn có thể nhấp vào các nguồn này (nếu giao diện hỗ trợ) để xem chi tiết hơn.
    *   *(Hình ảnh minh họa: Câu trả lời của chatbot với trích dẫn nguồn - dựa trên mô tả và ví dụ trong #frontend/components/chat-interface.tsx dòng 453)*

## 5. Lưu ý Quan trọng về Phạm vi Kiến thức

*   **Chatbot chỉ trả lời dựa trên nội dung có trong (các) tài liệu bạn đã tải lên và chọn.**
*   Nó **KHÔNG** sử dụng kiến thức bên ngoài internet hoặc kiến thức chưa được cung cấp trong tài liệu.
*   Nếu thông tin không có hoặc không đầy đủ trong tài liệu, chatbot có thể sẽ thông báo rằng không tìm thấy thông tin hoặc chỉ cung cấp thông tin giới hạn. Ví dụ: "Tôi không thể trả lời đầy đủ câu hỏi này dựa trên tài liệu hiện có. Thông tin về [chủ đề] không được tìm thấy trong tài liệu được cung cấp."
*   Mục tiêu của chatbot là giúp bạn khai thác thông tin hiệu quả từ chính tài liệu học tập của mình.

Chúc bạn có một trải nghiệm hữu ích với chatbot! Nếu có bất kỳ thắc mắc nào trong quá trình sử dụng, đừng ngần ngại hỏi người hướng dẫn.