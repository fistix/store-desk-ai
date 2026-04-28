from agent.base_tool import BaseTool
from core.graphql_client import graphql_client
from typing import Dict, Any, List, Optional

class StockMonitoringTool(BaseTool):
    """Tool for updating stock monitoring settings for products."""

    def __init__(self):
        super().__init__("stock_monitoring", self.__doc__.strip())

    def to_langchain_tool(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "productIds": {"items": {"type": "string"}, "description": "List of product IDs to apply the change to. Required if isApplyToAllProducts is false."},
                        "bulkStockMonitoring": {
                            "type": "object",
                            "properties": {
                                "isApplyToAllProducts": {"description": "Whether to apply the change to all products. Set to true if user explicitly mentions 'all products'."},
                                "isQuantityEnabled": {"description": "Whether quantity monitoring is enabled."},
                                "quantityThreshold": {"description": "The quantity threshold for stock alerts."}
                            },
                            "required": ["isApplyToAllProducts", "isQuantityEnabled", "quantityThreshold"]
                        }
                    },
                    "required": ["bulkStockMonitoring"]
                }
            }
        }

    async def execute(self, parameters: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[STOCK_MONITORING_TOOL] 🔧 EXECUTING STOCK MONITORING UPDATE")
        print(f"[STOCK_MONITORING_TOOL] 📝 Parameters: {parameters}")
        print(f"[STOCK_MONITORING_TOOL] 👤 User Context: {user_context}")
        
        input_data = parameters.get("bulkStockMonitoring", {})
        product_ids = parameters.get("productIds")
        
        print(f"[STOCK_MONITORING_TOOL] 📊 Input Data: {input_data}")
        print(f"[STOCK_MONITORING_TOOL] 🏷️ Product IDs: {product_ids}")

        if not input_data.get("isApplyToAllProducts") and not product_ids:
            print(f"[STOCK_MONITORING_TOOL] ❌ Validation failed: No product IDs provided for specific update")
            return {"success": False, "message": "Product IDs are required if not applying to all products.", "intent": "UPDATE_STOCK_MONITORING"}
        
        if not input_data.get("isApplyToAllProducts") and product_ids:
            # Validate product_ids against selected_product_ids in user_context if available
            selected_product_ids = user_context.get("selected_product_ids", [])
            print(f"[STOCK_MONITORING_TOOL] 🔍 Selected Product IDs from context: {selected_product_ids}")
            
            if selected_product_ids and not all(p_id in selected_product_ids for p_id in product_ids):
                print(f"[STOCK_MONITORING_TOOL] ❌ Validation failed: Some product IDs not in selected context")
                return {"success": False, "message": "Some product IDs are not in the selected context.", "intent": "UPDATE_STOCK_MONITORING"}

        mutation_variables = {
            "productIds": product_ids if not input_data.get("isApplyToAllProducts") else [], # Empty list if applying to all
            "bulkStockMonitoring": {
                "isApplyToAllProducts": input_data.get("isApplyToAllProducts"),
                "isQuantityEnabled": input_data.get("isQuantityEnabled"),
                "quantityThreshold": input_data.get("quantityThreshold")
            }
        }
        
        print(f"[STOCK_MONITORING_TOOL] 🔄 Executing GraphQL mutation with variables: {mutation_variables}")

        try:
            print(f"[STOCK_MONITORING_TOOL] 🔄 Executing GraphQL mutation...")
            response = await graphql_client.execute_mutation(
                "updateBulkStockMonitoringCommand",
                mutation_variables,
                user_context
            )
            
            print(f"[STOCK_MONITORING_TOOL] 📦 GraphQL Response: {response}")

            if response["success"]:
                affected_count = len(product_ids) if product_ids else 0
                print(f"[STOCK_MONITORING_TOOL] ✅ Stock monitoring updated successfully for {affected_count} products")
                
                # Extract message from response data
                response_data = response.get("data", {})
                if isinstance(response_data, dict):
                    message = response_data.get("message", response.get("message", "Stock monitoring updated successfully"))
                else:
                    message = response.get("message", "Stock monitoring updated successfully")
                
                return {"success": True, "message": message, "intent": "UPDATE_STOCK_MONITORING", "affectedCount": affected_count}
            else:
                print(f"[STOCK_MONITORING_TOOL] ❌ Stock monitoring update failed: {response['message']}")
                return {"success": False, "message": response["message"], "intent": "UPDATE_STOCK_MONITORING"}
        except Exception as e:
            print(f"[STOCK_MONITORING_TOOL] ❌ GraphQL execution error: {str(e)}")
            print(f"[STOCK_MONITORING_TOOL] ❌ Error type: {type(e)}")
            
            # Check if it's an HTTPException and get more details
            if hasattr(e, 'status_code'):
                print(f"[STOCK_MONITORING_TOOL] ❌ HTTP Status Code: {e.status_code}")
            if hasattr(e, 'detail'):
                print(f"[STOCK_MONITORING_TOOL] ❌ HTTP Detail: {e.detail}")
            
            # Get full exception details
            import traceback
            print(f"[STOCK_MONITORING_TOOL] ❌ Full traceback: {traceback.format_exc()}")
            
            return {"success": False, "message": f"GraphQL execution failed: {str(e)}", "intent": "UPDATE_STOCK_MONITORING"}
