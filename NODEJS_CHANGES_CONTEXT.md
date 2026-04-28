# StoreDesk AI - NodeJS Backend Changes Context

## 🎯 **PURPOSE**

NodeJS backend changes to integrate StoreDesk AI service with existing platform, providing GraphQL mutations, authentication, and real-time features for product management.

---

## 📋 **ARCHITECTURE OVERVIEW**

### **Integration Points**
```
NodeJS Backend (Existing Platform)
├── GraphQL API Extensions
│   ├── StoreDesk AI mutations
│   ├── Product management queries
│   └── Real-time subscriptions
├── Authentication Middleware
│   ├── Service key validation
│   ├── HMAC signature verification
│   └── User context injection
├── WebSocket Integration
│   ├── Stock level notifications
│   ├── Price change alerts
│   └── Real-time updates
└── API Gateway
    ├── StoreDesk AI proxy
    ├── Request routing
    └── Response formatting
```

### **Technology Stack**
- **Backend**: Node.js with Express.js
- **GraphQL**: Apollo Server with existing schema extensions
- **Database**: PostgreSQL with existing product tables
- **Authentication**: JWT + HMAC integration
- **Real-time**: WebSocket server with Socket.io
- **Caching**: Redis for session and performance

---

## 🏗️ **FILE STRUCTURE & CHANGES**

### **Modified Files**
```
backend/
├── graphql/
│   ├── schema.graphql              # EXTENDED - Add StoreDesk AI mutations
│   ├── resolvers/
│   │   ├── productResolver.js      # MODIFIED - Add AI mutations
│   │   ├── connectionResolver.js    # MODIFIED - Add AI context
│   │   └── index.js              # MODIFIED - Import new resolvers
│   └── typeDefs/
│       └── index.js               # MODIFIED - Add new types
├── middleware/
│   ├── auth.js                   # MODIFIED - Add HMAC verification
│   └── cors.js                   # MODIFIED - Allow AI service
├── routes/
│   ├── storedesk.js               # NEW - AI service integration
│   └── debug.js                  # NEW - Debug endpoints
├── services/
│   ├── productService.js          # MODIFIED - Add AI-specific methods
│   ├── notificationService.js     # NEW - Real-time notifications
│   └── aiIntegrationService.js    # NEW - AI service integration
├── websocket/
│   ├── server.js                 # NEW - WebSocket server
│   └── handlers.js               # NEW - Event handlers
└── config/
    ├── redis.js                  # NEW - Redis configuration
    └── ai.js                    # NEW - AI service config
```

---

## 🛠️ **DETAILED IMPLEMENTATION**

