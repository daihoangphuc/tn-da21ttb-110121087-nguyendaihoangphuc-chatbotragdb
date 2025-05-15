/**
 * Controller quản lý theme
 */
class ThemeController {
    constructor() {
        this.darkMode = sessionStorage.getItem('darkMode') === 'true';
        this.applyTheme();
    }

    toggleTheme() {
        this.darkMode = !this.darkMode;
        sessionStorage.setItem('darkMode', this.darkMode);
        this.applyTheme();
    }

    applyTheme() {
        if (this.darkMode) {
            document.body.classList.add('dark-theme');
            document.getElementById('themeToggle').innerHTML = '<i class="fas fa-sun"></i>';
        } else {
            document.body.classList.remove('dark-theme');
            document.getElementById('themeToggle').innerHTML = '<i class="fas fa-moon"></i>';
        }
        
        // Phát ra sự kiện khi theme thay đổi để các component khác có thể lắng nghe
        document.dispatchEvent(new CustomEvent('themeChange', { detail: { darkMode: this.darkMode } }));
    }
}

/**
 * Controller quản lý nguồn tài liệu
 */
class SourceController {
    constructor() {
        this.selectedSources = [];
        this.fileToDelete = null;
        this.loadSources();
    }

    async loadSources() {
        try {
            const sourceList = document.getElementById('sourceList');
            sourceList.innerHTML = '<div class="loading-sources">Đang tải...</div>';
            
            const response = await apiService.getFiles();
            
            if (response && response.files && Array.isArray(response.files)) {
                this.renderSources(response.files);
            } else {
                sourceList.innerHTML = '<div class="no-sources">Chưa có tài liệu nào. Hãy tải lên tài liệu đầu tiên.</div>';
            }
        } catch (error) {
            document.getElementById('sourceList').innerHTML = 
                `<div class="error-message">Lỗi khi tải danh sách tài liệu: ${error.message}</div>`;
        }
    }

    renderSources(files) {
        const sourceList = document.getElementById('sourceList');
        sourceList.innerHTML = ''; // Clear previous list
        
        if (!files || files.length === 0) {
            sourceList.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <i class="fas fa-folder-open text-4xl mb-3"></i>
                    <p>Chưa có tài liệu nào. Hãy tải lên tài liệu để bắt đầu.</p>
                </div>
            `;
            return;
        }
        
        files.forEach(file => {
            // Tạo ID an toàn cho checkbox
            const safeId = this.makeSafeId(file.path);
            
            // Lớp css cho icon dựa vào loại file
            let iconClass = "source-icon";
            if (file.filename.endsWith('.pdf')) {
                iconClass += " pdf";
            } else if (file.filename.endsWith('.doc') || file.filename.endsWith('.docx')) {
                iconClass += " doc";
            } else {
                iconClass += " txt";
            }
            
            // Tạo thẻ HTML cho mỗi mục
            const sourceItem = document.createElement('div');
            sourceItem.className = 'source-item';
            sourceItem.innerHTML = `
                <div class="flex items-center">
                    <input type="checkbox" id="${safeId}" 
                        class="source-checkbox w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-0 focus:outline-none cursor-pointer" 
                        data-path="${file.path}" ${this.selectedSources.includes(file.path) ? 'checked' : ''}>
                    <div class="${iconClass}">
                        <i class="fas fa-file-alt"></i>
                    </div>
                    <div class="source-info">
                        <span class="source-name" title="${file.filename}">${file.filename}</span>
                        <div class="source-date">${this.getTimeAgo(file.upload_date)}</div>
                    </div>
                </div>
                <button class="source-delete" data-filename="${file.filename}">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            
            sourceList.appendChild(sourceItem);
            
            // Add event listeners
            const checkbox = sourceItem.querySelector(`#${safeId}`);
            checkbox.addEventListener('change', (e) => {
                this.toggleSource(file.path, e.target.checked);
            });
            
            const deleteBtn = sourceItem.querySelector('.source-delete');
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.confirmDelete(file.filename);
            });
            
            // Thêm sự kiện click cho toàn bộ source-item để toggle checkbox
            sourceItem.addEventListener('click', (e) => {
                // Nếu đã click vào checkbox hoặc nút xóa thì không cần xử lý
                if (e.target === checkbox || e.target === deleteBtn || deleteBtn.contains(e.target)) {
                    return;
                }
                
                // Toggle checkbox
                checkbox.checked = !checkbox.checked;
                
                // Gọi sự kiện change để kích hoạt listener đã đăng ký
                const changeEvent = new Event('change', { bubbles: true });
                checkbox.dispatchEvent(changeEvent);
            });
        });
        
        // Update selectAll checkbox state
        this.updateSelectAllState();
    }

    // Tạo ID an toàn từ đường dẫn tệp
    makeSafeId(path) {
        return 'file-' + path.replace(/[^a-z0-9]/gi, '-').toLowerCase();
    }

    toggleSource(sourcePath, selected) {
        if (selected) {
            this.selectedSources.push(sourcePath);
        } else {
            this.selectedSources = this.selectedSources.filter(path => path !== sourcePath);
        }
        
        // Update the checkbox visual state
        const safeId = this.makeSafeId(sourcePath);
        const checkbox = document.getElementById(safeId);
        if (checkbox) {
            checkbox.checked = selected;
        }
        
        // Update selectAll checkbox state
        this.updateSelectAllState();
        
        // Show/hide no sources selected alert
        document.getElementById('noSourceAlert').style.display = 
            this.selectedSources.length === 0 ? 'flex' : 'none';
    }

    selectAll(checked) {
        const checkboxes = document.querySelectorAll('.source-checkbox');
        
        checkboxes.forEach(checkbox => {
            const sourcePath = checkbox.getAttribute('data-path');
            checkbox.checked = checked;
            
            if (checked) {
                if (!this.selectedSources.includes(sourcePath)) {
                    this.selectedSources.push(sourcePath);
                }
            } else {
                this.selectedSources = [];
            }
        });
        
        // Show/hide no sources selected alert
        document.getElementById('noSourceAlert').style.display = 
            this.selectedSources.length === 0 ? 'flex' : 'none';
    }

    updateSelectAllState() {
        const selectAllCheckbox = document.getElementById('selectAll');
        const sourceCheckboxes = document.querySelectorAll('.source-checkbox');
        
        if (sourceCheckboxes.length === 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.disabled = true;
            return;
        }
        
        selectAllCheckbox.disabled = false;
        
        const allChecked = Array.from(sourceCheckboxes).every(checkbox => checkbox.checked);
        selectAllCheckbox.checked = allChecked;
        
        // Show/hide no sources selected alert
        document.getElementById('noSourceAlert').style.display = 
            this.selectedSources.length === 0 ? 'flex' : 'none';
    }

    confirmDelete(filename) {
        this.fileToDelete = filename;
        const modalController = new ModalController();
        modalController.openModal('deleteModal');
        
        // Khôi phục nút xóa nếu đã bị thay đổi trước đó
        document.querySelectorAll('.source-delete').forEach(button => {
            if (button.disabled && button.getAttribute('data-filename') === filename) {
                button.innerHTML = button.dataset.originalContent || '<i class="fas fa-trash"></i>';
                button.disabled = false;
                button.style.opacity = '';
            }
        });
    }

    resetDeleteState() {
        // Khôi phục nút xóa nếu đã bị thay đổi và chưa hoàn tất xóa
        if (this.fileToDelete) {
            document.querySelectorAll('.source-delete').forEach(button => {
                if (button.disabled && button.getAttribute('data-filename') === this.fileToDelete) {
                    button.innerHTML = button.dataset.originalContent || '<i class="fas fa-trash"></i>';
                    button.disabled = false;
                    button.style.opacity = '';
                }
            });
        }
        
        this.fileToDelete = null;
    }

    async deleteSelectedFile() {
        if (!this.fileToDelete) return;
        
        // Lấy tham chiếu đến các nút trong modal để reset sau này
        const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
        const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
        
        // Tìm và thay đổi biểu tượng thùng rác thành spinner
        const deleteButtons = document.querySelectorAll('.source-delete');
        let targetButton = null;
        deleteButtons.forEach(button => {
            if (button.getAttribute('data-filename') === this.fileToDelete) {
                targetButton = button;
                // Lưu lại nội dung cũ để khôi phục nếu có lỗi
                button.dataset.originalContent = button.innerHTML;
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                button.disabled = true;
                button.style.opacity = '1'; // Đảm bảo spinner luôn hiển thị
            }
        });
        
        try {
            // Đảm bảo modal được khóa trong quá trình xử lý
            const modalOverlay = document.querySelector('#deleteModal .modal-overlay');
            const closeModalBtn = document.querySelector('#deleteModal .close-modal-btn');
            
            if (modalOverlay) modalOverlay.style.pointerEvents = 'none';
            if (closeModalBtn) closeModalBtn.disabled = true;
            
            // Thêm độ trễ nhỏ để hiển thị spinner
            await new Promise(resolve => setTimeout(resolve, 200));
            
            await apiService.deleteFile(this.fileToDelete);
            
            // Hiển thị thông báo thành công trong modal
            const modalBody = document.querySelector('#deleteModal .modal-body');
            if (modalBody) {
                const originalContent = modalBody.innerHTML;
                modalBody.innerHTML = `
                    <div style="text-align:center; padding:0.5rem 0;">
                        <i class="fas fa-check-circle" style="color:#34A853; font-size:2rem; margin-bottom:0.5rem;"></i>
                        <p style="color:#34A853; font-weight:500;">Đã xóa tài liệu thành công!</p>
                    </div>
                `;
                
                // Hiển thị thông báo thành công trong 1 giây trước khi đóng modal
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                // Khôi phục nội dung ban đầu của modal body
                modalBody.innerHTML = originalContent;
            }
            
            // Đặt fileToDelete về null để đánh dấu hoàn thành
            this.fileToDelete = null;
            
            // Reload sources list
            this.loadSources();
            
            // Đóng modal sau khi xóa thành công
            const modalController = new ModalController();
            modalController.closeModal('deleteModal');
            
            // Reset trạng thái nút trong modal (cho lần mở tiếp theo)
            if (confirmDeleteBtn) {
                confirmDeleteBtn.disabled = false;
                confirmDeleteBtn.innerHTML = 'Xóa';
            }
            if (cancelDeleteBtn) {
                cancelDeleteBtn.disabled = false;
            }
            
            // Kích hoạt lại các điều khiển modal
            if (modalOverlay) modalOverlay.style.pointerEvents = '';
            if (closeModalBtn) closeModalBtn.disabled = false;
            
        } catch (error) {
            console.error('Lỗi khi xóa tài liệu:', error);
            
            // Khôi phục nút xóa nếu có lỗi
            if (targetButton) {
                targetButton.innerHTML = targetButton.dataset.originalContent || '<i class="fas fa-trash"></i>';
                targetButton.disabled = false;
                targetButton.style.opacity = '';
            }
            
            // Reset trạng thái nút trong modal khi có lỗi
            if (confirmDeleteBtn) {
                confirmDeleteBtn.disabled = false;
                confirmDeleteBtn.innerHTML = 'Xóa';
            }
            if (cancelDeleteBtn) {
                cancelDeleteBtn.disabled = false;
            }
            
            // Kích hoạt lại modal overlay và nút đóng
            const modalOverlay = document.querySelector('#deleteModal .modal-overlay');
            const closeModalBtn = document.querySelector('#deleteModal .close-modal-btn');
            
            if (modalOverlay) modalOverlay.style.pointerEvents = '';
            if (closeModalBtn) closeModalBtn.disabled = false;
            
            alert(`Không thể xóa tài liệu: ${error.message}`);
        }
    }

    getTimeAgo(date) {
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) {
            return 'vừa xong';
        }
        
        const diffInMinutes = Math.floor(diffInSeconds / 60);
        if (diffInMinutes < 60) {
            return `${diffInMinutes} phút trước`;
        }
        
        const diffInHours = Math.floor(diffInMinutes / 60);
        if (diffInHours < 24) {
            return `${diffInHours} giờ trước`;
        }
        
        const diffInDays = Math.floor(diffInHours / 24);
        if (diffInDays < 30) {
            return `${diffInDays} ngày trước`;
        }
        
        const diffInMonths = Math.floor(diffInDays / 30);
        if (diffInMonths < 12) {
            return `${diffInMonths} tháng trước`;
        }
        
        const diffInYears = Math.floor(diffInMonths / 12);
        return `${diffInYears} năm trước`;
    }
}

