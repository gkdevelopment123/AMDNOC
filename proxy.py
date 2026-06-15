#!/usr/bin/env python3
import json
import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import time

VLLM_BASE = "http://localhost:8000"
app = FastAPI()

async def forward_non_stream(path: str, body: dict, headers: dict):
    body["stream"] = False
    body.pop("stream_options", None)
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{VLLM_BASE}{path}",
            json=body,
            headers={k: v for k, v in headers.items()
                     if k.lower() in ("content-type", "authorization")},
        )
        return resp.json()

async def fake_sse_stream(data: dict):
    print(f"[PROXY DEBUG] full response: {json.dumps(data)[:500]}")
    if "error" in data:
        yield f"data: {json.dumps({'error': data['error']})}\n\n"
        yield "data: [DONE]\n\n"
        return
    rid = data.get("id", f"chatcmpl-{int(time.time())}")
    created = data.get("created", int(time.time()))
    model = data.get("model", "unknown")
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})
    tool_calls = message.get("tool_calls") or []
    content = message.get("content") or ""
    print(f"[PROXY DEBUG] finish_reason={choice.get('finish_reason')} tool_calls={len(tool_calls)} content={repr(content[:80])}")
    yield f"data: {json.dumps({'id': rid, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': ''}, 'finish_reason': None}]})}\n\n"
    if content:
        yield f"data: {json.dumps({'id': rid, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'content': content}, 'finish_reason': None}]})}\n\n"
    for i, tc in enumerate(tool_calls):
        yield f"data: {json.dumps({'id': rid, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'tool_calls': [{'index': i, 'id': tc.get('id'), 'type': 'function', 'function': {'name': tc.get('function', {}).get('name', ''), 'arguments': ''}}]}, 'finish_reason': None}]})}\n\n"
        args = tc.get("function", {}).get("arguments", "")
        if args:
            yield f"data: {json.dumps({'id': rid, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'tool_calls': [{'index': i, 'function': {'arguments': args}}]}, 'finish_reason': None}]})}\n\n"
    yield f"data: {json.dumps({'id': rid, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': choice.get('finish_reason', 'stop')}], 'usage': data.get('usage')})}\n\n"
    yield "data: [DONE]\n\n"

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    wants_stream = body.get("stream", False)
    data = await forward_non_stream("/v1/chat/completions", body, dict(request.headers))
    if wants_stream:
        return StreamingResponse(fake_sse_stream(data), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})
    return JSONResponse(data)

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def passthrough(request: Request, path: str):
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.request(method=request.method, url=f"{VLLM_BASE}/{path}",
            params=dict(request.query_params),
            headers={k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")},
            content=await request.body())
        return JSONResponse(content=resp.json(), status_code=resp.status_code)

if __name__ == "__main__":
    print("Starting proxy on port 8001 -> vLLM on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