### **1. GraphQL Schema Extensions**
```graphql
# graphql/schema.graphql - EXTENSIONS

# Add to existing Product type
extend type Product {
  "Stock monitoring configuration"
  stockMonitoring: StockMonitoring
  
  "Price monitoring configuration"
  priceMonitoring: PriceMonitoring
  
  "AI-generated insights"
  aiInsights: [AIInsight!]
  
  "Last AI analysis timestamp"
  lastAnalyzedAt: String
}

# New types for AI integration
type StockMonitoring {
  enabled: Boolean!
  threshold: Int!
  lastAlert: String
  alertCount: Int!
  createdAt: String!
  updatedAt: String!
}

type PriceMonitoring {
  enabled: Boolean!
  marginPercentage: Float!
  lastAlert: String
  alertCount: Int!
  createdAt: String!
  updatedAt: String!
}

type AIInsight {
  id: ID!
  productId: ID!
  insightType: AIInsightType!
  title: String!
  description: String!
  confidence: Float!
  recommendations: [String!]!
  createdAt: String!
}

enum AIInsightType {
  STOCK_OPTIMIZATION
  PRICE_ADJUSTMENT
  TREND_ANALYSIS
  INVENTORY_FORECAST
}

# New mutations for StoreDesk AI
extend type Mutation {
  "Enable bulk stock monitoring for products"
  updateBulkStockMonitoring(
    input: BulkStockMonitoringInput!
  ): BulkStockMonitoringResponse!

  "Enable bulk price monitoring for products"
  updateBulkPriceMonitoring(
    input: BulkPriceMonitoringInput!
  ): BulkPriceMonitoringResponse!

  "Get product status with AI insights"
  getProductStatus(
    input: ProductStatusInput!
  ): ProductStatusResponse!

  "Create or update AI-generated insights"
  createAIInsight(
    input: AIInsightInput!
  ): AIInsightResponse!

  "Trigger AI analysis for products"
  triggerAIAnalysis(
    input: AIAnalysisInput!
  ): AIAnalysisResponse!
}

# New queries for StoreDesk AI
extend type Query {
  "Get AI insights for products"
  getAIInsights(
    productId: ID
    connectorId: ID!
    insightTypes: [AIInsightType!]
  ): [AIInsight!]!

  "Get AI analysis status"
  getAIAnalysisStatus(
    connectorId: ID!
  ): AIAnalysisStatus!
}

# New subscriptions for real-time updates
extend type Subscription {
  "Subscribe to stock level changes"
  stockLevelChanges(
    connectorId: ID!
    productIds: [ID!]
  ): StockChange!

  "Subscribe to price changes"
  priceChanges(
    connectorId: ID!
    productIds: [ID!]
  ): PriceChange!

  "Subscribe to AI insights"
  aiInsights(
    connectorId: ID!
    productIds: [ID!]
  ): AIInsight!
}

# Input types
input BulkStockMonitoringInput {
  productIds: [ID!]
  bulkStockMonitoring: BulkStockMonitoringDetailsInput!
  connectorId: ID!
}

input BulkStockMonitoringDetailsInput {
  isApplyToAllProducts: Boolean!
  isQuantityEnabled: Boolean!
  quantityThreshold: Int!
}

input BulkPriceMonitoringInput {
  productIds: [ID!]
  bulkPriceMonitoring: BulkPriceMonitoringDetailsInput!
  connectorId: ID!
}

input BulkPriceMonitoringDetailsInput {
  isApplyToAllProducts: Boolean!
  isMarginEnabled: Boolean!
  marginPercentage: Float!
}

input ProductStatusInput {
  productIds: [ID!]
  connectorId: ID!
  includeAIInsights: Boolean = false
}

input AIInsightInput {
  productId: ID!
  insightType: AIInsightType!
  title: String!
  description: String!
  confidence: Float!
  recommendations: [String!]!
}

input AIAnalysisInput {
  productIds: [ID!]
  connectorId: ID!
  analysisTypes: [AIInsightType!]
}

# Response types
type BulkStockMonitoringResponse {
  success: Boolean!
  message: String!
  affectedProducts: Int!
  updatedProducts: [Product!]!
  errors: [String!]!
}

type BulkPriceMonitoringResponse {
  success: Boolean!
  message: String!
  affectedProducts: Int!
  updatedProducts: [Product!]!
  errors: [String!]!
}

type ProductStatusResponse {
  success: Boolean!
  message: String!
  products: [Product!]!
  aiInsights: [AIInsight!]!
  totalCount: Int!
}

type AIInsightResponse {
  success: Boolean!
  message: String!
  insight: AIInsight
}

type AIAnalysisResponse {
  success: Boolean!
  message: String!
  analysisId: ID!
  estimatedDuration: Int!
}

type AIAnalysisStatus {
  analysisId: ID!
  status: AnalysisStatus!
  progress: Float!
  estimatedCompletion: String!
  results: [AIInsight!]
}

enum AnalysisStatus {
  PENDING
  IN_PROGRESS
  COMPLETED
  FAILED
}
```

