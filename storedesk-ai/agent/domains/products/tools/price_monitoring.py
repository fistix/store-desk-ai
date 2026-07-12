from agent.base_tool import BaseTool
from core.graphql_client import graphql_client
from typing import Dict, Any, List, Optional

class PriceMonitoringTool(BaseTool):
    """Enable or disable price/margin monitoring for selected or all products. Use for both enable and disable requests."""
    def __init__(self):
        super().__init__("price_monitoring", self.__doc__.strip())

    def to_langchain_tool(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "productIds": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Product IDs to update. When the user says 'selected products', "
                                "use the Available Product IDs from the system prompt. "
                                "Leave empty when isApplyToAllProducts is true."
                            ),
                        },
                        "bulkPriceMonitoring": {
                            "type": "object",
                            "properties": {
                                "isApplyToAllProducts": {
                                    "type": "boolean",
                                    "description": "True only if the user explicitly says 'all products'. False for 'selected products'.",
                                },
                                "isPriceEnabled": {
                                    "type": "boolean",
                                    "description": "true to enable price monitoring, false to disable it.",
                                },
                                "priceThresholdPercentage": {
                                    "type": "number",
                                    "description": (
                                        "Margin/price threshold percentage when enabling. "
                                        "Use 0 when disabling price monitoring."
                                    ),
                                },
                            },
                            "required": ["isApplyToAllProducts", "isPriceEnabled", "priceThresholdPercentage"]
                        }
                    },
                    "required": ["bulkPriceMonitoring"]
                }
            }
        }

    async def execute(self, parameters: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[PRICE_MONITORING_TOOL] 🔧 EXECUTING PRICE MONITORING UPDATE")
        print(f"[PRICE_MONITORING_TOOL] 📝 Parameters: {parameters}")
        print(f"[PRICE_MONITORING_TOOL] 👤 User Context: {user_context}")
        
        input_data = parameters.get("bulkPriceMonitoring", {})
        product_ids = parameters.get("productIds")
        selected_product_ids = user_context.get("selected_product_ids", []) or []
        
        print(f"[PRICE_MONITORING_TOOL] 📊 Input Data: {input_data}")
        print(f"[PRICE_MONITORING_TOOL] 🏷️ Product IDs: {product_ids}")

        # Prefer UI-selected products when the model omitted productIds
        if not input_data.get("isApplyToAllProducts") and not product_ids and selected_product_ids:
            product_ids = list(selected_product_ids)
            parameters["productIds"] = product_ids
            print(f"[PRICE_MONITORING_TOOL] ✅ Using selected_product_ids from context: {product_ids}")

        if not input_data.get("isApplyToAllProducts") and not product_ids:
            print(f"[PRICE_MONITORING_TOOL] ❌ Validation failed: No product IDs provided for specific update")
            return {"success": False, "message": "Product IDs are required if not applying to all products.", "intent": "UPDATE_PRICE_MONITORING"}
        
        if not input_data.get("isApplyToAllProducts") and product_ids:
            # Validate product_ids against selected_product_ids in user_context if available
            print(f"[PRICE_MONITORING_TOOL] 🔍 Selected Product IDs from context: {selected_product_ids}")
            
            if selected_product_ids and not all(p_id in selected_product_ids for p_id in product_ids):
                print(f"[PRICE_MONITORING_TOOL] ❌ Validation failed: Some product IDs not in selected context")
                return {"success": False, "message": "Some product IDs are not in the selected context.", "intent": "UPDATE_PRICE_MONITORING"}

        mutation_variables = {
            "productIds": product_ids if not input_data.get("isApplyToAllProducts") else [], # Empty list if applying to all
            "bulkPriceMonitoring": {
                "isApplyToAllProducts": input_data.get("isApplyToAllProducts"),
                "isPriceEnabled": input_data.get("isPriceEnabled"),
                "priceThresholdPercentage": input_data.get("priceThresholdPercentage")
            }
        }
        
        print(f"[PRICE_MONITORING_TOOL] 🔄 Executing GraphQL mutation with variables: {mutation_variables}")

        response = await graphql_client.execute_mutation(
            "updateBulkPriceMonitoringCommand",
            mutation_variables,
            user_context
        )
        
        print(f"[PRICE_MONITORING_TOOL] 📦 GraphQL Response: {response}")

        if response["success"]:
            affected_count = len(product_ids) if product_ids else 0
            print(f"[PRICE_MONITORING_TOOL] ✅ Price monitoring updated successfully for {affected_count} products")
            
            # Extract message from response data
            response_data = response.get("data", {})
            if isinstance(response_data, dict):
                message = response_data.get("message", response.get("message", "Price monitoring updated successfully"))
            else:
                message = response.get("message", "Price monitoring updated successfully")
            
            return {"success": True, "message": message, "intent": "UPDATE_PRICE_MONITORING", "affectedCount": affected_count}
        else:
            print(f"[PRICE_MONITORING_TOOL] ❌ Price monitoring update failed: {response['message']}")
            return {"success": False, "message": response["message"], "intent": "UPDATE_PRICE_MONITORING"}
