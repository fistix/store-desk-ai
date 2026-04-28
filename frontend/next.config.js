/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_STOREDESK_TEST_ENABLED: process.env.NEXT_PUBLIC_STOREDESK_TEST_ENABLED || 'true',
    NEXT_PUBLIC_TEST_CONNECTOR_ID: process.env.NEXT_PUBLIC_TEST_CONNECTOR_ID || 'test-connector-123',
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:4010'
  }
}

module.exports = nextConfig
