# SETUP_AND_KICKOFF.md — Get Aider Building in 10 Minutes

Build agent is **Aider** (node/npm aren't installed, so Claude Code direct is out — and Aider is simpler anyway: pure Python, talks straight to your vLLM, no proxy needed).

Everything runs in JupyterLab terminals. Repo root: **`/workspace/shared/noc-copilot/`** (persistent).

---

## Terminal layout

```
Tab 1 → vLLM serving Qwen3-32B on :8000        (restart each session — see START_HERE.md)
Tab 2 → aider                                   (the build agent)
Tab 3 → mock servers (router :8001, itsm :8002)
Tab 4 → Gradio app on :7860
```

---

## STEP 1 — Make sure the model is up (Tab 1)

Follow START_HERE.md to start vLLM, then confirm:
```bash
curl -s http://localhost:8000/v1/models | head -c 200   # expect "id":"Qwen/Qwen3-32B"
```

---

## STEP 2 — Get the repo into persistent storage (Tab 2)

```bash
cd /workspace/shared
git clone https://github.com/gkdevelopment123/AMDNOC.git noc-copilot
cd noc-copilot

# copy the 6 kit .md files into this folder (MASTERPLAN, PROMPTS, DESIGN_SPEC,
# RULES_AND_GIT, START_HERE, HANDOVER) if they aren't already here, then:
git add -A && git commit -m "docs: add build kit" && git push
```

Configure git identity (once):
```bash
git config user.email "team@hackathon.local"
git config user.name  "NOC Team"
```

---

## STEP 3 — Install the build agent + missing package (Tab 2)

```bash
pip install aider-chat gradio
```

---

## STEP 4 — Launch Aider pointed at your local Qwen (Tab 2)

Aider talks to vLLM directly via its OpenAI-compatible endpoint — no proxy, no key.

```bash
cd /workspace/shared/noc-copilot
export OPENAI_API_BASE=http://localhost:8000/v1
export OPENAI_API_KEY=EMPTY

aider --model openai/Qwen/Qwen3-32B \
      --no-auto-commits \
      --yes-always \
      MASTERPLAN.md PROMPTS.md DESIGN_SPEC.md RULES_AND_GIT.md HANDOVER.md
```

Notes:
- `--no-auto-commits` → you control commits (the prompt tells it when to commit). Remove if you want Aider to commit automatically.
- Passing the 5 .md files on launch puts them in Aider's context immediately.
- If `openai/Qwen/Qwen3-32B` errors on model naming, try `--openai-api-base http://localhost:8000/v1 --openai-api-key EMPTY --model openai/Qwen/Qwen3-32B`.

---

## STEP 5 — Paste the KICKOFF PROMPT (Tab 2, into Aider)

---

# ███ THE KICKOFF PROMPT (paste into Aider, session 1) ███

```
You are my senior full-stack + AI engineer for the TCS x AMD hackathon. We are
building a Telecom NOC Agentic Copilot that must WIN. We are scored: Technical
Implementation 40% (a genuinely WORKING multi-agent pipeline), Future Work 20%,
Innovation 15%, Demo Quality 15%, Problem Definition 10%. Protect the working
demo above all polish.

READ THESE FILES FIRST (they are in context): MASTERPLAN.md (source of truth),
PROMPTS.md (exact agent prompts + JSON schemas + tool defs), DESIGN_SPEC.md (the
premium UI brief), RULES_AND_GIT.md (testing + git + security), HANDOVER.md
(progress + next step).

HARD RULES:
- All LLM calls use base_url="http://localhost:8000/v1", api_key="EMPTY",
  model="Qwen/Qwen3-32B". NO external APIs in the app.
- Qwen3-32B emits <think>...</think>. llm.py MUST strip it before JSON parsing.
  For simple/structured agents also pass
  extra_body={"chat_template_kwargs":{"enable_thinking":false}} to speed them up.
- Repo root is /workspace/shared/noc-copilot/ (persistent). ChromaDB persists to
  ./chroma_db. Never write large files into /workspace/shared (28 GB cap). Never
  load model weights in code.
- Build ALL agents (multi-agent is the selling point); they run sequentially on
  one GPU — fine. Frontend is Gradio, share=False, built to DESIGN_SPEC.md. Keep
  UI (app.py + CSS) separable from logic.
- The synthetic alarm generator is CODE you write (data/alarm_generator.py) — no
  external data needed. The model reasons about the data it generates.

DISCIPLINE (per RULES_AND_GIT.md):
- After EVERY component: write a tiny test, RUN it, show output, confirm it works.
- After every tested component: git add -A && git commit -m "..." && git push.
- Run the security self-audit before each push. Update HANDOVER.md each task.
- If a tool/package is missing, tell me the exact pip/install command. sudo works
  without a password here, but ASK me before any sudo or destructive command.

FIRST TASK (from HANDOVER.md "Next concrete step"):
Create config.py and llm.py. In llm.py implement:
  - chat(messages, tools=None, response_format=None, thinking=True) calling vLLM
  - strip_think(text) removing <think>...</think>
  - parse_json(text): strip think + markdown fences then json.loads, with one
    repair retry if parsing fails
Then write a tiny test that asks for JSON and prints the clean parsed dict,
proving <think> stripping works. Do NOT proceed until it round-trips cleanly.

Start now: confirm you've read the files, then build config.py + llm.py and test.
```

---

## SESSION RITUAL

**Start of each session (after START_HERE.md restart):**
```
Read MASTERPLAN.md and HANDOVER.md. Tell me the current state and the next step,
then continue. Remember the hard rules (internal vLLM, strip <think>, Gradio
share=False, depth-first, test+commit each component).
```

**End of each session:**
```
Update HANDOVER.md: what we completed, current working state + how to run it,
blockers, and the single next concrete step. Then git add -A, commit, push.
```

---

## Sanity checks
- App calls internal only: `grep -rn "base_url" . | grep -v 8000` should be empty.
- Nothing external leaked: `grep -rn "api.anthropic\|api.openai\|api.deepseek" agents/ app.py llm.py` returns nothing.
- All LLM calls reach :8000: `grep -rn "localhost:8000" .`

---

## If Aider underperforms on a hard file
A 32B model can struggle with big/complex files (especially the Gradio UI). When that happens:
1. Have Aider build the WORKING version first (function over form).
2. For UI polish, zip and bring it to a stronger model (RULES_AND_GIT.md §5):
   `zip -r ui_for_polish.zip app.py *.css static/ templates/ 2>/dev/null; ls -lh ui_for_polish.zip`
3. Paste the improved files back; Aider re-tests.
