const rateLimit = require('express-rate-limit');

const storedeskRateLimit = rateLimit({
  windowMs: (process.env.STOREDESK_AI_RATE_LIMIT_WINDOW_SECONDS || 60) * 1000,
  max: parseInt(process.env.STOREDESK_AI_RATE_LIMIT_PER_USER || '30'),
  keyGenerator: (req) => {
    // Rate limit per user based on X-User-Id
    // In a real app, the user context is extracted from JWT by existing middleware
    return req.header('X-User-Id') || req.ip;
  },
  message: {
    error: 'Too many requests, please try again later.'
  }
});

module.exports = storedeskRateLimit;
