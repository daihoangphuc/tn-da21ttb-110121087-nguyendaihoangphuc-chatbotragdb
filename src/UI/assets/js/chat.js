// chat.js - Quản lý giao diện và chức năng chat

// Lấy hoặc thiết lập API_BASE_URL như một thuộc tính của window
window.API_BASE_URL = window.apiService ? window.apiService.baseUrl : 'http://localhost:8000';

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

// Thêm biến để theo dõi tab hiện tại
let currentTab = 'sources';

// Hàm xử lý chuyển tab
function switchTab(tabName) {
    // Cập nhật tab hiện tại
    currentTab = tabName;
    
    // Bỏ active tất cả các tab button
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
        btn.classList.remove('text-blue-600');
        btn.classList.remove('border-b-2');
        btn.classList.remove('border-blue-600');
        btn.classList.add('text-gray-500');
    });
    
    // Active tab button được chọn
    const selectedBtn = document.getElementById(`${tabName}TabBtn`);
    if (selectedBtn) {
        selectedBtn.classList.add('active');
        selectedBtn.classList.add('text-blue-600');
        selectedBtn.classList.add('border-b-2');
        selectedBtn.classList.add('border-blue-600');
        selectedBtn.classList.remove('text-gray-500');
    }

    // Hiển thị nội dung tab được chọn mà không ẩn các tab khác
    const selectedTab = document.getElementById(`${tabName}TabContent`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Load dữ liệu nếu là tab lịch sử
    if (tabName === 'history') {
        loadConversations();
    }
}

