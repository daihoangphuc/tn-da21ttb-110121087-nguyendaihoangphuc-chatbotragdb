// Dynamic configuration for API URL
export function getApiUrl(): string {
  // Check if we're in browser environment
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    
    // Production environment
    if (hostname === 'chat.phucndh.id.vn') {
      return 'https://api.phucndh.id.vn/api';
    }
    
    // Staging environment
    if (hostname === 'staging.chat.phucndh.id.vn') {
      return 'https://staging.api.phucndh.id.vn/api';
    }
    
    // Local development or other environments
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:8000/api';
    }
    
    // Fallback for other cases - assume HTTPS for production domains
    if (protocol === 'https:') {
      return 'https://api.phucndh.id.vn/api';
    }
    
    // Default fallback for browser
    return 'https://api.phucndh.id.vn/api';
  }
  
  // Server-side rendering or fallback
  return process.env.NEXT_PUBLIC_API_URL || 'https://api.phucndh.id.vn/api';
}

// Export for use in components
export const API_BASE_URL = getApiUrl(); 