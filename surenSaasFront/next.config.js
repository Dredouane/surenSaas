/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    unoptimized: true,
  },
  env: {
    BUILD_ID: process.env.BUILD_ID || 'dev',
  },
  // Le proxy API est géré par app/api/v1/[[...path]]/route.ts
  // Pas besoin de rewrites ici
};

module.exports = nextConfig;
