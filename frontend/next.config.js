// frontend/next.config.js

const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    optimizePackageImports: ['clsx', 'tailwind-merge'],
  },
  
  images: {
    domains: ['lh3.googleusercontent.com'],
  },
  
  // Remove the multiple lockfiles warning
  outputFileTracingRoot: path.join(__dirname, '..'),
  
  // Environment variables (optional - .env file is primary source)
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },
};

module.exports = nextConfig;