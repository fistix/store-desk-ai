const express = require('express');
const axios = require('axios');
const crypto = require('crypto');
const storedeskRateLimit = require('../middleware/storedeskRateLimit');
const router = express.Router();

const HMAC_SECRET = process.env.STOREDESK_AI_HMAC_SECRET;
const AI_SERVICE_URL = process.env.STOREDESK_AI_URL;

router.post('/assist', storedeskRateLimit, async (req, res) => {
  try {
    // In a real app, user context is extracted from JWT
    // For this implementation, we assume headers or req.user exist
    // We'll extract them as defined in the plan
    const userContext = {
      userId: req.header('X-User-Id'), // These would normally come from req.user (JWT)
      tenantId: req.header('X-Tenant-Id'),
      connectorId: req.header('X-Connector-Id'),
      email: req.header('X-User-Email'),
      permissions: req.header('X-User-Permissions')
    };

    if (!userContext.userId || !userContext.tenantId || !userContext.connectorId) {
        return res.status(400).json({ error: 'Incomplete user context' });
    }

    const timestamp = Math.floor(Date.now() / 1000).toString();
    const rawBody = JSON.stringify(req.body);

    // HMAC-SHA256 signature using shared secret + timestamp + raw request body
    const signature = crypto
      .createHmac('sha256', HMAC_SECRET)
      .update(timestamp + rawBody)
      .digest('hex');

    const headers = {
      'Content-Type': 'application/json',
      'X-HMAC-Signature': signature,
      'X-Timestamp': timestamp,
      'X-User-Id': userContext.userId,
      'X-Tenant-Id': userContext.tenantId,
      'X-Connector-Id': userContext.connectorId
    };

    const response = await axios.post(`${AI_SERVICE_URL}/api/storedesk/assist`, req.body, { headers });

    // Logs every AI request with userId, timestamp, inputType (text/audio)
    console.log(`[AI Request] User: ${userContext.userId}, Timestamp: ${new Date().toISOString()}, InputType: ${req.body.inputType}`);

    res.status(response.status).send(response.data);
  } catch (error) {
    console.error('[AI Gateway Error]', error.message);
    if (error.response) {
      res.status(error.response.status).send(error.response.data);
    } else {
      res.status(500).json({ error: 'Internal AI gateway error' });
    }
  }
});

router.post('/voice-to-text', async (req, res) => {
  try {
    const { audioBase64 } = req.body;
    
    if (!audioBase64) {
      return res.status(400).json({ error: 'audioBase64 is required' });
    }

    const timestamp = Math.floor(Date.now() / 1000).toString();
    const rawBody = JSON.stringify({ audioBase64 });

    // HMAC-SHA256 signature using shared secret + timestamp + raw request body
    const signature = crypto
      .createHmac('sha256', HMAC_SECRET)
      .update(timestamp + rawBody)
      .digest('hex');

    const headers = {
      'Content-Type': 'application/json',
      'X-HMAC-Signature': signature,
      'X-Timestamp': timestamp
    };

    const response = await axios.post(`${AI_SERVICE_URL}/api/voice-to-text`, { audioBase64 }, { headers });

    console.log(`[Voice-to-Text] Request processed, Timestamp: ${new Date().toISOString()}`);

    res.status(response.status).send(response.data);
  } catch (error) {
    console.error('[Voice-to-Text Error]', error.message);
    if (error.response) {
      res.status(error.response.status).send(error.response.data);
    } else {
      res.status(500).json({ error: 'Internal voice-to-text error' });
    }
  }
});

module.exports = router;
