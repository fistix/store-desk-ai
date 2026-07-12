from .base import LLMProvider
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import List, Dict, Any, Optional
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import asyncio

class GeminiProvider(LLMProvider):
    def __init__(self, name: str, model: str, api_key: str):
        super().__init__(name, model, supports_tool_calling=True, api_key=api_key)
        # Track quota usage to prevent retries
        self._quota_exhausted = False
        self._quota_reset_time = 0

        # Create LLM with minimal configuration to avoid safety conflicts
        self.llm = ChatGoogleGenerativeAI(
            model=model, 
            google_api_key=api_key, 
            convert_system_message_to_human=True,
            max_retries=0
        )
        self._last_request_time = 0
        self._min_request_interval = 2.0  # Minimum 2 seconds between requests

    async def complete(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        print(f"[GEMINI] 🤖 Processing request with {len(messages)} messages")
        
        # Check if quota is exhausted and fail fast
        if self._quota_exhausted:
            print("[GEMINI] 🚫 Quota exhausted - failing fast without API call")
            return {
                "content": "API quota exceeded. Please try again later or use a different provider.",
                "provider": self.name,
                "error": "quota_exceeded"
            }
        
        # Implement custom rate limiting
        import time
        current_time = time.time()
        if current_time - self._last_request_time < self._min_request_interval:
            wait_time = self._min_request_interval - (current_time - self._last_request_time)
            print(f"[GEMINI] ⏱️ Rate limiting - waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        lc_messages = []
        for msg in messages:
            # Handle both LangChain message objects and dictionary messages
            if hasattr(msg, 'content'):
                # LangChain message object
                if hasattr(msg, 'type') and msg.type == 'system':
                    lc_messages.append(SystemMessage(content=msg.content))
                elif hasattr(msg, 'type') and msg.type == 'human':
                    lc_messages.append(HumanMessage(content=msg.content))
                elif hasattr(msg, 'type') and msg.type == 'ai':
                    lc_messages.append(AIMessage(content=msg.content))
                else:
                    # Fallback for message types without explicit type
                    lc_messages.append(msg)
            else:
                # Dictionary message
                if msg["role"] == "user":
                    lc_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    lc_messages.append(AIMessage(content=msg["content"]))

        try:
            if tools:
                print(f"[GEMINI] 🔧 Tool calling requested with {len(tools)} tools")
                # Use simple text response approach - pass tools for context but don't use them directly
                print(f"[GEMINI] 💬 Using text-based approach for tool calling")
                response = await self._safe_ainvoke(lc_messages, tools=tools)
                print(f"[GEMINI] ✅ Response received for tool-based request")
            else:
                print(f"[GEMINI] 💬 Invoking model {self.model} (no tools)")
                # Use async invoke with custom error handling
                response = await self._safe_ainvoke(lc_messages, tools=None)
            
            self._last_request_time = time.time()
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower() or "ResourceExhausted" in error_str:
                print("[GEMINI] 🚨 Rate limit error caught - failing fast without LangChain retries")
                print(f"[GEMINI] 🛑 Original error: {error_str}")
                # Mark quota as exhausted to prevent further requests
                self._quota_exhausted = True
                # Re-raise as a simple exception to prevent LangChain retries
                raise Exception("429 Rate limit exceeded - no retries to save tokens")
            else:
                print(f"[GEMINI] ❌ Error occurred: {str(e)}")
                raise  # Re-raise non-rate-limit errors
        
        print(f"[GEMINI] 📦 Raw response type: {type(response)}")
        print(f"[GEMINI] 💬 Response content: {response.content[:200]}..." if len(response.content) > 200 else f"[GEMINI] Response content: {response.content}")

        # Handle tool calls in response
        result = {"content": response.content, "provider": self.name}
        
        # Check if response has tool calls (native)
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_calls_data = []
            for tc in response.tool_calls:
                tool_calls_data.append({
                    "function": {
                        "name": tc.name,
                        "arguments": tc.args
                    }
                })
            result["tool_calls"] = tool_calls_data
            print(f"[GEMINI] 🔧 Native tool calls detected: {len(tool_calls_data)}")
        else:
            # Try to parse tool calls from text response
            parsed_tools = self._parse_tool_calls_from_text(response.content, tools)
            if parsed_tools:
                result["tool_calls"] = parsed_tools
                print(f"[GEMINI] 🔧 Parsed tool calls from text: {len(parsed_tools)}")
            else:
                print(f"[GEMINI] 💬 No tool calls found - text response only")
        
        print(f"[GEMINI] ✅ Returning response with provider: {self.name}")
        
        return result

    def _parse_tool_calls_from_text(self, content, tools):
        """Parse tool calls from LLM text response"""
        import re
        
        if not tools:
            return []
        
        print(f"[GEMINI] 🔍 Parsing tool calls from content: {content[:100]}...")
        
        tool_calls = []
        
        # Extract tool information
        for tool in tools:
            tool_name = tool.get("function", {}).get("name", "")
            tool_desc = tool.get("function", {}).get("description", "").lower()
            
            print(f"[GEMINI] 🔍 Checking tool: {tool_name}")
            
            # Check if content specifically mentions this tool type
            tool_mentioned = False
            
            # First check if LLM explicitly said no tools needed
            if '"tool": "none"' in content or '"tool":"none"' in content:
                tool_mentioned = False
            else:
                if "stock_monitoring" in tool_name.lower():
                    # Only detect stock monitoring if content mentions stock-related terms
                    stock_keywords = ["stock", "quantity", "alert"]
                    if any(keyword in content.lower() for keyword in stock_keywords):
                        tool_mentioned = True
                elif "price_monitoring" in tool_name.lower():
                    # Only detect price monitoring if content mentions price-related terms
                    price_keywords = ["price", "margin", "percentage"]
                    if any(keyword in content.lower() for keyword in price_keywords):
                        tool_mentioned = True
            
            if tool_mentioned:
                print(f"[GEMINI] ✅ Tool {tool_name} detected in response")
                
                # Parse arguments based on tool type and content
                args = {}
                
                if "stock_monitoring" in tool_name.lower():
                    # Stock monitoring tool
                    args = self._parse_stock_args(content)
                elif "price_monitoring" in tool_name.lower():
                    # Price monitoring tool  
                    args = self._parse_price_args(content)
                
                if args:
                    tool_calls.append({
                        "function": {
                            "name": tool_name,
                            "arguments": args
                        }
                    })
                    print(f"[GEMINI] ✅ Parsed tool call: {tool_name} with args: {args}")
        
        return tool_calls
    
    def _parse_stock_args(self, content):
        """Parse stock monitoring arguments from content"""
        import re
        args = {
            "bulkStockMonitoring": {
                "isApplyToAllProducts": False,
                "isQuantityEnabled": True
            }
        }
        
        # Extract threshold - try JSON format first, then text format
        threshold_match = re.search(r'"threshold"\s*:\s*(\d+)', content)
        if not threshold_match:
            threshold_match = re.search(r'threshold\s*:\s*(\d+)', content)
        if not threshold_match:
            threshold_match = re.search(r'threshold\s*(\d+)', content.lower())
        
        if threshold_match:
            args["bulkStockMonitoring"]["quantityThreshold"] = int(threshold_match.group(1))
            print(f"[GEMINI] ✅ Extracted threshold: {args['bulkStockMonitoring']['quantityThreshold']}")
        else:
            # Default threshold
            args["bulkStockMonitoring"]["quantityThreshold"] = 10
            print(f"[GEMINI] ⚠️ No threshold found, using default: 10")
        
        # Extract product IDs from JSON response
        product_ids = []
        product_ids_match = re.search(r'"productIds"\s*:\s*\[([^\]]*)\]', content)
        if product_ids_match:
            ids_str = product_ids_match.group(1)
            # Extract individual IDs (handle both UUID strings and numbers)
            # First try to extract quoted strings (UUIDs)
            uuid_matches = re.findall(r'"([^"]+)"', ids_str)
            if uuid_matches:
                # Use UUID strings as-is
                product_ids = uuid_matches
                print(f"[GEMINI] ✅ Extracted product IDs (UUIDs): {product_ids}")
            else:
                # Fallback to extracting numbers
                id_matches = re.findall(r'(\d+)', ids_str)
                if id_matches:
                    product_ids = [int(id_match) for id_match in id_matches]
                    print(f"[GEMINI] ✅ Extracted product IDs (numbers): {product_ids}")
        
        # Check for "all products"
        if "all products" in content.lower():
            args["bulkStockMonitoring"]["isApplyToAllProducts"] = True
        else:
            # Use extracted product IDs or empty array
            args["productIds"] = product_ids
        
        return args
    
    def _parse_price_args(self, content):
        """Parse price monitoring arguments from content"""
        import re
        args = {
            "bulkPriceMonitoring": {
                "isApplyToAllProducts": False,
                "isPriceEnabled": True
            }
        }
        
        # Extract percentage - try JSON format first, then text format
        percent_match = re.search(r'"percentage"\s*:\s*(\d+)', content)
        if not percent_match:
            percent_match = re.search(r'percentage\s*:\s*(\d+)', content)
        if not percent_match:
            percent_match = re.search(r'(\d+)%', content.lower())
        
        if percent_match:
            args["bulkPriceMonitoring"]["priceThresholdPercentage"] = float(percent_match.group(1))
            print(f"[GEMINI] ✅ Extracted percentage: {args['bulkPriceMonitoring']['priceThresholdPercentage']}")
        else:
            # Default percentage
            args["bulkPriceMonitoring"]["priceThresholdPercentage"] = 10.0
            print(f"[GEMINI] ⚠️ No percentage found, using default: 10.0")
        
        # Extract product IDs from JSON response
        product_ids = []
        product_ids_match = re.search(r'"productIds"\s*:\s*\[([^\]]*)\]', content)
        if product_ids_match:
            ids_str = product_ids_match.group(1)
            # Extract individual IDs (handle both UUID strings and numbers)
            # First try to extract quoted strings (UUIDs)
            uuid_matches = re.findall(r'"([^"]+)"', ids_str)
            if uuid_matches:
                # Use UUID strings as-is
                product_ids = uuid_matches
                print(f"[GEMINI] ✅ Extracted product IDs (UUIDs) for price monitoring: {product_ids}")
            else:
                # Fallback to extracting numbers
                id_matches = re.findall(r'(\d+)', ids_str)
                if id_matches:
                    product_ids = [int(id_match) for id_match in id_matches]
                    print(f"[GEMINI] ✅ Extracted product IDs (numbers) for price monitoring: {product_ids}")
        
        # Check for "all products"
        if "all products" in content.lower():
            args["bulkPriceMonitoring"]["isApplyToAllProducts"] = True
        else:
            # Use extracted product IDs or empty array
            args["productIds"] = product_ids
        
        return args

    def _generate_stock_tool_call(self, user_message):
        """Generate stock monitoring tool call from user message"""
        import re
        threshold_match = re.search(r'(\d+)\s*(?:units?|items?)', user_message.lower())
        threshold = int(threshold_match.group(1)) if threshold_match else 10
        
        return [{
            "function": {
                "name": "stock_monitoring",
                "arguments": {
                    "bulkStockMonitoring": {
                        "isApplyToAllProducts": "all products" in user_message.lower(),
                        "isQuantityEnabled": True,
                        "quantityThreshold": threshold
                    },
                    "productIds": []  # Will be filled by base_agent
                }
            }
        }]

    def _generate_price_tool_call(self, user_message):
        """Generate price monitoring tool call from user message"""
        import re
        percent_match = re.search(r'(\d+)%', user_message.lower())
        percentage = float(percent_match.group(1)) if percent_match else 10.0
        
        return [{
            "function": {
                "name": "price_monitoring", 
                "arguments": {
                    "bulkPriceMonitoring": {
                        "isApplyToAllProducts": "all products" in user_message.lower(),
                        "isPriceEnabled": True,
                        "priceThresholdPercentage": percentage
                    },
                    "productIds": []  # Will be filled by base_agent
                }
            }
        }]

    async def _safe_ainvoke(self, messages, tools=None):
        """Safe async invoke with proper tool calling and exception handling"""
        try:
            print(f"[GEMINI] 🔍 _safe_ainvoke called with {len(messages)} messages")
            print(f"[GEMINI] 🔍 Tools provided: {tools is not None}")
            if tools:
                print(f"[GEMINI] 🔍 Tools count: {len(tools)}")
            
            if tools:
                print("[GEMINI] 🛠️ Using reliable manual tool calling approach")
                
                # Extract user message and product IDs
                user_message = ""
                product_ids = []
                for msg in messages:
                    if hasattr(msg, 'content') and isinstance(msg.content, str):
                        # Extract product IDs from system message
                        if "Available Product IDs:" in msg.content:
                            import re
                            id_match = re.search(r'Available Product IDs:.*?\[(.*?)\]', msg.content)
                            if id_match:
                                # Extract IDs and strip quotes
                                raw_ids = id_match.group(1).split(',')
                                product_ids = [id.strip().strip("'").strip('"') for id in raw_ids if id.strip()]
                                print(f"[GEMINI] 📋 Extracted product IDs: {product_ids}")
                        # Extract user message (not system message)
                        elif not msg.content.startswith("You help"):
                            user_message = msg.content
                
                # Create a prompt for the LLM to decide which tool to use
                decision_prompt = f"""User request: "{user_message}"

Available tools:
1. stock_monitoring - for stock alerts and quantity monitoring
2. price_monitoring - for price monitoring and percentage thresholds

Available product IDs: {product_ids}

Analyze the user's request and determine:
1. Which tool(s) should be used (stock_monitoring, price_monitoring, both, or none)
2. What parameters are needed (include productIds if applicable)

IMPORTANT: If the user says "for all products" or similar, use productIds: "all" (string value).
For disable/enable operations, use enabled: true/false parameter.

CLARIFICATION RULE: If the user says "monitoring" or "enable monitoring" WITHOUT specifying "stock" or "price", 
you MUST ask for clarification. Do NOT assume both tools. Return no tools and indicate clarification is needed.

If multiple tools are needed, return an array of tool calls.

Respond in JSON format:
- Single tool: {{"tool": "tool_name", "parameters": {{"key": "value"}}}}
- Multiple tools: {{"tools": [{{"tool": "tool_name", "parameters": {{"key": "value"}}}}, ...]}}
- Clarification needed: {{"tool": "none", "parameters": {{"clarification": "Ask user which type of monitoring they want"}}}}"""
                
                # Call Gemini WITHOUT tools to get a decision
                decision_messages = [HumanMessage(content=decision_prompt)]
                decision_response = await self.llm.ainvoke(decision_messages)
                
                print(f"[GEMINI] 🧠 LLM decision: {decision_response.content[:200]}...")
                
                # Parse the LLM's decision and generate tool calls
                tool_calls = self._parse_llm_decision_to_tool_calls(decision_response.content, tools)
                
                if tool_calls:
                    print(f"[GEMINI] ✅ Generated {len(tool_calls)} tool calls from LLM decision")
                    return self._format_response_with_tool_calls(decision_response, tool_calls)
                else:
                    print("[GEMINI] 📝 No tool calls needed, returning text response")
                    return decision_response
            else:
                print("[GEMINI] 💬 No tools - calling LLM normally")
                response = await self.llm.ainvoke(messages)
                return response
            
        except Exception as e:
            error_str = str(e)
            print(f"[GEMINI] ❌ _safe_ainvoke error: {error_str}")
            print(f"[GEMINI] ❌ Error type: {type(e)}")
            
            # Handle StopCandidateException specifically
            if "StopCandidateException" in str(type(e)) or "finish_reason" in error_str:
                print("[GEMINI] 🚨 StopCandidateException - safety filter triggered")
                print("[GEMINI] 🔧 Attempting alternative approach with simplified context")
                
                # Try with extremely simplified messages
                simplified_response = await self._try_simplified_approach(messages, tools)
                if simplified_response:
                    return simplified_response
                
                # Final fallback: generate tool calls based on user intent analysis
                print("[GEMINI] 🔧 Using intent-based tool generation as fallback")
                return await self._generate_fallback_tool_calls(messages, tools)
            
            # Handle rate limit errors
            elif "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                print("[GEMINI] 🚨 Rate limit detected - failing fast")
                raise Exception("429 Rate limit exceeded - no retries to save tokens")
            
            # Re-raise other errors
            else:
                raise

    def _clean_messages(self, messages):
        """Clean messages to avoid triggering Gemini safety filters"""
        clean_messages = []
        for msg in messages:
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                if msg.content.startswith("You help"):
                    # Simplify system prompt to minimal
                    clean_content = "Help with product monitoring using available tools."
                    clean_messages.append(SystemMessage(content=clean_content))
                else:
                    clean_messages.append(msg)
            else:
                clean_messages.append(msg)
        return clean_messages

    def _clean_tool_schemas(self, tools):
        """Clean tool schemas to remove unsupported fields for Gemini"""
        clean_tools = []
        for tool in tools:
            clean_tool = tool.copy()
            if "function" in clean_tool:
                clean_function = clean_tool["function"].copy()
                if "parameters" in clean_function:
                    clean_function["parameters"] = self._clean_schema_recursive(clean_function["parameters"])
                clean_tool["function"] = clean_function
            clean_tools.append(clean_tool)
        
        print(f"[GEMINI] 🔄 Cleaned {len(clean_tools)} tool schemas for Gemini")
        return clean_tools

    def _clean_schema_recursive(self, schema):
        """Recursively clean schema to remove unsupported fields for Gemini"""
        if isinstance(schema, dict):
            clean_schema = {}
            for key, value in schema.items():
                # Remove unsupported validation fields
                if key in ["minimum", "maximum", "format", "pattern", "minLength", "maxLength"]:
                    continue
                # Keep type for objects and arrays (required by Gemini)
                if key == "type" and isinstance(value, str) and value in ["object", "array"]:
                    clean_schema[key] = value
                elif key == "type":
                    # Remove type for primitives (string, integer, boolean, number)
                    continue
                else:
                    clean_schema[key] = self._clean_schema_recursive(value)
            return clean_schema
        elif isinstance(schema, list):
            return [self._clean_schema_recursive(item) for item in schema]
        else:
            return schema

    def _parse_llm_decision_to_tool_calls(self, decision_text, tools):
        """Parse LLM decision into structured tool calls"""
        import json
        import re
        
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', decision_text, re.DOTALL)
            if json_match:
                decision_data = json.loads(json_match.group())
                
                # Check for clarification needed
                tool_name = decision_data.get("tool", "")
                if tool_name == "none":
                    clarification = decision_data.get("parameters", {}).get("clarification", "Please specify which type of monitoring you want (stock or price).")
                    print(f"[GEMINI] 📝 Clarification needed: {clarification}")
                    # Return empty tool calls to trigger clarification flow
                    return []
                
                # Check for multiple tools
                if "tools" in decision_data and isinstance(decision_data["tools"], list):
                    tool_calls = []
                    for tool_data in decision_data["tools"]:
                        tool_name = tool_data.get("tool", "")
                        parameters = tool_data.get("parameters", {})
                        tool_call = self._build_single_tool_call(tool_name, parameters)
                        if tool_call:
                            tool_calls.append(tool_call)
                    return tool_calls
                else:
                    # Single tool
                    tool_name = decision_data.get("tool", "")
                    parameters = decision_data.get("parameters", {})
                    tool_call = self._build_single_tool_call(tool_name, parameters)
                    if tool_call:
                        return [tool_call]
                
                # If we got here, no valid tool calls were found - return empty
                print(f"[GEMINI] 📝 No tool calls needed, returning text response")
                return []
        except Exception as e:
            print(f"[GEMINI] ❌ Error parsing LLM decision: {str(e)}")
        
        # Fallback: use existing text parsing ONLY if no JSON was found
        # Don't fall back if JSON parsing failed but we found "tool": "none"
        if "tool" in decision_text and "none" in decision_text:
            print(f"[GEMINI] 📝 Detected 'tool: none' in text, returning empty tool calls")
            return []
        return self._parse_tool_calls_from_text(decision_text, tools)

    def _build_single_tool_call(self, tool_name, parameters):
        """Build a single tool call structure"""
        if tool_name in ["stock_monitoring", "price_monitoring"]:
            # Build proper tool call structure
            if tool_name == "stock_monitoring":
                # Handle 'enabled' parameter for enable/disable operations
                is_enabled = parameters.get("enabled", True)
                print(f"[GEMINI] 🔍 Raw enabled value: {is_enabled} (type: {type(is_enabled)})")
                if isinstance(is_enabled, str):
                    is_enabled = is_enabled.lower() in ["true", "yes", "1"]
                elif isinstance(is_enabled, bool):
                    # Keep the boolean value as-is
                    pass
                print(f"[GEMINI] 🔍 Parsed enabled value: {is_enabled}")
                
                # Handle 'productIds: all' to set isApplyToAllProducts
                product_ids = parameters.get("productIds", [])
                is_apply_to_all = False
                print(f"[GEMINI] 🔍 Raw productIds value: {product_ids} (type: {type(product_ids)})")
                
                if isinstance(product_ids, str) and product_ids.lower() == "all":
                    is_apply_to_all = True
                    product_ids = []
                    print(f"[GEMINI] ✅ Detected 'all' - setting isApplyToAllProducts to True")
                else:
                    is_apply_to_all = parameters.get("isApplyToAllProducts", False)
                    print(f"[GEMINI] ⚠️ Not 'all' - using isApplyToAllProducts from parameters: {is_apply_to_all}")
                
                if "bulkStockMonitoring" not in parameters:
                    threshold_value = parameters.get("quantityThreshold", parameters.get("threshold", 10))
                    print(f"[GEMINI] 🔍 Threshold extraction - quantityThreshold: {parameters.get('quantityThreshold')}, threshold: {parameters.get('threshold')}, final: {threshold_value}")
                    parameters["bulkStockMonitoring"] = {
                        "isApplyToAllProducts": is_apply_to_all,
                        "isQuantityEnabled": is_enabled,
                        "quantityThreshold": threshold_value
                    }
                parameters["productIds"] = product_ids if isinstance(product_ids, list) else []
                
            elif tool_name == "price_monitoring":
                # Handle 'enabled' parameter for enable/disable operations
                is_enabled = parameters.get("enabled", True)
                if isinstance(is_enabled, str):
                    is_enabled = is_enabled.lower() in ["true", "yes", "1"]
                elif isinstance(is_enabled, bool):
                    # Keep the boolean value as-is
                    pass
                
                # Handle 'productIds: all' to set isApplyToAllProducts
                product_ids = parameters.get("productIds", [])
                is_apply_to_all = False
                
                if isinstance(product_ids, str) and product_ids.lower() == "all":
                    is_apply_to_all = True
                    product_ids = []
                else:
                    is_apply_to_all = parameters.get("isApplyToAllProducts", False)
                
                print(f"[GEMINI] 🔍 Raw productIds value: {product_ids} (type: {type(product_ids)})")
                print(f"[GEMINI] 🔍 Parsed productIds value: {product_ids}")
                print(f"[GEMINI] 🔍 isApplyToAllProducts value: {is_apply_to_all}")
                
                if "bulkPriceMonitoring" not in parameters:
                    parameters["bulkPriceMonitoring"] = {
                        "isApplyToAllProducts": is_apply_to_all,
                        "isPriceEnabled": is_enabled,
                        "priceThresholdPercentage": parameters.get("priceThresholdPercentage", parameters.get("percentage", 10.0))
                    }
                parameters["productIds"] = product_ids if isinstance(product_ids, list) else []
            
            return {
                "function": {
                    "name": tool_name,
                    "arguments": parameters
                }
            }
        return None

    def _format_response_with_tool_calls(self, response, tool_calls=None):
        """Format response with proper tool calls structure"""
        from langchain_core.messages import AIMessage
        
        if tool_calls:
            # Use provided tool calls
            formatted_calls = [
                {
                    "id": f"call_{i}",
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"]
                    }
                }
                for i, tc in enumerate(tool_calls)
            ]
            return AIMessage(
                content=response.content,
                additional_kwargs={"tool_calls": formatted_calls}
            )
        else:
            # Use response's existing tool calls
            return response

    async def _try_simplified_approach(self, messages, tools):
        """Try simplified approach to avoid safety triggers"""
        try:
            # Extract just the user message
            user_message = ""
            for msg in messages:
                if hasattr(msg, 'content') and isinstance(msg.content, str):
                    if not msg.content.startswith("You help"):
                        user_message = msg.content
                        break
            
            # Create minimal prompt
            minimal_prompt = f"User: {user_message}\n\nAvailable tools: stock_monitoring, price_monitoring\n\nWhich tool should be used and with what parameters?"
            
            minimal_messages = [HumanMessage(content=minimal_prompt)]
            response = await self.llm.ainvoke(minimal_messages)
            
            # Parse tool calls from response
            if response.content and tools:
                tool_calls = self._parse_tool_calls_from_text(response.content, tools)
                if tool_calls:
                    print(f"[GEMINI] ✅ Simplified approach succeeded with {len(tool_calls)} tool calls")
                    return self._format_response_with_tool_calls(response, tool_calls)
            
            return None
        except Exception as e:
            print(f"[GEMINI] ❌ Simplified approach failed: {str(e)}")
            return None

    async def _generate_fallback_tool_calls(self, messages, tools):
        """Generate fallback tool calls based on user intent analysis"""
        from langchain_core.messages import AIMessage
        
        # Extract user message
        user_message = ""
        for msg in messages:
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                if not msg.content.startswith("You help"):
                    user_message = msg.content
                    break
        
        # Analyze intent using simple LLM call
        intent_prompt = f"""Analyze this user request: "{user_message}"

Determine:
1. Which tool to use: stock_monitoring or price_monitoring or none
2. What parameters to extract

Respond in JSON format: {{"tool": "tool_name", "parameters": {{"key": "value"}}}}"""
        
        try:
            intent_response = await self.llm.ainvoke([HumanMessage(content=intent_prompt)])
            
            # Try to parse JSON response
            import json
            intent_data = json.loads(intent_response.content)
            
            if intent_data.get("tool") in ["stock_monitoring", "price_monitoring"]:
                tool_name = intent_data["tool"]
                parameters = intent_data.get("parameters", {})
                
                # Add missing required fields
                if tool_name == "stock_monitoring":
                    if "bulkStockMonitoring" not in parameters:
                        parameters["bulkStockMonitoring"] = {
                            "isApplyToAllProducts": False,
                            "isQuantityEnabled": True,
                            "quantityThreshold": parameters.get("quantityThreshold", 10)
                        }
                    if "productIds" not in parameters:
                        parameters["productIds"] = []
                elif tool_name == "price_monitoring":
                    if "bulkPriceMonitoring" not in parameters:
                        parameters["bulkPriceMonitoring"] = {
                            "isApplyToAllProducts": False,
                            "isPriceEnabled": True,
                            "priceThresholdPercentage": parameters.get("priceThresholdPercentage", 10.0)
                        }
                    if "productIds" not in parameters:
                        parameters["productIds"] = []
                
                tool_calls = [{
                    "function": {
                        "name": tool_name,
                        "arguments": parameters
                    }
                }]
                
                print(f"[GEMINI] ✅ Fallback generated {len(tool_calls)} tool call(s)")
                return AIMessage(
                    content=f"I'll help you set up {tool_name.replace('_', ' ')} for your products.",
                    additional_kwargs={"tool_calls": [
                        {
                            "id": "call_0",
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": parameters
                            }
                        }
                    ]}
                )
        except Exception as e:
            print(f"[GEMINI] ❌ Fallback intent analysis failed: {str(e)}")
        
        # Final fallback
        return AIMessage(content="I understand your request. Let me help you with product monitoring.")

    