### **2. Product Resolver Extensions**
```javascript
// graphql/resolvers/productResolver.js - MODIFICATIONS

const { 
  getProducts, 
  getProduct, 
  updateProducts,
  createAIInsight,
  triggerAnalysis
} = require('../../services/productService');
const { 
  notifyStockChange, 
  notifyPriceChange 
} = require('../../services/notificationService');

const productResolver = {
  // Existing queries remain unchanged
  Query: {
    // ... existing queries ...
    
    // NEW: Get AI insights
    getAIInsights: async (_, { productId, connectorId, insightTypes }, { user }) => {
      console.log(`[AI] Get insights: productId=${productId}, connectorId=${connectorId}`);
      
      try {
        const insights = await getAIInsights({
          productId,
          connectorId,
          insightTypes,
          userId: user.id
        });
        
        return insights;
      } catch (error) {
        console.error(`[AI] Error getting insights:`, error);
        throw new Error('Failed to retrieve AI insights');
      }
    },

    // NEW: Get AI analysis status
    getAIAnalysisStatus: async (_, { connectorId }, { user }) => {
      console.log(`[AI] Get analysis status: connectorId=${connectorId}`);
      
      try {
        const status = await getAIAnalysisStatus({
          connectorId,
          userId: user.id
        });
        
        return status;
      } catch (error) {
        console.error(`[AI] Error getting analysis status:`, error);
        throw new Error('Failed to retrieve analysis status');
      }
    }
  },

  Mutation: {
    // Existing mutations remain unchanged
    // ... existing mutations ...

    // NEW: Update bulk stock monitoring
    updateBulkStockMonitoring: async (_, { input }, { user }) => {
      console.log(`[AI] Update bulk stock monitoring:`, input);
      
      try {
        const result = await updateBulkStockMonitoring({
          input,
          userId: user.id,
          tenantId: user.tenantId
        });

        // Trigger real-time notifications
        if (result.success && result.updatedProducts.length > 0) {
          await notifyStockChange({
            connectorId: input.connectorId,
            products: result.updatedProducts,
            changeType: 'MONITORING_ENABLED'
          });
        }

        return result;
      } catch (error) {
        console.error(`[AI] Error updating stock monitoring:`, error);
        return {
          success: false,
          message: `Failed to update stock monitoring: ${error.message}`,
          affectedProducts: 0,
          updatedProducts: [],
          errors: [error.message]
        };
      }
    },

    // NEW: Update bulk price monitoring
    updateBulkPriceMonitoring: async (_, { input }, { user }) => {
      console.log(`[AI] Update bulk price monitoring:`, input);
      
      try {
        const result = await updateBulkPriceMonitoring({
          input,
          userId: user.id,
          tenantId: user.tenantId
        });

        // Trigger real-time notifications
        if (result.success && result.updatedProducts.length > 0) {
          await notifyPriceChange({
            connectorId: input.connectorId,
            products: result.updatedProducts,
            changeType: 'MONITORING_ENABLED'
          });
        }

        return result;
      } catch (error) {
        console.error(`[AI] Error updating price monitoring:`, error);
        return {
          success: false,
          message: `Failed to update price monitoring: ${error.message}`,
          affectedProducts: 0,
          updatedProducts: [],
          errors: [error.message]
        };
      }
    },

    // NEW: Get product status
    getProductStatus: async (_, { input }, { user }) => {
      console.log(`[AI] Get product status:`, input);
      
      try {
        const result = await getProductStatus({
          input,
          userId: user.id,
          tenantId: user.tenantId
        });

        return result;
      } catch (error) {
        console.error(`[AI] Error getting product status:`, error);
        return {
          success: false,
          message: `Failed to get product status: ${error.message}`,
          products: [],
          aiInsights: [],
          totalCount: 0
        };
      }
    },

    // NEW: Create AI insight
    createAIInsight: async (_, { input }, { user }) => {
      console.log(`[AI] Create insight:`, input);
      
      try {
        const insight = await createAIInsight({
          input,
          userId: user.id,
          tenantId: user.tenantId
        });

        // Trigger real-time notification
        await notifyInsightCreated({
          connectorId: input.connectorId,
          insight
        });

        return {
          success: true,
          message: 'AI insight created successfully',
          insight
        };
      } catch (error) {
        console.error(`[AI] Error creating insight:`, error);
        return {
          success: false,
          message: `Failed to create insight: ${error.message}`,
          insight: null
        };
      }
    },

    // NEW: Trigger AI analysis
    triggerAIAnalysis: async (_, { input }, { user }) => {
      console.log(`[AI] Trigger analysis:`, input);
      
      try {
        const result = await triggerAnalysis({
          input,
          userId: user.id,
          tenantId: user.tenantId
        });

        return result;
      } catch (error) {
        console.error(`[AI] Error triggering analysis:`, error);
        return {
          success: false,
          message: `Failed to trigger analysis: ${error.message}`,
          analysisId: null,
          estimatedDuration: 0
        };
      }
    }
  },

  // NEW: Subscriptions
  Subscription: {
    stockLevelChanges: {
      subscribe: async (_, { connectorId, productIds }, { user }) => {
        console.log(`[AI] Subscribe to stock changes: connectorId=${connectorId}`);
        
        // Validate user has access to this connector
        if (!await hasAccessToConnector(user.id, connectorId)) {
          throw new Error('Access denied to connector');
        }

        return {
          [Symbol.asyncIterator]: async function* () {
            // Use Redis pub/sub for real-time updates
            const channel = `stock_changes:${connectorId}`;
            const subscriber = redis.duplicate();
            
            await subscriber.subscribe(channel);
            
            for await (const message of subscriber) {
              const change = JSON.parse(message);
              
              // Filter by product IDs if specified
              if (productIds.length > 0 && !productIds.includes(change.productId)) {
                continue;
              }
              
              yield change;
            }
          }
        };
      }
    },

    priceChanges: {
      subscribe: async (_, { connectorId, productIds }, { user }) => {
        console.log(`[AI] Subscribe to price changes: connectorId=${connectorId}`);
        
        if (!await hasAccessToConnector(user.id, connectorId)) {
          throw new Error('Access denied to connector');
        }

        return {
          [Symbol.asyncIterator]: async function* () {
            const channel = `price_changes:${connectorId}`;
            const subscriber = redis.duplicate();
            
            await subscriber.subscribe(channel);
            
            for await (const message of subscriber) {
              const change = JSON.parse(message);
              
              if (productIds.length > 0 && !productIds.includes(change.productId)) {
                continue;
              }
              
              yield change;
            }
          }
        };
      }
    },

    aiInsights: {
      subscribe: async (_, { connectorId, productIds }, { user }) => {
        console.log(`[AI] Subscribe to AI insights: connectorId=${connectorId}`);
        
        if (!await hasAccessToConnector(user.id, connectorId)) {
          throw new Error('Access denied to connector');
        }

        return {
          [Symbol.asyncIterator]: async function* () {
            const channel = `ai_insights:${connectorId}`;
            const subscriber = redis.duplicate();
            
            await subscriber.subscribe(channel);
            
            for await (const message of subscriber) {
              const insight = JSON.parse(message);
              
              if (productIds.length > 0 && !productIds.includes(insight.productId)) {
                continue;
              }
              
              yield insight;
            }
          }
        };
      }
    }
  }
};

module.exports = { productResolver };
```

