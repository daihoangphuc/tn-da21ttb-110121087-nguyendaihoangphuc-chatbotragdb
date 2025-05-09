// Cấu hình API
const API_BASE_URL = 'http://localhost:8000';
console.log('API sẽ được gọi qua URL:', API_BASE_URL);

// Class APIService quản lý các tương tác với API
class APIService {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        console.log('APIService khởi tạo với baseUrl:', baseUrl);
    }

    // Hàm helper chung để gọi API
    async fetchApi(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        console.log(`Gọi API: ${options.method || 'GET'} ${url}`);
        
        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers,
                },
            });
    
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`Lỗi API (${response.status}):`, errorText);
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
                sources: sources || []
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
            sources: sources || []
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
                eventHandlers.endHandlers.push(handler);
                return this;
            },
            
            onError: (handler) => {
                eventHandlers.errorHandlers.push(handler);
                return this;
            },
            
            close: () => {
                if (isStreamActive) {
                    console.log('Hủy streaming request');
                    abortController.abort();
                    isStreamActive = false;
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

        // Tạo một promise để xử lý upload
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            // Theo dõi tiến trình upload (chỉ dùng khi cần, giờ không cần hiển thị tiến trình)
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
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (e) {
                        reject(new Error('Failed to parse response'));
                    }
                } else {
                    reject(new Error(`Upload failed with status ${xhr.status}`));
                }
            });
            
            // Xử lý lỗi
            xhr.addEventListener('error', () => {
                reject(new Error('Network error during upload'));
            });
            
            xhr.addEventListener('abort', () => {
                reject(new Error('Upload aborted'));
            });
            
            // Mở kết nối và gửi request
            xhr.open('POST', `${this.baseUrl}/api/upload`);
            xhr.send(formData);
        });
    }
}

// Khởi tạo service
const apiService = new APIService(API_BASE_URL); 