# MASTERPLAN.md — Telecom NOC Agentic Copilot

> **READ THIS FILE FIRST, EVERY SESSION.** Then read `HANDOVER.md` to see what's done and what's next. This is the single source of truth for the project. If anything elsewhere contradicts this file, this file wins.

---

## 1. What we are building

A **multi-agent AI system** for a Telecom Network Operations Center (NOC). NOC teams are flooded with alarms; a single root fault cascades into dozens of downstream alerts, burying the real cause and causing SLA breaches.

Our system: **ingests an alarm storm → correlates dozens of alarms into ONE incident → identifies the root cause → proposes a remediation → executes it via tool-calls (mocked router/ITSM APIs) → opens a ticket → shows the whole thing live on a dashboard.**

**The demo arc (memorise this — everything serves it):**
> 40 alarms flood in → collapse to 1 incident → root cause named in seconds → router reset pushed + ticket auto-created → SLA breach avoided. Zero human intervention. Runs 100% on AMD MI300X.

---

## 2. Hard constraints (NON-NEGOTIABLE)

| Constraint | Detail |
|---|---|
| **Everything runs in JupyterLab** | All dev, all servers, all demo happen inside the provided JupyterLab pod. |
| **LLM is internal only** | The app's agents MUST call the local vLLM endpoint. NO external LLM APIs in the shipped app. |
| **Model** | `Qwen/Qwen3-32B` served by vLLM on `http://localhost:8000/v1`. |
| **No API key** | The vLLM server is open. Use `api_key="EMPTY"` in all clients. |
| **Single GPU** | One AMD Instinct MI300X. `tensor-parallel-size 1`. |
| **RAM cap** | Pod is OOM-killed above ~240 GB system RAM. Do NOT load model weights in notebooks — vLLM already holds them in VRAM. |
| **Frontend** | **Gradio** (runs inline in Jupyter). Use `share=False` — NO public tunnel (internal-only rule). |
| **Build agent** | **Aider** (pure Python, points at vLLM directly). node/npm are NOT installed, so Claude Code direct is out. |
| **Deadline** | Submission **17 June 2026, 20:30 IST**. ~30 working hours total (12 hrs/day). |

## 2a. PERSISTENCE — READ CAREFULLY (this bites you if ignored)

The pod has TWO filesystems with very different behaviour:

| Path | Type | Survives session end? | Size | Use for |
|---|---|---|---|---|
| `/workspace/shared/` | network mount (wekafs) | ✅ YES — persistent | **28 GB** | **ALL code, repo, ChromaDB, runbooks** |
| `/` , `/root/.cache`, `/workspace` (non-shared) | overlay | ❌ NO — wiped on session end | 879 GB | model cache (too big for shared), scratch |

**RULES:**
- **The project lives at `/workspace/shared/noc-copilot/`.** All code, the git repo, ChromaDB (`/workspace/shared/noc-copilot/chroma_db`), runbooks — everything you write goes here so it survives.
- **The model (71 GB) CANNOT fit in the 28 GB shared mount.** It stays in `/root/.cache/huggingface` and is **re-downloaded each new session** (~65 GB). This is unavoidable. The morning restart runbook (START_HERE.md) handles it.
- **Push to GitHub frequently** — that's your real backup, not the pod. The overlay can vanish; GitHub can't.
- Never write the model or large artifacts into `/workspace/shared/` — you'll fill the 28 GB and break things.

## 2b. Evaluation criteria — what we are scored on (weight our effort to this)

| Criteria | Weight | Our lever |
|---|---|---|
| **Technical Implementation** | **40%** | A genuinely working multi-agent pipeline end to end. Correctness > everything. Test every component. |
| **Learnings & Future Work** | 20% | Impact / scalability / applicability story in README + closing. "Mock → real ServiceNow = config change." On-prem AMD. |
| **Innovation & Creativity** | 15% | Agents that ACT (tool-calls), correlation collapse, approval gate. Not just a chatbot. |
| **Presentation & Demo Quality** | 15% | The chaos→calm animation + tight 5-min storytelling. The premium UI. |
| **Problem Definition & Relevance** | 10% | NOC alarm-storm pain stated sharply with numbers. |

**The 40% is "does it actually work."** Protect the working demo above all polish. A working ugly pipeline beats a beautiful broken one.

---

## 3. The model quirk you MUST handle

