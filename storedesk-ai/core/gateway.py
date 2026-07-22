from fastapi import APIRouter, Request, HTTPException, Depends, Header, BackgroundTasks
from typing import Optional, List, Dict, Any
from core.context import AssistRequest, UserContext
from core.auth import verify_hmac
from core.stt import transcribe_audio
from core.session_manager import session_manager
from agent.orchestrator import orchestrator, AgentState
from providers.manager import provider_manager
from config.settings import settings
from security.prompt_sanitizer import PromptSanitizer, SecurityException
from security.security_monitor import security_monitor
import base64
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize security sanitizer
prompt_sanitizer = PromptSanitizer()

async def get_user_context(x_user_id: str = Header(...), x_tenant_id: str = Header(...), x_connector_id: str = Header(...)) -> UserContext:
    return UserContext(
        user_id=x_user_id,
        tenant_id=x_tenant_id,
        connector_id=x_connector_id
    )

async def validate_and_sanitize_input(input_text: str, user_id: str) -> str:
    """
    Validate and sanitize user input at gateway level using Redis
    """
    try:
        # Check rate limiting
        if await security_monitor.is_rate_limited(user_id, "input_validation", limit=20, window_minutes=1):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Check if user is blocked
        if await security_monitor.should_block_user(user_id):
            raise HTTPException(status_code=403, detail="Access blocked due to security concerns")
        
        # Sanitize input
        sanitized_input = prompt_sanitizer.sanitize_input(input_text, user_id)
        
        return sanitized_input
        
    except SecurityException as e:
        # Log security event
        await security_monitor.log_security_event(
            "security_exception",
            user_id,
            input_text[:100],
            str(e),
            "HIGH"
        )
        raise HTTPException(status_code=400, detail="Invalid input detected")

@router.post("/api/storedesk/assist")
async def assist_endpoint(
    assist_request: AssistRequest,
    user_context: UserContext = Depends(get_user_context),
    _authenticated: bool = Depends(verify_hmac),
):
    logger.info(
        "Processing AI request session=%s input_type=%s",
        assist_request.sessionId,
        assist_request.inputType,
    )
    
    # Extract selectedProductIds from request context
    selected_product_ids = []
    if assist_request.context and "selectedProductIds" in assist_request.context:
        selected_product_ids = assist_request.context["selectedProductIds"]
    
    # Update user context with selected product IDs
    user_context.selected_product_ids = selected_product_ids
    
    session_id = assist_request.sessionId
    message_content = assist_request.message

    # Get session data
    conversation_history = await session_manager.get_history(session_id)
    pending_confirmation = await session_manager.get_pending_confirmation(session_id)

    # Process input
    if assist_request.inputType == "audio" and assist_request.audioBase64:
        audio_bytes = base64.b64decode(assist_request.audioBase64)
        try:
            message_content = await transcribe_audio(audio_bytes)
        except Exception as e:
            logger.exception("Audio transcription failed")
            raise HTTPException(status_code=500, detail="Audio transcription failed") from e
    elif assist_request.inputType == "text" and assist_request.message:
        message_content = assist_request.message
    else:
        raise HTTPException(status_code=400, detail="Invalid inputType or missing message/audioBase64")

    if not message_content:
        raise HTTPException(status_code=400, detail="Empty message or failed transcription")

    # Sanitize input at gateway level
    sanitized_message = await validate_and_sanitize_input(message_content, user_context.user_id)

    # Add to session history
    await session_manager.add_to_history(session_id, "user", sanitized_message)

    # Prepare state for orchestrator
    initial_state = AgentState(
        userMessage=sanitized_message,
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
    try:
        orchestrator_result = await orchestrator.graph.compile().ainvoke(
            initial_state, 
            config={"max_iterations": settings.REQUEST_MAX_ITERATIONS}
        )
    except Exception as e:
        logger.exception("Orchestrator failed")
        raise HTTPException(status_code=500, detail="AI orchestration failed") from e

    # Compose final response
    final_response_data = await orchestrator._compose_response_node(orchestrator_result)
    
    # Handle confirmations
    if orchestrator_result.get("requiresConfirmation") and orchestrator_result.get("toolCallsMade"):
        pending_tool_calls = orchestrator_result["toolCallsMade"]
        pending_tool_call = pending_tool_calls[0]["function"]
        await session_manager.set_pending_confirmation(
            session_id,
            pending_tool_call["name"],
            pending_tool_call["arguments"],
            orchestrator_result.get("clarificationQuestion", ""),
            user_context.dict(),
            tool_calls=pending_tool_calls,
        )
        final_response_data["requiresConfirmation"] = True
        final_response_data["confirmationQuestion"] = orchestrator_result.get("clarificationQuestion")
        final_response_data["actionsExecuted"] = []
    elif not orchestrator_result.get("requiresConfirmation") and orchestrator_result.get("toolResults"):
        # If confirmation was resolved and tool executed, clear pending confirmation from Redis
        await session_manager.clear_pending_confirmation(session_id)
    elif orchestrator_result.get("finalResponse") and isinstance(orchestrator_result["finalResponse"], dict) and orchestrator_result["finalResponse"].get("message") and "Action cancelled." in orchestrator_result["finalResponse"].get("message", ""):
        # If user cancelled, clear pending confirmation from Redis
        await session_manager.clear_pending_confirmation(session_id)

    # Add AI response to history (skip error responses to prevent accumulation)
    ai_message_content = final_response_data.get("message", "")
    if final_response_data.get("requiresConfirmation"):
        ai_message_content = final_response_data.get("confirmationQuestion", "")
    elif final_response_data.get("clarificationQuestion"):
        ai_message_content = final_response_data.get("clarificationQuestion", "")

    # Skip saving error responses to prevent history accumulation
    if ai_message_content and not ai_message_content.startswith("Products agent error:") and not ai_message_content.startswith("Error:"):
        await session_manager.add_to_history(session_id, "assistant", ai_message_content)
    
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
        for provider in provider_manager.providers:
            name = provider.name
            status = await provider_manager.get_provider_status(name)
            usage = await provider_manager.get_current_usage(name)
            all_providers_status.append({"name": name, "status": status, "usage": usage})
        return all_providers_status

    @router.delete("/debug/session/{session_id}")
    async def debug_clear_session(session_id: str):
        await session_manager.clear_session(session_id)
        return {"message": "Session cleared"}
