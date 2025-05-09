// chat.js - Quản lý giao diện và chức năng chat

// Khởi tạo UI
function initializeChatUI() {
    console.log('Khởi tạo chat UI');
    
    // Xử lý nút xóa hội thoại
    const clearChatBtn = document.getElementById('clear-chat-btn');
    if (clearChatBtn) {
        clearChatBtn.addEventListener('click', clearConversation);
        console.log('Đã đăng ký sự kiện cho nút xóa hội thoại');
    } else {
        console.error('Không tìm thấy nút xóa hội thoại');
    }
}

// Xóa hội thoại hiện tại
function clearConversation() {
    if (confirm('Bạn có chắc chắn muốn xóa toàn bộ hội thoại hiện tại?')) {
        // Xóa hội thoại trên server
        apiService.resetSession()
            .then(() => {
                // Xóa giao diện chat
                const chatMessages = document.getElementById('messagesContainer');
                chatMessages.innerHTML = '';
                
                // Thêm tin nhắn chào mừng
                const welcomeMessage = createSystemMessage(
                    'Chào mừng bạn đến với hệ thống RAG! Bạn có thể đặt câu hỏi về các tài liệu đã tải lên.'
                );
                chatMessages.appendChild(welcomeMessage);
                
                // Thông báo
                showNotification('Đã xóa hội thoại thành công!', 'success');
            })
            .catch(error => {
                console.error('Lỗi khi xóa hội thoại:', error);
                showNotification('Có lỗi xảy ra khi xóa hội thoại', 'error');
            });
    }
}

// Tạo tin nhắn hệ thống
function createSystemMessage(content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message system-message';
    
    messageDiv.innerHTML = `
        <div class="avatar message-avatar">
            <i class="fas fa-info-circle"></i>
        </div>
        <div class="message-content">
            <p>${content}</p>
        </div>
    `;
    
    return messageDiv;
}

// Hiển thị thông báo
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Hiệu ứng hiển thị
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Tự động ẩn sau 5 giây
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 5000);
}

// Khi trang được tải, tự động khởi tạo UI
document.addEventListener('DOMContentLoaded', function() {
    // Gọi hàm khởi tạo UI
    initializeChatUI();
}); 