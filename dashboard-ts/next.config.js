/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 修正：在開發環境下直接存取 3001 時，將 /api 代理到 api-server
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://api-server:8080/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig