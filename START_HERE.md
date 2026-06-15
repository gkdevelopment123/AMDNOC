# START_HERE.md — Run This Every New Session

> The pod's model and running servers are on the overlay filesystem, which is **wiped when a session ends**. Only `/workspace/shared/` survives. So every new session you must restart the model + servers. This is the checklist. Takes ~10–15 min (mostly model download).

---

## The persistence reality (why this file exists)

- ✅ **Survives:** `/workspace/shared/noc-copilot/` — all your code + git repo (28 GB mount)
- ❌ **Wiped:** the model in `/root/.cache` (71 GB), all running processes (vLLM, mocks, Gradio)
- 🛟 **Real backup:** GitHub. Push often. If the overlay vanishes mid-build, you `git clone` back into shared and only lose the model (which re-downloads).

---

## Every-session restart sequence

### Tab 1 — start the model (do this FIRST, it takes longest)
```bash
vllm serve Qwen/Qwen3-32B \
  --host 0.0.0.0 --port 8000 \
  --tensor-parallel-size 1 \
  --max-model-len 32768 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```
- If the cache was wiped, it re-downloads ~65 GB (several min). If not, it loads in ~1–2 min.
- Wait for: `Application startup complete` / `Uvicorn running on http://0.0.0.0:8000`.
- Leave this tab open all session.

**Verify (new tab):**
```bash
curl -s http://localhost:8000/v1/models | head -c 200    # expect "id":"Qwen/Qwen3-32B"
```

### Tab 2 — get your code back (first session, or if overlay was wiped)
```bash
cd /workspace/shared
# first time:
git clone https://github.com/gkdevelopment123/AMDNOC.git noc-copilot
cd noc-copilot
# later sessions (code already in shared): just
cd /workspace/shared/noc-copilot && git pull
```

### Tab 2 — reinstall the two packages that aren't pre-baked
Everything else (openai, langgraph, chromadb, sentence-transformers, fastapi, networkx, litellm) is already in the image. Only these may need reinstalling after a wipe:
```bash
pip install gradio aider-chat
```

### Tab 3 — start the mock servers (once code exists)
```bash
cd /workspace/shared/noc-copilot
uvicorn mocks.router_api:app --port 8001 &
uvicorn mocks.itsm_api:app --port 8002 &
```

### Tab 4 — start the dashboard (once app.py exists)
```bash
cd /workspace/shared/noc-copilot
python app.py        # Gradio on :7860, share=False
```

---

## Quick health check (paste anytime)
```bash
echo "model:"; curl -s http://localhost:8000/v1/models | grep -o '"id":"[^"]*"' | head -1
echo "router mock:"; curl -s http://localhost:8001/health 2>/dev/null || echo "down"
echo "itsm mock:";   curl -s http://localhost:8002/health 2>/dev/null || echo "down"
echo "code present:"; ls /workspace/shared/noc-copilot/app.py 2>/dev/null && echo yes || echo "no app.py yet"
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