`Qwen/Qwen3-32B` is a **reasoning model** — it emits `<think>...</think>` blocks before its answer. Raw output looks like:
```
<think>Okay, the user wants... let me analyse...</think>
{"root_cause": "..."}
```
**Every agent that needs clean JSON must strip the think block.** Two-layer defence:
1. In `llm.py`, post-process: remove everything between `<think>` and `</think>` before parsing.
2. In prompts, instruct: "Output ONLY valid JSON. No explanation, no markdown fences."
3. Use vLLM's structured output (`guided_json` / `response_format`) where possible to force schema-valid output.

This is the #1 source of bugs in this build. Handle it in the shared `llm.py` helper so no agent has to think about it.

---

## 4. Architecture

```
                    ┌──────────────────────────────────────────┐
                    │         GRADIO DASHBOARD (:7860)          │
                    │  Simulate Outage button · live panels:    │
                    │  alarms · incident graph · RCA · actions  │
                    │  · tickets · SLA timer                    │
                    └────────────────────┬─────────────────────┘
                                         │
                    ┌────────────────────▼─────────────────────┐
                    │     ORCHESTRATOR  (LangGraph state machine)│
                    │  routes incident through the agent chain   │
                    └──┬──────────┬──────────┬──────────┬───────┘
                       │          │          │          │
              ┌────────▼──┐ ┌─────▼─────┐ ┌──▼───────┐ ┌▼──────────┐
              │ INGESTION │ │CORRELATION│ │ROOT CAUSE│ │REMEDIATION│
              │  agent    │ │  agent ★  │ │ agent ★  │ │  agent ★  │
              └────────┬──┘ └─────┬─────┘ └──┬───────┘ └┬──────────┘
                       │          │          │ (RAG)    │ (tool-calls)
                       │          │     ┌────▼─────┐  ┌──▼────────────┐
                       │          │     │ ChromaDB │  │ ACTION EXECUTOR│
                       │          │     │ runbooks │  └──┬─────────┬───┘
                       │          │     └──────────┘     │         │
                       │          │              ┌───────▼──┐  ┌───▼──────┐
                       │          │              │Mock Router│  │Mock ITSM │
                       │          │              │   API     │  │  API     │
                       │          │              └───────────┘  └──────────┘
                       │          │
              ┌────────▼──────────▼─────────────────────────────┐
              │   ALL agents call vLLM Qwen3-32B @ :8000/v1      │
              │              (single shared endpoint)            │
              └──────────────────────────────────────────────────┘
```

---

## 5. The agent team

★ = core three. Build these first; they carry the entire demo.

| # | Agent | Job | Priority |
|---|-------|-----|----------|
| 1 | **Ingestion** | Normalise raw alarms/logs/KPIs into one clean schema. (Can be plain Python first, LLM later.) | P2 |
| 2 | **Correlation ★** | Group the storm into ONE incident; mark root event vs cascade. **Highest-value piece.** | P0 |
| 3 | **Root Cause ★** | Reason over the correlated incident + retrieved runbooks (RAG) → name cause + confidence. | P0 |
| 4 | **Remediation ★** | Decide the fix; choose which tool to call; low-risk = auto, high-risk = human approval gate. | P0 |
| 5 | **Orchestrator** | LangGraph graph wiring the chain together with state + branching. | P1 |
| – | **Action Executor** | Executes chosen tool-calls against mock Router + mock ITSM; returns results. | P1 |

---

## 6. Tech stack

| Layer | Tool | Notes |
|---|---|---|
| LLM serving | **vLLM** (already running) | `Qwen/Qwen3-32B` @ :8000, open, TP=1 |
| LLM client | **openai-python** | pointed at `localhost:8000/v1`, key `"EMPTY"` — fully internal |
| Agent framework | **LangGraph** | multi-agent state machine + handoffs |
| RAG | **ChromaDB** + sentence-transformers | runbooks + past incidents; reduces hallucination |
| Mock APIs | **FastAPI** | fake Router API + fake ITSM (ServiceNow-like) |
| Alarm data | **Custom Python generator** | synthetic alarms + the scripted storm scenario |
| State store | **in-memory dicts / SQLite** | a demo needs no real DB |
| Correlation viz | **NetworkX** rendered in Gradio | "40 alarms → 1 incident" graphic |
| Dashboard | **Gradio** | `share=False`, inline in Jupyter |
| Build agent | **Claude Code** via **litellm** proxy | proxy bridges Anthropic format → local vLLM |

---

## 7. Repository layout

> Root: **`/workspace/shared/noc-copilot/`** (persistent). The git repo is initialised here.