### **3. Authentication Middleware Extensions**
```javascript
// middleware/auth.js - MODIFICATIONS

const jwt = require('jsonwebtoken');
const crypto = require('crypto');
const { getUserById } = require('../services/userService');

// Existing authentication logic
// ... existing code ...

// NEW: HMAC signature verification for StoreDesk AI
function verifyStoreDeskAISignature(req, res, next) {
  // Skip for non-AI endpoints
  if (!req.path.startsWith('/api/storedesk') && !req.path.startsWith('/api/debug')) {
    return next();
  }

  const signature = req.headers['x-signature'];
  const timestamp = req.headers['x-timestamp'];
  const payload = JSON.stringify(req.body);

  if (!signature || !timestamp) {
    return res.status(401).json({ 
      error: 'Missing signature or timestamp' 
    });
  }

  // Check timestamp to prevent replay attacks (30 second window)
  const requestTime = parseInt(timestamp);
  const currentTime = Math.floor(Date.now() / 1000);
  
  if (Math.abs(currentTime - requestTime) > 30) {
    return res.status(401).json({ 
      error: 'Request timestamp too old' 
    });
  }

  // Verify HMAC signature
  const hmacSecret = process.env.STOREDESK_AI_HMAC_SECRET;
  const message = `${timestamp}:${payload}`;
  const expectedSignature = crypto
    .createHmac('sha256', hmacSecret)
    .update(message)
    .digest('hex');

  if (!crypto.timingSafeEqual(expectedSignature, signature)) {
    return res.status(401).json({ 
      error: 'Invalid signature' 
    });
  }

  // Extract user context from request
  const userContext = req.body.context || {};
  
  // Validate service key
  const serviceKey = req.headers['x-service-key'];
  if (serviceKey !== process.env.STOREDESK_AI_SERVICE_KEY) {
    return res.status(401).json({ 
      error: 'Invalid service key' 
    });
  }

  // Attach user context to request
  req.user = {
    id: userContext.user_id,
    tenantId: userContext.tenant_id,
    connectorId: userContext.connector_id,
    permissions: ['read', 'write', 'ai_access']
  };

  req.isStoreDeskAI = true;
  
  console.log(`[AUTH] StoreDesk AI request authenticated: user=${req.user.id}, tenant=${req.user.tenantId}`);
  
  next();
}

// Export both existing and new middleware
module.exports = {
  // Existing middleware
  authenticateToken,
  verifyToken,
  
  // NEW: StoreDesk AI authentication
  verifyStoreDeskAISignature
};
```

