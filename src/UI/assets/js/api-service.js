// Cấu hình API
const API_BASE_URL = 'http://localhost:8000';
console.log('API sẽ được gọi qua URL:', API_BASE_URL);

// Class APIService quản lý các tương tác với API
class APIService {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        console.log('APIService khởi tạo với baseUrl:', baseUrl);
        
        // Session ID cho hội thoại hiện tại
        this.conversation_id = localStorage.getItem('currentConversationId') || this._generateConversationId();
        
        console.log('Khởi tạo ApiService với conversation_id:', this.conversation_id);
    }

    _generateConversationId() {
        // Tạo UUID đơn giản
        const conversationId = 'conversation_' + Math.random().toString(36).substring(2, 15);
        localStorage.setItem('currentConversationId', conversationId);
        return conversationId;
    }
    
    // Lấy conversation ID hiện tại
    getConversationId() {
        if (!this.conversation_id && typeof localStorage !== 'undefined') {
            this.conversation_id = localStorage.getItem('currentConversationId');
        }
        return this.conversation_id;
    }
    
    // Đặt conversation ID mới
    setConversationId(conversationId) {
        this.conversation_id = conversationId;
        localStorage.setItem('currentConversationId', conversationId);
        console.log(`Đã lưu conversation_id hiện tại: ${conversationId}`);
    }
    
    // Tạo conversation ID mới và xóa conversation cũ
    resetConversation() {
        // Trước tiên, thử xóa conversation cũ
        this.clearConversation(this.conversation_id)
            .then(() => console.log('Đã xóa conversation cũ:', this.conversation_id))
            .catch(err => console.error('Lỗi khi xóa conversation cũ:', err));
            
        // Sau đó tạo conversation mới
        this.conversation_id = this._generateConversationId();
        console.log('Đã tạo conversation mới:', this.conversation_id);
        return this.conversation_id;
    }
    
    // Phương thức để xóa hội thoại
    async clearConversation(conversationId = null) {
        const cid = conversationId || this.conversation_id;
        try {
            const response = await fetch(`${this.baseUrl}/conversation/clear`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    conversation_id: cid
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Lỗi khi xóa hội thoại');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Lỗi khi gọi API xóa hội thoại:', error);
            throw error;
        }
    }
    
    // Phương thức để lấy lịch sử hội thoại
    async getConversationHistory(conversationId = null) {
        const cid = conversationId || this.conversation_id;
        try {
            const response = await fetch(`${this.baseUrl}/conversation/history?conversation_id=${cid}`);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Lỗi khi lấy lịch sử hội thoại');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Lỗi khi gọi API lấy lịch sử hội thoại:', error);
            throw error;
        }
    }
    
    // Kiểm tra kết nối API
    async checkConnection() {
        try {
            const response = await fetch(`${this.baseUrl}/`);
            if (response.ok) {
                return true;
            }
            return false;
        } catch (error) {
            console.error('Lỗi kết nối API:', error);
            return false;
        }
    }
    
    // Hàm helper chung để gọi API
    async fetchApi(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        console.log(`Gọi API: ${options.method || 'GET'} ${url}`);
        
        // Thêm token xác thực vào header nếu người dùng đã đăng nhập
        const authToken = this.getAuthToken();
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };
        
        if (authToken) {
            // Đảm bảo token không chứa chuỗi 'Bearer' ở đầu
            const token = authToken.startsWith('Bearer ') ? authToken.substring(7) : authToken;
            headers['Authorization'] = `Bearer ${token}`;
            console.log('Thêm Authorization header cho request:', endpoint);
        }
        
        try {
            const response = await fetch(url, {
                ...options,
                headers: headers,
            });
    
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`Lỗi API (${response.status}):`, errorText);
                
                // Xử lý trường hợp token hết hạn
                if (response.status === 401) {
                    console.warn('Phiên đăng nhập đã hết hạn, đang đăng xuất...');
                    sessionStorage.removeItem('auth_token');
                    sessionStorage.removeItem('user_info');
                    
                    // Chuyển hướng đến trang đăng nhập nếu cần
                    if (window.location.pathname !== '/login.html') {
                        window.location.href = '/login.html';
                    }
                }
                
                throw new Error(`API error (${response.status}): ${errorText}`);
            }
    
            const data = await response.json();
            console.log(`Nhận phản hồi từ ${endpoint}:`, data);
            return data;
        } catch (error) {
            console.error(`Lỗi khi gọi ${endpoint}:`, error);
            throw error;
        }
    }

    // Kiểm tra trạng thái API
    async checkApiStatus() {
        return this.fetchApi('/api');
    }

    // Truy vấn RAG
    async queryRAG(question, searchType = 'hybrid', maxSources, sources = []) {
        const url = maxSources ? `/api/ask?max_sources=${maxSources}` : '/api/ask';
        
        return this.fetchApi(url, {
            method: 'POST',
            body: JSON.stringify({ 
                question, 
                search_type: searchType,
                alpha: 0.7,
                sources: sources || [],
                conversation_id: this.conversation_id
            }),
        });
    }
    
    // Truy vấn RAG dùng SSE streaming
    queryRAGStream(question, searchType = 'hybrid', maxSources, sources = []) {
        const url = maxSources 
            ? `${this.baseUrl}/api/ask/stream?max_sources=${maxSources}`
            : `${this.baseUrl}/api/ask/stream`;
        
        console.log(`Gọi API Stream: POST ${url}`);
        
        // Tạo payload
        const payload = {
            question,
            search_type: searchType,
            alpha: 0.7,
            sources: sources || [],
            conversation_id: this.conversation_id
        };
        
        // Biến lưu trạng thái
        let abortController = new AbortController();
        let isStreamActive = false;
        
        // Các event handlers
        const eventHandlers = {
            sourcesHandlers: [],
            contentHandlers: [],
            endHandlers: [],
            errorHandlers: []
        };
        
        // Hàm phân tích dữ liệu SSE
        const parseSSE = (data) => {
            // Mỗi sự kiện SSE có định dạng:
            // event: eventName
            // data: JSON data
            // [empty line]
            
            const lines = data.split('\n');
            let eventName = '';
            let eventData = '';
            
            for (const line of lines) {
                if (line.startsWith('event:')) {
                    eventName = line.substring(6).trim();
                } else if (line.startsWith('data:')) {
                    eventData = line.substring(5).trim();
                } else if (line === '' && eventName && eventData) {
                    // Empty line indicates end of event
                    try {
                        const parsedData = JSON.parse(eventData);
                        // Trigger appropriate handlers based on event type
                        if (eventName === 'sources' && eventHandlers.sourcesHandlers.length > 0) {
                            eventHandlers.sourcesHandlers.forEach(handler => handler(parsedData));
                        } else if (eventName === 'content' && eventHandlers.contentHandlers.length > 0) {
                            eventHandlers.contentHandlers.forEach(handler => handler(parsedData.content));
                        } else if (eventName === 'end' && eventHandlers.endHandlers.length > 0) {
                            // Đảm bảo trường related_questions được truyền vào nếu có
                            console.log('End event data:', parsedData);
                            // Truyền toàn bộ parsedData để đảm bảo related_questions được bao gồm
                            eventHandlers.endHandlers.forEach(handler => handler(parsedData));
                            // Kết thúc stream
                            isStreamActive = false;
                        } else if (eventName === 'error' && eventHandlers.errorHandlers.length > 0) {
                            eventHandlers.errorHandlers.forEach(handler => handler(parsedData));
                            // Kết thúc stream nếu có lỗi
                            isStreamActive = false;
                        }
                    } catch (error) {
                        console.error('Lỗi khi parse dữ liệu SSE:', error, eventData);
                    }
                    
                    // Reset for next event
                    eventName = '';
                    eventData = '';
                }
            }
        };
        
        // Bắt đầu streaming với fetch
        const startStream = async () => {
            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${this.getAuthToken()}`
                    },
                    body: JSON.stringify(payload),
                    signal: abortController.signal
                });
                
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`API error (${response.status}): ${errorText}`);
                }
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                
                isStreamActive = true;
                
                while (isStreamActive) {
                    const { done, value } = await reader.read();
                    
                    if (done) {
                        isStreamActive = false;
                        break;
                    }
                    
                    // Decode và thêm vào buffer
                    const chunk = decoder.decode(value, { stream: true });
                    buffer += chunk;
                    
                    // Tìm các sự kiện hoàn chỉnh (kết thúc bằng 2 dòng trống)
                    const events = buffer.split('\n\n');
                    
                    // Phần cuối cùng có thể chưa hoàn chỉnh, giữ lại để xử lý trong chunk tiếp theo
                    buffer = events.pop() || '';
                    
                    // Xử lý các sự kiện hoàn chỉnh
                    for (const event of events) {
                        if (event.trim()) { // Bỏ qua các sự kiện rỗng
                            parseSSE(event + '\n\n'); // Thêm lại ký tự kết thúc
                        }
                    }
                }
                
                // Xử lý phần buffer còn lại nếu có
                if (buffer.trim()) {
                    parseSSE(buffer);
                }
                
            } catch (error) {
                console.error('Lỗi khi streaming:', error);
                const errorData = {
                    error: true,
                    message: error.message || 'Lỗi kết nối đến server'
                };
                
                // Gọi error handlers
                eventHandlers.errorHandlers.forEach(handler => handler(errorData));
                isStreamActive = false;
            }
        };
        
        // Khởi động stream
        startStream();
        
        // Trả về đối tượng cho phép đăng ký event handlers
        return {
            onSources: (handler) => {
                eventHandlers.sourcesHandlers.push(handler);
                return this;
            },
            
            onContent: (handler) => {
                eventHandlers.contentHandlers.push(handler);
                return this;
            },
            
            onEnd: (handler) => {
                // Đăng ký handler gốc
                eventHandlers.endHandlers.push(handler);
                
                // Thêm handler mới để kích hoạt lại input
                eventHandlers.endHandlers.push(() => {
                    // Đảm bảo input được kích hoạt lại khi kết thúc stream
                    console.log('Stream kết thúc, kích hoạt lại input');
                    const messageInput = document.getElementById('messageInput');
                    const sendButton = document.getElementById('sendButton');
                    if (messageInput && sendButton) {
                        setTimeout(() => {
                            messageInput.disabled = false;
                            sendButton.disabled = messageInput.value.trim() === '';
                            messageInput.focus();
                        }, 200);
                    }
                });
                
                return this;
            },
            
            onError: (handler) => {
                // Đăng ký handler gốc
                eventHandlers.errorHandlers.push(handler);
                
                // Thêm handler mới để kích hoạt lại input khi có lỗi
                eventHandlers.errorHandlers.push(() => {
                    console.log('Stream gặp lỗi, kích hoạt lại input');
                    const messageInput = document.getElementById('messageInput');
                    const sendButton = document.getElementById('sendButton');
                    if (messageInput && sendButton) {
                        setTimeout(() => {
                            messageInput.disabled = false;
                            sendButton.disabled = messageInput.value.trim() === '';
                            messageInput.focus();
                        }, 200);
                    }
                });
                
                return this;
            },
            
            close: () => {
                if (isStreamActive) {
                    console.log('Hủy streaming request');
                    abortController.abort();
                    isStreamActive = false;
                    
                    // Kích hoạt lại input khi đóng stream
                    const messageInput = document.getElementById('messageInput');
                    const sendButton = document.getElementById('sendButton');
                    if (messageInput && sendButton) {
                        setTimeout(() => {
                            messageInput.disabled = false;
                            sendButton.disabled = messageInput.value.trim() === '';
                            messageInput.focus();
                        }, 200);
                    }
                }
            },
            
            isConnected: () => {
                return isStreamActive;
            }
        };
    }

    // Lấy danh sách tài liệu
    async getFiles() {
        return this.fetchApi('/api/files');
    }

    // Xóa tài liệu
    async deleteFile(filename) {
        return this.fetchApi(`/api/files/${filename}`, { 
            method: 'DELETE' 
        });
    }

    // Reindex toàn bộ tài liệu
    async reindexAll() {
        return this.fetchApi('/api/reindex', { method: 'POST' });
    }

    // Upload tài liệu
    async uploadFile(file, onProgress, category) {
        const formData = new FormData();
        formData.append('file', file);
        if (category) {
            formData.append('category', category);
        }
        
        return this._uploadFileWithProgress(formData, onProgress);
    }

    // Phương thức hỗ trợ upload file với hiển thị tiến trình
    _uploadFileWithProgress(formData, onProgress) {
        console.log('Bắt đầu upload file...');
        
        // Tạo một promise để xử lý upload
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            // Theo dõi tiến trình upload
            if (typeof onProgress === 'function') {
                xhr.upload.addEventListener('progress', (event) => {
                    if (event.lengthComputable) {
                        const percentComplete = (event.loaded / event.total) * 100;
                        onProgress(percentComplete);
                    }
                });
            }
            
            // Xử lý khi upload hoàn tất
            xhr.addEventListener('load', () => {
                console.log('Upload response status:', xhr.status);
                console.log('Response headers:', xhr.getAllResponseHeaders());
                
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        console.log('Upload thành công, response:', response);
                        resolve(response);
                    } catch (e) {
                        console.error('Lỗi parse response:', e);
                        console.log('Response text:', xhr.responseText);
                        reject(new Error('Failed to parse response'));
                    }
                } else {
                    // Log thêm thông tin lỗi chi tiết
                    console.error(`Upload failed with status ${xhr.status}:`, xhr.responseText);
                    reject(new Error(`Upload failed with status ${xhr.status}: ${xhr.responseText}`));
                }
            });
            
            // Xử lý lỗi
            xhr.addEventListener('error', (e) => {
                console.error('Network error during upload:', e);
                reject(new Error('Network error during upload'));
            });
            
            xhr.addEventListener('abort', () => {
                console.log('Upload aborted');
                reject(new Error('Upload aborted'));
            });
            
            // Mở kết nối và gửi request
            xhr.open('POST', `${this.baseUrl}/api/upload`);
            
            // Thêm token xác thực vào header
            const authToken = this.getAuthToken();
            if (authToken) {
                // Log token để debug (ẩn phần sau)
                console.log('Using auth token:', authToken.substring(0, 15) + '...');
                xhr.setRequestHeader('Authorization', `Bearer ${authToken}`);
            } else {
                console.warn('Không tìm thấy token xác thực trong sessionStorage');
                // Thử lấy thông tin người dùng hiện tại và đăng nhập lại
                console.log('Đang thử lấy thông tin người dùng hiện tại...');
            }
            
            console.log('Đang gửi request upload...');
            xhr.send(formData);
        });
    }

    // Các phương thức xác thực

    // Đăng ký tài khoản mới
    async signup(email, password) {
        return this.fetchApi('/api/auth/signup', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
    }

    // Đăng nhập
    async login(email, password) {
        try {
            console.log(`Đang đăng nhập với email: ${email}`);
            
            const result = await this.fetchApi('/api/auth/login', {
                method: 'POST',
                body: JSON.stringify({ email, password }),
            });
            
            // Lưu token và thông tin người dùng vào sessionStorage
            // Đảm bảo chỉ lưu token gốc, không thêm tiền tố Bearer
            const token = result.access_token;
            
            if (!token) {
                console.error('Không nhận được token từ API login');
                throw new Error('Không nhận được token xác thực');
            }
            
            console.log('Đã nhận token, lưu vào sessionStorage');
            sessionStorage.setItem('auth_token', token);
            sessionStorage.setItem('user_info', JSON.stringify(result.user));
            
            console.log('Đăng nhập thành công, thông tin user:', result.user.email);
            return result;
        } catch (error) {
            console.error('Lỗi đăng nhập:', error);
            throw error;
        }
    }

    // Đăng xuất
    async logout() {
        try {
            // Gọi API đăng xuất
            await this.fetchApi('/api/auth/logout', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            // Xóa token và thông tin người dùng khỏi sessionStorage
            sessionStorage.removeItem('auth_token');
            sessionStorage.removeItem('user_info');
            
            return { success: true };
        } catch (error) {
            console.error('Lỗi đăng xuất:', error);
            // Xóa token và thông tin người dùng khỏi sessionStorage ngay cả khi có lỗi
            sessionStorage.removeItem('auth_token');
            sessionStorage.removeItem('user_info');
            throw error;
        }
    }

    // Lấy thông tin người dùng hiện tại
    async getCurrentUser() {
        try {
            return await this.fetchApi('/api/auth/user', {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
        } catch (error) {
            console.error('Lỗi lấy thông tin người dùng:', error);
            throw error;
        }
    }

    // Kiểm tra phiên đăng nhập
    async checkSession() {
        try {
            const result = await this.fetchApi('/api/auth/session', {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            return result.is_authenticated;
        } catch (error) {
            console.error('Lỗi kiểm tra phiên đăng nhập:', error);
            return false;
        }
    }

    // Lấy token từ sessionStorage
    getAuthToken() {
        const token = sessionStorage.getItem('auth_token');
        
        if (!token) {
            console.warn('Không tìm thấy auth_token trong sessionStorage');
            return null;
        }
        
        if (token.startsWith('Bearer ')) {
            console.warn('Token đã chứa tiền tố Bearer, sẽ bị loại bỏ');
            return token.substring(7);
        }
        
        return token;
    }

    // Kiểm tra xem người dùng đã đăng nhập chưa
    isLoggedIn() {
        return !!this.getAuthToken();
    }

    // Lấy thông tin người dùng từ sessionStorage
    getUserInfo() {
        const userInfo = sessionStorage.getItem('user_info');
        return userInfo ? JSON.parse(userInfo) : null;
    }

    // Phương thức đăng nhập bằng Google
    async getGoogleAuthUrl() {
        const redirectUrl = `${window.location.origin}/auth-callback.html`;
        console.log(`Lấy URL đăng nhập Google với redirect_url: ${redirectUrl}`);
        
        try {
            console.log(`Gọi API: GET ${this.baseUrl}/api/auth/google/url với redirect_url=${encodeURIComponent(redirectUrl)}`);
            
            const response = await fetch(`${this.baseUrl}/api/auth/google/url?redirect_url=${encodeURIComponent(redirectUrl)}`);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`Lỗi API Auth URL (${response.status}):`, errorText);
                throw new Error(`Lỗi khi lấy URL xác thực (${response.status}): ${errorText}`);
            }
            
            const result = await response.json();
            console.log('Nhận được URL Google Auth:', result);
            
            if (!result.url) {
                console.error('API trả về nhưng không có URL:', result);
                throw new Error('Không nhận được URL xác thực Google');
            }
            
            return result.url;
        } catch (error) {
            console.error('Lỗi lấy URL đăng nhập Google:', error);
            throw error;
        }
    }

    // Xử lý OAuth callback
    async handleOAuthCallback(code, provider = 'google') {
        try {
            const result = await this.fetchApi('/api/auth/google', {
                method: 'POST',
                body: JSON.stringify({ code, provider })
            });
            
            // Lưu token và thông tin người dùng
            const token = result.access_token;
            sessionStorage.setItem('auth_token', token);
            sessionStorage.setItem('user_info', JSON.stringify(result.user));
            
            console.log('OAuth callback thành công, lưu token vào sessionStorage');
            return result;
        } catch (error) {
            console.error(`Lỗi xử lý OAuth callback từ ${provider}:`, error);
            throw error;
        }
    }

    // Xác thực với Google oauth token
    async loginWithGoogle(accessToken) {
        try {
            const result = await this.fetchApi('/api/auth/google', {
                method: 'POST',
                body: JSON.stringify({ access_token: accessToken })
            });
            
            // Lưu token và thông tin người dùng
            const token = result.access_token;
            sessionStorage.setItem('auth_token', token);
            sessionStorage.setItem('user_info', JSON.stringify(result.user));
            
            console.log('Đăng nhập Google thành công, lưu token vào sessionStorage');
            return result;
        } catch (error) {
            console.error('Lỗi đăng nhập với Google:', error);
            throw error;
        }
    }

    // Lấy danh sách lịch sử chat
    async getChatHistory() {
        try {
            return await this.fetchApi('/api/chat/history', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
        } catch (error) {
            console.error('Lỗi khi lấy lịch sử chat:', error);
            // Trả về mảng rỗng nếu có lỗi
            return [];
        }
    }
    
    // Lấy thông tin chi tiết của một phiên chat
    async getChatSession(chatId) {
        try {
            return await this.fetchApi(`/api/chat/sessions/${chatId}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
        } catch (error) {
            console.error(`Lỗi khi lấy thông tin phiên chat ${chatId}:`, error);
            throw error;
        }
    }
    
    // Xóa một phiên chat
    async deleteChatSession(chatId) {
        try {
            return await this.fetchApi(`/api/chat/sessions/${chatId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
        } catch (error) {
            console.error(`Lỗi khi xóa phiên chat ${chatId}:`, error);
            throw error;
        }
    }
    
    // Đổi tên một phiên chat
    async renameChatSession(chatId, newTitle) {
        try {
            return await this.fetchApi(`/api/chat/sessions/${chatId}/rename`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({ title: newTitle })
            });
        } catch (error) {
            console.error(`Lỗi khi đổi tên phiên chat ${chatId}:`, error);
            throw error;
        }
    }
    
    // Lấy danh sách hội thoại
    async getConversations(page = 1, pageSize = 10) {
        try {
            const response = await this.fetchApi(`/conversations?page=${page}&page_size=${pageSize}`, {
                method: 'GET'
            });
            return response;
        } catch (error) {
            console.error('Lỗi khi lấy danh sách hội thoại:', error);
            throw error;
        }
    }
    
    // Lấy chi tiết một conversation
    async getConversationDetail(conversationId) {
        try {
            const response = await this.fetchApi(`/conversations/${conversationId}`, {
                method: 'GET'
            });
            return response;
        } catch (error) {
            console.error('Lỗi khi lấy chi tiết hội thoại:', error);
            throw error;
        }
    }
    
    // Tạo conversation mới
    async createConversation() {
        try {
            const response = await this.fetchApi('/conversations/create', {
                method: 'POST'
            });
            return response;
        } catch (error) {
            console.error('Lỗi khi tạo hội thoại mới:', error);
            throw error;
        }
    }
    
    // Xóa một conversation
    async deleteConversation(conversationId) {
        try {
            const response = await this.fetchApi(`/conversations/${conversationId}`, {
                method: 'DELETE'
            });
            return response;
        } catch (error) {
            console.error('Lỗi khi xóa hội thoại:', error);
            throw error;
        }
    }
    
    // Lấy tin nhắn của một hội thoại
    async getMessages(conversationId) {
        try {
            const response = await this.fetchApi(`/api/messages?conversation_id=${conversationId}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });
            
            // Kiểm tra cấu trúc dữ liệu trả về
            if (!response.data || !response.data.messages) {
                console.error('Cấu trúc dữ liệu trả về không đúng:', response);
                return { 
                    status: 'error', 
                    message: 'Cấu trúc dữ liệu trả về không đúng', 
                    data: { 
                        conversation_id: conversationId,
                        messages: [] 
                    } 
                };
            }
            
            // Đảm bảo messages là một mảng
            if (!Array.isArray(response.data.messages)) {
                console.error('Dữ liệu messages không phải là mảng:', response.data.messages);
                response.data.messages = [];
            }
            
            return response;
        } catch (error) {
            console.error(`Lỗi khi lấy tin nhắn của hội thoại ${conversationId}:`, error);
            return { 
                status: 'error', 
                message: `Không thể tải nội dung hội thoại: ${error.message}`,
                data: { 
                    conversation_id: conversationId,
                    messages: [] 
                } 
            };
        }
    }
}

// Khởi tạo đối tượng APIService dùng chung toàn ứng dụng
const apiService = new APIService(API_BASE_URL);

// Export đối tượng apiService
window.apiService = apiService; 