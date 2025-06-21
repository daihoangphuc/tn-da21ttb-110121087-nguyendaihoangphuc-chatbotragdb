// Dynamic configuration for API URL
export function getApiUrl(): string {
  // Check if we're in browser environment
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    
    // Production environment
    if (hostname === 'chat.phucndh.me') {
      return 'https://api.phucndh.me/api';
    }
    
    // Staging environment
    if (hostname === 'staging.chat.phucndh.me') {
      return 'https://staging.api.phucndh.me/api';
    }
    
    // Local development or other environments
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:8000/api';
    }
    
    // Fallback for other cases - assume HTTPS for production domains
    if (protocol === 'https:') {
      return 'https://api.phucndh.me/api';
    }
    
    // Default fallback for browser
    return 'https://api.phucndh.me/api';
  }
  
  // Server-side rendering or fallback
  return process.env.NEXT_PUBLIC_API_URL || 'https://api.phucndh.me/api';
}

// Export for use in components
export const API_BASE_URL = getApiUrl(); 