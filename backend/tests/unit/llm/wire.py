"""In-process ASGI fakes that speak the real provider wire formats.

These assert against actual HTTP/SSE behavior: the SDK's own transport stack
parses what these apps emit, so adapters are tested end to end without network
access.
"""

from __future__ import annotations

import json
from typing import Any

# ---------------------------------------------------------------------------
# OpenAI Chat Completions wire format
# ---------------------------------------------------------------------------


class FakeOpenAIApp:
    """ASGI app pretending to be an OpenAI-compatible chat endpoint."""

    def __init__(self, *, base_path: str = "/chat/completions", status: int = 200) -> None:
        self.base_path = base_path
        self.requests: list[dict[str, Any]] = []
        self.status = status
        self.completion: dict[str, Any] = {
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "created": 1_700_000_000,
            "model": "gpt-fake",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello there"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7},
        }
        self.chunks: list[dict[str, Any]] = []
        self.error_body: dict[str, Any] = {"error": {"message": "boom", "type": "api_error"}}

    def as_chunks(self) -> list[dict[str, Any]]:
        """Default text streaming sequence matching ``self.completion``."""
        return [
            {
                "id": "chatcmpl-2",
                "object": "chat.completion.chunk",
                "created": 1_700_000_000,
                "model": "gpt-fake",
                "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-2",
                "object": "chat.completion.chunk",
                "created": 1_700_000_000,
                "model": "gpt-fake",
                "choices": [{"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-2",
                "object": "chat.completion.chunk",
                "created": 1_700_000_000,
                "model": "gpt-fake",
                "choices": [{"index": 0, "delta": {"content": " there"}, "finish_reason": None}],
            },
            {
                "id": "chatcmpl-2",
                "object": "chat.completion.chunk",
                "created": 1_700_000_000,
                "model": "gpt-fake",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            },
            {
                "id": "chatcmpl-2",
                "object": "chat.completion.chunk",
                "created": 1_700_000_000,
                "model": "gpt-fake",
                "choices": [],
                "usage": {"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7},
            },
        ]

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        body = await _read_body(receive)
        if body:
            self.requests.append(json.loads(body.decode("utf-8")))
        else:
            self.requests.append({})
        if self.status != 200:
            await _send_json(send, self.status, self.error_body, headers={"retry-after": "3"})
            return
        if self.requests[-1].get("stream"):
            await _send_sse(send, _sse_lines(self.chunks or self.as_chunks()))
        else:
            await _send_json(send, 200, self.completion)


def tool_call_chunks() -> list[dict[str, Any]]:
    """A two-chunk tool call sequence (header then partial arguments)."""
    return [
        {
            "id": "chatcmpl-3",
            "object": "chat.completion.chunk",
            "created": 1_700_000_000,
            "model": "gpt-fake",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "get_weather", "arguments": ""},
                            }
                        ]
                    },
                    "finish_reason": None,
                }
            ],
        },
        {
            "id": "chatcmpl-3",
            "object": "chat.completion.chunk",
            "created": 1_700_000_000,
            "model": "gpt-fake",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "tool_calls": [{"index": 0, "function": {"arguments": '{"city":"Paris"}'}}]
                    },
                    "finish_reason": None,
                }
            ],
        },
        {
            "id": "chatcmpl-3",
            "object": "chat.completion.chunk",
            "created": 1_700_000_000,
            "model": "gpt-fake",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
        },
        {
            "id": "chatcmpl-3",
            "object": "chat.completion.chunk",
            "created": 1_700_000_000,
            "model": "gpt-fake",
            "choices": [],
            "usage": {"prompt_tokens": 10, "completion_tokens": 6, "total_tokens": 16},
        },
    ]


def tool_call_completion() -> dict[str, Any]:
    """A non-streaming completion whose choice is a single tool call."""
    return {
        "id": "chatcmpl-4",
        "object": "chat.completion",
        "created": 1_700_000_000,
        "model": "gpt-fake",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_9",
                            "type": "function",
                            "function": {"name": "get_weather", "arguments": '{"city":"Paris"}'},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 6, "total_tokens": 16},
    }


# ---------------------------------------------------------------------------
# Anthropic Messages wire format
# ---------------------------------------------------------------------------


