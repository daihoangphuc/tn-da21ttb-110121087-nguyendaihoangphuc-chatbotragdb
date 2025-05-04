document.addEventListener('DOMContentLoaded', function() {
    // API URL cơ sở - thay đổi khi triển khai
    const API_BASE_URL = 'http://localhost:8000/api'; 
    
    // Cấu hình axios
    const axiosInstance = axios.create({
        baseURL: API_BASE_URL,
        headers: {
            'Content-Type': 'application/json'
        }
    });

    // Biến lưu trữ trạng thái ứng dụng
    const appState = {
        documents: [],
        taskId: null,
        currentSources: [],
        isUploading: false,
        selectedSourceIndex: null
    };

    // Các elements
    const elements = {
        conversationContainer: document.getElementById('conversation'),
        queryForm: document.getElementById('query-form'),
        queryInput: document.getElementById('query-input'),
        sourcePanel: document.getElementById('source-panel'),
        sourceContent: document.getElementById('source-content'),
        sourceModal: document.getElementById('source-modal'),
        sourceModalContent: document.getElementById('source-modal-content'),
        uploadModal: document.getElementById('upload-modal'),
        uploadForm: document.getElementById('upload-form'),
        fileUpload: document.getElementById('file-upload'),
        fileList: document.getElementById('file-list'),
        selectedFiles: document.getElementById('selected-files'),
        uploadProgress: document.getElementById('upload-progress'),
        progressBar: document.getElementById('progress-bar'),
        progressText: document.getElementById('progress-text'),
        sidebar: document.getElementById('sidebar'),
        documentList: document.getElementById('document-list'),
        documentsLoading: document.getElementById('documents-loading'),
        connectionModal: document.getElementById('connection-modal'),
        connectionErrorMessage: document.getElementById('connection-error-message')
    };

    // Các buttons
    const buttons = {
        uploadButton: document.getElementById('upload-button'),
        uploadButtonMobile: document.getElementById('upload-button-mobile'),
        closeUploadModal: document.getElementById('close-upload-modal'),
        cancelUpload: document.getElementById('cancel-upload'),
        submitUpload: document.getElementById('submit-upload'),
        mobileMenuButton: document.getElementById('mobile-menu-button'),
        closeSidebar: document.getElementById('close-sidebar'),
        closeSourceModal: document.getElementById('close-source-modal'),
        refreshDocuments: document.getElementById('refresh-documents'),
        checkConnection: document.getElementById('check-connection-btn')
    };

    // API URLs - sử dụng URL cơ sở 
    const API = {
        baseUrl: API_BASE_URL,
        query: `${API_BASE_URL}/query`,
        upload: `${API_BASE_URL}/upload`,
        files: `${API_BASE_URL}/files`,
        indexStatus: (taskId) => `${API_BASE_URL}/index/status/${taskId}`,
        indexProgress: (taskId) => `${API_BASE_URL}/index/progress/${taskId}`,
        health: `${API_BASE_URL}/`
    };

    // Khởi tạo ứng dụng
    initApp();
    
    // Khởi tạo ứng dụng
    function initApp() {
        // Khởi tạo sự kiện
        initEventListeners();
        
        // Khởi tạo toast container
        initToasts();
        
        // Kiểm tra kết nối đến API
        checkAPIConnection();
        
        // Tải danh sách tài liệu ngay khi trang tải xong
        loadDocuments();
        
        console.log('Ứng dụng đã khởi tạo, đang tải danh sách tài liệu...');
    }

    // Khởi tạo container cho toast messages
    function initToasts() {
        // Kiểm tra nếu đã có toast container
        if (document.getElementById('toast-container')) return;
        
        // Tạo toast container
        const toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'fixed bottom-4 right-4 flex flex-col space-y-2 z-50';
        document.body.appendChild(toastContainer);
    }

    // Hiển thị toast message
    function showToast(message, type = 'info', duration = 3000) {
        const toastContainer = document.getElementById('toast-container');
        
        if (!toastContainer) return;
        
        // Tạo toast element
        const toast = document.createElement('div');
        const id = 'toast-' + Date.now();
        toast.id = id;
        
        // Xác định class dựa trên loại toast
        let bgColorClass, iconHtml;
        
        switch (type) {
            case 'success':
                bgColorClass = 'bg-green-500';
                iconHtml = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>';
                break;
            case 'error':
                bgColorClass = 'bg-red-500';
                iconHtml = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>';
                break;
            case 'warning':
                bgColorClass = 'bg-yellow-500';
                iconHtml = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>';
                break;
            default: // info
                bgColorClass = 'bg-blue-500';
                iconHtml = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>';
        }
        
        // Tạo nội dung toast
        toast.className = `${bgColorClass} text-white rounded-md shadow-lg transform transition-all duration-300 ease-in-out px-4 py-3 flex items-center opacity-0 translate-x-full`;
        toast.innerHTML = `
            <div class="mr-2">
                ${iconHtml}
            </div>
            <div class="flex-1">
                <p class="text-sm font-medium">${message}</p>
            </div>
            <button class="ml-2 text-white focus:outline-none">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        `;
        
        // Thêm toast vào container
        toastContainer.appendChild(toast);
        
        // Thêm event listener cho nút đóng
        const closeButton = toast.querySelector('button');
        closeButton.addEventListener('click', () => removeToast(id));
        
        // Animation hiển thị toast
        setTimeout(() => {
            toast.classList.remove('opacity-0', 'translate-x-full');
        }, 50);
        
        // Tự động xóa toast sau thời gian
        setTimeout(() => removeToast(id), duration);
        
        return id;
    }

    // Xóa toast message
    function removeToast(id) {
        const toast = document.getElementById(id);
        if (!toast) return;
        
        // Animation ẩn toast
        toast.classList.add('opacity-0', 'translate-x-full');
        
        // Xóa toast sau khi animation hoàn thành
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }

    // Khởi tạo các sự kiện
    function initEventListeners() {
        // Xử lý form truy vấn
        elements.queryForm.addEventListener('submit', handleQuery);

        // Nút upload và modal - chỉ mở modal, không xử lý upload
        buttons.uploadButton.addEventListener('click', () => showModal(elements.uploadModal));
        buttons.uploadButtonMobile.addEventListener('click', () => showModal(elements.uploadModal));
        buttons.closeUploadModal.addEventListener('click', () => hideModal(elements.uploadModal));
        buttons.cancelUpload.addEventListener('click', () => hideModal(elements.uploadModal));
        
        // Mobile menu
        buttons.mobileMenuButton.addEventListener('click', toggleSidebar);
        buttons.closeSidebar.addEventListener('click', toggleSidebar);

        // Modal nguồn
        buttons.closeSourceModal.addEventListener('click', () => hideModal(elements.sourceModal));
        
        // Refresh documents button
        if (buttons.refreshDocuments) {
            buttons.refreshDocuments.addEventListener('click', loadDocuments);
        }
        
        // Check connection button
        if (buttons.checkConnection) {
            buttons.checkConnection.addEventListener('click', checkAPIConnection);
        }
        
        // Export loadDocuments to window for upload script
        window.loadDocuments = loadDocuments;
    }

    // Kiểm tra kết nối API
    async function checkAPIConnection() {
        console.log("Kiểm tra kết nối API tại:", API.health);
        
        try {
            const response = await axiosInstance.get('/');
            
            if (elements.connectionModal) {
                elements.connectionModal.classList.add('hidden');
            }
        } catch (error) {
            console.error("Kết nối API thất bại:", error);
            
            if (elements.connectionModal && elements.connectionErrorMessage) {
                elements.connectionErrorMessage.textContent = "Không thể kết nối đến API backend. Hãy đảm bảo API đang chạy và truy cập được từ địa chỉ: " + API_BASE_URL;
                elements.connectionModal.classList.remove('hidden');
            }
        }
    }

    // Xử lý truy vấn
    async function handleQuery(e) {
        e.preventDefault();
        const query = elements.queryInput.value.trim();
        
        if (!query) return;

        // Hiển thị truy vấn của người dùng
        appendMessage('user', query);
        elements.queryInput.value = '';
        
        // Hiển thị indicator đang tải
        const loadingId = appendLoadingMessage();

        try {
            const response = await axiosInstance.post('/query', { query });
            
            // Xóa indicator đang tải
            removeLoadingMessage(loadingId);
            
            // Hiển thị câu trả lời
            appendMessage('system', response.data.response, response.data.sources);
            
            // Lưu trữ nguồn để hiển thị bên panel
            appState.currentSources = response.data.sources;
            
            // Nếu có sources, hiển thị source đầu tiên
            if (response.data.sources && response.data.sources.length > 0) {
                showSourcePanel();
                showSource(0);
            }
        } catch (error) {
            console.error('Error:', error);
            removeLoadingMessage(loadingId);
            appendMessage('error', 'Đã xảy ra lỗi khi xử lý truy vấn của bạn.');
        }
    }

    // Hiển thị source panel
    function showSourcePanel() {
        elements.sourcePanel.classList.remove('hidden');
    }

    // Ẩn source panel
    function hideSourcePanel() {
        elements.sourcePanel.classList.add('hidden');
    }

    // Thêm tin nhắn vào cuộc trò chuyện
    function appendMessage(type, message, sources = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `mb-4 ${type === 'user' ? 'ml-auto' : 'mr-auto'} max-w-[80%]`;
        messageDiv.id = 'msg-' + Date.now();
        
        let messageContent = '';
        
        if (type === 'user') {
            messageContent = `
                <div class="flex items-start justify-end">
                    <div class="bg-blue-600 text-white p-3 rounded-lg">
                        <p>${escapeHtml(message)}</p>
                    </div>
                </div>
            `;
        } else if (type === 'system') {
            messageContent = `
                <div class="flex items-start">
                    <div class="bg-white p-3 rounded-lg shadow-sm border border-gray-200">
                        <div class="prose prose-sm max-w-none">${markdownToHtml(message)}</div>
                        ${sources && sources.length > 0 ? createSourcesList(sources) : ''}
                    </div>
                </div>
            `;
        } else if (type === 'error') {
            messageContent = `
                <div class="flex items-start">
                    <div class="bg-red-50 p-3 rounded-lg text-red-600 border border-red-100">
                        <p>${escapeHtml(message)}</p>
                    </div>
                </div>
            `;
        }
        
        messageDiv.innerHTML = messageContent;
        elements.conversationContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        elements.conversationContainer.scrollTop = elements.conversationContainer.scrollHeight;
        
        // Add click handlers for sources if present
        if (sources && sources.length > 0) {
            sources.forEach((_, index) => {
                const sourceButton = messageDiv.querySelector(`[data-source-index="${index}"]`);
                if (sourceButton) {
                    sourceButton.addEventListener('click', () => showSource(index));
                }
            });
        }
        
        return messageDiv.id;
    }

    // Thêm thông báo đang tải
    function appendLoadingMessage() {
        const loadingId = 'loading-' + Date.now();
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'mb-4 mr-auto';
        loadingDiv.id = loadingId;
        
        loadingDiv.innerHTML = `
            <div class="flex items-start">
                <div class="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
                    <div class="flex items-center space-x-2">
                        <div class="animate-pulse flex space-x-2">
                            <div class="h-2 w-2 bg-blue-600 rounded-full"></div>
                            <div class="h-2 w-2 bg-blue-600 rounded-full"></div>
                            <div class="h-2 w-2 bg-blue-600 rounded-full"></div>
                        </div>
                        <p class="text-gray-500">Đang xử lý...</p>
                    </div>
                </div>
            </div>
        `;
        
        elements.conversationContainer.appendChild(loadingDiv);
        elements.conversationContainer.scrollTop = elements.conversationContainer.scrollHeight;
        
        return loadingId;
    }

    // Xóa thông báo đang tải
    function removeLoadingMessage(id) {
        const loadingElement = document.getElementById(id);
        if (loadingElement) {
            loadingElement.remove();
        }
    }

    // Tạo danh sách nguồn
    function createSourcesList(sources) {
        if (!sources || sources.length === 0) return '';
        
        let sourcesList = `
            <div class="mt-3 pt-3 border-t border-gray-100">
                <p class="text-xs text-gray-500 mb-2">Nguồn (${sources.length}):</p>
                <div class="flex flex-wrap gap-2">
        `;
        
        sources.forEach((source, index) => {
            const fileName = source.source_path.split('/').pop();
            sourcesList += `
                <button data-source-index="${index}" class="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded-full text-gray-700 flex items-center">
                    <span class="truncate max-w-[150px]">${escapeHtml(fileName)}</span>
                </button>
            `;
        });
        
        sourcesList += `
                </div>
            </div>
        `;
        
        return sourcesList;
    }

    // Hiển thị nguồn
    function showSource(index) {
        if (!appState.currentSources || !appState.currentSources[index]) return;
        
        const source = appState.currentSources[index];
        const fileName = source.source_path.split('/').pop();
        appState.selectedSourceIndex = index;
        
        // Chuẩn bị nội dung HTML
        let sourceHtml = `
            <div class="mb-4">
                <h3 class="text-base font-medium">${escapeHtml(fileName)}</h3>
                <p class="text-xs text-gray-500">
                    ${source.file_type.toUpperCase()} · 
                    ${source.chunk_word_count} từ · 
                    ${source.page_number ? 'Trang ' + source.page_number : ''}
                </p>
            </div>
            <div class="prose prose-sm max-w-none bg-gray-50 p-4 rounded-lg">
                ${formatSourceContent(source.content_preview)}
            </div>
        `;
        
        // Hiển thị nội dung
        elements.sourceContent.innerHTML = sourceHtml;
        elements.sourceModalContent.innerHTML = sourceHtml;
        
        // Hiển thị panel nguồn trên desktop
        showSourcePanel();
        
        // Hiển thị modal trên mobile
        if (window.innerWidth < 1024) {
            showModal(elements.sourceModal);
        }
    }

    // Format nội dung nguồn
    function formatSourceContent(content) {
        if (!content) return '<p class="text-gray-500">Không có nội dung</p>';
        
        // Phân đoạn văn bản thành các đoạn
        const paragraphs = content.split('\n\n');
        
        return paragraphs
            .map(p => {
                if (!p.trim()) return '';
                
                // Nếu là danh sách
                if (p.match(/^\s*[\*\-]\s+/m)) {
                    const listItems = p.split(/\n[\*\-]\s+/).filter(i => i.trim());
                    return `<ul class="list-disc pl-5 mb-4">
                        ${listItems.map(item => `<li>${escapeHtml(item.trim())}</li>`).join('')}
                    </ul>`;
                }
                
                return `<p class="mb-4">${escapeHtml(p)}</p>`;
            })
            .join('');
    }

    // Hiển thị modal
    function showModal(modal) {
        if (modal) {
            modal.classList.remove('hidden');
        }
    }

    // Ẩn modal
    function hideModal(modal) {
        if (modal) {
            modal.classList.add('hidden');
        }
    }

    // Toggle sidebar trên mobile
    function toggleSidebar() {
        const isHidden = elements.sidebar.classList.contains('hidden') || 
                         elements.sidebar.classList.contains('-translate-x-full');
        
        if (isHidden) {
            elements.sidebar.classList.remove('hidden');
            // Đợi một khoảng thời gian nhỏ để transition hoạt động
            setTimeout(() => {
                elements.sidebar.classList.remove('-translate-x-full');
            }, 10);
        } else {
            elements.sidebar.classList.add('-translate-x-full');
            // Đợi transition hoàn thành rồi mới ẩn hoàn toàn
            setTimeout(() => {
                if (window.innerWidth < 1024) {
                    elements.sidebar.classList.add('hidden');
                }
            }, 300);
        }
    }

    // Xử lý khi chọn file - không sử dụng nữa, xử lý trong inline script
    function handleFileSelect(e) {
        // Function kept for backward compatibility
        console.log("File selection handled by inline script");
    }

    // Xử lý upload file - không sử dụng nữa, xử lý trong inline script
    async function handleUpload(e) {
        // Function kept for backward compatibility
        console.log("Upload handled by inline script");
        if (window.handleFileUploadClick) {
            window.handleFileUploadClick(e);
        }
    }

    // Theo dõi tiến trình indexing
    async function trackIndexingProgress(taskId) {
        let retryCount = 0;
        const maxRetries = 3;
        let progressTrackerId = null;

        const checkProgress = async () => {
            try {
                let response;
                try {
                    response = await axiosInstance.get(`/index/progress/${taskId}`);
                } catch (error) {
                    if (retryCount < maxRetries) {
                        retryCount++;
                        response = await axiosInstance.get(`/index/status/${taskId}`);
                    } else {
                        throw error;
                    }
                }

                const data = response.data;
                let progressValue = 0;

                if (data.progress && typeof data.progress.progress_percent === 'number') {
                    progressValue = data.progress.progress_percent * 100;
                } else if (data.progress && typeof data.progress === 'number') {
                    progressValue = data.progress * 100;
                } else if (typeof data.progress === 'number') {
                    progressValue = data.progress * 100;
                }

                updateProgressBar(progressValue);

                if ((data.status === 'completed' || data.status === 'success') && progressValue >= 100) {
                    updateProgressBar(100);
                    setTimeout(() => {
                        resetUploadForm();
                        hideModal(elements.uploadModal);
                        loadDocuments();
                        showToast('Tài liệu đã được tải lên và xử lý thành công!', 'success');
                        if (progressTrackerId) {
                            clearTimeout(progressTrackerId);
                        }
                    }, 1000);
                    return;
                } else if (data.status === 'failed' || data.status === 'error') {
                    showToast(`Tải lên thất bại: ${data.message || 'Lỗi không xác định'}`, 'error');
                    resetUploadForm();
                    if (progressTrackerId) {
                        clearTimeout(progressTrackerId);
                    }
                    return;
                }

                progressTrackerId = setTimeout(checkProgress, 2000);
            } catch (error) {
                console.error('Lỗi khi theo dõi tiến trình:', error);
                if (retryCount >= maxRetries) {
                    showToast('Không thể theo dõi tiến trình. Tài liệu có thể đã được tải lên, vui lòng kiểm tra danh sách tài liệu.', 'warning');
                    resetUploadForm();
                    hideModal(elements.uploadModal);
                    loadDocuments();
                    if (progressTrackerId) {
                        clearTimeout(progressTrackerId);
                    }
                    return;
                }
                retryCount++;
                progressTrackerId = setTimeout(checkProgress, 3000);
            }
        };

        checkProgress();
    }

    // Cập nhật thanh tiến trình
    function updateProgressBar(percent) {
        const roundedPercent = Math.round(percent);
        elements.progressBar.style.width = `${roundedPercent}%`;
        elements.progressText.textContent = `${roundedPercent}%`;
    }

    // Reset form upload
    function resetUploadForm() {
        elements.uploadForm.reset();
        elements.uploadForm.classList.remove('hidden');
        elements.uploadProgress.classList.add('hidden');
        elements.fileList.classList.add('hidden');
        elements.selectedFiles.innerHTML = '';
        updateProgressBar(0);
        appState.isUploading = false;
    }

    // Tải danh sách tài liệu
    async function loadDocuments() {
        showDocumentsLoading();

        try {
            const response = await axiosInstance.get('/files');
            
            if (Array.isArray(response.data)) {
                renderDocumentList(response.data);
            } else if (response.data.documents && Array.isArray(response.data.documents)) {
                renderDocumentList(response.data.documents);
            } else if (response.data.files && Array.isArray(response.data.files)) {
                renderDocumentList(response.data.files);
            } else {
                renderDocumentList([]);
                console.warn('Format phản hồi API không đúng', response.data);
            }
        } catch (error) {
            console.error('Lỗi khi tải danh sách tài liệu:', error);
            elements.documentList.innerHTML = '<li class="text-red-500 text-sm">Không thể tải danh sách tài liệu</li>';
        } finally {
            hideDocumentsLoading();
        }
    }
    
    // Hiển thị màn hình loading tài liệu
    function showDocumentsLoading() {
        if (elements.documentsLoading) {
            elements.documentsLoading.classList.remove('hidden');
        }
        if (elements.documentList) {
            elements.documentList.classList.add('hidden');
        }
    }
    
    // Ẩn màn hình loading tài liệu
    function hideDocumentsLoading() {
        if (elements.documentsLoading) {
            elements.documentsLoading.classList.add('hidden');
        }
        if (elements.documentList) {
            elements.documentList.classList.remove('hidden');
        }
    }

    // Hiển thị danh sách tài liệu
    function renderDocumentList(files) {
        if (!files || files.length === 0) {
            elements.documentList.innerHTML = '<li class="text-gray-400 text-sm italic">Chưa có tài liệu nào</li>';
            return;
        }
        
        elements.documentList.innerHTML = '';
        
        files.forEach(file => {
            const li = document.createElement('li');
            li.className = 'py-2';
            
            const fileName = file.name;
            const fileSize = formatFileSize(file.size);
            const fileDate = new Date(file.last_modified * 1000).toLocaleDateString();
            
            // Tạo tên file ngắn gọn hơn để hiển thị
            const displayName = fileName.length > 22 
                ? fileName.substring(0, 19) + '...' 
                : fileName;
            
            li.innerHTML = `
                <div class="flex items-start justify-between">
                    <div class="flex-1 pr-2 overflow-hidden">
                        <p class="text-sm font-medium text-gray-900 truncate" title="${escapeHtml(fileName)}">${escapeHtml(displayName)}</p>
                        <p class="text-xs text-gray-500">${fileSize} · ${fileDate}</p>
                    </div>
                    <button class="delete-file-btn text-red-500 hover:text-red-700 flex-shrink-0" data-file="${encodeURIComponent(fileName)}">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                    </button>
                </div>
            `;
            
            elements.documentList.appendChild(li);
        });
        
        // Thêm event listeners cho các nút xóa
        document.querySelectorAll('.delete-file-btn').forEach(button => {
            button.addEventListener('click', () => handleDeleteFile(button.dataset.file));
        });
    }

    // Hiển thị màn hình loading toàn cục
    function showLoading() {
        // Nếu đã có loading overlay, không tạo thêm
        if (document.getElementById('global-loading')) return;
        
        // Tạo loading overlay
        const loadingOverlay = document.createElement('div');
        loadingOverlay.id = 'global-loading';
        loadingOverlay.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        loadingOverlay.innerHTML = `
            <div class="bg-white rounded-lg p-4 flex items-center space-x-3">
                <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                <p class="text-gray-700">Đang xử lý...</p>
            </div>
        `;
        
        // Thêm vào body
        document.body.appendChild(loadingOverlay);
    }

    // Ẩn màn hình loading toàn cục
    function hideLoading() {
        const loadingOverlay = document.getElementById('global-loading');
        if (loadingOverlay) {
            loadingOverlay.remove();
        }
    }

    // Xử lý xóa file
    async function handleDeleteFile(fileId) {
        const fileName = decodeURIComponent(fileId);
        
        if (!confirm(`Bạn có chắc chắn muốn xóa tài liệu "${fileName}" không?`)) {
            return;
        }

        const loadingId = appendLoadingMessage();
        
        try {
            const response = await axiosInstance.delete(`/files/${encodeURIComponent(fileName)}`);
            
            removeLoadingMessage(loadingId);
            
            if (response.data.success) {
                let message = `Tài liệu "${fileName}" đã được xóa thành công.`;
                
                if (response.data.deleted_embeddings && response.data.deleted_embeddings > 0) {
                    message += ` Đã xóa ${response.data.deleted_embeddings} embedding.`;
                }
                
                showToast(message, 'success');
                loadDocuments();
            } else {
                showToast(`Không thể xóa tài liệu: ${response.data.message || 'Lỗi không xác định'}`, 'error');
            }
        } catch (error) {
            console.error('Lỗi khi xóa tài liệu:', error);
            showToast(`Không thể xóa tài liệu: ${error.response?.data?.message || error.message}`, 'error');
            removeLoadingMessage(loadingId);
        }
    }

    // Format kích thước file
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Chuyển đổi markdown sang HTML
    function markdownToHtml(markdown) {
        if (!markdown) return '';
        
        // Chuyển đổi ** thành bold
        let html = markdown.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Chuyển đổi * thành italic
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Chuyển đổi xuống dòng
        html = html.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
        
        // Wrap trong <p>
        html = '<p>' + html + '</p>';
        
        // Fix double <p> tags
        html = html.replace(/<p><\/p>/g, '');
        
        return html;
    }

    // Escape HTML
    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}); 