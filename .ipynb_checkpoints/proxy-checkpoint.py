#!/usr/bin/env python3
"""
Proxy: OpenCode -> localhost:8001 -> vLLM localhost:8000
Converts streaming requests to non-streaming to avoid vLLM tool parser bug.
"""
import json
import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse

VLLM_BASE = "http://localhost:8000"

app = FastAPI()


async def forward_non_stream(path: str, body: dict, headers: dict):
    """Call vLLM with stream=False and return raw JSON response."""
    body["stream"] = False
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{VLLM_BASE}{path}",
            json=body,
            headers={k: v for k, v in headers.items()
                     if k.lower() in ("content-type", "authorization")},
        )
        return resp.json()


async def fake_sse_stream(data: dict):
    """
    Fake an SSE stream from a non-streaming response.
    Properly handles both text and tool_call responses.
    """
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})
    tool_calls = message.get("tool_calls") or []

    print(f"[PROXY DEBUG] finish_reason={choice.get('finish_reason')} tool_calls={len(tool_calls)} content={repr(message.get('content','')[:80])}")

    # Chunk 1: role only
    yield f"data: {json.dumps({'id': data['id'], 'object': 'chat.completion.chunk', 'created': data['created'], 'model': data['model'], 'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': ''}, 'finish_reason': None}]})}\n\n"

    # Chunk 2: content (if any)
    content = message.get("content") or ""
    if content:
        yield f"data: {json.dumps({'id': data['id'], 'object': 'chat.completion.chunk', 'created': data['created'], 'model': data['model'], 'choices': [{'index': 0, 'delta': {'content': content}, 'finish_reason': None}]})}\n\n"

    # Chunks for tool calls (if any)
    for i, tc in enumerate(tool_calls):
        # First tool call chunk: id, type, function name
        tc_chunk = {
            "id": data["id"],
            "object": "chat.completion.chunk",
            "created": data["created"],
            "model": data["model"],
            "choices": [{
                "index": 0,
                "delta": {
                    "tool_calls": [{
                        "index": i,
                        "id": tc.get("id"),
                        "type": "function",
                        "function": {
                            "name": tc.get("function", {}).get("name", ""),
                            "arguments": ""
                        }
                    }]
                },
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(tc_chunk)}\n\n"

        # Second tool call chunk: arguments
        args = tc.get("function", {}).get("arguments", "")
        if args:
            args_chunk = {
                "id": data["id"],
                "object": "chat.completion.chunk",
                "created": data["created"],
                "model": data["model"],
                "choices": [{
                    "index": 0,
                    "delta": {
                        "tool_calls": [{
                            "index": i,
                            "function": {
                                "arguments": args
                            }
                        }]
                    },
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(args_chunk)}\n\n"

    # Final chunk with finish_reason
    yield f"data: {json.dumps({'id': data['id'], 'object': 'chat.completion.chunk', 'created': data['created'], 'model': data['model'], 'choices': [{'index': 0, 'delta': {}, 'finish_reason': choice.get('finish_reason', 'stop')}], 'usage': data.get('usage')})}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    wants_stream = body.get("stream", False)

    data = await forward_non_stream("/v1/chat/completions", body, dict(request.headers))

    if wants_stream:
        return StreamingResponse(
            fake_sse_stream(data),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        return JSONResponse(data)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def passthrough(request: Request, path: str):
    """Pass everything else (models, health, etc.) straight to vLLM."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.request(
            method=request.method,
            url=f"{VLLM_BASE}/{path}",
            params=dict(request.query_params),
            headers={k: v for k, v in request.headers.items()
                     if k.lower() not in ("host", "content-length")},
            content=await request.body(),
        )
        return JSONResponse(content=resp.json(), status_code=resp.status_code)


if __name__ == "__main__":
    print("Starting proxy on port 8001 -> vLLM on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")