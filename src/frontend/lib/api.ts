import { 
  LoginRequest, 
  SignupRequest, 
  ForgotPasswordRequest, 
  ResetPasswordRequest,
  AuthResponse, 
  ForgotPasswordResponse 
} from '@/types/auth';
import { getApiUrl } from '@/lib/config';

// Định nghĩa URL cơ sở cho API - sử dụng dynamic config
export const API_BASE_URL = getApiUrl();

// Hàm tiện ích để truy cập localStorage an toàn
const getLocalStorage = (key: string): string | null => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(key);
  }
  return null;
};

// Hàm tiện ích để gọi API
export async function fetchApi(
  endpoint: string,
  options: RequestInit = {}
): Promise<any> {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  
  // Lấy token từ localStorage nếu có
  let token = getLocalStorage('auth_token');
  
  // Nếu không tìm thấy token trực tiếp, thử tìm trong session
  if (!token) {
    const session = getLocalStorage('session');
    if (session) {
      try {
        const sessionData = JSON.parse(session);
        token = sessionData.access_token;
        console.log('Using token from session:', token ? token.substring(0, 15) + '...' : 'null');
      } catch (e) {
        console.error('Error parsing session data:', e);
      }
    }
  } else {
    console.log('Using token from auth_token:', token.substring(0, 15) + '...');
  }
  
  // Thiết lập headers mặc định
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const config: RequestInit = {
    ...options,
    headers,
  };

  try {
    console.log(`Calling API: ${url}`, { 
      method: options.method || 'GET',
      hasToken: !!token,
      headers: Object.keys(headers)
    });
    const response = await fetch(url, config);
    
    // Nếu response không ok, ném lỗi
    if (!response.ok) {
      // Xử lý lỗi 401 Unauthorized (token hết hạn)
      if (response.status === 401) {
        // Xóa token và thông tin người dùng
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user_info');
          localStorage.removeItem('session');
        }
        
        // Thông báo cho người dùng
        const errorMessage = "Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại";
        
        // Chuyển hướng về trang đăng nhập nếu không phải đang ở trang đăng nhập
        if (typeof window !== 'undefined' && 
            !window.location.pathname.includes('/auth/login') &&
            !window.location.pathname.includes('/auth/signup')) {
          // Lưu URL hiện tại để sau khi đăng nhập có thể quay lại
          localStorage.setItem('redirect_after_login', window.location.pathname);
          
          // Chuyển hướng với thông báo
          window.location.href = `/auth/login?error=${encodeURIComponent(errorMessage)}`;
        }
        
        throw new Error(errorMessage);
      }

      let errorMessage = 'Có lỗi xảy ra khi gọi API';
      try {
        const errorData = await response.json();
        errorMessage = errorData.message || errorMessage;
      } catch (e) {
        // Nếu không parse được JSON, sử dụng status text
        errorMessage = `${errorMessage} (${response.status}: ${response.statusText})`;
      }
      throw new Error(errorMessage);
    }
    
    // Xử lý response 204 No Content (thành công nhưng không có nội dung)
    if (response.status === 204) {
      return null; // hoặc {} tùy theo yêu cầu
    }
    
    // Parse JSON nếu response có nội dung
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }
    
    return await response.text();
  } catch (error) {
    // Xử lý lỗi mạng hoặc lỗi kết nối
    if (error instanceof TypeError && error.message.includes('fetch')) {
      console.error('Lỗi kết nối đến server:', error);
      throw new Error('Không thể kết nối đến server. Vui lòng kiểm tra kết nối mạng của bạn.');
    }
    
    console.error('API Error:', error);
    throw error;
  }
}

