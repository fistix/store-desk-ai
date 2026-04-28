const mockResponses = require('./config/mockResponses');

const resolvers = {
  Mutation: {
    updateBulkStockMonitoringCommand: async (_, { input }, context) => {
      const scenario = process.env.MOCK_SCENARIO || 'happy_path';
      console.log(`[Mock] Mutation: updateBulkStockMonitoringCommand`);
      console.log(`[Mock] User: ${context.userId}`);
      console.log(`[Mock] Variables: ${JSON.stringify(input)}`);

      if (scenario === 'slow_response') {
        await new Promise(resolve => setTimeout(resolve, parseInt(process.env.MOCK_SLOW_RESPONSE_MS || 3000)));
      }

      if (scenario === 'server_error') {
        throw new Error('Internal Server Error');
      }

      return mockResponses[scenario].stock;
    },
    updateBulkPriceMonitoringCommand: async (_, { input }, context) => {
      const scenario = process.env.MOCK_SCENARIO || 'happy_path';
      console.log(`[Mock] Mutation: updateBulkPriceMonitoringCommand`);
      console.log(`[Mock] User: ${context.userId}`);
      console.log(`[Mock] Variables: ${JSON.stringify(input)}`);

      if (scenario === 'slow_response') {
        await new Promise(resolve => setTimeout(resolve, parseInt(process.env.MOCK_SLOW_RESPONSE_MS || 3000)));
      }

      if (scenario === 'server_error') {
        throw new Error('Internal Server Error');
      }

      return mockResponses[scenario].price;
    }
  },
  Query: {
    health: () => 'ok'
  }
};

module.exports = resolvers;