/**
 * Controller quản lý hội thoại
 */
class ConversationController {
    constructor() {
        this.conversation = {
            title: "RAG Assistant",
            messages: [],
            sources: []
        };
        
        this.loadingMessage = false;
    }

    async sendMessage(message) {
        if (!message || this.loadingMessage) return;
        
        console.log('Bắt đầu gửi tin nhắn:', message);
        
        // Lấy tất cả nguồn được chọn từ các checkbox
        const sourceCheckboxes = document.querySelectorAll('.source-checkbox:checked');
        const selectedSources = Array.from(sourceCheckboxes).map(checkbox => checkbox.getAttribute('data-path'));
        console.log('Nguồn được chọn:', selectedSources);
        
        // Kiểm tra nếu không có nguồn nào được chọn
        if (selectedSources.length === 0) {
            console.log('Không có nguồn nào được chọn');
            document.getElementById('noSourceAlert').style.display = 'flex';
            return;
        }
        
        // Vô hiệu hóa input khi đang xử lý câu hỏi
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        messageInput.disabled = true;
        sendButton.disabled = true;
        
        // Hiển thị tin nhắn người dùng
        this.addMessage(message, 'user');
        console.log('Đã thêm tin nhắn người dùng vào UI', document.querySelectorAll('.user-message').length);
        
        // Kiểm tra xem tin nhắn người dùng có hiển thị không
        const userMessages = document.querySelectorAll('.user-message');
        const lastUserMessage = userMessages[userMessages.length - 1];
        console.log('Tin nhắn người dùng cuối cùng:', lastUserMessage);
        
        // Đợi một khoảng thời gian ngắn để đảm bảo tin nhắn người dùng được hiển thị trước
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Hiển thị loading cho tin nhắn hệ thống
        this.showLoadingMessage();
        console.log('Đã hiển thị loading message');
        
        try {
            console.log('Gọi API với câu hỏi:', message);
            
            // Bắt đầu streaming
            let streamResponse = '';
            let sources = [];
            let isStreaming = false;
            
            // Sử dụng streaming API
            const stream = apiService.queryRAGStream(
                message,
                'hybrid',
                undefined,
                selectedSources
            );
            
            // Xử lý khi nhận được sources
            stream.onSources(sourcesData => {
                console.log('Nhận được sources:', sourcesData);
                sources = sourcesData.sources || [];
                
                // Xóa loading message
                this.removeLoadingMessage();
                
                // Thêm message trống cho assistant, sẽ được cập nhật dần dần
                this.addMessage('', 'assistant', sources);
                
                // Thêm indicator cho nội dung sẽ được cập nhật
                this.updateMessageContent('', false);
                
                // Cập nhật trạng thái đang streaming
                isStreaming = true;
            });
            
            // Xử lý khi nhận được từng đoạn nội dung
            stream.onContent(content => {
                if (!isStreaming) return; // Đảm bảo sources đã được xử lý trước
                
                console.log('Nhận được nội dung:', content);
                streamResponse += content;
                
                // Cập nhật nội dung tin nhắn trong UI
                this.updateMessageContent(streamResponse);
            });
            
            // Xử lý khi kết thúc stream
            stream.onEnd(endData => {
                console.log('Stream kết thúc:', endData);
                
                // Hoàn tất tin nhắn
                if (streamResponse) {
                    // Đã có nội dung, cập nhật lần cuối
                    this.updateMessageContent(streamResponse, true, endData.related_questions);
                } else {
                    // Phòng trường hợp không có nội dung nào được stream
                    this.updateMessageContent("Không nhận được phản hồi từ hệ thống. Vui lòng thử lại sau.", true);
                }
                
                // Cập nhật meta thông tin
                this.updateConversationMeta();
                
                // Nếu có sources, hiển thị nguồn đầu tiên
                if (sources && sources.length > 0) {
                    const sourceViewController = new SourceViewController();
                    sourceViewController.showSource(sources[0]);
                    console.log('Hiển thị nguồn đầu tiên');
                    
                    // Trên mobile, tự động chuyển sang source view
                    if (window.innerWidth < 640) {
                        const mobileNavController = new MobileNavController();
                        mobileNavController.switchPanel('sourceView');
                    }
                }
            });
            
            // Xử lý khi có lỗi
            stream.onError(error => {
                console.error('Lỗi stream:', error);
                
                // Xóa loading message nếu còn
                if (this.loadingMessage) {
                    this.removeLoadingMessage();
                }
                
                // Hiển thị tin nhắn lỗi
                if (!isStreaming) {
                    // Chưa hiển thị tin nhắn nào, thêm tin nhắn lỗi mới
                    this.addMessage(`Đã xảy ra lỗi khi xử lý truy vấn của bạn: ${error.message}. Vui lòng thử lại sau.`, 'assistant');
                } else {
                    // Đã có tin nhắn, cập nhật tin nhắn hiện tại
                    this.updateMessageContent(`${streamResponse}\n\nLỗi: ${error.message}. Kết nối bị ngắt.`, true);
                }
                
                // Tạo một độ trễ ngắn để đảm bảo tin nhắn lỗi đã được hiển thị hoàn tất
                setTimeout(() => {
                    // Kích hoạt lại input
                    const messageInput = document.getElementById('messageInput');
                    const sendButton = document.getElementById('sendButton');
                    if (messageInput && sendButton) {
                        messageInput.disabled = false;
                        sendButton.disabled = messageInput.value.trim() === '';
                        messageInput.focus();
                    }
                }, 500); // Đợi 500ms để đảm bảo UI đã được cập nhật
                
                // Hiển thị thông báo lỗi trong 5 giây
                const apiAlert = document.getElementById('apiAlert');
                const apiAlertMessage = document.getElementById('apiAlertMessage');
                if (apiAlert && apiAlertMessage) {
                    apiAlertMessage.textContent = `Lỗi: ${error.message}`;
                    apiAlert.style.display = 'flex';
                    setTimeout(() => {
                        apiAlert.style.display = 'none';
                    }, 5000);
                }
            });
        } catch (error) {
            console.error('Lỗi khi xử lý câu hỏi:', error);
            
            // Xóa loading message
            this.removeLoadingMessage();
            
            // Hiển thị tin nhắn lỗi
            this.addMessage(`Đã xảy ra lỗi khi xử lý truy vấn của bạn: ${error.message}. Vui lòng thử lại sau.`, 'assistant');
            
            // Tạo một độ trễ ngắn để đảm bảo tin nhắn lỗi đã được hiển thị hoàn tất
            setTimeout(() => {
                // Kích hoạt lại input
                const messageInput = document.getElementById('messageInput');
                const sendButton = document.getElementById('sendButton');
                if (messageInput && sendButton) {
                    messageInput.disabled = false;
                    sendButton.disabled = messageInput.value.trim() === '';
                    messageInput.focus();
                }
            }, 500); // Đợi 500ms để đảm bảo UI đã được cập nhật
        }
    }

