require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const storedeskRoutes = require('./routes/storedesk');
const storedeskServiceKeyAuth = require('./middleware/storedeskServiceKeyAuth');

const app = express();
const PORT = process.env.PORT || 4010;

// CORS middleware - Allow frontend access
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization, X-User-Id, X-Tenant-Id, X-Connector-Id, X-Service-Key, X-User-Email, X-User-Permissions');
    
    if (req.method === 'OPTIONS') {
        res.sendStatus(200);
    } else {
        next();
    }
});

app.use(bodyParser.json());

// 1.2 New AI Gateway Endpoint
// In real app, there would be JWT middleware here
app.use('/api/storedesk', storedeskRoutes);

// 1.3 Service Key Scoped Authorization
// This is where storedesk-ai calls back into NodeJS GraphQL
// Using middleware to protect internal routes
app.post('/graphql', storedeskServiceKeyAuth, (req, res) => {
    // Mock GraphQL execution
    const { query, variables } = req.body;
    console.log(`[GraphQL Callback] User: ${req.header('X-User-Id')}, Query: ${query}`);
    
    // Whitelist logic is already handled in storedeskServiceKeyAuth
    // In real app, this would execute the mutation
    res.json({
        data: {
            isSuccess: true,
            message: "Mutation executed successfully"
        }
    });
});

app.get('/health', (req, res) => {
    res.json({ status: 'ok', service: 'backend-proxy' });
});

app.listen(PORT, () => {
    console.log(`Backend server running on port ${PORT}`);
});
