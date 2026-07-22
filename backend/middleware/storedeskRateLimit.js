const rateLimit = require('express-rate-limit');

const windowSeconds = parseInt(
  process.env.STOREDESK_AI_RATE_LIMIT_WINDOW_SECONDS || '60',
  10
);
const maxRequests = parseInt(
  process.env.STOREDESK_AI_RATE_LIMIT_PER_USER || '30',
  10
);

const storedeskRateLimit = rateLimit({
  windowMs: windowSeconds * 1000,
  max: maxRequests,
  standardHeaders: true, // RateLimit-Limit, RateLimit-Remaining, RateLimit-Reset
  legacyHeaders: false,
  keyGenerator: (req) => {
    // Rate limit per user based on X-User-Id
    // In a real app, the user context is extracted from JWT by existing middleware
    return req.header('X-User-Id') || req.ip;
  },
  message: {
    error: 'Too many requests, please try again later.',
  },
  handler: (req, res, _next, options) => {
    res.setHeader('Retry-After', String(Math.ceil(options.windowMs / 1000)));
    res.status(options.statusCode).send(options.message);
  },
});

module.exports = storedeskRateLimit;