```
/workspace/shared/noc-copilot/
├── MASTERPLAN.md          # this file — source of truth
├── PROMPTS.md             # per-agent system prompts + schemas + tool defs
├── DESIGN_SPEC.md         # the billion-dollar UI brief
├── RULES_AND_GIT.md       # testing, git, security
├── START_HERE.md          # session restart runbook (run every new session)
├── HANDOVER.md            # living progress log (update end of every session)
├── README.md              # how to run (for judges)
├── requirements.txt
├── .gitignore             # excludes chroma_db, __pycache__, .env, *.log
│
├── llm.py                 # shared LLM client + <think> stripping + JSON parse
├── config.py              # endpoints, model name, paths, constants
│
├── data/
│   ├── alarm_generator.py # synthetic alarms + scripted storm  (AGENT BUILDS THIS)
│   ├── topology.json      # mock network topology
│   └── runbooks/          # text runbooks for RAG
│
├── agents/
│   ├── ingestion.py
│   ├── correlation.py     # ★ build first
│   ├── root_cause.py      # ★
│   ├── remediation.py     # ★
│   └── orchestrator.py    # LangGraph graph
│
├── mocks/
│   ├── itsm_api.py        # FastAPI fake ServiceNow
│   └── router_api.py      # FastAPI fake device API
│
├── rag/
│   └── knowledge_base.py  # ChromaDB build + query (persist to ./chroma_db)
│
└── app.py                 # Gradio dashboard (the demo)
```

---

## 8. Build order (depth-first — always keep a working version)

> Full scope, nothing skipped (~30 hrs available). The **synthetic alarm generator is built by the agent** as code — no manual data creation, no download needed. The model reasons *about* this generated data.

**Day 1 (15 Jun) — spine working end to end**
1. `config.py` + `llm.py` (with `<think>` stripping) — prove a clean JSON call works.
2. `data/alarm_generator.py` + `data/topology.json` — synthetic alarms + the scripted storm (1 root fault → ~40 cascading alarms). **Agent writes this.**
3. `agents/root_cause.py` alone — one agent, alarm in → root cause JSON out. **First win.**
4. `mocks/itsm_api.py` + `mocks/router_api.py` — FastAPI, realistic responses.
5. `agents/remediation.py` → tool-calls → mocks. Action executes end to end.

**Day 2 (16 Jun) — full multi-agent + intelligence + premium UI**
6. `agents/correlation.py` — storm → 1 incident (rule-based first, LLM-enhanced after).
7. `agents/orchestrator.py` — LangGraph chain: ingest → correlate → RAG → RCA → remediate → approval? → execute → ticket.
8. `rag/knowledge_base.py` — ChromaDB + `all-MiniLM-L6-v2` embeddings; write 6–8 runbooks; plug retrieval into Root Cause. **Full scope — this grounds the RCA and is a strong "not hallucinated" talking point.**
9. `app.py` — Gradio dashboard built to DESIGN_SPEC.md (the chaos→calm animation, live panels, NetworkX incident graph).
10. Human-approval gate before destructive actions + audit log panel.

**Day 3 (17 Jun, until 20:30 IST) — polish + ship**
11. `agents/ingestion.py` + SLA timer + prompt-injection defence on alarm text.
12. UI polish escalation if needed (RULES_AND_GIT §5).
13. Rehearse the storm demo until it lands every time.
14. README + record a backup demo video. Final push. SUBMIT.

---

## 9. Definition of done (minimum demo)

A judge clicks **"Simulate Outage"** and sees, live:
- [ ] ~40 alarms flood a panel
- [ ] They collapse into **1 incident** (with the NetworkX graph)
- [ ] Root cause appears with a confidence score
- [ ] A remediation is proposed; low-risk auto-executes, high-risk asks approval
- [ ] A mock router reset returns success
- [ ] A mock ITSM ticket is created and shown
- [ ] SLA timer shows the breach was avoided
- [ ] Every LLM call provably hit `localhost:8000` (AMD GPU), nothing external

If all boxes tick, we have a winning demo. Everything else is bonus.

---

## 10. Security (design in — judges reward it)

**App-level (the NOC agents):**
- Human-approval gate before destructive tool-calls (router reset).
- Scoped tools per agent — Correlation agent literally cannot call `reset_router`.
- Input validation on tool arguments (device IDs from a known topology only).
- Audit log of every action taken (who/what/when/result).

**Build-level (Claude Code):**
- API key / secrets in `.env`, never committed (`.gitignore` it).
- Review every change before running shell commands.

---

## 11. The winning narrative (for the pitch)

> "NOC teams drown in 500+ alarms an hour — real causes get buried, SLAs breach. Our multi-agent copilot collapses the storm to one incident, finds the root cause, fixes it, and files the ticket in seconds — with a human approval gate on risky actions. And it never leaves the AMD MI300X: fully on-prem, no external API, deployable inside any telco's secure network."
