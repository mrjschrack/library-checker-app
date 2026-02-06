/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'i.gr-assets.com',
      },
      {
        protocol: 'https',
        hostname: 'images.gr-assets.com',
      },
      {
        protocol: 'https',
        hostname: 's.gr-assets.com',
      },
    ],
  },
}

module.exports = nextConfig