// Hàm load danh sách hội thoại
async function loadConversations() {
    try {
        console.log('Đang tải danh sách hội thoại...');
        
        // Hiển thị trạng thái đang tải
        const historyList = document.getElementById('historyList');
        historyList.innerHTML = `
            <div class="loading-message text-center py-4">
                <i class="fas fa-spinner fa-spin mr-2"></i>
                Đang tải danh sách hội thoại...
            </div>
        `;
        
        // Lấy token xác thực
        let authToken = sessionStorage.getItem('auth_token');
        if (!authToken) {
            console.error('Không tìm thấy token xác thực');
            historyList.innerHTML = `
                <div class="error-message text-red-500 text-center py-4">
                    <i class="fas fa-exclamation-circle mr-2"></i>
                    Vui lòng đăng nhập lại để xem lịch sử hội thoại.
                </div>
            `;
            return;
        }
        
        // Đảm bảo token không có tiền tố "Bearer" trùng lặp
        if (authToken.startsWith('Bearer ')) {
            authToken = authToken.substring(7);
        }
        
        console.log('Token được sử dụng (loadConversations):', authToken.substring(0, 15) + '...');
        
        // Gọi API trực tiếp
        const apiURL = `${window.API_BASE_URL}/api/conversations`;
        console.log('Gọi API lấy danh sách hội thoại trực tiếp:', apiURL);
        
        const response = await fetch(apiURL, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`Lỗi API (${response.status}):`, errorText);
            
            // Xử lý lỗi 403 - Forbidden hoặc 401 - Unauthorized
            if (response.status === 403 || response.status === 401) {
                console.error(`Lỗi ${response.status}: Không có quyền truy cập hoặc token hết hạn`);
                
                historyList.innerHTML = `
                    <div class="error-message text-center py-4">
                        <i class="fas fa-exclamation-triangle text-yellow-500 text-xl mb-2"></i>
                        <p class="text-red-500">Lỗi quyền truy cập (${response.status})</p>
                        <p class="text-gray-500 text-sm">Phiên đăng nhập có thể đã hết hạn</p>
                        <button class="btn btn-primary mt-3" id="refreshLoginBtn">Đăng nhập lại</button>
                    </div>
                `;
                
                // Thêm sự kiện cho nút đăng nhập lại
                const refreshLoginBtn = document.getElementById('refreshLoginBtn');
                if (refreshLoginBtn) {
                    refreshLoginBtn.addEventListener('click', () => {
                        window.location.href = 'login.html';
                    });
                }
                
                return;
            }
            
            historyList.innerHTML = `
                <div class="error-message text-red-500 text-center py-4">
                    <i class="fas fa-exclamation-circle mr-2"></i>
                    Không thể tải danh sách hội thoại: ${response.status} ${response.statusText}
                </div>
            `;
            return;
        }
        
        const result = await response.json();
        console.log('Kết quả từ API conversations:', result);
        
        // Kiểm tra nếu API trả về lỗi
        if (result.status === 'error') {
            console.error('API trả về lỗi:', result.message);
            historyList.innerHTML = `
                <div class="error-message text-red-500 text-center py-4">
                    <i class="fas fa-exclamation-circle mr-2"></i>
                    Lỗi từ server: ${result.message}
                </div>
            `;
            return;
        }
        
        // Xóa nội dung cũ
        historyList.innerHTML = '';

        if (!result || !result.data || result.data.length === 0) {
            // Hiển thị thông báo khi không có hội thoại nào
            historyList.innerHTML = `
                <div class="empty-history-message flex flex-col items-center justify-center h-full py-12">
                    <div class="bg-gray-100 rounded-full p-4 mb-4">
                        <i class="fas fa-history text-3xl text-gray-400"></i>
                    </div>
                    <p class="text-gray-500 text-center">Chưa có cuộc trò chuyện nào</p>
                    <p class="text-gray-400 text-sm text-center mt-2">Bắt đầu cuộc trò chuyện mới bằng cách nhấp vào "Tạo mới"</p>
                </div>
            `;
            return;
        }

        // Tạo danh sách các hội thoại
        result.data.forEach(conversation => {
            // Kiểm tra session_id hợp lệ
            if (!conversation.session_id) {
                console.error('Hội thoại thiếu session_id:', conversation);
                return; // Bỏ qua hội thoại không có session_id
            }
            
            const conversationElement = document.createElement('div');
            conversationElement.className = 'history-item flex items-center justify-between p-2 hover:bg-gray-100 rounded-lg cursor-pointer';
            conversationElement.dataset.sessionId = conversation.session_id; // Thêm session_id vào dataset
            
            // Format thời gian
            let lastUpdated;
            try {
                lastUpdated = new Date(conversation.last_updated).toLocaleString('vi-VN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            } catch (e) {
                console.warn('Lỗi định dạng thời gian:', e);
                lastUpdated = 'Không rõ';
            }
            
            // Tạo tiêu đề an toàn
            const safeTitle = conversation.first_message ? 
                conversation.first_message.substring(0, 30) + (conversation.first_message.length > 30 ? '...' : '') : 
                'Cuộc trò chuyện mới';
            
            const messageCount = conversation.message_count || 0;
            
            conversationElement.innerHTML = `
                <div class="flex-1 cursor-pointer">
                    <div class="font-medium text-gray-900 truncate">${safeTitle}</div>
                    <div class="text-sm text-gray-500">
                        ${lastUpdated} · ${messageCount} tin nhắn
                    </div>
                </div>
                <button class="delete-conversation-btn text-red-600 hover:text-red-800 p-2">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            
            // Thêm sự kiện click cho toàn bộ phần tử
            conversationElement.querySelector('.flex-1').addEventListener('click', function() {
                console.log('Click vào hội thoại:', conversation.session_id);
                loadConversation(conversation.session_id);
            });
            
            // Thêm sự kiện xóa riêng cho từng nút
            const deleteButton = conversationElement.querySelector('.delete-conversation-btn');
            deleteButton.addEventListener('click', function(event) {
                event.stopPropagation();
                console.log('Xóa hội thoại:', conversation.session_id);
                deleteConversation(conversation.session_id);
            });
            
            historyList.appendChild(conversationElement);
        });
    } catch (error) {
        console.error('Lỗi khi tải danh sách hội thoại:', error);
        const historyList = document.getElementById('historyList');
        historyList.innerHTML = `
            <div class="error-message text-red-500 text-center py-4">
                <i class="fas fa-exclamation-circle mr-2"></i>
                Không thể tải danh sách hội thoại: ${error.message}
            </div>
        `;
    }
}

// Hàm tạo hội thoại mới
async function createNewConversation() {
    try {
        // Sử dụng phương thức createConversation của apiService thay vì post
        const response = await apiService.createConversation();
        
        if (response && response.status === 'success' && response.data && response.data.session_id) {
            // Lưu session_id mới
            currentSessionId = response.data.session_id;
            
            // Xóa tin nhắn cũ trong giao diện
            const messagesContainer = document.getElementById('messagesContainer');
            messagesContainer.innerHTML = `
                <div class="welcome-message">
                    <p>Chào mừng bạn đến với hệ thống RAG hỗ trợ môn cơ sở dữ liệu! Hãy đặt câu hỏi về tài liệu của bạn.</p>
                    <p>Ví dụ: "Phân biệt giữa INNER JOIN và LEFT JOIN trong SQL?" hay "Cho tôi ví dụ về một câu truy vấn nested."</p>
                </div>
            `;
            
            // Cập nhật danh sách hội thoại
            await loadConversations();
        } else {
            console.error('Lỗi: Không thể tạo hội thoại mới, response không hợp lệ', response);
            showNotification('Không thể tạo hội thoại mới', 'error');
        }
    } catch (error) {
        console.error('Lỗi khi tạo hội thoại mới:', error);
        showNotification('Không thể tạo hội thoại mới', 'error');
    }
}

// Hàm xóa hội thoại
async function deleteConversation(sessionId) {
    // Kiểm tra sessionId hợp lệ
    if (!sessionId || sessionId === 'undefined' || sessionId === 'null') {
        console.error('Không thể xóa hội thoại: ID không hợp lệ', sessionId);
        showNotification('Không thể xóa hội thoại: ID không hợp lệ', 'error');
        return;
    }

    if (!confirm('Bạn có chắc chắn muốn xóa cuộc trò chuyện này?')) {
        return;
    }

    try {
        console.log('Đang xóa hội thoại với ID:', sessionId);
        
        // Hiển thị trạng thái đang xóa trên nút (nếu có)
        const deleteBtn = document.querySelector(`.delete-conversation-btn[onclick*="${sessionId}"]`);
        if (deleteBtn) {
            deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            deleteBtn.disabled = true;
        }
        
        // Lấy token để xác thực
        let authToken = sessionStorage.getItem('auth_token');
        if (!authToken) {
            console.error('Không tìm thấy token xác thực');
            showNotification('Vui lòng đăng nhập lại để tiếp tục', 'error');
            return;
        }
        
        // Đảm bảo token không có tiền tố "Bearer" trùng lặp
        if (authToken.startsWith('Bearer ')) {
            authToken = authToken.substring(7);
        }
        
        console.log('Token được sử dụng (deleteConversation):', authToken.substring(0, 15) + '...');
        
        // Gọi API trực tiếp
        const apiURL = `${window.API_BASE_URL}/api/conversations/${sessionId}`;
        console.log('Gọi API xóa trực tiếp:', apiURL);
        
        const response = await fetch(apiURL, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            }
        });
        
        // Xử lý các trường hợp lỗi
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`Lỗi API (${response.status}):`, errorText);
            
            // Xử lý lỗi 403 - Forbidden hoặc 401 - Unauthorized
            if (response.status === 403 || response.status === 401) {
                console.error(`Lỗi ${response.status}: Không có quyền truy cập hoặc token hết hạn`);
                showNotification(`Lỗi quyền truy cập (${response.status}): Phiên đăng nhập có thể đã hết hạn`, 'error');
                
                // Khôi phục nút xóa
                if (deleteBtn) {
                    deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
                    deleteBtn.disabled = false;
                }
                
                // Hiển thị hộp thoại xác nhận đăng nhập lại
                if (confirm('Phiên đăng nhập có thể đã hết hạn. Bạn có muốn đăng nhập lại không?')) {
                    window.location.href = 'login.html';
                }
                
                return;
            }
            
            showNotification(`Không thể xóa hội thoại: ${response.status} ${response.statusText}`, 'error');
            
            // Khôi phục nút xóa
            if (deleteBtn) {
                deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
                deleteBtn.disabled = false;
            }
            
            return;
        }
        
        let result;
        try {
            result = await response.json();
        } catch (e) {
            console.warn('Không thể parse JSON từ response:', e);
            // Nếu không parse được JSON, giả định là thành công
            result = { success: true };
        }
        
        console.log('Kết quả xóa hội thoại:', result);
        
        if (response.ok && (result.success === true || result.status === 'success')) {
            // Nếu đang ở hội thoại bị xóa, tạo hội thoại mới
            if (currentSessionId === sessionId) {
                await createNewConversation();
            }
            
            // Cập nhật danh sách hội thoại
            await loadConversations();
            
            showNotification('Đã xóa hội thoại thành công', 'success');
        } else {
            // Xử lý lỗi từ server
            const errorMessage = result.error || result.message || 'Không thể xóa hội thoại';
            console.error('Lỗi từ server:', errorMessage);
            showNotification(errorMessage, 'error');
            
            // Khôi phục nút xóa
            if (deleteBtn) {
                deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
                deleteBtn.disabled = false;
            }
        }
    } catch (error) {
        console.error('Lỗi khi xóa hội thoại:', error);
        showNotification(error.message || 'Không thể xóa hội thoại', 'error');
        
        // Khôi phục nút xóa trong trường hợp lỗi
        const deleteBtn = document.querySelector(`.delete-conversation-btn[onclick*="${sessionId}"]`);
        if (deleteBtn) {
            deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
            deleteBtn.disabled = false;
        }
    }
}

// Hàm load nội dung hội thoại
async function loadConversation(sessionId) {
    try {
        if (!sessionId) {
            console.error('Không thể tải hội thoại: ID không hợp lệ');
            showNotification('Không thể tải hội thoại: ID không hợp lệ', 'error');
            return;
        }
        
        console.log('Đang tải nội dung hội thoại:', sessionId);
        
        // Chuyển tab từ Lịch sử sang tab Tin nhắn
        if (currentTab === 'history') {
            // Hiển thị phần hội thoại mà không ẩn tab history
            const conversationPanel = document.getElementById('conversationPanel');
            const historyTabContent = document.getElementById('historyTabContent');
            
            if (conversationPanel) {
                conversationPanel.classList.add('active');
            }
            
            // Giữ nguyên hiển thị của tab history
            if (historyTabContent) {
                historyTabContent.classList.add('active');
            }
        }
        
        // Hiển thị trạng thái đang tải
        const messagesContainer = document.getElementById('messagesContainer');
        messagesContainer.innerHTML = `
            <div class="loading-message text-center py-4">
                <i class="fas fa-spinner fa-spin mr-2"></i>
                Đang tải nội dung hội thoại...
            </div>
        `;
        
        // Lưu session_id hiện tại
        currentSessionId = sessionId;
        sessionStorage.setItem('rag_session_id', sessionId);
        
        // Cập nhật UI để hiển thị session_id hiện tại
        const conversationMeta = document.getElementById('conversationMeta');
        if (conversationMeta) {
            conversationMeta.textContent = `Hội thoại: ${sessionId.substring(0, 8)}...`;
        }
        
        // Lấy token xác thực
        let authToken = sessionStorage.getItem('auth_token');
        if (!authToken) {
            console.error('Không tìm thấy token xác thực');
            showNotification('Vui lòng đăng nhập lại để tiếp tục', 'error');
            return;
        }
        
        // Đảm bảo token không có tiền tố "Bearer" trùng lặp
        if (authToken.startsWith('Bearer ')) {
            authToken = authToken.substring(7);
        }
        
        console.log('Token được sử dụng:', authToken.substring(0, 15) + '...');
        
        // Gọi API trực tiếp để lấy tin nhắn
        const apiURL = `${window.API_BASE_URL}/api/messages?session_id=${sessionId}`;
        console.log('Gọi API lấy tin nhắn trực tiếp:', apiURL);
        
        const response = await fetch(apiURL, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`Lỗi API (${response.status}):`, errorText);
            
            // Xử lý lỗi 403 - Forbidden
            if (response.status === 403) {
                console.error('Lỗi 403: Không có quyền truy cập vào hội thoại này');
                messagesContainer.innerHTML = `
                    <div class="error-message text-center py-4">
                        <i class="fas fa-exclamation-triangle text-yellow-500 text-xl mb-2"></i>
                        <p class="text-red-500">Lỗi quyền truy cập (403)</p>
                        <p class="text-gray-500 text-sm">Bạn không có quyền xem hội thoại này hoặc token đã hết hạn</p>
                        <button class="btn btn-primary mt-3" onclick="window.location.href='login.html'">Đăng nhập lại</button>
                    </div>
                `;
                return;
            }
            
            // Xử lý các lỗi khác
            showNotification(`Không thể tải hội thoại: ${response.status} ${response.statusText}`, 'error');
            messagesContainer.innerHTML = `
                <div class="error-message text-center py-4">
                    <i class="fas fa-exclamation-circle text-red-500 text-xl mb-2"></i>
                    <p class="text-red-500">Lỗi ${response.status}: ${response.statusText}</p>
                    <p class="text-gray-500 text-sm">${errorText}</p>
                </div>
            `;
            return;
        }
        
        const result = await response.json();
        console.log('Kết quả lấy tin nhắn:', result);
        
        // Kiểm tra nếu API trả về lỗi
        if (result.status === 'error') {
            console.error('API trả về lỗi:', result.message);
            showNotification(`Lỗi: ${result.message}`, 'error');
            messagesContainer.innerHTML = `
                <div class="error-message text-center py-4">
                    <i class="fas fa-exclamation-circle text-red-500 text-xl mb-2"></i>
                    <p class="text-red-500">Lỗi từ server</p>
                    <p class="text-gray-500 text-sm">${result.message}</p>
                </div>
            `;
            return;
        }
        
        // Xóa tin nhắn cũ trong giao diện
        messagesContainer.innerHTML = '';
        
        // Kiểm tra nếu không có tin nhắn nào
        if (!result.data || result.data.length === 0) {
            messagesContainer.innerHTML = `
                <div class="welcome-message">
                    <p>Chào mừng bạn đến với hội thoại mới!</p>
                    <p>Hãy đặt câu hỏi về tài liệu của bạn.</p>
                </div>
            `;
            return;
        }
        
        // Hiển thị các tin nhắn
        result.data.forEach(message => {
            const messageElement = document.createElement('div');
            messageElement.className = `message ${message.role}-message`;
            
            let avatarHTML = '';
            let contentHTML = '';
            
            // Xử lý avatar và nội dung dựa vào role
            if (message.role === 'assistant') {
                avatarHTML = '<div class="avatar message-avatar"><i class="fas fa-robot"></i></div>';
                
                // Xử lý nội dung tin nhắn của assistant
                contentHTML = `<div class="message-content">`;
                
                // Chuyển đổi Markdown thành HTML
                contentHTML += `<div class="markdown-content">${marked.parse(message.content)}</div>`;
                
                // Thêm nguồn tham khảo nếu có
                if (message.metadata && message.metadata.sources && message.metadata.sources.length > 0) {
                    contentHTML += `
                        <div class="message-sources mt-3">
                            <div class="sources-header">
                                <span class="sources-toggle" onclick="toggleSources(this)">
                                    <i class="fas fa-book mr-1"></i>
                                    Nguồn tham khảo (${message.metadata.sources.length})
                                    <i class="fas fa-chevron-down ml-1"></i>
                                </span>
                            </div>
                            <div class="sources-content hidden">
                                <ul class="sources-list">
                    `;
                    
                    message.metadata.sources.forEach((source, index) => {
                        const sourceName = source.source ? source.source.split('/').pop() : 'Nguồn không xác định';
                        const score = source.score ? Math.round(source.score * 100) / 100 : '';
                        const scoreText = score ? `(Điểm: ${score})` : '';
                        
                        contentHTML += `
                            <li class="source-item">
                                <div class="source-header">
                                    <strong>${index + 1}. ${sourceName}</strong> ${scoreText}
                                </div>
                                <div class="source-content">
                                    ${source.content || ''}
                                </div>
                            </li>
                        `;
                    });
                    
                    contentHTML += `
                                </ul>
                            </div>
                        </div>
                    `;
                }
                
                contentHTML += '</div>';
            } else if (message.role === 'user') {
                avatarHTML = '<div class="avatar message-avatar"><i class="fas fa-user"></i></div>';
                contentHTML = `
                    <div class="message-content">
                        <p>${message.content}</p>
                    </div>
                `;
            }
            
            messageElement.innerHTML = avatarHTML + contentHTML;
            messagesContainer.appendChild(messageElement);
        });
        
        // Cuộn xuống tin nhắn cuối cùng
        scrollToBottom();
        
        // Cập nhật UI để chỉ ra hội thoại hiện tại
        document.querySelectorAll('.history-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.sessionId === sessionId) {
                item.classList.add('active');
            }
        });
        
        // Chuyển sang tab hội thoại nếu đang ở trên mobile
        if (window.innerWidth < 768) {
            const conversationPanel = document.getElementById('conversationPanel');
            if (conversationPanel) {
                // Hiển thị panel hội thoại
                document.querySelectorAll('.main-interface > div').forEach(panel => {
                    panel.classList.remove('active');
                });
                conversationPanel.classList.add('active');
                
                // Cập nhật nút điều hướng mobile
                document.querySelectorAll('.nav-button').forEach(btn => {
                    btn.classList.remove('active');
                    if (btn.getAttribute('data-panel') === 'conversation') {
                        btn.classList.add('active');
                    }
                });
            }
        }
    } catch (error) {
        console.error('Lỗi khi tải nội dung hội thoại:', error);
        showNotification('Không thể tải nội dung hội thoại: ' + error.message, 'error');
        
        // Hiển thị tin nhắn lỗi trong khung chat
        const messagesContainer = document.getElementById('messagesContainer');
        messagesContainer.innerHTML = `
            <div class="error-message text-center py-4">
                <i class="fas fa-exclamation-circle text-red-500 text-xl mb-2"></i>
                <p class="text-red-500">Không thể tải nội dung hội thoại</p>
                <p class="text-gray-500 text-sm">Vui lòng thử lại sau hoặc tạo hội thoại mới</p>
            </div>
        `;
    }
}

// Thêm sự kiện cho các tab
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM đã tải xong, khởi tạo sự kiện cho các tab');

    // Thêm sự kiện cho các nút tab
    const sourcesTabBtn = document.getElementById('sourcesTabBtn');
    const historyTabBtn = document.getElementById('historyTabBtn');
    
    if (sourcesTabBtn) {
        console.log('Tìm thấy tab Sources, đăng ký sự kiện');
        sourcesTabBtn.addEventListener('click', () => switchTab('sources'));
    } else {
        console.warn('Không tìm thấy tab Sources');
    }
    
    // Không đăng ký event cho tab History ở đây vì đã được xử lý trong ChatHistoryController
    if (historyTabBtn) {
        console.log('Tìm thấy tab Lịch sử nhưng KHÔNG đăng ký sự kiện tại đây để tránh trùng lặp');
        // Event đã được đăng ký trong ChatHistoryController
    } else {
        console.warn('Không tìm thấy tab Lịch sử');
    }
    
    // Không đăng ký sự kiện cho nút tạo mới ở đây để tránh trùng lặp với ui-controllers.js
    // Việc đăng ký event cho nút tạo mới được xử lý trong ChatHistoryController
    const createNewChatBtn = document.getElementById('createNewChatBtn');
    if (createNewChatBtn) {
        console.log('Tìm thấy nút tạo mới nhưng KHÔNG đăng ký sự kiện tại đây để tránh trùng lặp');
        // Đã được đăng ký trong ui-controllers.js
    } else {
        console.warn('Không tìm thấy nút tạo mới hội thoại');
    }
    
    // Load dữ liệu cho tab hiện tại
    const historyTab = document.getElementById('historyTabContent');
    if (historyTab && historyTab.classList.contains('active')) {
        console.log('Tab Lịch sử đang active, tải danh sách hội thoại');
        loadConversations();
    }
    
    // Gọi hàm khởi tạo UI
    initializeChatUI();
}); 

// Biến để theo dõi phiên hiện tại
let currentSessionId = sessionStorage.getItem('rag_session_id') || '';

// Hàm thêm tin nhắn từ người dùng
function appendUserMessage(content) {
    const messagesContainer = document.getElementById('messagesContainer');
    
    // Tạo phần tử tin nhắn
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user-message';
    
    messageDiv.innerHTML = `
        <div class="avatar message-avatar">
            <i class="fas fa-user"></i>
        </div>
        <div class="message-content">
            <p>${content}</p>
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

// Hàm thêm tin nhắn từ AI
function appendAIMessage(content, sources = null) {
    const messagesContainer = document.getElementById('messagesContainer');
    
    // Tạo phần tử tin nhắn
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message ai-message';
    
    // Xử lý nguồn tài liệu (nếu có)
    let sourcesHTML = '';
    if (sources && Array.isArray(sources) && sources.length > 0) {
        sourcesHTML = `
            <div class="message-sources mt-3">
                <div class="sources-header">
                    <span class="sources-toggle" onclick="toggleSources(this)">
                        <i class="fas fa-book mr-1"></i> 
                        Nguồn tham khảo (${sources.length})
                        <i class="fas fa-chevron-down ml-1"></i>
                    </span>
                </div>
                <div class="sources-content hidden">
                    <ul class="sources-list">
        `;
        
        sources.forEach((source, index) => {
            const sourceName = source.source ? source.source.split('/').pop() : 'Nguồn không xác định';
            const score = source.score ? Math.round(source.score * 100) / 100 : '';
            const scoreText = score ? `(Điểm: ${score})` : '';
            
            sourcesHTML += `
                <li class="source-item">
                    <div class="source-header">
                        <strong>${index + 1}. ${sourceName}</strong> ${scoreText}
                    </div>
                    <div class="source-snippet">
                        ${source.content_snippet || source.content || 'Không có trích đoạn'}
                    </div>
                </li>
            `;
        });
        
        sourcesHTML += `
                    </ul>
                </div>
            </div>
        `;
    }
    
    // Chuyển đổi nội dung Markdown thành HTML
    let processedContent = content;
    
    // Kiểm tra xem thư viện marked có tồn tại không
    if (typeof marked !== 'undefined') {
        try {
            // Bọc bảng trong một div có lớp table-responsive để xử lý bảng quá rộng
            const renderer = new marked.Renderer();
            const originalTable = renderer.table;
            
            renderer.table = function(header, body) {
                const table = originalTable.call(this, header, body);
                return '<div class="table-responsive">' + table + '</div>';
            };
            
            marked.setOptions({
                renderer: renderer,
                gfm: true,
                breaks: true,
                sanitize: false,
                smartLists: true,
                smartypants: false,
                xhtml: false
            });
            
            processedContent = marked.parse(content);
        } catch (e) {
            console.error('Lỗi khi chuyển đổi Markdown sang HTML:', e);
            // Nếu có lỗi, sử dụng nội dung gốc
            processedContent = `<p>${content}</p>`;
        }
    } else {
        // Nếu không có thư viện marked, hiển thị nội dung gốc
        processedContent = `<p>${content}</p>`;
        console.warn('Thư viện marked.js không được tìm thấy. Nội dung Markdown sẽ không được xử lý.');
    }
    
    // Tạo nội dung HTML cho tin nhắn
    messageDiv.innerHTML = `
        <div class="avatar message-avatar">
            <i class="fas fa-robot"></i>
        </div>
        <div class="message-content markdown">
            ${processedContent}
            ${sourcesHTML}
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    
    // Áp dụng highlight.js cho các khối mã sau khi thêm vào DOM
    if (typeof hljs !== 'undefined') {
        messageDiv.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    }
    
    scrollToBottom();
    
    // Đảm bảo kích hoạt lại trường nhập
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    if (messageInput && sendButton) {
        // Đặt timeout ngắn để đảm bảo UI đã được cập nhật
        setTimeout(() => {
            messageInput.disabled = false;
            sendButton.disabled = messageInput.value.trim() === '';
            messageInput.focus();
        }, 100);
    }
}

// Hàm cuộn xuống tin nhắn cuối cùng
function scrollToBottom() {
    const messagesContainer = document.getElementById('messagesContainer');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// Hàm hiển thị/ẩn nguồn tham khảo
function toggleSources(element) {
    // Tìm phần tử cha gần nhất có class 'message-sources'
    const sourcesSection = element.closest('.message-sources');
    if (sourcesSection) {
        // Tìm phần nội dung nguồn
        const sourcesContent = sourcesSection.querySelector('.sources-content');
        if (sourcesContent) {
            // Chuyển đổi trạng thái hiển thị
            sourcesContent.classList.toggle('hidden');
            
            // Đổi mũi tên
            const arrow = element.querySelector('.fa-chevron-down, .fa-chevron-up');
            if (arrow) {
                arrow.classList.toggle('fa-chevron-down');
                arrow.classList.toggle('fa-chevron-up');
            }
        }
    }
} 