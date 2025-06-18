/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  // Đã xóa cấu hình output: export và distDir: out để sử dụng middleware
  // Cấu hình cho Docker standalone build
  output: 'standalone',
  
  // Cấu hình để xử lý hydration mismatch tốt hơn
  reactStrictMode: true,
  
  // Cấu hình experimental để cải thiện hydration
  experimental: {
    // Tối ưu hydration cho production
    optimizeCss: true,
  },
  
  // Webpack config để xử lý hydration issues
  webpack: (config, { dev, isServer }) => {
    if (dev && !isServer) {
      // Trong development mode, suppress hydration warnings
      config.resolve.alias = {
        ...config.resolve.alias,
        // Add any webpack aliases if needed
      };
    }
    return config;
  },
}

export default nextConfig