### **4. StoreDesk AI Integration Routes**
```javascript
// routes/storedesk.js - NEW FILE

const express = require('express');
const { verifyStoreDeskAISignature } = require('../middleware/auth');
const { 
  processAIRequest,
  getSessionData,
  clearSessionData 
} = require('../services/aiIntegrationService');
const { 
  getProviderStatus,
  getProviderUsage 
} = require('../services/providerService');

const router = express.Router();

// Main AI endpoint - proxy to StoreDesk AI service
router.post('/assist', verifyStoreDeskAISignature, async (req, res) => {
  try {
    console.log(`[AI] Processing request: ${req.body.message}`);
    
    // Process request through AI service
    const result = await processAIRequest({
      request: req.body,
      user: req.user,
      sessionId: req.body.sessionId
    });

    res.json(result);
  } catch (error) {
    console.error(`[AI] Error processing request:`, error);
    res.status(500).json({
      error: 'Internal server error',
      message: error.message
    });
  }
});

// Debug endpoints
router.get('/debug/session/:sessionId', verifyStoreDeskAISignature, async (req, res) => {
  try {
    const sessionData = await getSessionData(req.params.sessionId);
    res.json(sessionData);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.get('/debug/providers', verifyStoreDeskAISignature, async (req, res) => {
  try {
    const [status, usage] = await Promise.all([
      getProviderStatus(),
      getProviderUsage()
    ]);
    
    res.json({ status, usage });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.delete('/debug/session/:sessionId', verifyStoreDeskAISignature, async (req, res) => {
  try {
    await clearSessionData(req.params.sessionId);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
```

### **5. AI Integration Service**
```javascript
// services/aiIntegrationService.js - NEW FILE

const axios = require('axios');
const redis = require('../config/redis');

class AIIntegrationService {
  constructor() {
    this.aiServiceUrl = process.env.STOREDESK_AI_URL || 'http://localhost:8000';
    this.sessionTimeout = 3600; // 1 hour
  }

  async processAIRequest({ request, user, sessionId }) {
    console.log(`[AI] Processing request for session ${sessionId}`);

    try {
      // Load existing session data
      const sessionData = await this.getSessionData(sessionId);
      
      // Prepare request for AI service
      const aiRequest = {
        ...request,
        context: {
          ...request.context,
          existingHistory: sessionData.conversationHistory || [],
          pendingConfirmation: sessionData.pendingConfirmation
        }
      };

      // Call StoreDesk AI service
      const response = await axios.post(`${this.aiServiceUrl}/api/storedesk/assist`, aiRequest, {
        headers: {
          'Content-Type': 'application/json',
          'x-user-id': user.id,
          'x-tenant-id': user.tenantId,
          'x-connector-id': user.connectorId
        },
        timeout: 30000 // 30 second timeout
      });

      // Update session with new data
      await this.updateSessionData(sessionId, {
        conversationHistory: [
          ...(sessionData.conversationHistory || []),
          {
            role: 'user',
            content: request.message,
            timestamp: new Date().toISOString()
          },
          {
            role: 'assistant', 
            content: response.data.message,
            timestamp: new Date().toISOString(),
            actionsExecuted: response.data.actionsExecuted || []
          }
        ],
        pendingConfirmation: response.data.requiresConfirmation ? {
          question: response.data.message,
          timestamp: new Date().toISOString()
        } : null
      });

      return response.data;
    } catch (error) {
      console.error(`[AI] Error calling AI service:`, error);
      throw error;
    }
  }

  async getSessionData(sessionId) {
    try {
      const data = await redis.get(`session:${sessionId}`);
      return data ? JSON.parse(data) : {};
    } catch (error) {
      console.error(`[AI] Error getting session data:`, error);
      return {};
    }
  }

  async updateSessionData(sessionId, updates) {
    try {
      const existing = await this.getSessionData(sessionId);
      const updated = { ...existing, ...updates };
      
      await redis.setex(
        `session:${sessionId}`, 
        this.sessionTimeout, 
        JSON.stringify(updated)
      );
      
      console.log(`[AI] Session ${sessionId} updated`);
    } catch (error) {
      console.error(`[AI] Error updating session data:`, error);
    }
  }

  async clearSessionData(sessionId) {
    try {
      await redis.del(`session:${sessionId}`);
      console.log(`[AI] Session ${sessionId} cleared`);
    } catch (error) {
      console.error(`[AI] Error clearing session data:`, error);
    }
  }
}

module.exports = new AIIntegrationService();
```

