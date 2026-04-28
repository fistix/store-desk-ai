const crypto = require('crypto');

const storedeskServiceKeyAuth = (req, res, next) => {
  const serviceKey = req.header('X-Service-Key');
  const storedHashedKey = process.env.STOREDESK_AI_SERVICE_KEY; // This should be a hash in env

  if (!serviceKey) {
    return res.status(401).json({ error: 'Service key missing' });
  }

  // Hash the incoming key to compare with the stored hash
  const incomingHash = crypto.createHash('sha256').update(serviceKey).digest('hex');

  if (incomingHash !== storedHashedKey) {
    return res.status(401).json({ error: 'Invalid service key' });
  }

  // Validate presence of forwarded user context headers
  const userId = req.header('X-User-Id');
  const tenantId = req.header('X-Tenant-Id');
  const connectorId = req.header('X-Connector-Id');

  if (!userId || !tenantId || !connectorId) {
    return res.status(400).json({ error: 'Missing user context headers' });
  }

  // Whitelist check for mutations (only if this is the GraphQL endpoint)
  // For the purpose of this mock, we assume the AI gateway is POST /api/storedesk/assist
  // and the callback might be GraphQL.
  if (req.body && req.body.query) {
      const allowedMutations = process.env.STOREDESK_AI_ALLOWED_MUTATIONS.split(',');
      const query = req.body.query;
      const isMutationAllowed = allowedMutations.some(mutation => query.includes(mutation));
      
      if (!isMutationAllowed) {
          return res.status(403).json({ error: 'Mutation not authorized for AI service' });
      }
  }

  next();
};

module.exports = storedeskServiceKeyAuth;
