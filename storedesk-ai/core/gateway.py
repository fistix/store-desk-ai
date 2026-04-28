from fastapi import APIRouter, Request, HTTPException, Depends, Header, BackgroundTasks
from typing import Optional, List, Dict, Any
from core.context import AssistRequest, UserContext
from core.auth import verify_hmac
from core.stt import transcribe_audio
from core.session_manager import session_manager
from agent.orchestrator import orchestrator, AgentState
from providers.manager import provider_manager
from config.settings import settings
import base64

router = APIRouter()

async def get_user_context(x_user_id: str = Header(...), x_tenant_id: str = Header(...), x_connector_id: str = Header(...)) -> UserContext:
    return UserContext(
        user_id=x_user_id,
        tenant_id=x_tenant_id,
        connector_id=x_connector_id
    )

@router.post("/api/storedesk/assist")  # Temporarily disabled for flow testing
async def assist_endpoint(assist_request: AssistRequest, user_context: UserContext = Depends(get_user_context)):
    print("[GATEWAY] 🚀 AI ASSIST REQUEST RECEIVED")
    print(f"[GATEWAY] 📝 Session ID: {assist_request.sessionId}")
    print(f"[GATEWAY] 📝 Input Type: {assist_request.inputType}")
    print(f"[GATEWAY] � Request Context: {assist_request.context}")
    
    # Extract selectedProductIds from request context
    selected_product_ids = []
    if assist_request.context and "selectedProductIds" in assist_request.context:
        selected_product_ids = assist_request.context["selectedProductIds"]
    
    # Update user context with selected product IDs
    user_context.selected_product_ids = selected_product_ids
    
    print(f"[GATEWAY] � User Context: {user_context.dict()}")
    
    session_id = assist_request.sessionId
    message_content = assist_request.message

    # Get session data
    print("[GATEWAY] 📚 Loading session data...")
    conversation_history = await session_manager.get_history(session_id)
    pending_confirmation = await session_manager.get_pending_confirmation(session_id)
    
    print(f"[GATEWAY] 📖 History length: {len(conversation_history)}")
    print(f"[GATEWAY] ⏳ Pending confirmation: {bool(pending_confirmation)}")

    # Process input
    if assist_request.inputType == "audio" and assist_request.audioBase64:
        print("[GATEWAY] 🎵 Processing audio input...")
        try:
            audio_bytes = base64.b64decode(assist_request.audioBase64)
            message_content = await transcribe_audio(audio_bytes)
            print(f"[GATEWAY] 🎤 Transcribed: '{message_content[:100]}{'...' if len(message_content) > 100 else ''}'")
        except Exception as e:
            print(f"[GATEWAY] ❌ Audio transcription failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Audio transcription failed: {str(e)}")
    elif assist_request.inputType == "text" and assist_request.message:
        print("[GATEWAY] 📝 Processing text input...")
        message_content = assist_request.message
        print(f"[GATEWAY] 📝 Text: '{message_content[:100]}{'...' if len(message_content) > 100 else ''}'")
    else:
        print("[GATEWAY] ❌ Invalid input type or missing data")
        raise HTTPException(status_code=400, detail="Invalid inputType or missing message/audioBase64")

    if not message_content:
        print("[GATEWAY] ❌ Empty message content")
        raise HTTPException(status_code=400, detail="Empty message or failed transcription")

    # Add to session history
    print("[GATEWAY] 💾 Adding user message to history...")
    await session_manager.add_to_history(session_id, "user", message_content)

    # Prepare state for orchestrator
    print("[GATEWAY] 🏗️ Preparing orchestrator state...")
    initial_state = AgentState(
        userMessage=message_content,
        userContext=user_context.dict(),
        conversationHistory=conversation_history,
        pendingConfirmation=pending_confirmation,
        toolCallsMade=[],
        toolResults=[],
        iterationCount=0,
        finalResponse=None,
        clarificationQuestion=None,
        requiresConfirmation=False
    )
    
    print(f"[GATEWAY] 📊 State keys: {list(initial_state.keys())}")
    print("[GATEWAY] 🔄 Invoking orchestrator graph...")
    
    try:
        orchestrator_result = await orchestrator.graph.compile().ainvoke(
            initial_state, 
            config={"max_iterations": settings.REQUEST_MAX_ITERATIONS}
        )
        
        print("[GATEWAY] ✅ Orchestrator completed successfully")
        print(f"[GATEWAY] 📦 Result type: {type(orchestrator_result)}")
        print(f"[GATEWAY] 📋 Result keys: {list(orchestrator_result.keys()) if isinstance(orchestrator_result, dict) else 'Not a dict'}")
        
    except Exception as e:
        print(f"[GATEWAY] ❌ Orchestrator failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Orchestrator error: {str(e)}")

    # Compose final response
    print("[GATEWAY] 📝 Composing final response...")
    final_response_data = await orchestrator._compose_response_node(orchestrator_result)
    
    # Handle confirmations
    if orchestrator_result.get("requiresConfirmation") and orchestrator_result.get("toolCallsMade"):
        print("[GATEWAY] ⏳ Setting pending confirmation...")
        pending_tool_call = orchestrator_result["toolCallsMade"][0]["function"]
        await session_manager.set_pending_confirmation(
            session_id,
            pending_tool_call["name"],
            pending_tool_call["arguments"],
            orchestrator_result.get("clarificationQuestion", ""),
            user_context.dict()
        )
        final_response_data["requiresConfirmation"] = True
        final_response_data["confirmationQuestion"] = orchestrator_result.get("clarificationQuestion")
        final_response_data["actionsExecuted"] = []
        print("[GATEWAY] ✅ Pending confirmation set")
    elif not orchestrator_result.get("requiresConfirmation") and orchestrator_result.get("toolResults"):
        # If confirmation was resolved and tool executed, clear pending confirmation from Redis
        print("[GATEWAY] 🧹 Clearing pending confirmation from Redis after execution...")
        await session_manager.clear_pending_confirmation(session_id)
    elif orchestrator_result.get("finalResponse") and isinstance(orchestrator_result["finalResponse"], dict) and "Action cancelled." in orchestrator_result["finalResponse"].get("message", ""):
        # If user cancelled, clear pending confirmation from Redis
        print("[GATEWAY] 🧹 Clearing pending confirmation from Redis after cancellation...")
        await session_manager.clear_pending_confirmation(session_id)

    # Add AI response to history (skip error responses to prevent accumulation)
    ai_message_content = final_response_data.get("message", "")
    if final_response_data.get("requiresConfirmation"):
        ai_message_content = final_response_data.get("confirmationQuestion", "")
    elif final_response_data.get("clarificationQuestion"):
        ai_message_content = final_response_data.get("clarificationQuestion", "")

    # Skip saving error responses to prevent history accumulation
    if ai_message_content and not ai_message_content.startswith("Products agent error:") and not ai_message_content.startswith("Error:"):
        print("[GATEWAY] 💾 Adding AI response to history...")
        await session_manager.add_to_history(session_id, "assistant", ai_message_content)
    elif ai_message_content:
        print("[GATEWAY] Skipping error response - not adding to history")

    print("[GATEWAY] 🎉 Request completed successfully")
    response_message = final_response_data.get('message', '') or final_response_data.get('clarificationQuestion', '') or final_response_data.get('confirmationQuestion', '')
    print(f"[GATEWAY] 📤 Response: {response_message[:100]}{'...' if len(response_message) > 100 else ''}")
    
    return final_response_data

