# Telecom NOC Agentic Copilot

An autonomous, multi-agent AI system that monitors a telecom Network Operations Center (NOC),
detects incidents from a storm of alarms, finds the root cause, recommends and executes
remediation (with a human approval gate for risky actions), opens and manages ITSM tickets,
and notifies the right teams — all running **100% on-prem** on a single **AMD Instinct MI300X**
GPU with a locally-served **Qwen3-Coder-30B** model.

---

## What it does

When a network outage occurs, a NOC team is flooded with dozens of alarms and must manually
correlate them, diagnose the cause, fix it, and raise tickets — slow, error-prone work that
risks SLA breaches. This Copilot does it end-to-end in seconds:

1. **Ingests** alarms, logs and KPIs from network devices
2. **Correlates** the alarm storm into a single root incident
3. **Finds the root cause** using RAG over runbooks + an LLM reranker
4. **Recommends remediation** with risk levels; auto-executes safe steps, holds risky ones for human approval
5. **Opens an ITSM ticket** (ServiceNow-style) and keeps it updated through its lifecycle
6. **Alerts** the right teams based on severity and customer impact

A built-in **Copilot chat** lets an engineer ask questions and drive ticket updates/resolution
in natural language.

---

## The multi-agent system

All agents call the same local Qwen model with specialised prompts, orchestrated by `pipeline.py`:

| Agent | Role |
|-------|------|
| **Correlation Agent** | Collapses ~33 raw alarms across 17 devices into one root incident |
| **RAG + Reranker** | Retrieves candidate runbooks (ChromaDB + all-MiniLM-L6-v2), then an LLM reranks them so the best match leads |
| **Root Cause Agent** | Diagnoses the underlying fault with a confidence score and evidence |
| **Remediation Agent** | Produces a risk-ranked action plan; low-risk steps auto-execute, high-risk steps require approval |
| **Execution** | Calls mock device APIs (clear BGP, restart interface, reset router) |
| **ITSM Agent** | Creates/updates tickets through a ServiceNow-style board |
| **Alerting Agent** | Decides who to notify (on-call, NOC tier-2, management) and drafts the messages |

---

## Architecture & services

| Service | Port | What it is |
|---------|------|-----------|
| vLLM (Qwen3-Coder-30B) | 8000 | Local LLM inference server |
| Mock Router API | 8001 | Simulated device remediation endpoints |
| Mock ITSM API | 8002 | In-memory ServiceNow-style ticket store |
| ITSM Board | 8080 | Standalone ServiceDesk-style incident board (clickable, live) |
| Admin Panel | 8090 | Configure SLA timer + notification recipients |
| Dashboard | 7860 | Main command-center UI (Gradio) + Copilot chat |

**Pipeline flow:** alarms → correlate → RAG+rerank → root cause → remediate → execute → ticket → alert

---

## Tech stack

- **Model:** Qwen/Qwen3-Coder-30B-A3B-Instruct (served locally via vLLM 0.11)
- **Hardware:** AMD Instinct MI300X (192 GB), ROCm 7.0
- **RAG:** ChromaDB vector store + `all-MiniLM-L6-v2` sentence embeddings + LLM reranking
- **Backend:** Python 3.12, FastAPI (mock APIs + board + admin), Gradio (dashboard)
- **Everything runs on-prem** — no external API calls, full data sovereignty

---

## Prerequisites

- An AMD Instinct MI300X (or compatible ROCm GPU) with vLLM installed
- Python 3.12
- Python packages: `gradio`, `fastapi`, `uvicorn`, `requests`, `chromadb`,
  `sentence-transformers`, `openai` (client), plus the pinned dependency below

**Important dependency pin** (RAG needs this exact range, or retrieval silently fails):
```bash
pip install "huggingface-hub>=0.34.0,<1.0"
```

---

## How to run (step by step)