### **6. WebSocket Server for Real-time Updates**
```javascript
// websocket/server.js - NEW FILE

const http = require('http');
const socketIo = require('socket.io');
const redis = require('../config/redis');
const { verifyStoreDeskAISignature } = require('../middleware/auth');

class WebSocketServer {
  constructor() {
    this.server = http.createServer();
    this.io = socketIo(this.server, {
      cors: {
        origin: process.env.ALLOWED_ORIGINS?.split(',') || ["http://localhost:3000"],
        methods: ["GET", "POST"]
      }
    });
    
    this.setupRedisAdapter();
    this.setupEventHandlers();
  }

  setupRedisAdapter() {
    // Use Redis adapter for scaling across multiple server instances
    const { createAdapter } = require('@socket.io/redis-adapter');
    const pubClient = redis.duplicate();
    const subClient = redis.duplicate();
    
    this.io.adapter(createAdapter(pubClient, subClient));
  }

  setupEventHandlers() {
    this.io.use(async (socket, next) => {
      try {
        // Authenticate WebSocket connection
        const token = socket.handshake.auth.token;
        const user = await this.verifyWebSocketToken(token);
        
        if (!user) {
          return next(new Error('Authentication failed'));
        }

        socket.user = user;
        socket.join(`tenant:${user.tenantId}`);
        socket.join(`connector:${user.connectorId}`);
        
        console.log(`[WS] User connected: ${user.id} to tenant ${user.tenantId}`);
        next();
      } catch (error) {
        next(error);
      }
    });

    this.io.on('connection', (socket) => {
      console.log(`[WS] New connection: ${socket.id}`);

      // Handle stock level changes
      socket.on('subscribe:stock', (data) => {
        const { productIds } = data;
        const room = `stock:${socket.user.connectorId}`;
        
        socket.join(room);
        console.log(`[WS] User ${socket.user.id} subscribed to stock changes for ${productIds?.length || 'all'} products`);
      });

      // Handle price changes
      socket.on('subscribe:price', (data) => {
        const { productIds } = data;
        const room = `price:${socket.user.connectorId}`;
        
        socket.join(room);
        console.log(`[WS] User ${socket.user.id} subscribed to price changes for ${productIds?.length || 'all'} products`);
      });

      // Handle AI insights
      socket.on('subscribe:insights', (data) => {
        const { productIds } = data;
        const room = `insights:${socket.user.connectorId}`;
        
        socket.join(room);
        console.log(`[WS] User ${socket.user.id} subscribed to AI insights for ${productIds?.length || 'all'} products`);
      });

      socket.on('disconnect', () => {
        console.log(`[WS] User disconnected: ${socket.id}`);
      });
    });
  }

  async verifyWebSocketToken(token) {
    try {
      const decoded = jwt.verify(token, process.env.JWT_SECRET);
      return await getUserById(decoded.userId);
    } catch (error) {
      return null;
    }
  }

  // Public methods for emitting events
  async emitStockChange(connectorId, change) {
    this.io.to(`stock:${connectorId}`).emit('stock:change', change);
    
    // Also publish to Redis for cross-server communication
    await redis.publish(`stock_changes:${connectorId}`, JSON.stringify(change));
  }

  async emitPriceChange(connectorId, change) {
    this.io.to(`price:${connectorId}`).emit('price:change', change);
    
    await redis.publish(`price_changes:${connectorId}`, JSON.stringify(change));
  }

  async emitAIInsight(connectorId, insight) {
    this.io.to(`insights:${connectorId}`).emit('ai:insight', insight);
    
    await redis.publish(`ai_insights:${connectorId}`, JSON.stringify(insight));
  }

  start(port = 3002) {
    this.server.listen(port, () => {
      console.log(`🚀 WebSocket server ready on port ${port}`);
    });
  }
}

module.exports = WebSocketServer;
```

---

## 🚀 **DEPLOYMENT & CONFIGURATION**

### **Environment Variables**
```bash
# .env.production - ADDITIONS
STOREDESK_AI_URL=http://storedesk-ai:8000
STOREDESK_AI_HMAC_SECRET=your-secret-key-here
STOREDESK_AI_SERVICE_KEY=your-service-key-here
WEBSOCKET_PORT=3002
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3002
REDIS_URL=redis://redis:6379
```

