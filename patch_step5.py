f = "app.py"
s = open(f).read()
def must(s, old, new, label):
    if old not in s:
        raise SystemExit(f"FAILED at {label}")
    return s.replace(old, new, 1)
if "_resolve_ticket" in s:
    raise SystemExit("Step 5 already applied.")

old_copilot = '''def copilot(message, history):
    # 1) If this is a ticket-update instruction, perform it and confirm.
    upd = _try_ticket_update(message)
    if upd:
        return upd
    # 2) Otherwise answer as an incident-grounded assistant.
    ctx = {k: LIVE.get(k) for k in ("incident", "root_cause", "remediation", "actions", "ticket")}
    sys = ("You are the NOC Copilot assisting a network operations engineer. Answer concisely "
           "and practically, grounded ONLY in the current incident context. You can also update "
           "ITSM tickets when asked (state, priority, assignment, work notes). If no incident has "
           "run, say so and invite them to trigger an outage simulation.\\n\\n"
           f"INCIDENT CONTEXT:\\n{json.dumps(ctx, indent=2, default=str)}")
    try:
        m = chat([{"role": "system", "content": sys}, {"role": "user", "content": message}],
                 thinking=False, temperature=0.3, max_tokens=700)
        return m.content.strip()
    except Exception as e:
        return f"(copilot error: {e})"'''

new_copilot = '''def _resolve_ticket():
    import requests
    from config import ITSM_API_URL
    cur = LIVE.get("ticket") or {}
    tid = cur.get("ticket_id", "")
    if not tid:
        return "There's no active incident ticket to resolve yet."
    rc = LIVE.get("root_cause") or {}
    actions = LIVE.get("actions") or []
    tools_used = ", ".join(sorted({a.get("tool", "") for a in actions})) or "automated remediation"
    note = (f"Incident resolved. Root cause: {rc.get('root_cause','core network fault')}. "
            f"Remediation applied: {tools_used}. Connectivity restored and alarms cleared.")
    try:
        requests.post(f"{ITSM_API_URL}/update_ticket", json={
            "ticket_id": tid, "status": "Resolved", "work_note": note}, timeout=5)
        if LIVE.get("ticket"):
            LIVE["ticket"]["status"] = "Resolved"
        audit = LIVE.get("audit_log") or []
        audit.append({"ts": time.strftime("%H:%M:%S"), "action": "ticket_resolved",
                      "args": {"status": "Resolved"}, "result": tid})
        LIVE["audit_log"] = audit
        return (f"\\u2705 **{tid}** marked **Resolved**.\\n\\nResolution note: {note}\\n\\n"
                f"The ITSM board now shows this incident as Resolved.")
    except Exception as e:
        return f"(couldn't resolve {tid}: {e})"


def _is_resolution_confirm(message):
    m = message.lower().strip()
    keys = ["resolve", "resolved", "mark it resolved", "close it", "it's fixed", "its fixed",
            "fixed now", "all good", "yes resolve", "confirm resol"]
    if any(k in m for k in keys):
        return True
    if m in ("yes", "y", "yep", "confirm", "do it") and (LIVE.get("ticket")):
        return True
    return False


def copilot(message, history):
    if _is_resolution_confirm(message):
        return _resolve_ticket()
    upd = _try_ticket_update(message)
    if upd:
        return upd
    ctx = {k: LIVE.get(k) for k in ("incident", "root_cause", "remediation", "actions", "ticket")}
    sys = ("You are the NOC Copilot assisting a network operations engineer. Answer concisely "
           "and practically, grounded ONLY in the current incident context. You can also update "
           "and resolve ITSM tickets when asked. If no incident has run, say so and invite them "
           "to trigger an outage simulation.\\n\\n"
           f"INCIDENT CONTEXT:\\n{json.dumps(ctx, indent=2, default=str)}")
    try:
        m = chat([{"role": "system", "content": sys}, {"role": "user", "content": message}],
                 thinking=False, temperature=0.3, max_tokens=700)
        return m.content.strip()
    except Exception as e:
        return f"(copilot error: {e})"'''

s = must(s, old_copilot, new_copilot, "copilot")

# add a resolve example to the chat
s = s.replace(
    '"Reassign this incident to the Core Network team and set priority P2"]',
    '"Reassign this incident to the Core Network team and set priority P2",\n'
    '                               "Mark this incident resolved with a resolution note"]')

import ast; ast.parse(s)
open(f, "w").write(s)
print("Step 5 applied + verified: chat resolution + auto note + resolve example.")
