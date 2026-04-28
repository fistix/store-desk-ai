const serviceKeyAuth = (req, res, next) => {
  const serviceKey = req.header('X-Service-Key');
  const expectedKey = process.env.MOCK_SERVICE_KEY;

  if (!serviceKey || serviceKey !== expectedKey) {
    console.log(`[Mock Auth] Service Key: [${serviceKey ? 'INVALID' : 'MISSING'}]`);
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const userId = req.header('X-User-Id');
  const tenantId = req.header('X-Tenant-Id');
  const connectorId = req.header('X-Connector-Id');

  if (!userId || !tenantId || !connectorId) {
    console.log(`[Mock Auth] User context headers missing: UserId=${userId}, TenantId=${tenantId}, ConnectorId=${connectorId}`);
    return res.status(400).json({ error: 'Missing user context headers' });
  }

  console.log(`[Mock Auth] Authorized for User: ${userId}`);
  next();
};

module.exports = serviceKeyAuth;
