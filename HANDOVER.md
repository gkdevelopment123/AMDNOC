# HANDOVER.md — Living Progress Log

> **Claude Code: at the START of every session, read `MASTERPLAN.md` then this file.**
> **At the END of every session, update this file:** mark what's done, note the current working state and exactly how to run it, list any blockers, and write the single next concrete step.

---

## Current status: 🟡 PROJECT START — nothing built yet

**Last updated:** (session 0 — kit just dropped in)
**Updated by:** initial setup

---

## Environment (confirmed working)

- ✅ vLLM serves `Qwen/Qwen3-32B` at `http://localhost:8000/v1` — OPEN, no API key (use `"EMPTY"`)
- ✅ 1× AMD Instinct MI300X, vLLM 0.11.0, ROCm 7.0, Python 3.12
- ✅ Build agent: **Aider** (node/npm NOT installed; Aider is pure Python, no proxy)
- ✅ Pre-installed: openai, langgraph, chromadb, sentence-transformers, fastapi, networkx, litellm
- ⚠️ NOT installed: **gradio, aider-chat** → `pip install gradio aider-chat`
- ✅ git 2.34, sudo works without password
- ✅ Repo: https://github.com/gkdevelopment123/AMDNOC → clone to `/workspace/shared/noc-copilot/`

**PERSISTENCE (critical):**
- ✅ ONLY `/workspace/shared/` survives session end (28 GB, wekafs mount) → all code + repo here
- ❌ `/root/.cache` (model, 71 GB) + all processes are WIPED each session → re-run START_HERE.md
- 🛟 GitHub is the real backup — push often

**Model quirks:**
- ⚠️ Emits `<think>...</think>` — strip before JSON parse (MASTERPLAN §3). Disable via `enable_thinking:false` on simple agents.
- ⚠️ vLLM has NO `/v1/messages` (Anthropic format) — irrelevant now (using Aider, OpenAI format).
- ⚠️ Pod OOM-killed above 240 GB RAM — never load weights in code.

**How to verify the model is up:**
```bash
curl http://localhost:8000/v1/models   # expect "id":"Qwen/Qwen3-32B"
```

---

## Progress tracker

Legend: ✅ done · 🔄 in progress · ⬜ not started · ❌ blocked

### Day 1 — spine end to end
- [x] `config.py` — endpoints, model name, constants
- [x] `llm.py` — shared client + `strip_think()` + safe JSON parse  ← **START HERE**
- [x] `data/topology.json` — mock network topology
- [x] `agents/root_cause.py` — first single-agent win
- [x] `mocks/router_api.py` + `mocks/itsm_api.py` — FastAPI, realistic responses
- [x] `agents/remediation.py` → tool-calls → mocks
- [x] `agents/orchestrator.py` — LangGraph chain
- ⬜ `mocks/itsm_api.py` — FastAPI fake ServiceNow
- ⬜ `mocks/router_api.py` — FastAPI fake device API
- ⬜ Remediation → tool-call → mock executes end to end

### Day 2 — multi-agent + intelligence + UI
- ⬜ `agents/correlation.py` — storm → 1 incident
- ⬜ `agents/orchestrator.py` — LangGraph chain
- [x] `rag/knowledge_base.py` — ChromaDB runbooks → into Root Cause
- ⬜ `app.py` — Gradio dashboard + NetworkX incident graph
- ⬜ Human-approval gate on destructive actions

### Day 3 — polish + ship (until 20:30 IST 17 Jun)
- ⬜ `agents/ingestion.py` + SLA timer + audit log panel
- ⬜ Rehearse storm demo
- ⬜ README + backup demo video
- ⬜ SUBMIT

---

## Definition of done (the demo must show)
- ⬜ ~40 alarms flood in
- ⬜ collapse to 1 incident (NetworkX graph)
- ⬜ root cause + confidence
- ⬜ remediation proposed; low-risk auto, high-risk approval
- ⬜ mock router reset returns success
- ⬜ mock ITSM ticket created + shown
- ⬜ SLA timer shows breach avoided
- ⬜ all LLM calls provably hit localhost:8000

---

## Current working state / how to run
Nothing built yet. Once `app.py` exists, the run command will go here, e.g.:
```bash
# Tab 1: vLLM (already running)
# Tab 2: uvicorn mocks.router_api:app --port 8001
# Tab 3: uvicorn mocks.itsm_api:app --port 8002
# Tab 4: python app.py   # Gradio on :7860
```

---

## Known issues / blockers
- None yet.

---

## ⏭️ NEXT CONCRETE STEP
All intelligent components are now implemented. The next step is to implement the dashboard. Create `app.py` — Gradio dashboard + NetworkX incident graph. Then prove it works: the complete NOC workflow can be launched from the dashboard and shows all panels in real-time. Do NOT move on until that round-trips cleanly.
