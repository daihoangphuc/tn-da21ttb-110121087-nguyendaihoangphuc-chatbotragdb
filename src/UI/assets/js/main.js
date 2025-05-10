document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo các controllers
    const themeController = new ThemeController();
    const sourceController = new SourceController();
    const conversationController = new ConversationController();
    const sourceViewController = new SourceViewController();
    const mobileNavController = new MobileNavController();
    const uploadController = new UploadController();
    const modalController = new ModalController();
    const chatHistoryController = new ChatHistoryController();
    
    // Lưu conversationController vào window để có thể truy cập từ các controller khác
    window.conversationController = conversationController;

    // Khởi tạo các component Flowbite
    initFlowbiteComponents();

    // Kiểm tra trạng thái API khi khởi động
    checkApiConnection();

    // Toggle theme
    document.getElementById('themeToggle').addEventListener('click', function() {
        themeController.toggleTheme();
    });

    // Xử lý user dropdown (vì Flowbite dropdown có thể không hoạt động với cấu trúc hiện tại)
    const userDropdownTrigger = document.querySelector('.user-dropdown-trigger');
    const userDropdownContent = document.querySelector('.user-dropdown-content');
    
    if (userDropdownTrigger && userDropdownContent) {
        // Mở/đóng dropdown khi click
        userDropdownTrigger.addEventListener('click', function(e) {
            e.preventDefault();
            userDropdownContent.classList.toggle('hidden');
        });
        
        // Đóng dropdown khi click bên ngoài
        document.addEventListener('click', function(e) {
            if (!userDropdownTrigger.contains(e.target) && !userDropdownContent.contains(e.target)) {
                userDropdownContent.classList.add('hidden');
            }
        });
        
        // Lắng nghe sự kiện thay đổi theme
        document.addEventListener('themeChange', function(e) {
            if (e.detail.darkMode) {
                userDropdownContent.classList.add('dark-dropdown');
            } else {
                userDropdownContent.classList.remove('dark-dropdown');
            }
        });
        
        // Cập nhật trạng thái dropdown ngay khi trang tải
        if (document.body.classList.contains('dark-theme')) {
            userDropdownContent.classList.add('dark-dropdown');
        } else {
            userDropdownContent.classList.remove('dark-dropdown');
        }
    }

    // Lắng nghe sự kiện submit form tin nhắn
    document.getElementById('messageForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (message) {
            conversationController.sendMessage(message);
            messageInput.value = '';
        }
    });

    // Enable/disable nút gửi dựa trên input
    document.getElementById('messageInput').addEventListener('input', function(e) {
        const sendButton = document.getElementById('sendButton');
        sendButton.disabled = e.target.value.trim() === '';
    });

    // Xử lý tìm kiếm lịch sử chat
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const query = e.target.value.trim();
            chatHistoryController.searchChatHistory(query);
            
            // Tự động chuyển đến tab lịch sử nếu đang tìm kiếm
            if (query !== '') {
                chatHistoryController.switchTab('history');
            }
        });
    }

    // Xử lý chọn tất cả nguồn
    document.getElementById('selectAll').addEventListener('change', function(e) {
        sourceController.selectAll(e.target.checked);
    });

    // Mở modal upload
    document.getElementById('addSourceBtn').addEventListener('click', function() {
        modalController.openModal('uploadModal');
    });

    // Mở panel nguồn trên mobile
    document.getElementById('viewSourcesBtn').addEventListener('click', function() {
        mobileNavController.switchPanel('sources');
    });

    // Quay lại conversation từ source view trên mobile
    document.getElementById('backToConversationBtn').addEventListener('click', function() {
        mobileNavController.switchPanel('conversation');
    });

    // Xử lý mobile navigation
    document.querySelectorAll('.nav-button').forEach(button => {
        button.addEventListener('click', function() {
            const panel = this.getAttribute('data-panel');
            mobileNavController.switchPanel(panel);
        });
    });

    // Thu gọn/mở rộng Source View Panel
    document.getElementById('collapseSourceViewBtn').addEventListener('click', function() {
        const sourceViewPanel = document.getElementById('sourceViewPanel');
        sourceViewPanel.classList.toggle('collapsed');
        
        // Lưu trạng thái vào sessionStorage
        sessionStorage.setItem('sourceViewPanelCollapsed', sourceViewPanel.classList.contains('collapsed'));
    });
    
    // Khôi phục trạng thái thu gọn/mở rộng từ sessionStorage
    if (sessionStorage.getItem('sourceViewPanelCollapsed') === 'true') {
        document.getElementById('sourceViewPanel').classList.add('collapsed');
    }

    // Xử lý clear chat button
    document.getElementById('clear-chat-btn').addEventListener('click', function() {
        if (confirm('Bạn có chắc chắn muốn xóa tất cả tin nhắn trong cuộc trò chuyện hiện tại?')) {
            conversationController.clearChat();
        }
    });

    // Xử lý upload modal
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    // Drag & drop handling
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });

    uploadArea.addEventListener('dragleave', function() {
        uploadArea.classList.remove('drag-over');
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        
        if (e.dataTransfer.files.length) {
            uploadController.addFiles(e.dataTransfer.files);
        }
    });

    fileInput.addEventListener('change', function() {
        if (this.files.length) {
            uploadController.addFiles(this.files);
        }
    });

    // Upload modal buttons
    document.getElementById('cancelUploadBtn').addEventListener('click', function() {
        modalController.closeModal('uploadModal');
        uploadController.reset();
    });

    document.getElementById('confirmUploadBtn').addEventListener('click', function() {
        uploadController.uploadFiles();
    });

    // Delete modal buttons
    document.getElementById('cancelDeleteBtn').addEventListener('click', function() {
        modalController.closeModal('deleteModal');
        sourceController.resetDeleteState();
        modalController.resetDeleteModal();
    });

    document.getElementById('confirmDeleteBtn').addEventListener('click', function() {
        // Vô hiệu hóa nút xóa trong modal khi đang thực hiện xóa
        this.disabled = true;
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang xóa...';
        
        // Vô hiệu hóa nút hủy khi đang xóa
        document.getElementById('cancelDeleteBtn').disabled = true;
        
        // Không đóng modal ở đây, để modal đóng sau khi hoàn tất xóa
        sourceController.deleteSelectedFile();
    });

    // Close buttons for modals
    document.querySelectorAll('.close-modal-btn').forEach(button => {
        button.addEventListener('click', function() {
            const modal = this.closest('.modal');
            modalController.closeModal(modal.id);
            
            if (modal.id === 'uploadModal') {
                uploadController.reset();
            } else if (modal.id === 'deleteModal') {
                sourceController.resetDeleteState();
                modalController.resetDeleteModal();
            }
        });
    });

    // Thêm sự kiện cho overlay để có thể đóng modal bằng cách click bên ngoài
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', function() {
            const modal = this.closest('.modal');
            modalController.closeModal(modal.id);
            
            if (modal.id === 'uploadModal') {
                uploadController.reset();
            } else if (modal.id === 'deleteModal') {
                sourceController.resetDeleteState();
                modalController.resetDeleteModal();
            }
        });
    });

    // Kiểm tra kết nối API
    async function checkApiConnection() {
        try {
            console.log("Đang kiểm tra kết nối API...");
            const status = await apiService.checkApiStatus();
            console.log("Kết nối API thành công:", status);
            document.getElementById('apiAlert').style.display = 'none';
            return true;
        } catch (error) {
            console.error("Lỗi kết nối API:", error);
            document.getElementById('apiAlertMessage').textContent = error.message || 'Không thể kết nối đến API. Vui lòng kiểm tra lại kết nối.';
            document.getElementById('apiAlert').style.display = 'flex';
            return false;
        }
    }

    // Khởi tạo các component của Flowbite
    function initFlowbiteComponents() {
        // Nếu đối tượng flowbite có sẵn, khởi tạo các component
        if (typeof flowbite !== 'undefined') {
            // Khởi tạo tooltips
            const tooltipElements = document.querySelectorAll('[data-tooltip-target]');
            if (tooltipElements.length) {
                tooltipElements.forEach(el => {
                    new flowbite.Tooltip(el);
                });
            }
            
            // Khởi tạo dropdowns
            const dropdownElements = document.querySelectorAll('[data-dropdown-toggle]');
            if (dropdownElements.length) {
                dropdownElements.forEach(el => {
                    new flowbite.Dropdown(el);
                });
            }
        }
    }

    // Chắc chắn rằng ban đầu sourcePanel hiển thị trên desktop
    if (window.innerWidth >= 640) {
        document.getElementById('sourcePanel').style.display = 'flex';
        document.getElementById('sourceViewPanel').style.display = 'flex';
    }
}); 