    // Thêm phương thức mới để cập nhật nội dung tin nhắn hiện tại
    updateMessageContent(content, isComplete = false, relatedQuestions = null) {
        if (!this.currentMessage) return;
        
        // Cập nhật nội dung tin nhắn
        const formattedContent = this.formatMessageContent(content);
        this.currentMessage.querySelector('.message-content').innerHTML = formattedContent;
        
            if (isComplete) {
            // Đã hoàn thành tin nhắn
            this.currentMessage.classList.remove('loading');
            this.loadingMessage = null;
            
            // Thêm related questions nếu có
            if (relatedQuestions && relatedQuestions.length > 0) {
                this.addRelatedQuestions(relatedQuestions);
            }
            
            // Kích hoạt highlight syntax
            this.highlightCodeBlocks();
            this.scrollToBottom();
        }
    }

    addMessage(content, role, sources = []) {
        // Thêm tin nhắn vào state
        const message = { role, content };
        this.conversation.messages.push(message);
        
        // Lưu lại sources cho trợ lý
        if (role === 'assistant' && sources && sources.length > 0) {
            this.conversation.sources = sources;
        }
        
        // Lưu trữ số tin nhắn hiện có trước khi thêm mới
        const prevMessageCount = document.querySelectorAll('.message').length;
        console.log(`Số tin nhắn hiện tại trước khi thêm: ${prevMessageCount}, thêm mới: ${role}`);
        
        // Hiển thị tin nhắn trong UI
        this.renderMessage(message, sources);
        
        // Kiểm tra số tin nhắn sau khi thêm mới
        const currentMessageCount = document.querySelectorAll('.message').length;
        console.log(`Số tin nhắn sau khi thêm: ${currentMessageCount}`);
        
        // Kiểm tra xem tin nhắn đã được thêm vào DOM chưa
        const userMessages = document.querySelectorAll('.user-message').length;
        const assistantMessages = document.querySelectorAll('.assistant-message').length;
        console.log(`Sau khi thêm tin nhắn: ${role}, user messages: ${userMessages}, assistant messages: ${assistantMessages}`);
        
        // Cập nhật thông tin cuộc hội thoại
        this.updateConversationMeta();
        
        // Cuộn xuống tin nhắn mới nhất
        this.scrollToBottom();
    }

    renderMessage(message, sources = []) {
        const messagesContainer = document.getElementById('messagesContainer');
        
        // QUAN TRỌNG: Chỉ xóa welcome message khi đây là tin nhắn đầu tiên của cuộc hội thoại
        // và chỉ khi có welcome message trong container
        if (this.conversation.messages.length === 1 && messagesContainer.querySelector('.welcome-message')) {
            console.log('Xóa welcome message vì đây là tin nhắn đầu tiên');
            const welcomeMsg = messagesContainer.querySelector('.welcome-message');
            if (welcomeMsg) welcomeMsg.remove();
        }
        
        const messageElement = document.createElement('div');
        messageElement.className = `message ${message.role}-message`;
        messageElement.setAttribute('data-role', message.role);
        console.log(`Hiển thị tin nhắn: ${message.role}, nội dung: ${message.content ? message.content.slice(0, 30) + '...' : 'rỗng'}`);
        
        // Avatar và nội dung tin nhắn
        let avatar = '';
        if (message.role === 'assistant') {
            avatar = `
                <div class="avatar message-avatar">
                    <i class="fas fa-file-alt"></i>
                </div>
            `;
        } else {
            avatar = `
                <div class="avatar message-avatar">
                    <span>U</span>
                </div>
            `;
        }
        
        // Format nội dung tin nhắn
        let formattedContent = '';
        if (message.role === 'user') {
            // Xử lý đặc biệt cho tin nhắn người dùng để hiển thị rõ ràng
            formattedContent = `<p>${message.content}</p>`;
            
            messageElement.innerHTML = `
                ${avatar}
                <div class="message-content">
                    ${formattedContent}
                </div>
            `;
            messagesContainer.appendChild(messageElement);
            // Lưu tham chiếu đến tin nhắn hiện tại cho tin nhắn của user
            if (message.role === 'user') {
                this.currentMessage = messageElement;
            }
        } else {
            // Với tin nhắn từ trợ lý, không hiển thị nội dung ngay, mà chỉ hiển thị avatar 
            // và placeholder để cập nhật sau bằng updateMessageContent
            messageElement.innerHTML = `
                ${avatar}
                <div class="message-content">
                    <div class="assistant-typing-content"></div>
                    ${this.renderSourcesHTML(sources)}
                </div>
            `;
            
            messagesContainer.appendChild(messageElement);
            // Lưu tham chiếu đến tin nhắn hiện tại cho tin nhắn của trợ lý
            if (message.role === 'assistant') {
                this.currentMessage = messageElement;
            }
        }
        
        // In log để debug
        console.log(`Đã render tin nhắn: ${message.role}, element class: ${messageElement.className}`);
        
        // Thêm event listeners cho các source chips
        if (sources && sources.length > 0) {
            const sourceChips = messageElement.querySelectorAll('.source-chip');
            sourceChips.forEach((chip, index) => {
                chip.addEventListener('click', () => {
                    const sourceViewController = new SourceViewController();
                    sourceViewController.showSource(sources[index]);
                    
                    // On mobile, switch to source view
                    if (window.innerWidth < 640) {
                        const mobileNavController = new MobileNavController();
                        mobileNavController.switchPanel('sourceView');
                    }
                });
            });
        }
    }

    formatMessageContent(content) {
        if (!content) return '';
        
        try {
            // Cấu hình marked.js để xử lý code blocks đúng cách
            if (typeof marked !== 'undefined') {
                // Xử lý code blocks
                marked.setOptions({
                    highlight: function(code, lang) {
                        // Code sẽ được xử lý bởi CSS
                        return code;
                    },
                    gfm: true,
                    breaks: true,
                    smartLists: true
                });
                
                // Chuyển đổi markdown sang HTML
                const renderer = new marked.Renderer();
                
                // Tùy chỉnh cách render code blocks
                renderer.code = function(code, language) {
                    language = language || '';
                    return `
                        <div class="code-block">
                            <div class="code-header">
                                <span>${language.toUpperCase() || 'CODE'}</span>
                                <button class="code-copy-btn">
                                    <i class="fas fa-copy"></i>
                                </button>
                            </div>
                            <pre><code class="code-content ${language}">${code}</code></pre>
                        </div>
                    `;
                };
                
                // Render markdown với renderer tùy chỉnh
                marked.setOptions({ renderer });
                const html = marked.parse(content);
                
                return `<div class="markdown">${html}</div>`;
            }
        } catch (e) {
            console.error('Lỗi khi xử lý markdown:', e);
        }
        
        // Fallback xử lý thủ công nếu marked.js không hoạt động
        let formattedContent = content;
        
        // Xử lý các code blocks
        const codeBlockRegex = /```(?:([\w-]+))?\s*([\s\S]*?)```/g;
        formattedContent = formattedContent.replace(codeBlockRegex, (match, language, code) => {
            language = language || '';
            code = code.trim();
            return `
                <div class="code-block">
                    <div class="code-header">
                        <span>${language.toUpperCase() || 'CODE'}</span>
                        <button class="code-copy-btn">
                            <i class="fas fa-copy"></i>
                        </button>
                    </div>
                    <pre><code class="code-content">${code}</code></pre>
                </div>
            `;
        });
        
        // Xử lý đơn giản cho các phần tử markdown cơ bản
        formattedContent = formattedContent
            // Xử lý tiêu đề
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            // Xử lý in đậm và in nghiêng
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Xử lý danh sách
            .replace(/^\s*- (.*$)/gim, '<ul><li>$1</li></ul>')
            .replace(/^\s*(\d+)\. (.*$)/gim, '<ol><li>$2</li></ol>')
            // Xử lý code inline
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // Xử lý đoạn văn
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');
        
        formattedContent = `<p>${formattedContent}</p>`;
        // Xử lý danh sách: ghép các thẻ ul/ol liền kề
        formattedContent = formattedContent
            .replace(/<\/ul><ul>/g, '')
            .replace(/<\/ol><ol>/g, '');
        
        return `<div class="markdown">${formattedContent}</div>`;
    }

    renderSourcesHTML(sources) {
        if (!sources || sources.length === 0) return '';
        
        let sourcesHTML = `
            <div class="message-sources">
                <div class="message-sources-label">Nguồn tham khảo:</div>
                <div class="source-chips">
        `;
        
        sources.forEach(source => {
            sourcesHTML += `
                <div class="source-chip">
                    <i class="fas fa-file-alt"></i>
                    <span>${source.source || 'Nguồn'}</span>
                    <i class="fas fa-external-link-alt"></i>
                </div>
            `;
        });
        
        sourcesHTML += '</div></div>';
        
        return sourcesHTML;
    }

