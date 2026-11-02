"""Session and message endpoints for chat workspace.

This module provides lightweight chat functionality using the configured
LLM providers. It is a preview for the upcoming Agent Studio integration
(M6-M8).
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException
from fastapi import Depends
from pydantic import BaseModel

from codepilot.api.deps import get_container
from codepilot.models.llm import (
    CompletionRequest,
    Message,
    MessageRole,
    ProviderId,
)

router = APIRouter(prefix="/v1", tags=["sessions"])

# In-memory session storage for development; replace with DB in M7
_SESSIONS: dict[str, dict] = {}


class SendMessageRequest(BaseModel):
    """Request body for sending a message."""

    content: str
    model: str | None = None


class SendMessageResponse(BaseModel):
    """Response for a sent message."""

    session_id: str
    user_message_id: str
    assistant_message_id: str
    assistant: dict[str, Any]


@router.post("/sessions")
async def create_session() -> dict:
    """Create a new chat session."""
    session_id = str(uuid.uuid4())
    _SESSIONS[session_id] = {"messages": [], "provider": None}
    return {"id": session_id}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    """Get a session's messages."""
    if session_id not in _SESSIONS:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {
        "id": session_id,
        "messages": _SESSIONS[session_id]["messages"],
    }


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    container: Annotated[Any, Depends(get_container)],
) -> SendMessageResponse:
    """Send a message and get an LLM response."""
    if session_id not in _SESSIONS:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Store user message
    user_msg = {
        "id": str(uuid.uuid4())[:8],
        "role": "user",
        "content": request.content,
    }
    _SESSIONS[session_id]["messages"].append(user_msg)

    # Get settings and registry from container
    settings = container.settings
    registry = container.llm_registry

    # Resolve provider and model
    model = request.model
    provider_id = settings.llm.default_provider

    if model:
        provider_str = model.split("/")[0] if "/" in model else model
        try:
            provider_id = ProviderId(provider_str)
        except ValueError:
            provider_id = settings.llm.default_provider

    try:
        provider = registry.get(provider_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Provider not available: {str(e)}")

    # Create completion request
    completion_request = CompletionRequest(
        messages=[Message(role=MessageRole.USER, content=request.content)],
        model=model or registry.model_for(provider_id),
        max_output_tokens=500,
    )

    # Get completion
    result = await provider.complete(completion_request)

    # Store assistant message
    assistant_msg = {
        "id": str(uuid.uuid4())[:8],
        "role": "assistant",
        "content": result.content or "",
        "model": model,
    }
    _SESSIONS[session_id]["messages"].append(assistant_msg)

    return SendMessageResponse(
        session_id=session_id,
        user_message_id=user_msg["id"],
        assistant_message_id=assistant_msg["id"],
        assistant=assistant_msg,
    )