// API Auth
export const authApi = {
  login: async ({ email, password }: LoginRequest): Promise<AuthResponse> => {
    return fetchApi('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },
  
  signup: async (email: string, password: string): Promise<AuthResponse> => {
    return fetchApi('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },
  
  logout: async () => {
    return fetchApi('/auth/logout', {
      method: 'POST',
    });
  },
  
  getUser: async () => {
    return fetchApi('/auth/user');
  },
  
  checkAuth: async () => {
    return fetchApi('/auth/user');
  },
  
  checkSession: async () => {
    return fetchApi('/auth/session');
  },
  
  getGoogleAuthUrl: async () => {
    // Lấy origin của trang hiện tại để tạo redirect_url
    const redirectUrl = `${typeof window !== 'undefined' ? window.location.origin : ''}/auth/callback`;
    
    return fetchApi(`/auth/google/url?redirect_url=${encodeURIComponent(redirectUrl)}`, {
      method: 'GET',
    });
  },

  forgotPassword: async (email: string, redirectUrl?: string): Promise<ForgotPasswordResponse> => {
    try {
      return await fetchApi('/auth/forgot-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          redirect_to: redirectUrl
        })
      });
    } catch (error) {
      console.error("Forgot password error:", error);
      throw error;
    }
  },

  resetPassword: async (token: string, password: string): Promise<{ status: string; message: string }> => {
    try {
      return await fetchApi('/auth/reset-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          password,
          access_token: token
        })
      });
    } catch (error) {
      console.error("Reset password error:", error);
      throw error;
    }
  },
};

// API Files
export const filesApi = {
  getFiles: async () => {
    try {
      const data = await fetchApi('/files');
      console.log('Raw API response:', data);
      
      // Kiểm tra cấu trúc dữ liệu trả về
      if (data && data.files && Array.isArray(data.files)) {
        // Trả về mảng files nếu API trả về dạng { total_files, files: [] }
        return data.files;
      } else if (data && Array.isArray(data)) {
        // Trả về trực tiếp nếu API đã trả về mảng
        return data;
      }
      
      // Trường hợp không có dữ liệu hợp lệ
      console.error('Cấu trúc dữ liệu không hợp lệ:', data);
      return [];
    } catch (error) {
      console.error('Error in getFiles:', error);
      throw error;
    }
  },
  
  deleteFile: async (filename: string) => {
    return fetchApi(`/files/${filename}`, {
      method: 'DELETE',
    });
  },
};

