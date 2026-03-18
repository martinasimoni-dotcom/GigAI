/** @type {import('next').NextConfig} */
const nextConfig = {
  // React 19 with concurrent rendering
  reactStrictMode: true,

  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },

  // Webpack optimization
  webpack: (config, { isServer }) => {
    return config;
  },

  // API routes
  rewrites: async () => {
    return {
      fallback: [
        {
          source: '/api/:path*',
          destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
        },
      ],
    };
  },

  // Image optimization
  images: {
    unoptimized: true,
  },

  // Compression
  compress: true,

  // SWR configuration for data fetching
  experimental: {
    esmExternals: true,
  },
};

module.exports = nextConfig;