class FakeAnthropicApp:
    """ASGI app pretending to be the Anthropic Messages endpoint."""

    def __init__(self, *, status: int = 200) -> None:
        self.requests: list[dict[str, Any]] = []
        self.status = status
        self.message: dict[str, Any] = {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": "claude-fake",
            "content": [{"type": "text", "text": "Hello there"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 9, "output_tokens": 4},
        }
        self.events: list[dict[str, Any]] = []
        self.error_body: dict[str, Any] = {"error": {"message": "boom", "type": "api_error"}}

    def as_events(self) -> list[dict[str, Any]]:
        """Default text streaming sequence matching ``self.message``."""
        return [
            {
                "type": "message_start",
                "message": {
                    "id": "msg_2",
                    "type": "message",
                    "role": "assistant",
                    "model": "claude-fake",
                    "content": [],
                    "usage": {"input_tokens": 9, "output_tokens": 1},
                },
            },
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "Hello"},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": " there"},
            },
            {"type": "content_block_stop", "index": 0},
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"output_tokens": 4},
            },
            {"type": "message_stop"},
        ]

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        body = await _read_body(receive)
        if body:
            self.requests.append(json.loads(body.decode("utf-8")))
        else:
            self.requests.append({})
        if self.status != 200:
            await _send_json(send, self.status, self.error_body, headers={"retry-after": "7"})
            return
        if self.requests[-1].get("stream"):
            await _send_sse(send, _anthropic_lines(self.events or self.as_events()))
        else:
            await _send_json(send, 200, self.message)


def tool_use_message() -> dict[str, Any]:
    """A non-streaming single text tool_use choice."""
    return {
        "id": "msg_3",
        "type": "message",
        "role": "assistant",
        "model": "claude-fake",
        "content": [
            {"type": "text", "text": "Checking"},
            {
                "type": "tool_use",
                "id": "toolu_1",
                "name": "get_weather",
                "input": {"city": "Paris"},
            },
        ],
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 8, "output_tokens": 12},
    }


def tool_use_events() -> list[dict[str, Any]]:
    """Streaming sequence that opens a tool_use block and feeds partial JSON."""
    return [
        {
            "type": "message_start",
            "message": {
                "id": "msg_4",
                "type": "message",
                "role": "assistant",
                "model": "claude-fake",
                "content": [],
                "usage": {"input_tokens": 8, "output_tokens": 1},
            },
        },
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "Checking"},
        },
        {"type": "content_block_stop", "index": 0},
        {
            "type": "content_block_start",
            "index": 1,
            "content_block": {"type": "tool_use", "id": "toolu_9", "name": "get_weather"},
        },
        {
            "type": "content_block_delta",
            "index": 1,
            "delta": {"type": "input_json_delta", "partial_json": '{"city":"Par'},
        },
        {
            "type": "content_block_delta",
            "index": 1,
            "delta": {"type": "input_json_delta", "partial_json": 'is"}'},
        },
        {"type": "content_block_stop", "index": 1},
        {
            "type": "message_delta",
            "delta": {"stop_reason": "tool_use", "stop_sequence": None},
            "usage": {"output_tokens": 12},
        },
        {"type": "message_stop"},
    ]


# ---------------------------------------------------------------------------
# ASGI plumbing
# ---------------------------------------------------------------------------


async def _read_body(receive: Any) -> bytes:
    chunks = []
    while True:
        message = await receive()
        if message["type"] == "http.request":
            chunks.append(message.get("body", b""))
            if not message.get("more_body"):
                break
        else:
            break
    return b"".join(chunks)


def _sse_lines(chunks: list[dict[str, Any]]) -> list[str]:
    lines = []
    for chunk in chunks:
        lines.append(f"data: {json.dumps(chunk)}\n\n")
    lines.append("data: [DONE]\n\n")
    return lines


def _anthropic_lines(events: list[dict[str, Any]]) -> list[str]:
    lines = []
    for event in events:
        kind = event["type"]
        lines.append(f"event: {kind}\ndata: {json.dumps(event)}\n\n")
    return lines


async def _send_json(
    send: Any, status: int, payload: dict[str, Any], headers: dict[str, str] | None = None
) -> None:
    body = json.dumps(payload).encode("utf-8")
    response_headers = [(b"content-type", b"application/json")]
    if headers:
        response_headers.extend(
            [(key.lower().encode(), value.encode()) for key, value in headers.items()]
        )
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": response_headers,
        },
    )
    await send({"type": "http.response.body", "body": body})


async def _send_sse(send: Any, lines: list[str]) -> None:
    body = "".join(lines).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/event-stream")],
        },
    )
    await send({"type": "http.response.body", "body": body})
