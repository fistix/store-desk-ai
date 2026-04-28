require('dotenv').config();
const express = require('express');
const { ApolloServer } = require('apollo-server-express');
const bodyParser = require('body-parser');
const typeDefs = require('./schema/typeDefs');
const resolvers = require('./resolvers');
const serviceKeyAuth = require('./middleware/serviceKeyAuth');

async function startServer() {
  const app = express();
  const PORT = process.env.PORT || 4010;

  app.use(bodyParser.json());

  // Apply service key auth middleware to the /graphql endpoint
  app.use('/graphql', serviceKeyAuth);

  const server = new ApolloServer({
    typeDefs,
    resolvers,
    context: ({ req }) => ({
      userId: req.header('X-User-Id'),
      tenantId: req.header('X-Tenant-Id'),
      connectorId: req.header('X-Connector-Id')
    })
  });

  await server.start();
  server.applyMiddleware({ app });

  // 2.8 Runtime Control Endpoints
  let currentScenario = process.env.MOCK_SCENARIO || 'happy_path';
  let requestLogs = [];

  app.post('/mock/scenario', (req, res) => {
    currentScenario = req.body.scenario;
    res.json({ scenario: currentScenario });
  });

  app.get('/mock/scenario', (req, res) => {
    res.json({ scenario: currentScenario });
  });

  app.get('/mock/requests', (req, res) => {
    res.json(requestLogs);
  });

  app.delete('/mock/requests', (req, res) => {
    requestLogs = [];
    res.json({ message: 'Logs cleared' });
  });

  app.get('/health', (req, res) => {
    res.json({ status: 'ok', service: 'mock-server' });
  });

  app.listen(PORT, () => {
    console.log(`Mock server running at http://localhost:${PORT}${server.graphqlPath}`);
  });
}

startServer();
