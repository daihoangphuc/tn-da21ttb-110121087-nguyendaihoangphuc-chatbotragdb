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