// API Upload
export const uploadApi = {
  uploadFile: async (file: File, category?: string) => {
    try {
      console.log('Uploading file:', file.name, 'size:', file.size, 'type:', file.type);
      
      // Kiểm tra kích thước file (10MB limit)
      const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
      if (file.size > MAX_FILE_SIZE) {
        throw new Error(`File quá lớn. Kích thước tối đa cho phép là 10MB. File của bạn: ${(file.size / (1024*1024)).toFixed(2)}MB`);
      }
      
      // Kiểm tra file có hợp lệ không
      const validTypes = ['.pdf', '.docx', '.doc', '.txt', '.sql', '.md'];
      const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      
      if (!validTypes.includes(fileExtension)) {
        throw new Error(`Định dạng file ${fileExtension} không được hỗ trợ. Vui lòng sử dụng: PDF, DOCX, TXT, SQL hoặc MD.`);
      }
      
      // Tạo FormData
      const formData = new FormData();
      formData.append('file', file);
      if (category) {
        formData.append('category', category);
      }
      
      // Lấy token từ localStorage
      let token = getLocalStorage('auth_token');
      if (!token) {
        const session = getLocalStorage('session');
        if (session) {
          try {
            const sessionData = JSON.parse(session);
            token = sessionData.access_token;
          } catch (e) {
            console.error('Error parsing session data:', e);
          }
        }
      }
      
      if (!token) {
        throw new Error('Không tìm thấy token xác thực. Vui lòng đăng nhập lại.');
      }
      
      // Gọi API trực tiếp thay vì qua fetchApi để có thể theo dõi tiến trình
      const url = `${API_BASE_URL}/upload`;
      
      console.log('Sending request to:', url);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
          // Không thiết lập Content-Type để trình duyệt tự thiết lập với boundary cho FormData
        },
        body: formData
      });
      
      if (!response.ok) {
        let errorMessage = `Lỗi khi tải lên file: ${response.status} ${response.statusText}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (e) {
          // Nếu không parse được JSON, sử dụng status text
        }
        throw new Error(errorMessage);
      }
      
      const data = await response.json();
      console.log('Upload response:', data);
      return data;
    } catch (error) {
      console.error('Error in uploadFile:', error);
      throw error;
    }
  },
};

// API Conversations
export const conversationsApi = {
  getConversations: async (page = 1, pageSize = 10) => {
    return fetchApi(`/conversations?page=${page}&page_size=${pageSize}`);
  },
  
  getConversation: async (conversationId: string) => {
    try {
      return await fetchApi(`/conversations/${conversationId}`);
    } catch (error: unknown) {
      // Kiểm tra nếu lỗi là do hội thoại mới (không có tin nhắn)
      if (error instanceof Error && 
          (error.message.includes("Không tìm thấy hội thoại với ID") || 
          error.message.includes("conversation_id"))) {
        // Trả về một đối tượng giả lập với status success và messages rỗng
        return {
          status: "success",
          message: "Hội thoại mới",
          data: {
            conversation_id: conversationId,
            messages: []
          }
        };
      }
      // Nếu là lỗi khác, ném lại lỗi đó
      throw error;
    }
  },
  
  createConversation: async () => {
    return fetchApi('/conversations/create', {
      method: 'POST',
    });
  },
  
  deleteConversation: async (conversationId: string) => {
    return fetchApi(`/conversations/${conversationId}`, {
      method: 'DELETE',
    });
  },
  
  getLatestConversation: async () => {
    return fetchApi('/latest-conversation');
  },

  // Thêm API tìm kiếm hội thoại
  searchConversations: async (searchParams: {
    query?: string;
    dateFrom?: string;
    dateTo?: string;
    page?: number;
    pageSize?: number;
  }) => {
    return fetchApi('/conversations/search', {
      method: 'POST',
      body: JSON.stringify({
        query: searchParams.query || "",
        date_from: searchParams.dateFrom,
        date_to: searchParams.dateTo,
        page: searchParams.page || 1,
        page_size: searchParams.pageSize || 10
      })
    });
  },
};

// API Questions
export const questionsApi = {
  ask: async (question: string, sources?: string[], fileId?: string[], sessionId?: string, maxSources?: number) => {
    const params = maxSources ? `?max_sources=${maxSources}` : '';
    return fetchApi(`/ask/stream${params}`, {
      method: 'POST',
      body: JSON.stringify({
        question,
        sources,
        file_id: fileId,
        session_id: sessionId,
      }),
    });
  },
  
  getSuggestions: async (numSuggestions = 3) => {
    return fetchApi(`/suggestions?num_suggestions=${numSuggestions}`);
  },
};

export async function fetchApiStream(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  let token = null;
  if (typeof window !== 'undefined') {
    token = localStorage.getItem('auth_token');
    if (!token) {
      const session = localStorage.getItem('session');
      if (session) {
        try {
          const sessionData = JSON.parse(session);
          token = sessionData.access_token;
        } catch (e) {
          console.error('Error parsing session data:', e);
        }
      }
    }
  }
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };
  const config: RequestInit = {
    ...options,
    headers,
  };
  
  const response = await fetch(url, config);
  
  // Xử lý lỗi 401 Unauthorized (token hết hạn)
  if (response.status === 401) {
    // Xóa token và thông tin người dùng
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_info');
      localStorage.removeItem('session');
    }
    
    // Thông báo cho người dùng
    const errorMessage = "Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại";
    
    // Chuyển hướng về trang đăng nhập nếu không phải đang ở trang đăng nhập
    if (typeof window !== 'undefined' && 
        !window.location.pathname.includes('/auth/login') &&
        !window.location.pathname.includes('/auth/signup')) {
      // Lưu URL hiện tại để sau khi đăng nhập có thể quay lại
      localStorage.setItem('redirect_after_login', window.location.pathname);
      
      // Chuyển hướng với thông báo
      window.location.href = `/auth/login?error=${encodeURIComponent(errorMessage)}`;
    }
    
    throw new Error(errorMessage);
  }
  
  return response;
}