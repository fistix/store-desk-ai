# StoreDesk AI - Complete Code Context for AI Models

## 🎯 **PURPOSE**

This document provides comprehensive code context for any AI model to understand, analyze, and assist with StoreDesk AI implementation. Perfect for code review, debugging, feature development, and system maintenance.

---

## 📋 **SYSTEM OVERVIEW**

### **Architecture**
```
NodeJS Frontend → FastAPI Gateway → LangGraph Orchestrator → Domain Agents → LLM Providers → Response
```

### **Technology Stack**
- **Backend**: Python 3.9+ with FastAPI
- **Orchestration**: LangGraph for state management and flow control
- **AI Integration**: Multiple LLM providers (Gemini, OpenAI, Groq)
- **Containerization**: Docker with production configuration
- **Authentication**: HMAC-based request security

---

## 🏗️ **CODE STRUCTURE & KEY FILES**

### **1. Core Gateway (`core/gateway.py`)**
```python
# Main API endpoint and request handling
from fastapi import FastAPI, Request, HTTPException
from agent.orchestrator import StoreDeskOrchestrator
from core.auth import verify_hmac_signature

app = FastAPI()

@app.post("/api/storedesk/assist")
async def assist_endpoint(request: AIRequest):
    """Main AI service endpoint"""
    # HMAC authentication
    signature = request.headers.get("x-signature")
    if not verify_hmac_signature(request_body, signature):
        raise HTTPException(401, "Invalid signature")
    
    # Orchestrator invocation
    orchestrator = StoreDeskOrchestrator()
    result = await orchestrator.process_request(
        user_message=request.message,
        user_context=request.context,
        session_id=request.sessionId
    )
    
    return result

@app.get("/health")
async def health_check():
    """Service health monitoring"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
```

### **2. Orchestrator (`agent/orchestrator.py`)**
```python
# Main request coordination and routing logic
from langgraph.graph import StateGraph, END
from agent.domains import DomainRegistry
from typing import Dict, Any

class StoreDeskOrchestrator:
    def __init__(self):
        self.domains = DomainRegistry()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """LangGraph construction with nodes and conditional edges"""
        graph = StateGraph(AgentState)
        
        # Core nodes
        graph.add_node("resolve_confirmation", self._resolve_confirmation_node)
        graph.add_node("route_to_domain", self._route_to_domain_node)
        graph.add_node("run_products_agent", self._run_products_agent_node)
        graph.add_node("handle_clarification", self._handle_clarification_node)
        graph.add_node("compose_response", self._compose_response_node)
        
        # Entry point
        graph.set_entry_point("resolve_confirmation")
        
        # Conditional routing (FIXED)
        graph.add_conditional_edges(
            "resolve_confirmation",
            self._decide_after_confirmation,
            {
                "proceed_with_action": "run_products_agent",
                "clarification": "handle_clarification",
                "cancel": "compose_response",
                "no_pending": "route_to_domain"
            }
        )
        
        # FIXED: Direct routing with lambda function
        graph.add_conditional_edges(
            "route_to_domain",
            lambda state: "run_products_agent" 
                if any(kw in state["userMessage"].lower() 
                    for kw in ["stock", "price", "product", "monitoring"]) 
                else "handle_clarification",
            {
                "run_products_agent": "compose_response",
                "handle_clarification": "compose_response"
            }
        )
        
        # Final edges
        graph.add_edge("run_products_agent", "compose_response")
        graph.add_edge("handle_clarification", "compose_response")
        graph.add_edge("compose_response", END)
        
        return graph
    
    async def process_request(self, user_message, user_context, session_id):
        """Main request processing entry point"""
        state = {
            "userMessage": user_message,
            "userContext": user_context,
            "conversationHistory": [],
            "pendingConfirmation": None,
            "toolCallsMade": [],
            "toolResults": [],
            "iterationCount": 0,
            "finalResponse": None,
            "clarificationQuestion": None,
            "requiresConfirmation": False
        }
        
        # Execute graph
        result = await self.graph.ainvoke(state)
        return result.get("finalResponse", {"message": None, "actionsExecuted": []})
```