### 1. Start the local LLM (vLLM) — Terminal 1
```bash
vllm serve Qwen/Qwen3-Coder-30B-A3B-Instruct \
  --host 0.0.0.0 --port 8000 \
  --tensor-parallel-size 1 \
  --max-model-len 100000 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_xml \
  --disable-log-stats
```
Wait until it prints that the server is running. Verify:
```bash
curl -s http://localhost:8000/v1/models
```
You should see `Qwen/Qwen3-Coder-30B-A3B-Instruct`.

### 2. Start all app services — Terminal 2
A single script starts the mock APIs, the ITSM board, the admin panel, and the dashboard
(it leaves vLLM alone, frees any stale ports, health-checks each service, and prints the URLs):
```bash
bash run_all.sh
```
Healthy output shows `router :8001 OK`, `itsm :8002 OK`, `board :8080 OK`,
`admin :8090 OK`, then a public dashboard link.

### 3. Open the interfaces
- **Dashboard:** the `gradio.live` link printed by `run_all.sh` (or port 7860 via your proxy)
- **ITSM Board:** `<your-host>/proxy/8080/`
- **Admin Panel:** `<your-host>/proxy/8090/`

> If you run behind a different host/proxy, edit `PROXY_BASE` at the top of `app.py`
> so the in-app links to the ITSM board and admin panel point to the right place.

### 4. Use it
- Click **⚡ Simulate P1 Outage (Critical)** to run the full pipeline on a core-router incident
- Or **🎲 Simulate Random Incident** for a varied-severity scenario (P2/P3)
- Watch the dashboard fill in: alarms → correlation → RAG → root cause → remediation → ticket → notifications
- Click **🔒 Approve & Execute High-Risk Action** to authorise the risky step (router reset)
- Open the **ITSM Board** to see the live ticket; click it for full details and to resolve it
- Use the **Copilot chat** to ask questions or update/resolve tickets (e.g. "resolve INC123 and add a note")
- Open the **Admin Panel** to change the SLA timer or notification teams — changes reflect live

### To stop / restart
Press **Ctrl+C** in the `run_all.sh` terminal, then run `bash run_all.sh` again.
Leave vLLM (Terminal 1) running — no need to restart the model.

---

## Troubleshooting

- **RAG shows "Awaiting retrieval" / board empty:** re-pin the dependency and restart:
  `pip install "huggingface-hub>=0.34.0,<1.0"` then `bash run_all.sh`
- **vLLM won't start ("free memory less than..."):** a previous vLLM is still holding the GPU.
  Find it with `rocm-smi`, kill the old process, then start vLLM again.
- **"address already in use":** `run_all.sh` already frees the app ports; if it persists,
  `fuser -k -9 8001/tcp 8002/tcp 8080/tcp 8090/tcp 7860/tcp` then re-run.

---

## Project structure

```
app.py                 Main dashboard (Gradio) + Copilot chat + approval flow
pipeline.py            The multi-agent orchestrator (correlate → ... → alert)
llm.py                 Local LLM client + JSON helpers + per-agent token logging
config.py              Model name, ports, URLs, SLA default
settings.py            Runtime settings store (SLA, notification recipients)
itsm_board.py          Standalone ServiceNow-style ITSM board (port 8080)
admin_panel.py         Admin / configuration panel (port 8090)
run_all.sh             One command to start all app services
runtime_settings.json  Persisted admin settings
data/
  alarm_generator.py   Generates the alarm storm + scenario variants
  topology.json        17-device network topology
mocks/
  router_api.py        Mock device remediation API (port 8001)
  itsm_api.py          Mock ITSM ticket API (port 8002)
rag/
  knowledge_base.py    ChromaDB + embeddings runbook retrieval
```

---

## Notes for reviewers

- Input alarms are **synthetic** (generated to simulate a realistic outage); the **AI processing
  is real** — every agent makes a live call to the local model.
- The ITSM board is **styled like ServiceNow**; in production this would connect to a real
  ServiceNow instance via the same update API.
- Token usage per agent is logged to the dashboard terminal for transparency on efficiency.