    showLoadingMessage() {
        this.loadingMessage = true;
        
        const messagesContainer = document.getElementById('messagesContainer');
        console.log('Hiển thị loading message, số tin nhắn hiện tại:', document.querySelectorAll('.message').length);
        
        // Lưu thời điểm bắt đầu
        this.responseStartTime = Date.now();
        
        // QUAN TRỌNG: Không xóa nội dung messagesContainer ở đây để giữ lại tin nhắn người dùng
        
        const loadingElement = document.createElement('div');
        loadingElement.className = 'message loading-message assistant-message';
        loadingElement.id = 'loadingMessage';
        loadingElement.style.cssText = 'opacity: 1; transition: opacity 0.3s ease;';
        
        loadingElement.innerHTML = `
            <div class="avatar message-avatar">
                <i class="fas fa-file-alt"></i>
            </div>
            <div class="message-content">
                <div class="loading-container">
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                    <div class="response-time" id="responseTimeIndicator">
                        <span id="responseTimeCounter">0.0</span>s
                    </div>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(loadingElement);
        
        // Force reflow để hiển thị animation
        window.getComputedStyle(loadingElement).opacity;
        
        // Bắt đầu bộ đếm thời gian - đơn giản chỉ hiển thị số giây
        this.responseTimerInterval = setInterval(() => {
            const elapsedTime = (Date.now() - this.responseStartTime) / 1000;
            const counter = document.getElementById('responseTimeCounter');
            if (counter) {
                counter.textContent = elapsedTime.toFixed(1);
            }
        }, 100);
        
        console.log('Sau khi thêm loading message, số tin nhắn hiện tại:', document.querySelectorAll('.message').length);
        
        // Cuộn xuống tin nhắn mới nhất
        this.scrollToBottom();
    }

    removeLoadingMessage() {
        this.loadingMessage = false;
        
        // Dừng bộ đếm thời gian phản hồi
        if (this.responseTimerInterval) {
            clearInterval(this.responseTimerInterval);
            this.responseTimerInterval = null;
        }
        
        // Ghi lại thời gian phản hồi
        if (this.responseStartTime) {
            this.lastResponseTime = ((Date.now() - this.responseStartTime) / 1000).toFixed(1);
            console.log(`Thời gian phản hồi: ${this.lastResponseTime}s`);
        }
        
        // Xóa loading message
        const loadingMessage = document.getElementById('loadingMessage');
        if (loadingMessage && loadingMessage.parentNode) {
            loadingMessage.remove();
        }
    }

    updateConversationMeta() {
        const meta = document.getElementById('conversationMeta');
        if (this.conversation.messages.length > 0) {
            meta.textContent = `${this.conversation.messages.length} tin nhắn`;
        } else {
            meta.textContent = 'Hỏi đáp với tài liệu';
        }
    }

    scrollToBottom() {
        const messagesContainer = document.getElementById('messagesContainer');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Tô màu cú pháp cho các code blocks
    highlightCodeBlocks() {
        // Kiểm tra xem highlight.js đã được tải chưa
        if (typeof hljs !== 'undefined' && this.currentMessage) {
            // Tìm tất cả các phần tử code trong tin nhắn hiện tại
            const codeBlocks = this.currentMessage.querySelectorAll('pre code');
            if (codeBlocks.length > 0) {
                console.log(`Tô màu cú pháp cho ${codeBlocks.length} khối mã`);
                codeBlocks.forEach(block => {
                    hljs.highlightElement(block);
                });
            }
            
            // Thêm sự kiện cho các nút copy nếu có
            const copyButtons = this.currentMessage.querySelectorAll('.code-copy-btn');
            copyButtons.forEach(btn => {
                if (!btn.hasAttribute('data-listener-added')) {
                    const codeBlock = btn.closest('.code-block');
                    if (codeBlock) {
                        const codeContent = codeBlock.querySelector('.code-content');
                        if (codeContent) {
                            btn.addEventListener('click', () => {
                                navigator.clipboard.writeText(codeContent.textContent);
                                // Hiệu ứng đã copy
                                btn.innerHTML = '<i class="fas fa-check"></i>';
                                setTimeout(() => {
                                    btn.innerHTML = '<i class="fas fa-copy"></i>';
                                }, 2000);
                            });
                            btn.setAttribute('data-listener-added', 'true');
                        }
                    }
                }
            });
        }
    }

    // Tạo hiệu ứng đánh máy
    typeWriterEffect(element, html) {
        // Tạo một div tạm thời để phân tích HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        
        // Xử lý từng phần tử HTML
        this.processTypeWriterNodes(element, tempDiv, 20);
    }
    
    // Hàm đệ quy để xử lý các node con
    processTypeWriterNodes(targetElement, sourceParent, speed = 20) {
        // Sao chép tất cả các node con
        const nodes = Array.from(sourceParent.childNodes);
        let currentIndex = 0;
        
        const processNextNode = () => {
            if (currentIndex >= nodes.length) {
                // Đã xử lý xong tất cả các node
                // Thêm class typing-done để ẩn cursor
                targetElement.classList.add('typing-done');
                
                // Cuộn xuống tin nhắn mới nhất
                this.scrollToBottom();
                return;
            }
            
            const currentNode = nodes[currentIndex];
            currentIndex++;
            
            if (currentNode.nodeType === Node.TEXT_NODE) {
                // Nếu là text node, hiển thị từng ký tự một
                this.typeWriterText(targetElement, currentNode.textContent, speed, processNextNode);
            } else if (currentNode.nodeType === Node.ELEMENT_NODE) {
                // Nếu là element node, tạo element tương ứng và xử lý các node con
                const newElement = document.createElement(currentNode.tagName);
                
                // Sao chép tất cả các thuộc tính
                Array.from(currentNode.attributes).forEach(attr => {
                    newElement.setAttribute(attr.name, attr.value);
                });
                
                // Thêm element mới vào target
                targetElement.appendChild(newElement);
                
                // Xử lý các node con của element này
                this.processTypeWriterNodes(newElement, currentNode, speed);
                
                // Tiếp tục với node tiếp theo
                setTimeout(processNextNode, 10);
            } else {
                // Các loại node khác, bỏ qua và tiếp tục
                processNextNode();
            }
        };
        
        // Bắt đầu xử lý node đầu tiên
        processNextNode();
    }
    
    // Hàm hiển thị từng ký tự text
    typeWriterText(element, text, speed, callback) {
        let index = 0;
        
        // Nếu text rỗng, gọi callback ngay
        if (!text || text.length === 0) {
            if (callback) callback();
            return;
        }
        
        // Hiển thị từng ký tự một
        const typeNextChar = () => {
            if (index < text.length) {
                element.appendChild(document.createTextNode(text.charAt(index)));
                index++;
                setTimeout(typeNextChar, speed);
            } else if (callback) {
                // Hoàn thành việc hiển thị text, gọi callback
                callback();
            }
        };
        
        typeNextChar();
    }

    // Tải một phiên chat từ lịch sử
    loadChatSession(chatSession) {
        if (!chatSession) {
            console.error('Không thể tải phiên chat: dữ liệu không hợp lệ');
            return;
        }
        
        // Xóa tin nhắn hiện tại
        this.clearChat(false); // false để không hiển thị confirm
        
        // Cập nhật tiêu đề và các thông tin khác
        this.conversation = {
            title: chatSession.title || "RAG Assistant",
            messages: chatSession.messages || [],
            sources: chatSession.sources || []
        };
        
        // Cập nhật tiêu đề hiển thị
        const conversationMeta = document.getElementById('conversationMeta');
        if (conversationMeta) {
            conversationMeta.textContent = chatSession.title || "Hỏi đáp với tài liệu";
        }
        
        // Hiển thị tin nhắn
        this.renderMessages();
        
        // Tự động chọn các nguồn tài liệu đã sử dụng trong phiên chat
        if (chatSession.sources && chatSession.sources.length > 0) {
            const sourceController = new SourceController();
            sourceController.selectAll(false); // Bỏ chọn hết
            
            chatSession.sources.forEach(source => {
                sourceController.toggleSource(source, true);
            });
        }
    }
    
    // Xóa chat hiện tại
    clearChat(showConfirm = true) {
        if (showConfirm && !confirm('Bạn có chắc chắn muốn xóa tất cả tin nhắn trong cuộc trò chuyện hiện tại?')) {
            return;
        }
        
        this.conversation = {
            title: "RAG Assistant",
            messages: [],
            sources: []
        };
        
        const messagesContainer = document.getElementById('messagesContainer');
        messagesContainer.innerHTML = `
            <div class="welcome-message">
                <p>Chào mừng bạn đến với hệ thống RAG hỗ trợ môn cơ sở dữ liệu! Hãy đặt câu hỏi về tài liệu của bạn.</p>
                <p>Ví dụ: "Phân biệt giữa INNER JOIN và LEFT JOIN trong SQL?" hay "Cho tôi ví dụ về một câu truy vấn nested."</p>
            </div>
        `;
        
        const conversationMeta = document.getElementById('conversationMeta');
        if (conversationMeta) {
            conversationMeta.textContent = "Hỏi đáp với tài liệu";
        }
    }

    // Thêm câu hỏi liên quan vào tin nhắn hiện tại
    addRelatedQuestions(questions) {
        if (!this.currentMessage || !questions || questions.length === 0) return;
        
        console.log('Thêm câu hỏi liên quan:', questions);
        
        // Tạo container cho câu hỏi liên quan
        const relatedQuestionsDiv = document.createElement('div');
        relatedQuestionsDiv.className = 'related-questions';
        
        // Tạo tiêu đề
        const titleDiv = document.createElement('div');
        titleDiv.className = 'related-questions-title';
        titleDiv.innerHTML = '<i class="fas fa-lightbulb mr-1"></i> Câu hỏi gợi ý:';
        relatedQuestionsDiv.appendChild(titleDiv);
        
        // Tạo danh sách câu hỏi
        const questionsList = document.createElement('div');
        questionsList.className = 'related-question-list';
        
        // Thêm mỗi câu hỏi vào danh sách
        questions.forEach(question => {
            const questionItem = document.createElement('div');
            questionItem.className = 'related-question-item';
            questionItem.textContent = question;
            
            // Thêm sự kiện click để gửi câu hỏi này
            questionItem.addEventListener('click', () => {
                // Lấy tham chiếu đến input và điền nội dung
                const messageInput = document.getElementById('messageInput');
                if (messageInput) {
                    messageInput.value = question;
                    messageInput.focus();
                    
                    // Kích hoạt nút gửi
                    const sendButton = document.getElementById('sendButton');
                    if (sendButton) {
                        sendButton.disabled = false;
                    }
                }
            });
            
            questionsList.appendChild(questionItem);
        });
        
        relatedQuestionsDiv.appendChild(questionsList);
        
        // Thêm vào tin nhắn
        this.currentMessage.querySelector('.message-content').appendChild(relatedQuestionsDiv);
    }
}

/**
 * Controller quản lý hiển thị nguồn
 */
class SourceViewController {
    constructor() {
        this.currentSource = null;
    }

    showSource(source) {
        if (!source) return;
        
        this.currentSource = source;
        const sourceContent = document.getElementById('sourceContent');
        
        // Hiển thị nội dung snippet
        if (source.content_snippet) {
            const formattedContent = this.formatSourceContent(source.content_snippet);
            sourceContent.innerHTML = `
                <div class="source-header">
                    <div class="source-title">${source.source || 'Nguồn không có tiêu đề'}</div>
                    <div class="source-score">Điểm liên quan: ${Math.round(source.score * 100)}%</div>
                </div>
                <div class="source-snippet">${formattedContent}</div>
            `;
            
            // Thêm event listeners cho nút copy code
            const codeBlocks = sourceContent.querySelectorAll('.code-block');
            codeBlocks.forEach(block => {
                const copyBtn = block.querySelector('.code-copy-btn');
                const codeContent = block.querySelector('.code-content').textContent;
                
                copyBtn.addEventListener('click', () => {
                    navigator.clipboard.writeText(codeContent);
                    copyBtn.innerHTML = '<i class="fas fa-check"></i>';
                    
                    setTimeout(() => {
                        copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
                    }, 2000);
                });
            });
        } else {
            sourceContent.innerHTML = `
                <div class="no-source-content">
                    <p>Không có nội dung chi tiết cho nguồn này</p>
                </div>
            `;
        }
    }

    formatSourceContent(content) {
        if (!content) return '<p>Không có nội dung</p>';
        
        // Kiểm tra có phải là SQL code block không
        const isSqlCode = (content) => {
            const sqlKeywords = ['SELECT', 'FROM', 'WHERE', 'INSERT', 'CREATE TABLE', 'ALTER TABLE',
                                'DROP', 'UPDATE', 'DELETE', 'JOIN', 'CONSTRAINT', 'PRIMARY KEY'];
            return sqlKeywords.some(keyword => content.toUpperCase().includes(keyword));
        };
        
        // Định dạng code block
        if (isSqlCode(content)) {
            return `
                <div class="code-block">
                    <div class="code-header">
                        <span>SQL</span>
                        <button class="code-copy-btn">
                            <i class="fas fa-copy"></i>
                        </button>
                    </div>
                    <div class="code-content">${content}</div>
                </div>
            `;
        }
        
        // Nếu không phải code block, hiển thị như văn bản thông thường
        content = content.replace(/\n/g, '<br>');
        return `<p>${content}</p>`;
    }
}

/**
 * Controller quản lý chế độ màn hình mobile
 */
class MobileNavController {
    constructor() {
        this.currentPanel = 'conversation';
    }

    switchPanel(panelName) {
        const sourcePanel = document.getElementById('sourcePanel');
        const conversationPanel = document.getElementById('conversationPanel');
        const sourceViewPanel = document.getElementById('sourceViewPanel');
        
        // Cập nhật UI chỉ trên mobile
        if (window.innerWidth < 640) {
            // Ẩn tất cả panels
            sourcePanel.style.display = 'none';
            conversationPanel.style.display = 'none';
            sourceViewPanel.style.display = 'none';
            
            // Hiển thị panel được chọn
            switch (panelName) {
                case 'sources':
                    sourcePanel.style.display = 'flex';
                    break;
                case 'conversation':
                    conversationPanel.style.display = 'flex';
                    break;
                case 'sourceView':
                    sourceViewPanel.style.display = 'flex';
                    break;
            }
            
            // Cập nhật trạng thái active của các nút mobile navigation
            const navButtons = document.querySelectorAll('.nav-button');
            navButtons.forEach(button => {
                const buttonPanel = button.getAttribute('data-panel');
                if (buttonPanel === panelName) {
                    button.classList.add('active');
                } else {
                    button.classList.remove('active');
                }
            });
            
            this.currentPanel = panelName;
        }
    }
}

/**
 * Controller quản lý modal
 */
class ModalController {
    openModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.add('open');
        
        // Nếu mở modal xác nhận xóa, đảm bảo reset trạng thái
        if (modalId === 'deleteModal') {
            this.resetDeleteModal();
        }
    }

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.remove('open');
    }
    
    // Reset trạng thái của modal xác nhận xóa
    resetDeleteModal() {
        const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
        const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
        const closeModalBtn = document.querySelector('#deleteModal .close-modal-btn');
        const modalOverlay = document.querySelector('#deleteModal .modal-overlay');
        const modalBody = document.querySelector('#deleteModal .modal-body');
        
        // Reset nút xác nhận xóa
        if (confirmDeleteBtn) {
            confirmDeleteBtn.disabled = false;
            confirmDeleteBtn.innerHTML = 'Xóa';
        }
        
        // Reset nút hủy
        if (cancelDeleteBtn) {
            cancelDeleteBtn.disabled = false;
        }
        
        // Reset nút đóng
        if (closeModalBtn) {
            closeModalBtn.disabled = false;
        }
        
        // Reset overlay
        if (modalOverlay) {
            modalOverlay.style.pointerEvents = '';
        }
        
        // Đảm bảo nội dung modal body được khôi phục về mặc định
        if (modalBody && modalBody.querySelector('.fa-check-circle')) {
            modalBody.innerHTML = `
                <p>Bạn có chắc chắn muốn xóa tài liệu này? Hành động này không thể hoàn tác.</p>
            `;
        }
        
        console.log('Đã reset trạng thái của modal xóa file');
    }
}

/**
 * Controller quản lý upload tài liệu
 */
class UploadController {
    constructor() {
        this.files = [];
        this.uploadArea = document.getElementById('uploadArea');
        this.uploadInfo = document.getElementById('uploadInfo');
        this.uploadFilesList = document.getElementById('uploadFilesList');
        this.uploadSpinner = document.getElementById('uploadSpinner');
        this.uploadStatus = document.getElementById('uploadStatus');
        this.confirmUploadBtn = document.getElementById('confirmUploadBtn');
        
        // Theo dõi số lượng file đã tải lên thành công và thất bại
        this.successCount = 0;
        this.failCount = 0;
        this.totalFiles = 0;
    }

    addFiles(filesArray) {
        if (!filesArray || filesArray.length === 0) return;
        
        // Convert FileList to array và kiểm tra các file hợp lệ
        const validFiles = [];
        const invalidFiles = [];
        const allowedExtensions = ['.pdf', '.docx', '.doc', '.txt', '.sql'];
        
        for (let i = 0; i < filesArray.length; i++) {
            const file = filesArray[i];
            const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
            
            if (allowedExtensions.includes(fileExtension)) {
                // Kiểm tra trùng lặp file dựa trên tên và kích thước
                const isDuplicate = this.files.some(existingFile => 
                    existingFile.name === file.name && existingFile.size === file.size
                );
                
                if (!isDuplicate) {
                    validFiles.push(file);
                } else {
                    invalidFiles.push({file, reason: 'duplicate'});
                }
            } else {
                invalidFiles.push({file, reason: 'format'});
            }
        }
        
        if (validFiles.length === 0) {
            if (filesArray.length > 0) {
                if (invalidFiles.some(item => item.reason === 'format')) {
                    alert('Định dạng file không được hỗ trợ. Vui lòng chọn file PDF, DOCX, DOC, TXT hoặc SQL.');
                } else {
                    alert('Các file đã tồn tại trong danh sách.');
                }
            }
            return;
        }
        
        // Thêm các file hợp lệ vào danh sách
        this.files = [...this.files, ...validFiles];
        
        // Cập nhật UI
        this.renderFilesList();
        
        // Hiển thị danh sách file và ẩn khu vực kéo thả
        this.uploadArea.style.display = 'none';
        this.uploadInfo.style.display = 'block';
        
        // Cập nhật thông báo với số lượng file được thêm
        this.uploadStatus.innerHTML = validFiles.length > 1 
            ? `<b>Đã thêm ${validFiles.length} file</b>` 
            : `<b>Đã thêm file "${validFiles[0].name}"</b>`;
        
        // Hiệu ứng "xuất hiện" cho các file mới
        setTimeout(() => {
            const fileItems = this.uploadFilesList.querySelectorAll('.file-item');
            const startIndex = fileItems.length - validFiles.length;
            
            for (let i = startIndex; i < fileItems.length; i++) {
                const item = fileItems[i];
                item.style.animation = 'fadeIn 0.3s ease-out forwards';
                item.style.opacity = '0';
                setTimeout(() => {
                    item.style.opacity = '1';
                    item.style.animation = '';
                }, 300);
            }
        }, 0);
        
        // Kích hoạt nút tải lên nếu có ít nhất 1 file
        this.confirmUploadBtn.disabled = this.files.length === 0;
    }
    
    removeFile(fileName) {
        this.files = this.files.filter(file => file.name !== fileName);
        this.renderFilesList();
        
        // Nếu không còn file nào, hiển thị lại khu vực kéo thả
        if (this.files.length === 0) {
            this.uploadArea.style.display = 'flex';
            this.uploadInfo.style.display = 'none';
            this.confirmUploadBtn.disabled = true;
        } else {
            // Cập nhật nút tải lên
            this.confirmUploadBtn.disabled = false;
        }
    }
    
    renderFilesList() {
        if (!this.uploadFilesList) return;
        
        this.uploadFilesList.innerHTML = '';
        
        this.files.forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            
            // Xác định icon dựa trên loại file
            const fileExtension = file.name.split('.').pop().toLowerCase();
            let iconClass = 'fa-file-alt';
            let iconExtraClass = '';
            
            if (fileExtension === 'pdf') {
                iconClass = 'fa-file-pdf';
                iconExtraClass = 'pdf';
            } else if (['doc', 'docx'].includes(fileExtension)) {
                iconClass = 'fa-file-word';
                iconExtraClass = 'doc';
            } else if (['txt', 'sql'].includes(fileExtension)) {
                iconClass = 'fa-file-code';
                iconExtraClass = 'txt';
            }
            
            fileItem.innerHTML = `
                <i class="fas ${iconClass} file-icon ${iconExtraClass}"></i>
                <div class="file-details">
                    <div class="file-name" title="${file.name}">${file.name}</div>
                    <div class="file-size">${this.formatFileSize(file.size)}</div>
                </div>
                <div class="file-actions">
                    <button class="file-remove" data-filename="${file.name}" title="Xóa">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            
            this.uploadFilesList.appendChild(fileItem);
            
            // Thêm event listener cho nút xóa
            const removeBtn = fileItem.querySelector('.file-remove');
            removeBtn.addEventListener('click', () => {
                this.removeFile(file.name);
            });
        });
    }

    async uploadFiles() {
        if (this.files.length === 0) return;
        
        console.log('Bắt đầu tải lên', this.files.length, 'file');
        console.log('Token xác thực:', apiService.getAuthToken() ? 'Có token' : 'Không có token');
        
        // Reset counters
        this.successCount = 0;
        this.failCount = 0;
        this.totalFiles = this.files.length;
        
        // Lưu tham chiếu đến các nút để có thể kích hoạt lại sau khi hoàn thành
        const closeModalBtn = document.querySelector('#uploadModal .close-modal-btn');
        const cancelUploadBtn = document.getElementById('cancelUploadBtn');
        let closingTimer = null;
        
        try {
            // Hiển thị spinner và cập nhật status
            this.uploadSpinner.style.display = 'flex';
            this.uploadStatus.innerHTML = `<b>Đang chuẩn bị...</b>`;
            this.confirmUploadBtn.disabled = true;
            
            // Vô hiệu hóa nút đóng modal và nút hủy
            if (closeModalBtn) closeModalBtn.disabled = true;
            if (cancelUploadBtn) cancelUploadBtn.disabled = true;
            
            // Vô hiệu hóa các nút xóa file
            const removeButtons = this.uploadFilesList.querySelectorAll('.file-remove');
            removeButtons.forEach(btn => btn.disabled = true);
            
            // Đánh dấu trạng thái các file
            const fileItems = this.uploadFilesList.querySelectorAll('.file-item');
            
            // Upload từng file một
            for (let i = 0; i < this.files.length; i++) {
                const file = this.files[i];
                const currentFileItem = fileItems[i];
                
                try {
                    // Cập nhật status với tiến trình hiện tại
                    this.uploadStatus.innerHTML = `<b>Đang tải lên...</b><br>${i+1}/${this.totalFiles} (${Math.round((i+1)/this.totalFiles*100)}%)`;
                    
                    // Đánh dấu file đang upload
                    if (currentFileItem) {
                        currentFileItem.style.backgroundColor = 'rgba(0, 120, 212, 0.1)';
                    }
                    
                    // Upload file
                    await apiService.uploadFile(file);
                    
                    // Đánh dấu thành công
                    this.successCount++;
                    if (currentFileItem) {
                        currentFileItem.style.backgroundColor = 'rgba(52, 168, 83, 0.1)';
                        currentFileItem.querySelector('.file-icon').insertAdjacentHTML('afterend', 
                            '<i class="fas fa-check-circle" style="color: #34A853; margin-left: -8px; margin-right: 8px;"></i>');
                    }
                } catch (fileError) {
                    console.error(`Lỗi khi tải lên file ${file.name}:`, fileError);
                    this.failCount++;
                    if (currentFileItem) {
                        currentFileItem.style.backgroundColor = 'rgba(231, 76, 60, 0.1)';
                        currentFileItem.querySelector('.file-icon').insertAdjacentHTML('afterend', 
                            '<i class="fas fa-times-circle" style="color: #E74C3C; margin-left: -8px; margin-right: 8px;"></i>');
                    }
                }
                
                // Cho phép hiển thị kết quả trước khi chuyển sang file tiếp theo
                await new Promise(resolve => setTimeout(resolve, 300));
            }
            
            // Hiển thị hiệu ứng thành công với đồ họa đẹp mắt
            let successContent = '';
            if (this.failCount === 0) {
                successContent = `
                    <div style="text-align:center; padding:1rem 0;">
                        <div style="position:relative; margin:0 auto; width:60px; height:60px;">
                            <i class="fas fa-check-circle" style="color:#34A853; font-size:60px; animation: scaleUp 0.4s ease-out;"></i>
                        </div>
                        <p style="color:#34A853; font-weight:500; margin-top:1rem; font-size:1rem;">
                            <b>Tải lên thành công ${this.successCount} file!</b>
                        </p>
                    </div>
                `;
            } else {
                successContent = `
                    <div style="text-align:center; padding:1rem 0;">
                        <div style="position:relative; margin:0 auto; width:60px; height:60px;">
                            <i class="fas fa-exclamation-triangle" style="color:#FFA000; font-size:60px; animation: scaleUp 0.4s ease-out;"></i>
                        </div>
                        <p style="color:#FFA000; font-weight:500; margin-top:1rem; font-size:1rem;">
                            <b>Tải lên ${this.successCount} thành công, ${this.failCount} thất bại.</b>
                        </p>
                    </div>
                `;
            }
            
            // Cập nhật nội dung modal
            const uploadInfo = document.getElementById('uploadInfo');
            if (uploadInfo) {
                // Lưu lại nội dung cũ
                const originalContent = uploadInfo.innerHTML;
                
                // Thay thế bằng nội dung thành công
                uploadInfo.innerHTML = successContent;
                
                // Áp dụng hiệu ứng CSS
                const style = document.createElement('style');
                style.innerHTML = `
                    @keyframes scaleUp {
                        0% { transform: scale(0.5); opacity: 0; }
                        70% { transform: scale(1.2); opacity: 1; }
                        100% { transform: scale(1); opacity: 1; }
                    }
                `;
                document.head.appendChild(style);
            }
            
            // QUAN TRỌNG: Kích hoạt lại các nút ngay sau khi hoàn thành
            if (closeModalBtn) closeModalBtn.disabled = false;
            if (cancelUploadBtn) cancelUploadBtn.disabled = false;
            
            // Thay đổi nút "Hủy" thành "Đóng"
            if (cancelUploadBtn) {
                cancelUploadBtn.textContent = 'Đóng';
                cancelUploadBtn.addEventListener('click', () => {
                    if (closingTimer) {
                        clearInterval(closingTimer);
                        closingTimer = null;
                    }
                }, { once: true });
            }
            
            // Tải lại danh sách nguồn ngay lập tức
            const sourceController = new SourceController();
            sourceController.loadSources();
            
            // Hiển thị bộ đếm thời gian đóng tự động
            let secondsLeft = 3;
            
            // Thêm thanh đếm ngược hiển thị đẹp mắt
            const countdownBar = document.createElement('div');
            countdownBar.innerHTML = `
                <div style="margin-top:1rem; text-align:center;">
                    <div style="background-color:var(--muted); height:4px; border-radius:2px; overflow:hidden; width:100%; max-width:200px; margin:0 auto;">
                        <div id="countdownFill" style="background-color:var(--primary); height:100%; width:100%; transition:width 3s linear;"></div>
                    </div>
                    <div style="margin-top:0.5rem; font-size:0.8rem; color:var(--muted-foreground);">
                        Tự động đóng sau <span id="countdown">${secondsLeft}</span> giây
                    </div>
                </div>
            `;
            
            uploadInfo.appendChild(countdownBar);
            
            // Animation thanh đếm ngược
            const countdownFill = document.getElementById('countdownFill');
            if (countdownFill) {
                setTimeout(() => {
                    countdownFill.style.width = '0%';
                }, 50);
            }
            
            const countdownSpan = document.getElementById('countdown');
            
            // Bắt đầu bộ đếm thời gian
            closingTimer = setInterval(() => {
                secondsLeft -= 1;
                if (countdownSpan) countdownSpan.textContent = secondsLeft;
                
                if (secondsLeft <= 0) {
                    clearInterval(closingTimer);
                    closingTimer = null;
                    
                    const modalController = new ModalController();
                    modalController.closeModal('uploadModal');
                    this.reset();
                }
            }, 1000);
            
        } catch (error) {
            this.uploadStatus.innerHTML = `<b style="color: #E74C3C;"><i class="fas fa-times-circle"></i> Lỗi: ${error.message}</b>`;
            
            // Kích hoạt lại các nút khi gặp lỗi
            if (closeModalBtn) closeModalBtn.disabled = false;
            if (cancelUploadBtn) cancelUploadBtn.disabled = false;
            this.confirmUploadBtn.disabled = false;
            
            // Kích hoạt lại các nút xóa file
            const removeButtons = this.uploadFilesList.querySelectorAll('.file-remove');
            removeButtons.forEach(btn => btn.disabled = false);
        } finally {
            // Hủy timer nếu cần thiết
            if (closingTimer) {
                clearInterval(closingTimer);
                closingTimer = null;
            }
            
            // Ẩn spinner sau khi hiển thị kết quả cuối cùng
            setTimeout(() => {
                this.uploadSpinner.style.display = 'none';
            }, 500);
        }
    }

    reset() {
        this.files = [];
        
        // Reset UI
        this.uploadArea.style.display = 'flex';
        this.uploadInfo.style.display = 'none';
        this.uploadSpinner.style.display = 'none';
        this.uploadStatus.textContent = 'Đang chuẩn bị...';
        this.confirmUploadBtn.disabled = true;
        
        // Xóa danh sách file
        if (this.uploadFilesList) {
            this.uploadFilesList.innerHTML = '';
        }
        
        // Reset file input
        document.getElementById('fileInput').value = '';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

/**
 * Controller quản lý lịch sử chat
 */
class ChatHistoryController {
    constructor() {
        this.historyItems = [];
        this.loadChatHistory();
        
        // Lắng nghe sự kiện đổi tab
        this.setupTabListeners();
        
        // Lắng nghe sự kiện tạo mới và xóa tất cả
        this.setupActionButtons();
        
        // Đảm bảo tab sources được chọn mặc định khi tải trang
        this.switchTab('sources');
    }
    
    setupTabListeners() {
        const sourcesTabBtn = document.getElementById('sourcesTabBtn');
        const historyTabBtn = document.getElementById('historyTabBtn');
        const sourcesTabContent = document.getElementById('sourcesTabContent');
        const historyTabContent = document.getElementById('historyTabContent');
        
        if (sourcesTabBtn && historyTabBtn) {
            sourcesTabBtn.addEventListener('click', () => {
                this.switchTab('sources');
            });
            
            historyTabBtn.addEventListener('click', () => {
                this.switchTab('history');
            });
        }
    }
    
    setupActionButtons() {
        const createNewBtn = document.getElementById('createNewChatBtn');
        const clearAllBtn = document.getElementById('clearAllHistoryBtn');
        
        if (createNewBtn) {
            createNewBtn.addEventListener('click', () => {
                // Tạo một cuộc trò chuyện mới và chuyển sang tab conversation
                window.conversationController.clearChat(false);
                const mobileNavController = new MobileNavController();
                mobileNavController.switchPanel('conversation');
            });
        }
        
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', () => {
                if (confirm('Bạn có chắc chắn muốn xóa tất cả lịch sử chat? Thao tác này không thể hoàn tác.')) {
                    this.clearAllHistory();
                }
            });
        }
    }
    
    switchTab(tabName) {
        const sourcesTabBtn = document.getElementById('sourcesTabBtn');
        const historyTabBtn = document.getElementById('historyTabBtn');
        const sourcesTabContent = document.getElementById('sourcesTabContent');
        const historyTabContent = document.getElementById('historyTabContent');
        
        if (tabName === 'sources') {
            sourcesTabBtn.classList.add('active');
            sourcesTabBtn.classList.add('text-blue-600');
            sourcesTabBtn.classList.add('border-b-2');
            sourcesTabBtn.classList.add('border-blue-600');
            
            historyTabBtn.classList.remove('active');
            historyTabBtn.classList.remove('text-blue-600');
            historyTabBtn.classList.remove('border-b-2');
            historyTabBtn.classList.remove('border-blue-600');
            historyTabBtn.classList.add('text-gray-500');
            
            sourcesTabContent.classList.add('active');
            historyTabContent.classList.remove('active');
        } else {
            sourcesTabBtn.classList.remove('active');
            sourcesTabBtn.classList.remove('text-blue-600');
            sourcesTabBtn.classList.remove('border-b-2');
            sourcesTabBtn.classList.remove('border-blue-600');
            sourcesTabBtn.classList.add('text-gray-500');
            
            historyTabBtn.classList.add('active');
            historyTabBtn.classList.add('text-blue-600');
            historyTabBtn.classList.add('border-b-2');
            historyTabBtn.classList.add('border-blue-600');
            
            sourcesTabContent.classList.remove('active');
            historyTabContent.classList.add('active');
        }
    }
    
    async loadChatHistory() {
        try {
            // Hiển thị loading
            document.getElementById('historyList').innerHTML = `
                <div class="loading-message" style="text-align: center; padding: 2rem;">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Đang tải lịch sử chat...</p>
                </div>`;
                
            // Lấy thông tin người dùng hiện tại
            const currentUser = apiService.getUserInfo();
            const userInfo = currentUser ? currentUser : { id: 'guest' };
            
            // Gọi API để lấy lịch sử chat cho user hiện tại
            // Sử dụng getConversations thay vì getChatHistory
            const response = await apiService.getConversations();
            
            // Kiểm tra response và khởi tạo historyItems
            if (response && response.status === 'success' && Array.isArray(response.data)) {
                // Chỉ hiển thị hội thoại của người dùng hiện tại
                if (userInfo && userInfo.id !== 'guest') {
                    this.historyItems = response.data.filter(item => {
                        return item.user_id === userInfo.id;
                    });
                } else {
                    this.historyItems = response.data;
                }
            } else {
                console.warn('API trả về dữ liệu không đúng định dạng:', response);
                this.historyItems = [];
            }
            
            // Render lịch sử chat
            this.renderChatHistory();
        } catch (error) {
            console.error('Lỗi khi tải lịch sử chat:', error);
            this.historyItems = []; // Đảm bảo historyItems luôn là mảng
            
            document.getElementById('historyList').innerHTML = `
                <div class="error-message" style="text-align: center; padding: 2rem;">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>Không thể tải lịch sử chat. Vui lòng thử lại sau.</p>
                </div>`;
        }
    }
    
    renderChatHistory() {
        const historyList = document.getElementById('historyList');
        
        // Đảm bảo this.historyItems luôn là mảng
        if (!Array.isArray(this.historyItems)) {
            console.warn('this.historyItems không phải là mảng:', this.historyItems);
            this.historyItems = [];
        }
        
        if (this.historyItems.length === 0) {
            historyList.innerHTML = `
                <div class="empty-history-message">
                    <i class="fas fa-history"></i>
                    <p>Chưa có cuộc trò chuyện nào</p>
                </div>`;
            return;
        }
        
        // Sắp xếp theo thời gian giảm dần (mới nhất lên đầu)
        const sortedItems = [...this.historyItems].sort((a, b) => {
            const dateA = new Date(a.last_updated || a.timestamp || 0);
            const dateB = new Date(b.last_updated || b.timestamp || 0);
            return dateB - dateA;
        });
        
        let historyHTML = '';
        
        sortedItems.forEach(item => {
            // Lấy ngày từ last_updated hoặc timestamp
            const date = new Date(item.last_updated || item.timestamp || new Date());
            const formattedDate = this.formatDate(date);
            
            // Lấy ID của item (có thể là item.id hoặc item.conversation_id)
            const itemId = item.id || item.conversation_id || '';
            
            // Trích xuất tiêu đề hoặc tin nhắn đầu tiên
            let title = item.title || 'Cuộc trò chuyện mới';
            if (!item.title && item.first_message) {
                title = item.first_message;
                if (title.length > 60) {
                    title = title.substring(0, 60) + '...';
                }
            }
            
            // Hiển thị số lượng tin nhắn nếu có
            const messageCount = item.message_count 
                ? `<span class="text-xs text-gray-500 ml-2">${item.message_count} tin nhắn</span>` 
                : '';
            
            historyHTML += `
                <div class="history-item" data-id="${itemId}">
                    <div class="history-item-content">
                        <div class="history-item-title">${title}</div>
                        <div class="history-item-date">${formattedDate} ${messageCount}</div>
                    </div>
                    <button class="history-item-delete" data-id="${itemId}" title="Xóa cuộc trò chuyện này">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>`;
        });
        
        historyList.innerHTML = historyHTML;
        
        // Thêm event listener cho các mục lịch sử
        document.querySelectorAll('.history-item').forEach(item => {
            const chatId = item.getAttribute('data-id');
            
            // Click vào mục để tải phiên chat
            item.addEventListener('click', (e) => {
                // Đảm bảo không bắt sự kiện click từ nút xóa
                if (!e.target.closest('.history-item-delete')) {
                    this.loadChatSession(chatId);
                }
            });
            
            // Nút xóa riêng cho từng mục
            const deleteBtn = item.querySelector('.history-item-delete');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation(); // Ngăn sự kiện click lan đến parent
                    this.deleteHistoryItem(chatId);
                });
            }
        });
    }
    
    async loadChatSession(chatId) {
        try {
            // Thêm class active cho mục được chọn
            document.querySelectorAll('.history-item').forEach(item => {
                if (item.getAttribute('data-id') === chatId) {
                    item.classList.add('active');
                } else {
                    item.classList.remove('active');
                }
            });
            
            // Hiển thị loading
            window.conversationController.showLoadingMessage();
            
            // Gọi API để lấy dữ liệu của phiên chat
            const response = await apiService.getMessages(chatId);
            
            if (!response || response.status === 'error') {
                throw new Error(response?.message || 'Không thể tải tin nhắn của cuộc trò chuyện');
            }
            
            // Kiểm tra cấu trúc dữ liệu để tránh lỗi ForEach
            if (!response.data || !response.data.messages) {
                console.error('Cấu trúc dữ liệu không đúng:', response);
                throw new Error('Cấu trúc dữ liệu tin nhắn không hợp lệ');
            }
            
            const messages = response.data.messages;
            
            // Đảm bảo messages là một mảng
            if (!Array.isArray(messages)) {
                console.error('Dữ liệu messages không phải là mảng:', messages);
                throw new Error('Dữ liệu messages không phải là mảng');
            }
            
            // Lưu conversation_id hiện tại
            apiService.setConversationId(chatId);
            
            // Chuyển đến panel conversation và hiển thị dữ liệu
            const mobileNavController = new MobileNavController();
            mobileNavController.switchPanel('conversation');
            
            // Xóa tin nhắn cũ trong giao diện
            window.conversationController.clearChat(false);
            
            // Hiển thị các tin nhắn
            let userSources = [];
            
            messages.forEach((message, index) => {
                if (message.role === 'user') {
                    // Nếu là tin nhắn cuối cùng của người dùng, lưu lại sources của nó
                    // để hiển thị với tin nhắn AI tiếp theo
                    if (index < messages.length - 1 && messages[index + 1].role === 'assistant') {
                        if (message.metadata && message.metadata.sources) {
                            userSources = message.metadata.sources;
                        }
                    }
                    
                    window.conversationController.addMessage(message.content, 'user');
                } else if (message.role === 'assistant') {
                    // Lấy sources từ metadata hoặc từ tin nhắn người dùng trước đó
                    let sources = [];
                    if (message.metadata && message.metadata.sources) {
                        sources = message.metadata.sources;
                    } else if (userSources.length > 0) {
                        sources = userSources;
                        userSources = []; // Reset sau khi sử dụng
                    }
                    
                    window.conversationController.addMessage(message.content, 'assistant', sources);
                }
            });
            
            // Cuộn xuống cuối
            window.conversationController.scrollToBottom();
            
            // Xóa loading
            window.conversationController.removeLoadingMessage();
        } catch (error) {
            console.error('Lỗi khi tải phiên chat:', error);
            window.conversationController.removeLoadingMessage();
            showNotification('Không thể tải nội dung hội thoại: ' + error.message, 'error');
        }
    }
    
    async deleteHistoryItem(chatId) {
        if (!confirm('Bạn có chắc chắn muốn xóa cuộc trò chuyện này?')) {
            return;
        }
        
        try {
            // Thay đổi trạng thái nút xóa để hiển thị đang tải
            const deleteBtn = document.querySelector(`.history-item-delete[data-id="${chatId}"]`);
            if (deleteBtn) {
                const originalHTML = deleteBtn.innerHTML;
                deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                deleteBtn.disabled = true;
            }
            
            // Gọi API để xóa chat session - sử dụng deleteConversation thay vì deleteChatSession
            await apiService.deleteConversation(chatId);
            
            // Xóa khỏi danh sách hiện tại
            this.historyItems = this.historyItems.filter(item => {
                const itemId = item.id || item.conversation_id;
                return itemId !== chatId;
            });
            
            // Cập nhật lại giao diện
            this.renderChatHistory();
            
            // Hiển thị thông báo thành công
            showNotification('Đã xóa cuộc trò chuyện thành công', 'success');
        } catch (error) {
            console.error('Lỗi khi xóa phiên chat:', error);
            
            // Khôi phục nút xóa nếu có lỗi
            const deleteBtn = document.querySelector(`.history-item-delete[data-id="${chatId}"]`);
            if (deleteBtn) {
                deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
                deleteBtn.disabled = false;
            }
            
            showNotification('Không thể xóa cuộc trò chuyện. Vui lòng thử lại sau.', 'error');
        }
    }
    
    async clearAllHistory() {
        try {
            // Hiển thị loading
            const historyList = document.getElementById('historyList');
            historyList.innerHTML = `
                <div class="loading-message" style="text-align: center; padding: 2rem;">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Đang xóa tất cả lịch sử...</p>
                </div>`;
            
            // Gọi API để xóa tất cả lịch sử 
            for (const item of this.historyItems) {
                // Lấy id của item (có thể là item.id hoặc item.conversation_id)
                const itemId = item.id || item.conversation_id || item.session_id;
                if (itemId) {
                    try {
                        await apiService.deleteConversation(itemId);
                        console.log(`Đã xóa cuộc trò chuyện ${itemId}`);
                    } catch (err) {
                        console.error(`Không thể xóa cuộc trò chuyện ${itemId}:`, err);
                    }
                }
            }
            
            // Xóa khỏi bộ nhớ
            this.historyItems = [];
            
            // Cập nhật giao diện
            this.renderChatHistory();
            
            // Tạo một cuộc trò chuyện mới
            console.log('Đang tạo hội thoại mới sau khi xóa tất cả...');
            const newConversation = await apiService.createConversation();
            console.log('Kết quả tạo hội thoại mới:', newConversation);
            
            if (newConversation && newConversation.status === 'success' && newConversation.conversation_id) {
                console.log('Đã tạo hội thoại mới thành công, ID mới:', newConversation.conversation_id);
                apiService.setConversationId(newConversation.conversation_id);
                
                // Làm mới giao diện chat để bắt đầu cuộc trò chuyện mới
                window.conversationController.clearChat(false);
            } else {
                console.error('Không thể tạo hội thoại mới:', newConversation?.message || 'Lỗi không xác định');
                showNotification('Không thể tạo hội thoại mới. Vui lòng tải lại trang.', 'error');
            }
            
            // Hiển thị thông báo thành công
            showNotification('Đã xóa toàn bộ lịch sử chat', 'success');
        } catch (error) {
            console.error('Lỗi khi xóa tất cả lịch sử:', error);
            this.loadChatHistory(); // Tải lại danh sách nếu có lỗi
            showNotification('Không thể xóa toàn bộ lịch sử. Vui lòng thử lại sau.', 'error');
        }
    }
    
    searchChatHistory(query) {
        if (!query || query.trim() === '') {
            this.renderChatHistory();
            return;
        }
        
        const searchTerm = query.toLowerCase().trim();
        const filteredItems = this.historyItems.filter(item => 
            (item.title && item.title.toLowerCase().includes(searchTerm)) || 
            (item.content && item.content.toLowerCase().includes(searchTerm))
        );
        
        const historyList = document.getElementById('historyList');
        
        if (filteredItems.length === 0) {
            historyList.innerHTML = `
                <div class="empty-history-message">
                    <i class="fas fa-search"></i>
                    <p>Không tìm thấy kết quả cho "${query}"</p>
                </div>`;
            return;
        }
        
        // Sắp xếp theo thời gian giảm dần (mới nhất lên đầu)
        const sortedItems = [...filteredItems].sort((a, b) => 
            new Date(b.timestamp) - new Date(a.timestamp)
        );
        
        let historyHTML = '';
        
        sortedItems.forEach(item => {
            const date = new Date(item.timestamp);
            const formattedDate = this.formatDate(date);
            
            historyHTML += `
                <div class="history-item" data-id="${item.id}">
                    <div class="history-item-content">
                        <div class="history-item-title">${item.title || 'Cuộc trò chuyện mới'}</div>
                        ${previewText ? `<div class="text-xs text-gray-500 mb-1 mt-0.5">${previewText}</div>` : ''}
                        <div class="history-item-date">${formattedDate}</div>
                    </div>
                    <button class="history-item-delete" data-id="${item.id}" title="Xóa cuộc trò chuyện này">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>`;
        });
        
        historyList.innerHTML = historyHTML;
        
        // Thêm event listener cho các mục lịch sử
        document.querySelectorAll('.history-item').forEach(item => {
            const chatId = item.getAttribute('data-id');
            
            // Click vào mục để tải phiên chat
            item.addEventListener('click', (e) => {
                // Đảm bảo không bắt sự kiện click từ nút xóa
                if (!e.target.closest('.history-item-delete')) {
                    this.loadChatSession(chatId);
                }
            });
            
            // Nút xóa riêng cho từng mục
            const deleteBtn = item.querySelector('.history-item-delete');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation(); // Ngăn sự kiện click lan đến parent
                    this.deleteHistoryItem(chatId);
                });
            }
        });
    }
    
    formatDate(date) {
        const now = new Date();
        const yesterday = new Date(now);
        yesterday.setDate(now.getDate() - 1);
        
        const isToday = date.toDateString() === now.toDateString();
        const isYesterday = date.toDateString() === yesterday.toDateString();
        
        if (isToday) {
            return `${date.getDate()}/${(date.getMonth() + 1)}/${date.getFullYear()}, ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
        } else if (isYesterday) {
            return `${date.getDate()}/${(date.getMonth() + 1)}/${date.getFullYear()}, ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
        } else {
            return `${date.getDate()}/${(date.getMonth() + 1)}/${date.getFullYear()}, ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
        }
    }
} 