### **3. Products Agent (`agent/domains/products/agent.py`)**
```python
# Specialized agent for product management
from agent.base_agent import BaseAgent
from agent.domains.products import product_tool_registry
from typing import List, Dict, Any

class ProductsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="products",
            description="Manage product stock and price monitoring",
            system_prompt=PRODUCT_AGENT_SYSTEM_PROMPT,
            tools=product_tool_registry.tools
        )
    
    def _build_graph(self) -> StateGraph:
        """Products agent specific graph"""
        graph = StateGraph(AgentState)
        
        graph.add_node("call_llm", self._call_llm_node)
        graph.add_node("execute_tool", self._execute_tool_node)
        graph.add_node("generate_response", self._generate_response_node)
        
        graph.set_entry_point("call_llm")
        
        # Conditional edges for tool execution
        graph.add_conditional_edges(
            "call_llm",
            self._decide_next_step,
            {
                "execute_tool": "execute_tool",
                "generate_response": "generate_response"
            }
        )
        
        graph.add_edge("execute_tool", "generate_response")
        graph.add_edge("generate_response", END)
        
        return graph
    
    async def _call_llm_node(self, state: AgentState) -> Dict[str, Any]:
        """LLM invocation with tools"""
        print(f"[PRODUCTS AGENT] Calling LLM with tools_available=True")
        print(f"[PRODUCTS AGENT] User message: {state.get('userMessage', 'No message')[:100]}...")
        
        llm_response = await self._call_llm(state, tools_available=True)
        print(f"[PRODUCTS AGENT] LLM response received: {type(llm_response)}")
        
        # Handle tool calls and confirmations
        if "tool_calls" in llm_response and llm_response["tool_calls"]:
            print(f"[PRODUCTS AGENT] Found {len(llm_response['tool_calls'])} tool calls")
            
            # Check for bulk operations requiring confirmation
            tool_call_args = llm_response["tool_calls"][0]["function"]["arguments"]
            if tool_call_args.get("bulkStockMonitoring", {}).get("isApplyToAllProducts", False) or \
               tool_call_args.get("bulkPriceMonitoring", {}).get("isApplyToAllProducts", False):
                
                confirmation_question = "Are you sure you want to apply this change to all products?"
                print(f"[PRODUCTS AGENT] Setting requiresConfirmation: True")
                return {
                    "toolCallsMade": llm_response["tool_calls"],
                    "requiresConfirmation": True,
                    "clarificationQuestion": confirmation_question,
                    "finalResponse": {"message": confirmation_question, "actionsExecuted": []}
                }
        
        return {
            "toolCallsMade": llm_response.get("tool_calls", []),
            "finalResponse": {"message": llm_response.get("content", "I'll help you set that up."), "actionsExecuted": []}
        }
```

### **4. Provider System (`providers/manager.py`, `providers/gemini.py`)**
```python
# LLM provider abstraction and management
from typing import Dict, Any, List
from config.settings import settings

class ProviderManager:
    def __init__(self):
        self.providers = {
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "groq": GroqProvider()
        }
    
    async def get_response(self, messages: List[Dict], tools=None):
        """Provider selection and API call management"""
        provider = self.select_provider()
        print(f"[PROVIDER] Selected provider: {provider.__class__.__name__}")
        
        try:
            print(f"[PROVIDER] Making API call to {provider.__class__.__name__}")
            response = await provider.call_api(messages, tools)
            print(f"[PROVIDER] Response received: {response.get('status_code', 'N/A')}")
            return response
        except Exception as e:
            print(f"[PROVIDER] Error: {str(e)}")
            return {"error": str(e)}

class GeminiProvider:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    
    async def call_api(self, messages: List[Dict], tools=None):
        """Google Gemini API integration"""
        print(f"[GEMINI] Calling API with {len(messages)} messages")
        
        headers = {"Content-Type": "application/json"}
        payload = self._build_payload(messages, tools)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, headers=headers, json=payload) as response:
                print(f"[GEMINI] Response status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"[GEMINI] Response received: {len(str(result))} chars")
                    return {"status_code": response.status, "content": result}
                else:
                    error_text = await response.text()
                    print(f"[GEMINI] Error response: {error_text}")
                    return {"status_code": response.status, "error": error_text}
```

---

## 🔄 **REQUEST FLOW & STATE MANAGEMENT**

### **LangGraph Execution Flow**
```python
# 1. Initial State Creation
state = AgentState(
    userMessage="What is the status of my products?",
    userContext={"user_id": "test-user", "selected_product_ids": []},
    conversationHistory=[],
    pendingConfirmation=None,
    toolCallsMade=[],
    toolResults=[],
    iterationCount=0,
    finalResponse=None,
    clarificationQuestion=None,
    requiresConfirmation=False
)

# 2. Graph Execution Path
resolve_confirmation (no pending) 
  → route_to_domain (keywords: ['product'] match)
    → run_products_agent (lambda returns "run_products_agent")
      → Products Agent LLM call
        → Tool execution (if needed)
          → Response composition
            → Gateway response
```

### **State Preservation Strategy**
```python
# FIXED: Lambda function for direct decision
graph.add_conditional_edges(
    "route_to_domain",
    lambda state: "run_products_agent"  # Direct decision, no state modification
        if any(kw in state["userMessage"].lower() 
            for kw in ["stock", "price", "product", "monitoring"]), 
    {"run_products_agent": "compose_response", "handle_clarification": "compose_response"}
)

# BEFORE (BROKEN): Method that modified state
def _route_to_products_agent(self, state: AgentState) -> str:
    state["domain_route"] = "products"  # State didn't persist
    return "run_products_agent"
```

---

## 🛠️ **TOOLS & BUSINESS LOGIC**

### **Product Management Tools**
```python
@tool
def bulkStockMonitoring(
    isApplyToAllProducts: bool,
    threshold: int,
    selectedProductIds: List[str] = None
) -> Dict[str, Any]:
    """Enable stock monitoring with threshold alerts"""
    print(f"[TOOL] bulkStockMonitoring: isApplyToAllProducts={isApplyToAllProducts}, threshold={threshold}")
    
    if isApplyToAllProducts:
        return {
            "message": f"Stock monitoring enabled for all products with threshold {threshold}",
            "actionsExecuted": [{"type": "bulk_stock_monitoring", "details": {"threshold": threshold}}]
        }
    else:
        return {
            "message": f"Stock monitoring enabled for {len(selectedProductIds)} products with threshold {threshold}",
            "actionsExecuted": [{"type": "selective_stock_monitoring", "details": {"product_ids": selectedProductIds, "threshold": threshold}}]
        }

@tool
def bulkPriceMonitoring(
    isApplyToAllProducts: bool,
    marginPercentage: float,
    selectedProductIds: List[str] = None
) -> Dict[str, Any]:
    """Set price monitoring for profit margin tracking"""
    print(f"[TOOL] bulkPriceMonitoring: isApplyToAllProducts={isApplyToAllProducts}, margin={marginPercentage}")
    
    return {
        "message": f"Price monitoring set to {marginPercentage}% margin for products",
        "actionsExecuted": [{"type": "price_monitoring", "details": {"margin_percentage": marginPercentage}}]
    }
```

### **Confirmation Workflow**
```python
# Bulk operation confirmation system
if isApplyToAllProducts:
    return {
        "requiresConfirmation": True,
        "clarificationQuestion": "Are you sure you want to apply this to all products?",
        "pendingConfirmation": {
            "pendingIntent": "bulkStockMonitoring",
            "pendingParameters": {
                "isApplyToAllProducts": True,
                "threshold": threshold
            }
        }
    }

# Confirmation resolution
if "yes" in user_message.lower():
    return {
        "userMessage": pending_confirmation["pendingIntent"],
        "toolCallsMade": [{
            "function": {
                "name": pending_confirmation["pendingIntent"],
                "arguments": pending_confirmation["pendingParameters"]
            }
        }],
        "pendingConfirmation": None,
        "requiresConfirmation": False
    }
```

---

## 📊 **ENHANCED LOGGING SYSTEM**

### **Complete Visibility Implementation**
```python
# Gateway Level Logging
[GATEWAY] About to invoke orchestrator graph
[GATEWAY] Initial state keys: ['userMessage', 'userContext', 'conversationHistory', ...]
[GATEWAY] Orchestrator result received: <class 'dict'>

# Orchestrator Level Logging
[ORCHESTRATOR] Initializing orchestrator...
[ORCHESTRATOR] Loaded domains: ['products']
[ORCHESTRATOR] Graph built successfully
[ORCHESTRATOR] Message: 'what is the status of my products?'
[ORCHESTRATOR] Keywords checked: ['stock', 'price', 'product', 'monitoring']
[ORCHESTRATOR] Matched keywords: ['product']
[ORCHESTRATOR] Routing to products agent for message: what is the status of my products?
[ORCHESTRATOR] Running products agent...
[ORCHESTRATOR] Products agent completed: <class 'dict'>

# Products Agent Level Logging
[PRODUCTS AGENT] Calling LLM with tools_available=True
[PRODUCTS AGENT] User message: what is the status of my products?...
[PRODUCTS AGENT] LLM response received: <class 'dict'>
[PRODUCTS AGENT] Found 1 tool calls
[PRODUCTS AGENT] Executing tool node
[TOOL] bulkStockMonitoring: isApplyToAllProducts=False, threshold=5

# Provider Level Logging
[PROVIDER] Selected provider: GeminiProvider
[PROVIDER] Making API call to GeminiProvider
[GEMINI] Calling API with 3 messages
[GEMINI] Response status: 200
[GEMINI] Response received: 1247 chars
```

