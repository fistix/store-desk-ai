const { gql } = require('apollo-server-express');

const typeDefs = gql`
  input BulkStockMonitoringInput {
    isApplyToAllProducts: Boolean!
    isQuantityEnabled: Boolean!
    quantityThreshold: Int!
  }

  input UpdateBulkStockMonitoringInput {
    productIds: [ID!]
    bulkStockMonitoring: BulkStockMonitoringInput!
  }

  input BulkPriceMonitoringInput {
    isApplyToAllProducts: Boolean!
    isPriceEnabled: Boolean!
    priceThresholdPercentage: Float!
  }

  input UpdateBulkPriceMonitoringInput {
    productIds: [ID!]
    bulkPriceMonitoring: BulkPriceMonitoringInput!
  }

  type UpdateResponse {
    isSuccess: Boolean!
    message: String!
  }

  type Mutation {
    updateBulkStockMonitoringCommand(input: UpdateBulkStockMonitoringInput!): UpdateResponse!
    updateBulkPriceMonitoringCommand(input: UpdateBulkPriceMonitoringInput!): UpdateResponse!
  }

  type Query {
    health: String
  }
`;

module.exports = typeDefs;