### **Docker Compose Updates**
```yaml
# docker-compose.prod.yml - MODIFICATIONS
version: '3.8'
services:
  # Existing services...
  
  # NEW: StoreDesk AI service
  storedesk-ai:
    build: ./storedesk-ai
    container_name: storedesk-ai
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - HMAC_SECRET=${HMAC_SECRET}
      - STOREDESK_AI_HMAC_SECRET=${STOREDESK_AI_HMAC_SECRET}
      - STOREDESK_AI_SERVICE_KEY=${STOREDESK_AI_SERVICE_KEY}
      - REDIS_URL=redis://redis:6379
    networks:
      - app-network
    depends_on:
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # NEW: WebSocket server
  websocket-server:
    build: ./backend
    container_name: websocket-server
    command: ["node", "websocket/server.js"]
    environment:
      - NODE_ENV=production
      - JWT_SECRET=${JWT_SECRET}
      - REDIS_URL=redis://redis:6379
      - WEBSOCKET_PORT=3002
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
    ports:
      - "3002:3002"
    networks:
      - app-network
    depends_on:
      - redis
    restart: unless-stopped

  # MODIFIED: Main backend with new routes
  backend:
    # ... existing configuration ...
    environment:
      # ... existing environment variables ...
      - STOREDESK_AI_URL=http://storedesk-ai:8000
      - STOREDESK_AI_HMAC_SECRET=${STOREDESK_AI_HMAC_SECRET}
      - STOREDESK_AI_SERVICE_KEY=${STOREDESK_AI_SERVICE_KEY}
      - REDIS_URL=redis://redis:6379
    volumes:
      # ... existing volumes ...
      - ./backend:/app
    networks:
      - app-network
    depends_on:
      - redis
      - storedesk-ai
    restart: unless-stopped

networks:
  app-network:
    driver: bridge
```

---

## 📊 **FEATURES & CAPABILITIES**

### **✅ New Features Added**
1. **GraphQL API Extensions**
   - StoreDesk AI specific mutations
   - Real-time subscriptions
   - AI insight management
   - Product status queries

2. **Authentication Integration**
   - HMAC signature verification
   - Service key validation
   - Replay attack prevention
   - User context injection

3. **Real-time Communication**
   - WebSocket server for live updates
   - Redis pub/sub for scaling
   - Stock/price change notifications
   - AI insight broadcasts

4. **Session Management**
   - Redis-based session storage
   - Conversation history persistence
   - Pending confirmation handling
   - Cross-request state management

5. **Debug Endpoints**
   - Session inspection
   - Provider status monitoring
   - Usage analytics
   - Health checks

### **🔧 Technical Features**
- **Scalable WebSocket architecture**
- **Redis-based caching and pub/sub**
- **Secure authentication flow**
- **GraphQL schema extensions**
- **Real-time event handling**
- **Error handling and logging**

---

## 🎯 **INTEGRATION TESTING**

### **Test Scenarios**
```bash
# Test StoreDesk AI integration
curl -X POST http://localhost:3000/api/storedesk/assist \
  -H "Content-Type: application/json" \
  -H "x-signature: $(echo -n '{"timestamp":"'$(date +%s)'","payload":"..."}' | openssl dgst -sha256 -hmac 'secret')" \
  -H "x-service-key: your-service-key" \
  -d '{"sessionId": "test123", "message": "Enable stock monitoring", "context": {...}}'

# Test WebSocket connection
wscat -c ws://localhost:3002?token=jwt-token

# Test debug endpoints
curl http://localhost:3000/api/debug/session/test123
curl http://localhost:3000/api/debug/providers
```

---

## 📝 **DEVELOPMENT GUIDELINES**

### **Adding New AI Features**
1. **Extend GraphQL schema** with new types and mutations
2. **Implement resolvers** with proper authentication
3. **Add WebSocket events** for real-time updates
4. **Update session management** for new state
5. **Add debug endpoints** for new features

### **Security Considerations**
- Always validate HMAC signatures
- Check user permissions for connectors
- Implement rate limiting for AI endpoints
- Log all AI service interactions
- Validate input data thoroughly

---

**🎉 NodeJS backend changes provide complete integration with StoreDesk AI service, including GraphQL extensions, authentication, real-time features, and comprehensive debugging capabilities!**