---

## 🔐 **SECURITY & AUTHENTICATION**

### **HMAC Authentication System**
```python
import hmac
import hashlib
from config.settings import settings

def verify_hmac_signature(payload: str, signature: str) -> bool:
    """Verify HMAC signature for request authentication"""
    secret = settings.HMAC_SECRET
    expected_signature = hmac.new(
        secret.encode(), 
        payload.encode(), 
        hashlib.sha256
    ).hexdigest()
    
    print(f"[AUTH] Verifying HMAC signature")
    print(f"[AUTH] Expected signature: {expected_signature}")
    print(f"[AUTH] Received signature: {signature}")
    
    is_valid = hmac.compare_digest(expected_signature, signature)
    print(f"[AUTH] Signature valid: {is_valid}")
    
    return is_valid

# Gateway middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers and validate requests"""
    # CORS headers
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response
```

---

## 🚀 **DEPLOYMENT & CONFIGURATION**

### **Docker Production Setup**
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  storedesk-ai:
    build: .
    container_name: storedesk-ai
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - HMAC_SECRET=${HMAC_SECRET}
      - SERVICE_ACCOUNT_KEY=${SERVICE_ACCOUNT_KEY}
      - STOREDESK_AI_HMAC_SECRET=${STOREDESK_AI_HMAC_SECRET}
      - STOREDESK_AI_SERVICE_KEY=${STOREDESK_AI_SERVICE_KEY}
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### **Environment Configuration**
```python
# config/settings.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # AI Provider Keys
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    
    # Authentication
    HMAC_SECRET: str = "Kj9#mP2@nQ5!wR3&tY7*vB1^eF6%zA0"
    SERVICE_ACCOUNT_KEY: str = ""
    STOREDESK_AI_HMAC_SECRET: str = "Kj9#mP2@nQ5!wR3&tY7*vB1^eF6%zA0"
    STOREDESK_AI_SERVICE_KEY: str = ""
    
    # Service Configuration
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env.production"
        case_sensitive = False

settings = Settings()
```

---

## 🎯 **KEY IMPLEMENTATION PATTERNS**

### **1. State Management with TypedDict**
```python
from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    """Type-safe state management for LangGraph"""
    userMessage: str
    userContext: Dict[str, Any]
    conversationHistory: List[Dict[str, str]]
    pendingConfirmation: Optional[Dict[str, Any]]
    toolCallsMade: List[Dict[str, Any]]
    toolResults: List[Dict[str, Any]]
    iterationCount: int
    finalResponse: Optional[Dict[str, Any]]
    clarificationQuestion: Optional[str]
    requiresConfirmation: bool
```

### **2. Tool Registration System**
```python
# Tool decorator for automatic registration
def tool(func):
    """Decorator for tool registration"""
    func._is_tool = True
    return func

# Tool registry
class ToolRegistry:
    def __init__(self):
        self.tools = []
    
    def register(self, tool_func):
        """Register tool with metadata"""
        self.tools.append({
            "name": tool_func.__name__,
            "description": tool_func.__doc__ or "",
            "parameters": self._extract_parameters(tool_func),
            "function": tool_func
        })
    
    @property
    def tools(self):
        """Get all registered tools"""
        return self.tools
```

### **3. Async/Await Patterns**
```python
# Proper async handling
async def process_request(self, user_message, user_context, session_id):
    """Async request processing with proper error handling"""
    try:
        state = self._create_initial_state(user_message, user_context)
        result = await self.graph.ainvoke(state)
        return self._format_response(result)
    except Exception as e:
        print(f"[ERROR] Request processing failed: {str(e)}")
        return {"message": f"Processing error: {str(e)}", "actionsExecuted": []}

# Provider async calls
async def call_api(self, messages: List[Dict], tools=None):
    """Async API call with timeout and retry logic"""
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.post(url, headers=headers, json=payload) as response:
                return await self._handle_response(response)
        except asyncio.TimeoutError:
            print(f"[PROVIDER] Request timeout after 30 seconds")
            return {"error": "Request timeout"}
```