@router.get("/health")
async def health_check():
    # Basic health check
    redis_ok = False
    try:
        await session_manager.redis_client.ping()
        redis_ok = True
    except Exception:
        pass

    providers_status = []
    for provider in provider_manager.providers:
        status = await provider_manager.get_provider_status(provider.name)
        providers_status.append({"name": provider.name, "status": status["status"], "until": status["until"]})
    
    return {"status": "ok", "redis_connected": redis_ok, "providers": providers_status}

# Debug Endpoints (conditionally enabled)
if settings.DEBUG_ENDPOINTS_ENABLED:
    @router.get("/debug/session/{session_id}")
    async def debug_session_history(session_id: str):
        return await session_manager.get_history(session_id)

    @router.get("/debug/providers")
    async def debug_providers_status():
        all_providers_status = []
        for provider_config in orchestrator.provider_manager.providers_config:
            name = provider_config["name"]
            status = await orchestrator.provider_manager.get_provider_status(name)
            usage = await orchestrator.provider_manager.get_current_usage(name)
            all_providers_status.append({"name": name, "status": status, "usage": usage})
        return all_providers_status

    @router.delete("/debug/session/{session_id}")
    async def debug_clear_session(session_id: str):
        await session_manager.clear_session(session_id)
        return {"message": "Session cleared"}
