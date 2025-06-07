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
}

export default nextConfig
