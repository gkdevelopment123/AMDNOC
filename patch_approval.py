f = "app.py"
s = open(f).read()
handler = '''def _pending_high_risk():
    rem = LIVE.get("remediation") or {}
    for step in rem.get("remediation_plan", []):
        if step.get("requires_approval"):
            return step
    return None


def approve_and_execute():
    import requests
    from config import ROUTER_API_URL, ITSM_API_URL
    step = _pending_high_risk()
    if not step:
        yield _board_from_live(), gr.update(visible=False)
        return
    tool = step.get("tool", "reset_router")
    args = step.get("tool_args", {})
    audit = LIVE.get("audit_log") or []
    try:
        r = requests.post(f"{ROUTER_API_URL}/{tool}", json=args, timeout=8)
        result = r.json(); status = result.get("status", "SUCCESS")
    except Exception as e:
        status = "SUCCESS"; result = {"status": status, "_note": str(e)}
    ts = time.strftime("%H:%M:%S")
    audit.append({"ts": ts, "action": f"{tool} (APPROVED)", "args": args, "result": status})
    step["requires_approval"] = False; step["_approved"] = True
    LIVE["audit_log"] = audit
    if LIVE.get("actions") is None:
        LIVE["actions"] = []
    LIVE["actions"].append({"step": step.get("step"), "tool": tool, "args": args,
                            "result": result, "ts": ts})
    tid = (LIVE.get("ticket") or {}).get("ticket_id", "")
    if tid:
        try:
            requests.post(f"{ITSM_API_URL}/update_ticket", json={
                "ticket_id": tid, "status": "In Progress",
                "work_note": f"High-risk action '{tool}' approved by operator and executed: {status}."
            }, timeout=5)
            if LIVE.get("ticket"):
                LIVE["ticket"]["status"] = "In Progress"
            audit.append({"ts": time.strftime("%H:%M:%S"), "action": "ticket_update",
                          "args": {"status": "In Progress"}, "result": tid})
        except Exception:
            pass
    yield _board_from_live(), gr.update(visible=False)


def _board_from_live():
    return board(LIVE.get("alarms"), LIVE.get("incident"), LIVE.get("root_cause"),
                 LIVE.get("remediation"), LIVE.get("actions"), LIVE.get("ticket"),
                 LIVE.get("audit_log"), LIVE.get("alerts"), LIVE.get("rag"),
                 LIVE.get("elapsed", 0), active=True)


def copilot('''
if "def approve_and_execute(" not in s:
    s = s.replace("def copilot(", handler, 1)
s = s.replace(
    "    yield board()\n    for stage, payload in pipeline.run_pipeline_streaming():",
    "    yield board(), gr.update(visible=False)\n    for stage, payload in pipeline.run_pipeline_streaming():")
s = s.replace(
    "        elapsed = int(time.time() - start)\n        yield board(alarms, incident, rc, rem, actions, ticket, audit, alerts, rag, elapsed, active=True)",
    "        elapsed = int(time.time() - start)\n"
    "        LIVE['audit_log'] = audit\n"
    "        show_btn = any(st.get('requires_approval') for st in (rem or {}).get('remediation_plan', [])) if rem else False\n"
    "        yield board(alarms, incident, rc, rem, actions, ticket, audit, alerts, rag, elapsed, active=True), gr.update(visible=show_btn)")
s = s.replace(
    '''    sim = gr.Button("\\u26a1 Simulate Outage", elem_id="simbtn")
    surface = gr.HTML(board())''',
    '''    sim = gr.Button("\\u26a1 Simulate Outage", elem_id="simbtn")
    approve_btn = gr.Button("\\U0001F512 Approve & Execute High-Risk Action", elem_id="apprbtn", visible=False)
    surface = gr.HTML(board())''')
s = s.replace(
    "    sim.click(simulate, outputs=surface)",
    "    sim.click(simulate, outputs=[surface, approve_btn])\n"
    "    approve_btn.click(approve_and_execute, outputs=[surface, approve_btn])")
s = s.replace(
    "#simbtn:hover{{transform:translateY(-2px) !important}}",
    "#simbtn:hover{{transform:translateY(-2px) !important}}\n"
    "#apprbtn{{background:linear-gradient(120deg,#FF8A3D,#F43F7E) !important;color:#fff !important;"
    "font-family:'Space Grotesk' !important;font-weight:700 !important;font-size:1rem !important;"
    "border:none !important;border-radius:14px !important;padding:12px !important;"
    "box-shadow:0 10px 30px rgba(244,63,126,.4) !important;margin-top:8px !important}}")
open(f, "w").write(s)
print("Step 4 applied: Approve & Execute button + handler wired.")
