/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // API 代理到独立 API 服务
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:3001/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
