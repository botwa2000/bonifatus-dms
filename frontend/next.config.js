/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  outputFileTracingRoot: require('path').join(__dirname),
  experimental: {
    optimizePackageImports: ['lucide-react'],
  },
}

module.exports = nextConfig