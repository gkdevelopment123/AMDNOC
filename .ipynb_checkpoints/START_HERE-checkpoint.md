# START_HERE.md — Run This Every New Session

> The pod's model and running servers are on the overlay filesystem, which is **wiped when a session ends**. Only `/workspace/shared/` survives. So every new session you must restart the model + servers. This is the checklist. Takes ~10–15 min (mostly model download).

---

## The persistence reality (why this file exists)

- ✅ **Survives:** `/workspace/shared/noc-copilot/` — all your code + git repo (28 GB mount)
- ❌ **Wiped:** the model in `/root/.cache` (77 GB), all running processes (vLLM, mocks, Gradio), `~/.bashrc` changes, `~/.config/opencode/`
- 🛟 **Real backup:** GitHub. Push often. If the overlay vanishes mid-build, you `git clone` back into shared and only lose the model (which re-downloads).

---

## Every-session restart sequence

### Tab 1 — start the model (do this FIRST, it takes longest)

```bash
vllm serve Qwen/Qwen3-Coder-30B-A3B-Instruct \
  --host 0.0.0.0 --port 8000 \
  --tensor-parallel-size 1 \
  --max-model-len 100000 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_xml
```

- If the cache was wiped, it re-downloads ~77 GB (several min). If not, loads in ~1–2 min.
- Wait for: `Application startup complete` / `Uvicorn running on http://0.0.0.0:8000`.
- Leave this tab open all session.

**Verify (new tab):**

```bash
curl -s http://localhost:8000/v1/models | head -c 200    # expect "id":"Qwen/Qwen3-Coder-30B-A3B-Instruct"
```

---

### Tab 2 — start the vLLM proxy (REQUIRED — fixes OpenCode streaming bug)

#### What was the bug?

When OpenCode used tools (e.g. reading files, running shell commands), it sent requests to vLLM with `stream=True`. vLLM's `Qwen3XMLToolParser` has a bug where it tries to access `prev_tool_call_arr[index]` before the array is populated, causing:

```
IndexError: list index out of range
  File "serving_chat.py", line 1121
    tool_parser.prev_tool_call_arr[index].get(
```

This crashed every tool call OpenCode tried to make, so it could never read files, run commands, or do anything useful. On top of this, OpenCode also sends a `stream_options` field in the request body which vLLM rejects outright when `stream=False`, causing a second error:

```
Value error: Stream options can only be defined when stream=True
```

#### Why we can't fix vLLM directly

vLLM is installed system-wide and shared across all teams on this pod. Patching `/usr/local/lib/python3.12/dist-packages/vllm/...` would affect everyone. We also can't upgrade vLLM as the environment is locked.

#### How we fixed it

We wrote a small proxy server (`proxy.py`) that sits between OpenCode and vLLM:

```
OpenCode → localhost:8001 (proxy) → localhost:8000 (vLLM)
```

The proxy does three things on every request:
1. Strips `stream_options` from the request body before forwarding (fixes the second error)
2. Forces `stream=False` when calling vLLM (bypasses the buggy tool parser code path)
3. Converts vLLM's non-streaming JSON response back into a proper SSE stream so OpenCode stays happy

OpenCode config points to port 8001 (proxy), not 8000 (vLLM directly).

#### Start the proxy

```bash
cd /workspace/shared/noc-copilot
pip install fastapi uvicorn httpx --quiet
nohup python proxy.py > proxy.log 2>&1 &
echo "Proxy PID: $!"
```

**Verify:**

```bash
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen3-Coder-30B-A3B-Instruct","messages":[{"role":"user","content":"hi"}],"stream":true}'
# expect: data: {...} chunks ending with data: [DONE]
```

---

### Tab 3 — get your code back (first session, or if overlay was wiped)

```bash
cd /workspace/shared
# first time:
git clone https://github.com/gkdevelopment123/AMDNOC.git noc-copilot
cd noc-copilot
# later sessions (code already in shared): just
cd /workspace/shared/noc-copilot && git pull
```

### Tab 3 — reinstall packages that aren't pre-baked

```bash
pip install gradio fastapi uvicorn httpx
```

### Tab 4 — start the mock servers (once code exists)

```bash
cd /workspace/shared/noc-copilot
uvicorn mocks.router_api:app --port 8002 &
uvicorn mocks.itsm_api:app --port 8003 &
```

> ⚠️ Mocks are on 8002/8003 — port 8001 is reserved for the vLLM proxy.

### Tab 5 — start the dashboard (once app.py exists)

```bash
cd /workspace/shared/noc-copilot
python app.py        # Gradio on :7860, share=False
```

---

## OpenCode setup (re-create every session — ~/.config is wiped on restart)

```bash
mkdir -p ~/.config/opencode && cat > ~/.config/opencode/opencode.json << 'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "vllm": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "vLLM (local)",
      "options": { "baseURL": "http://localhost:8001/v1" },
      "models": {
        "Qwen/Qwen3-Coder-30B-A3B-Instruct": {
          "name": "Qwen3-Coder (local)",
          "limit": { "context": 100000, "output": 8000 },
          "options": { "max_tokens": 8000 }
        }
      }
    }
  },
  "model": "vllm/Qwen/Qwen3-Coder-30B-A3B-Instruct",
  "small_model": "vllm/Qwen/Qwen3-Coder-30B-A3B-Instruct"
}
EOF
```

> ⚠️ `baseURL` must point to `8001` (proxy), NOT `8000` (vLLM). If you accidentally point to 8000, OpenCode tool calls will crash with `IndexError`.

Then launch OpenCode from any terminal inside JupyterLab:

```bash
opencode
```

---

## Quick health check (paste anytime)

```bash
echo "model:";       curl -s http://localhost:8000/v1/models | grep -o '"id":"[^"]*"' | head -1
echo "proxy:";       curl -s http://localhost:8001/v1/models | grep -o '"id":"[^"]*"' | head -1
echo "router mock:"; curl -s http://localhost:8002/health 2>/dev/null || echo "down"
echo "itsm mock:";   curl -s http://localhost:8003/health 2>/dev/null || echo "down"
echo "code present:"; ls /workspace/shared/noc-copilot/app.py 2>/dev/null && echo yes || echo "no app.py yet"
echo "proxy log:";   tail -3 /workspace/shared/noc-copilot/proxy.log
```

---

## If you ran out of disk in shared (28 GB)

```bash
du -sh /workspace/shared/* | sort -h     # find what's big
# ChromaDB or __pycache__ are usual culprits; never put the model here.
```

---

## Daily rhythm

1. **Morning:** run this restart sequence → `git pull` → read HANDOVER.md → continue from "next step".
2. **During:** commit + push after every working component.
3. **Night:** update HANDOVER.md, commit + push. The repo is always runnable on `main`.