---

## 📈 **PERFORMANCE & MONITORING**

### **Metrics Collection**
```python
# Request timing
import time
from datetime import datetime

class PerformanceMonitor:
    def __init__(self):
        self.request_times = []
        self.error_counts = {}
        self.provider_usage = {}
    
    def start_request(self, request_id: str):
        """Start timing a request"""
        self.request_times[request_id] = {
            "start_time": time.time(),
            "user_message": "",
            "provider": ""
        }
    
    def end_request(self, request_id: str, provider: str, success: bool):
        """End timing and record metrics"""
        if request_id in self.request_times:
            duration = time.time() - self.request_times[request_id]["start_time"]
            
            # Record timing
            self.request_times[request_id].update({
                "end_time": time.time(),
                "duration": duration,
                "provider": provider,
                "success": success
            })
            
            # Update provider usage
            if provider not in self.provider_usage:
                self.provider_usage[provider] = {"count": 0, "errors": 0}
            
            self.provider_usage[provider]["count"] += 1
            if not success:
                self.provider_usage[provider]["errors"] += 1
            
            print(f"[PERF] Request {request_id}: {duration:.2f}s, provider: {provider}, success: {success}")
```

---

## 🎉 **BUSINESS VALUE & FEATURES**

### **Core Capabilities**
1. **Product Management**
   - Real-time stock monitoring with threshold alerts
   - Price margin tracking and optimization
   - Bulk operations for all products
   - Status checking and reporting

2. **Intelligent Assistant**
   - Natural language understanding
   - Context-aware responses
   - Multi-domain support (products, orders, customers)
   - Conversation history management

3. **Enterprise Features**
   - HMAC-based authentication
   - Multi-provider LLM support
   - Comprehensive logging and monitoring
   - Docker containerization
   - Health check endpoints
   - Error handling and recovery

4. **Technical Excellence**
   - Type-safe implementation with TypedDict
   - Async/await architecture
   - Comprehensive error handling
   - Performance monitoring
   - Security best practices
   - Production-ready deployment

---

## 🔧 **DEVELOPMENT & DEBUGGING**

### **Common Patterns**
```python
# Error handling pattern
try:
    result = await some_operation()
except Exception as e:
    print(f"[ERROR] Operation failed: {str(e)}")
    return {"error": str(e), "success": False}

# Logging pattern
print(f"[COMPONENT] Detailed message: {details}")
print(f"[COMPONENT] State: {state}")
print(f"[COMPONENT] Decision: {decision}")

# Testing pattern
def test_component():
    """Unit testing helper"""
    assert component.method() == expected_result
    print(f"[TEST] {component.__name__}: PASSED")
```

### **Debugging Commands**
```bash
# View logs
docker compose logs storedesk-ai

# Test specific component
curl -X POST http://localhost:8000/api/storedesk/assist \
  -H "Content-Type: application/json" \
  -H "x-signature: $(echo -n 'payload' | openssl dgst -sha256 -hmac 'secret')" \
  -d '{"message": "test"}'

# Health check
curl http://localhost:8000/health
```

---

## 📝 **AI MODEL USAGE GUIDE**

### **For Code Review & Analysis**
1. **Architecture Understanding**: Review system flow and component interactions
2. **State Management**: Understand LangGraph state preservation patterns
3. **Tool Integration**: Analyze tool registration and execution
4. **Provider Management**: Review multi-provider abstraction
5. **Security Implementation**: Check authentication and validation
6. **Performance Optimization**: Identify bottlenecks and improvements
7. **Error Handling**: Review exception management and recovery

### **For Feature Development**
1. **Adding New Domains**: Follow existing agent patterns
2. **Tool Development**: Use decorator and registry system
3. **Provider Integration**: Implement new provider interfaces
4. **Logging Enhancement**: Add visibility to new components
5. **Testing**: Write unit tests and integration tests

### **For Debugging & Maintenance**
1. **Log Analysis**: Use comprehensive logging to trace issues
2. **State Debugging**: Monitor LangGraph state transitions
3. **Performance Monitoring**: Track response times and bottlenecks
4. **Provider Issues**: Debug API calls and responses
5. **Configuration**: Review environment variables and settings

---

**📝 This comprehensive code context enables any AI model to understand, analyze, and assist with the complete StoreDesk AI implementation including architecture, patterns, debugging approaches, and development guidelines!**
