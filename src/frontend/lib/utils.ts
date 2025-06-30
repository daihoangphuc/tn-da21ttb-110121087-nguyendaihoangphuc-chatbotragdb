import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import { format } from "date-fns"
import { vi } from "date-fns/locale"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Debounce function để tối ưu hóa API calls
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout | null = null
  
  return (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
    
    timeoutId = setTimeout(() => {
      func(...args)
    }, delay)
  }
}

/**
 * Format thời gian từ backend (đã được xử lý theo múi giờ Việt Nam)
 * Xử lý đúng cách để tránh double-convert timezone
 */
export function formatVietnameseDate(dateString: string): string {
  if (!dateString || dateString === "") {
    return "N/A";
  }
  
  try {
    // Nếu dateString đã có timezone info, parse trực tiếp
    const date = new Date(dateString);
    
    // Kiểm tra nếu date hợp lệ
    if (isNaN(date.getTime())) {
      return "Invalid Date";
    }
    
    return format(date, "dd/MM/yyyy HH:mm", { locale: vi });
  } catch (error) {
    console.error("Error formatting date:", error);
    return dateString; // Trả về chuỗi gốc nếu có lỗi
  }
}

/**
 * Clean browser extension attributes để tránh hydration mismatch
 * Các browser extensions thường thêm attributes như bis_skin_checked, etc.
 */
export function cleanBrowserExtensionAttributes(element: HTMLElement) {
  if (!element || typeof window === 'undefined') return;
  
  // Danh sách các attributes thường được thêm bởi browser extensions
  const extensionAttributes = [
    'bis_skin_checked',
    'data-darkreader',
    'data-darkreader-mode',
    'data-darkreader-scheme',
    'data-adblock',
    'data-extension-id',
    'data-honey-extension',
    'data-lastpass-icon-root',
    'data-grammarly-shadow-root'
  ];
  
  extensionAttributes.forEach(attr => {
    if (element.hasAttribute(attr)) {
      element.removeAttribute(attr);
    }
  });
  
  // Đệ quy clean cho tất cả children
  Array.from(element.children).forEach(child => {
    if (child instanceof HTMLElement) {
      cleanBrowserExtensionAttributes(child);
    }
  });
}

/**
 * Hook để clean browser extension attributes sau khi component mount
 */
export function useBrowserExtensionCleaner() {
  if (typeof window !== 'undefined') {
    // Clean ngay khi function được gọi
    setTimeout(() => {
      cleanBrowserExtensionAttributes(document.body);
    }, 100);
    
    // Set up MutationObserver để clean liên tục
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.target instanceof HTMLElement) {
          const target = mutation.target;
          const attributeName = mutation.attributeName;
          
          // Nếu attribute được thêm là của extension, remove nó
          if (attributeName && attributeName.includes('bis_') || 
              attributeName && attributeName.includes('data-darkreader') ||
              attributeName && attributeName.includes('data-adblock')) {
            target.removeAttribute(attributeName);
          }
        }
      });
    });
    
    observer.observe(document.body, {
      attributes: true,
      subtree: true,
      attributeFilter: ['bis_skin_checked', 'data-darkreader', 'data-adblock']
    });
    
    return () => observer.disconnect();
  }
  
  return () => {};
}
