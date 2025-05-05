document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo các controllers
    const themeController = new ThemeController();
    const sourceController = new SourceController();
    const conversationController = new ConversationController();
    const sourceViewController = new SourceViewController();
    const mobileNavController = new MobileNavController();
    const uploadController = new UploadController();
    const modalController = new ModalController();

    // Kiểm tra trạng thái API khi khởi động
    checkApiConnection();

    // Toggle theme
    document.getElementById('themeToggle').addEventListener('click', function() {
        themeController.toggleTheme();
    });

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
        
        // Lưu trạng thái vào localStorage
        localStorage.setItem('sourceViewPanelCollapsed', sourceViewPanel.classList.contains('collapsed'));
    });
    
    // Khôi phục trạng thái thu gọn/mở rộng từ localStorage
    if (localStorage.getItem('sourceViewPanelCollapsed') === 'true') {
        document.getElementById('sourceViewPanel').classList.add('collapsed');
    }

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

    // Chắc chắn rằng ban đầu sourcePanel hiển thị trên desktop
    if (window.innerWidth >= 640) {
        document.getElementById('sourcePanel').style.display = 'flex';
        document.getElementById('sourceViewPanel').style.display = 'flex';
    }
}); 