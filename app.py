# app.py - NOC Agentic Copilot :: Command Center (VIBRANT LIGHT EDITION)
# Entire surface is custom HTML/SVG we control. Wired to the REAL pipeline.
# Light, colorful, high-contrast, modern. No mock data.

import time
import json
import html as _html

import gradio as gr

from data.alarm_generator import load_topology
import pipeline
from llm import chat
from config import SLA_SECONDS

LIVE = {"incident": None, "root_cause": None, "remediation": None,
        "actions": None, "ticket": None, "alarms": None, "elapsed": 0}

SEV = {"CRITICAL": "#F43F7E", "MAJOR": "#FF8A3D", "MINOR": "#FFB020", "WARNING": "#6366F1"}

FONTS = ("https://fonts.googleapis.com/css2?"
         "family=Space+Grotesk:wght@500;600;700&"
         "family=Inter:wght@400;500;600;700&"
         "family=JetBrains+Mono:wght@400;500;700&display=swap")


def esc(s):
    return _html.escape(str(s))


def svg_storm(alarms):
    import random
    random.seed(7)
    n = len(alarms or [])
    dots = []
    for i in range(n):
        x = 40 + random.random() * 470
        y = 36 + random.random() * 220
        dots.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="5.5" fill="#F43F7E" opacity="0.85">'
            f'<animate attributeName="opacity" values="0.45;1;0.45" dur="{1+random.random():.1f}s" '
            f'repeatCount="indefinite"/></circle>')
    return (f'<svg viewBox="0 0 550 285" width="100%" height="285">'
            f'<text x="275" y="22" text-anchor="middle" fill="#F43F7E" '
            f'font-family="Space Grotesk" font-size="13" font-weight="700">'
            f'{n} ALARMS &#183; UNCORRELATED STORM</text>{"".join(dots)}</svg>')


def svg_incident(incident):
    import math
    devs = (incident or {}).get("affected_devices", [])[:18]
    cx, cy = 275, 155
    spokes, leaves = [], []
    for i, d in enumerate(devs):
        ang = (2 * math.pi * i) / max(1, len(devs))
        x = cx + 168 * math.cos(ang)
        y = cy + 96 * math.sin(ang)
        spokes.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.0f}" y2="{y:.0f}" stroke="#C7D2FE" stroke-width="1.4"/>')
        leaves.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="6.5" fill="#6366F1"/>'
            f'<text x="{x:.0f}" y="{y-11:.0f}" text-anchor="middle" fill="#64748B" '
            f'font-family="JetBrains Mono" font-size="7.5">{esc(d[:12])}</text>')
    hub = (
        f'<circle cx="{cx}" cy="{cy}" r="48" fill="#10B981" opacity="0.22">'
        f'<animate attributeName="r" values="44;56;44" dur="2.4s" repeatCount="indefinite"/></circle>'
        f'<circle cx="{cx}" cy="{cy}" r="32" fill="#10B981"/>'
        f'<text x="{cx}" y="{cy-1}" text-anchor="middle" fill="#fff" '
        f'font-family="Space Grotesk" font-size="13" font-weight="700">1</text>'
        f'<text x="{cx}" y="{cy+13}" text-anchor="middle" fill="#D1FAE5" '
        f'font-family="Space Grotesk" font-size="7.5" font-weight="600">INCIDENT</text>')
    return (f'<svg viewBox="0 0 550 305" width="100%" height="305">'
            f'<text x="275" y="18" text-anchor="middle" fill="#059669" '
            f'font-family="Space Grotesk" font-size="13" font-weight="700">'
            f'CORRELATED &#8594; 1 INCIDENT</text>{"".join(spokes)}{"".join(leaves)}{hub}</svg>')


def p_alarms(alarms):
    if not alarms:
        return ('<div class="cc-panel"><div class="cc-h">ALARM FEED</div>'
                '<div class="cc-empty">Awaiting outage trigger&#8230;</div></div>')
    counts = {}
    for a in alarms:
        counts[a["severity"]] = counts.get(a["severity"], 0) + 1
    chips = "".join(f'<span class="cc-chip" style="--c:{SEV.get(s,"#888")}">{esc(s)} {c}</span>'
                    for s, c in counts.items())
    rows = "".join(
        f'<div class="cc-arow"><i style="background:{SEV.get(a["severity"],"#888")}"></i>'
        f'<span class="cc-t">{esc(a["timestamp"][11:19])}</span>'
        f'<span class="cc-dev">{esc(a["device_id"])}</span>'
        f'<span class="cc-typ">{esc(a["alarm_type"])}</span></div>' for a in alarms[:16])
    more = (f'<div class="cc-more">+ {len(alarms)-16} more streaming&#8230;</div>' if len(alarms) > 16 else "")
    return (f'<div class="cc-panel"><div class="cc-h">ALARM FEED <span class="cc-chips">{chips}</span></div>'
            f'<div class="cc-feed">{rows}{more}</div></div>')


def p_map(alarms, incident):
    inner = svg_incident(incident) if incident else (svg_storm(alarms) if alarms
            else '<div class="cc-empty">No active incident.</div>')
    return f'<div class="cc-panel cc-map"><div class="cc-h">CORRELATION MAP</div>{inner}</div>'


def p_sla(elapsed, active):
    rem = max(0, SLA_SECONDS - elapsed)
    breached = rem <= 0
    color = "#F43F7E" if breached else "#10B981"
    label = "SLA BREACHED" if breached else ("WITHIN SLA" if active else "SLA READY")
    return (f'<div class="cc-panel cc-sla"><div class="cc-h">SLA TIMER</div>'
            f'<div class="cc-clock" style="color:{color}">{rem//60:02d}:{rem%60:02d}</div>'
            f'<div class="cc-slal" style="background:{color}">{label}</div></div>')


def p_rc(rc):
    if not rc:
        return ('<div class="cc-panel"><div class="cc-h">ROOT CAUSE</div>'
                '<div class="cc-empty">Awaiting analysis&#8230;</div></div>')
    conf = int(rc.get("confidence", 0) * 100)
    ev = "".join(f'<li>{esc(e)}</li>' for e in rc.get("evidence", [])[:4])
    return (f'<div class="cc-panel"><div class="cc-h">ROOT CAUSE '
            f'<span class="cc-cat">{esc(rc.get("category","?"))}</span></div>'
            f'<div class="cc-cause">{esc(rc.get("root_cause",""))}</div>'
            f'<div class="cc-conf"><div class="cc-bar"><div class="cc-fill" style="width:{conf}%"></div></div>'
            f'<span>{conf}%</span></div>'
            f'<div class="cc-evh">EVIDENCE</div><ul class="cc-ev">{ev}</ul></div>')


def p_actions(rem, actions):
    if not rem:
        return ('<div class="cc-panel"><div class="cc-h">REMEDIATION</div>'
                '<div class="cc-empty">Awaiting plan&#8230;</div></div>')
    rc = {"low": "#10B981", "medium": "#FF8A3D", "high": "#F43F7E"}
    steps = ""
    for s in rem.get("remediation_plan", []):
        risk = s.get("risk", "low")
        gate = ('<span class="cc-gate cc-appr">&#128274; APPROVAL</span>' if s.get("requires_approval")
                else '<span class="cc-gate cc-auto">&#9889; AUTO</span>')
        steps += (f'<div class="cc-step"><span class="cc-risk" style="--c:{rc.get(risk,"#888")}">{esc(risk)}</span>'
                  f'<span class="cc-act">{esc(s.get("action",""))}</span>{gate}</div>')
    done = "".join(
        f'<div class="cc-exec">&#10003; {esc(a.get("tool"))} &#8594; <b>{esc(a.get("result",{}).get("status","SUCCESS"))}</b></div>'
        for a in (actions or []))
    return (f'<div class="cc-panel"><div class="cc-h">REMEDIATION &amp; ACTIONS</div>'
            f'{steps}<div class="cc-execs">{done}</div></div>')


def p_ticket(t):
    if not t:
        return ('<div class="cc-panel"><div class="cc-h">ITSM TICKET</div>'
                '<div class="cc-empty">No ticket yet.</div></div>')
    return (f'<div class="cc-panel cc-tick"><div class="cc-h">ITSM TICKET</div>'
            f'<div class="cc-tid">{esc(t.get("ticket_id",""))}</div>'
            f'<div class="cc-trow"><span class="cc-prio">{esc(t.get("priority",""))}</span>'
            f'<span class="cc-tstat">{esc(t.get("status",""))}</span></div>'
            f'<div class="cc-turl">{esc(t.get("url",""))}</div></div>')


def p_audit(audit):
    if not audit:
        return ('<div class="cc-panel cc-auditp"><div class="cc-h">AUDIT LOG</div>'
                '<div class="cc-empty">No actions logged.</div></div>')
    lines = "".join(
        f'<div class="cc-aud"><span>{esc(e["ts"])}</span> {esc(e["action"])} '
        f'<b>{esc(e["result"])}</b></div>' for e in audit)
    return f'<div class="cc-panel cc-auditp"><div class="cc-h">AUDIT LOG</div>{lines}</div>'


def board(alarms=None, incident=None, rc=None, rem=None, actions=None,
          ticket=None, audit=None, elapsed=0, active=False):
    return f'''
<div class="cc-root">
  <div class="cc-grid">
    <div class="cc-col-l">{p_alarms(alarms)}</div>
    <div class="cc-col-c">{p_map(alarms, incident)}{p_sla(elapsed, active)}</div>
    <div class="cc-col-r">{p_rc(rc)}{p_ticket(ticket)}</div>
  </div>
  <div class="cc-grid2">
    <div>{p_actions(rem, actions)}</div>
    <div>{p_audit(audit)}</div>
  </div>
</div>'''


CSS = f"""
@import url('{FONTS}');
.gradio-container{{background:#EEF2FB !important;max-width:100% !important;padding:0 !important}}
footer{{display:none !important}}
.cc-root{{font-family:'Inter',sans-serif;color:#1E293B;padding:4px}}
.cc-grid{{display:grid;grid-template-columns:1fr 1.25fr 1fr;gap:16px;margin-bottom:16px}}
.cc-grid2{{display:grid;grid-template-columns:1.4fr 1fr;gap:16px}}
@media(max-width:1000px){{.cc-grid,.cc-grid2{{grid-template-columns:1fr}}}}
.cc-col-c,.cc-col-r{{display:flex;flex-direction:column;gap:16px}}
.cc-panel{{background:#FFFFFF;border:1px solid #E2E8F5;border-radius:18px;padding:18px 20px;
  box-shadow:0 10px 30px rgba(80,100,200,.10)}}
.cc-h{{font-family:'Space Grotesk';font-size:.74rem;letter-spacing:.12em;color:#64748B;
  font-weight:700;margin-bottom:14px;display:flex;align-items:center;gap:8px}}
.cc-empty{{color:#94A3B8;font-size:.85rem;padding:20px 0;text-align:center;font-style:italic}}
.cc-chips{{margin-left:auto;display:flex;gap:5px}}
.cc-chip{{font-family:'JetBrains Mono';font-size:.62rem;font-weight:700;color:#fff;
  background:var(--c);padding:3px 9px;border-radius:99px;box-shadow:0 2px 6px rgba(0,0,0,.12)}}
.cc-feed{{display:flex;flex-direction:column;gap:1px;max-height:300px;overflow:hidden}}
.cc-arow{{display:flex;align-items:center;gap:9px;font-family:'JetBrains Mono';font-size:.74rem;
  padding:5px 0;border-bottom:1px solid #F1F5FC}}
.cc-arow i{{width:8px;height:8px;border-radius:50%;flex:0 0 auto}}
.cc-t{{color:#94A3B8}}.cc-dev{{color:#334155;min-width:112px;font-weight:500}}.cc-typ{{color:#6366F1;font-weight:500}}
.cc-more{{color:#94A3B8;font-size:.72rem;padding-top:8px;font-family:'JetBrains Mono'}}
.cc-map svg{{display:block}}
.cc-sla{{text-align:center;background:linear-gradient(180deg,#FFFFFF,#F6F9FF)}}
.cc-clock{{font-family:'JetBrains Mono';font-size:2.8rem;font-weight:700;line-height:1;letter-spacing:.04em}}
.cc-slal{{display:inline-block;font-family:'Space Grotesk';font-size:.66rem;letter-spacing:.12em;
  font-weight:700;margin-top:8px;color:#fff;padding:4px 14px;border-radius:99px}}
.cc-cat{{margin-left:auto;font-family:'JetBrains Mono';font-size:.6rem;color:#7C3AED;
  background:#F3E8FF;padding:3px 10px;border-radius:99px;text-transform:uppercase;font-weight:700}}
.cc-cause{{font-size:1.02rem;font-weight:600;color:#0F172A;line-height:1.4;margin-bottom:14px}}
.cc-conf{{display:flex;align-items:center;gap:12px;margin-bottom:14px}}
.cc-bar{{flex:1;height:9px;background:#E8EDF8;border-radius:99px;overflow:hidden}}
.cc-fill{{height:100%;background:linear-gradient(90deg,#6366F1,#10B981);border-radius:99px;transition:width 1s ease}}
.cc-conf span{{font-family:'JetBrains Mono';font-weight:700;color:#059669;font-size:.92rem}}
.cc-evh{{font-family:'Space Grotesk';font-size:.62rem;letter-spacing:.12em;color:#94A3B8;font-weight:700;margin-bottom:6px}}
.cc-ev{{margin:0 0 0 18px;font-size:.82rem;color:#475569;line-height:1.6}}
.cc-ev li{{margin-bottom:3px}}
.cc-step{{display:flex;align-items:center;gap:11px;padding:9px 0;border-bottom:1px solid #F1F5FC;font-size:.85rem}}
.cc-risk{{font-family:'JetBrains Mono';font-size:.6rem;font-weight:700;color:#fff;background:var(--c);
  padding:3px 9px;border-radius:6px;text-transform:uppercase;flex:0 0 auto;box-shadow:0 2px 6px rgba(0,0,0,.1)}}
.cc-act{{color:#334155;flex:1;font-weight:500}}
.cc-gate{{font-family:'JetBrains Mono';font-size:.6rem;font-weight:700;padding:3px 9px;border-radius:6px}}
.cc-auto{{color:#059669;background:#D1FAE5}}.cc-appr{{color:#C2410C;background:#FFEDD5}}
.cc-execs{{margin-top:12px;display:flex;flex-direction:column;gap:5px}}
.cc-exec{{font-family:'JetBrains Mono';font-size:.76rem;color:#059669}}.cc-exec b{{color:#047857}}
.cc-tick{{background:linear-gradient(135deg,#FFFFFF,#ECFDF5)}}
.cc-tick .cc-tid{{font-family:'JetBrains Mono';font-size:1.6rem;font-weight:700;color:#059669}}
.cc-trow{{display:flex;gap:10px;align-items:center;margin:8px 0;font-family:'JetBrains Mono';font-size:.8rem}}
.cc-prio{{background:#FEE2E2;color:#DC2626;padding:2px 10px;border-radius:6px;font-weight:700}}
.cc-tstat{{background:#DBEAFE;color:#2563EB;padding:2px 10px;border-radius:6px;font-weight:700}}
.cc-turl{{font-family:'JetBrains Mono';font-size:.7rem;color:#94A3B8}}
.cc-auditp{{background:linear-gradient(180deg,#1E1B4B,#312E81)}}
.cc-auditp .cc-h{{color:#A5B4FC}}
.cc-aud{{font-family:'JetBrains Mono';font-size:.74rem;color:#C7D2FE;padding:3px 0}}
.cc-aud b{{color:#6EE7B7}} .cc-aud span{{color:#A78BFA}}
.cc-auditp .cc-empty{{color:#818CF8}}
#cc-hero{{background:linear-gradient(120deg,#6366F1,#8B5CF6 45%,#06B6D4);
  border-radius:20px;padding:24px 28px;margin:6px 4px 16px;
  box-shadow:0 16px 44px rgba(99,102,241,.35)}}
#cc-hero h1{{font-family:'Space Grotesk';font-size:1.6rem;font-weight:700;color:#fff;margin:0;letter-spacing:-.01em}}
#cc-hero p{{color:#E0E7FF;margin:6px 0 0;font-size:.85rem;font-family:'JetBrains Mono'}}
#cc-hero .live{{display:inline-block;width:8px;height:8px;border-radius:50%;background:#6EE7B7;
  margin-right:6px;animation:ccp 1.6s infinite;box-shadow:0 0 8px #6EE7B7}}
@keyframes ccp{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
#simbtn{{background:linear-gradient(120deg,#6366F1,#8B5CF6,#06B6D4) !important;color:#fff !important;
  font-family:'Space Grotesk' !important;font-weight:700 !important;font-size:1.1rem !important;
  border:none !important;border-radius:16px !important;padding:14px !important;
  box-shadow:0 10px 30px rgba(99,102,241,.45) !important;transition:transform .15s !important}}
#simbtn:hover{{transform:translateY(-2px) !important}}
.cc-chathead{{font-family:'Space Grotesk';font-weight:700;color:#0F172A;font-size:1.05rem;
  padding:14px 10px 4px;display:flex;align-items:center;gap:8px}}
.cc-chathead .dot{{width:9px;height:9px;border-radius:50%;background:#10B981;box-shadow:0 0 8px #10B981}}
.cc-chatsub{{color:#64748B;font-size:.82rem;padding:0 10px 12px}}
"""

HERO = ('<div id="cc-hero"><h1>&#128752; Telecom NOC &#183; Agentic Copilot</h1>'
        '<p><span class="live"></span>LIVE &#183; Qwen3-Coder on AMD Instinct MI300X &#183; multi-agent &#183; 100% on-prem</p></div>')

CHAT_HEAD = ('<div class="cc-chathead"><span class="dot"></span>Ask the Copilot</div>'
             '<div class="cc-chatsub">Ask about the live incident, or <b>update the ITSM ticket by chat</b> '
             '&#8212; e.g. &#8220;resolve this ticket and add a note&#8221;. Changes appear live on the ITSM board (port 8080).</div>')


def simulate():
    alarms = incident = rc = rem = actions = ticket = audit = None
    start = time.time()
    yield board()
    for stage, payload in pipeline.run_pipeline_streaming():
        if stage == "alarms":
            alarms = payload["alarms"]; LIVE["alarms"] = alarms
        elif stage == "incident":
            incident = payload; LIVE["incident"] = incident
        elif stage == "root_cause":
            rc = payload; LIVE["root_cause"] = rc
        elif stage == "remediation":
            rem = payload; LIVE["remediation"] = rem
        elif stage == "actions":
            actions = payload["actions_taken"]; audit = payload["audit_log"]; LIVE["actions"] = actions
        elif stage == "ticket":
            ticket = payload["ticket"]; audit = payload["audit_log"]; LIVE["ticket"] = ticket
        elif stage == "done":
            LIVE["elapsed"] = int(time.time() - start)
        elapsed = int(time.time() - start)
        yield board(alarms, incident, rc, rem, actions, ticket, audit, elapsed, active=True)


def _try_ticket_update(message):
    """Ask the model to extract a structured ITSM update from the user's message.
    If one is present, call the mock ITSM API. Returns a confirmation string or None.
    """
    import requests
    from config import ITSM_API_URL
    from llm import ask_json

    cur = LIVE.get("ticket") or {}
    cur_id = cur.get("ticket_id", "")
    extract_prompt = (
        "You convert a NOC engineer's instruction into an ITSM ticket update.\n"
        f"The current incident's ticket_id is: {cur_id or 'UNKNOWN'}.\n"
        "If the message asks to change/update/resolve/close/reassign/reprioritize a ticket or add a "
        "work note, return JSON: {\"is_update\": true, \"ticket_id\": \"...\", \"status\": null|\"New|In Progress|Resolved|Closed\", "
        "\"priority\": null|\"P1|P2|P3|P4\", \"assigned_to\": null|\"name\", \"assignment_group\": null|\"group\", "
        "\"work_note\": null|\"text\"}. Use the current ticket_id if the user doesn't specify one. "
        "If the message is NOT a ticket update (just a question), return {\"is_update\": false}. "
        "Return ONLY JSON."
    )
    try:
        intent = ask_json(extract_prompt, message, thinking=False)
    except Exception:
        return None
    if not intent.get("is_update"):
        return None

    tid = intent.get("ticket_id") or cur_id
    if not tid:
        return "I couldn't tell which ticket to update — no active incident ticket yet."
    body = {"ticket_id": tid}
    for f in ("status", "priority", "assigned_to", "assignment_group", "work_note"):
        if intent.get(f):
            body[f] = intent[f]
    try:
        r = requests.post(f"{ITSM_API_URL}/update_ticket", json=body, timeout=5)
        t = r.json()
        changed = ", ".join(f"{k}={v}" for k, v in body.items() if k != "ticket_id")
        # keep LIVE ticket fresh
        if LIVE.get("ticket"):
            LIVE["ticket"].update({k: v for k, v in body.items() if k != "ticket_id"})
        return (f"✅ Updated **{tid}** ({changed}). "
                f"State is now **{t.get('status','?')}**. The change is live on the ITSM board.")
    except Exception as e:
        return f"(couldn't reach ITSM to update {tid}: {e})"


def copilot(message, history):
    # 1) If this is a ticket-update instruction, perform it and confirm.
    upd = _try_ticket_update(message)
    if upd:
        return upd
    # 2) Otherwise answer as an incident-grounded assistant.
    ctx = {k: LIVE.get(k) for k in ("incident", "root_cause", "remediation", "actions", "ticket")}
    sys = ("You are the NOC Copilot assisting a network operations engineer. Answer concisely "
           "and practically, grounded ONLY in the current incident context. You can also update "
           "ITSM tickets when asked (state, priority, assignment, work notes). If no incident has "
           "run, say so and invite them to trigger an outage simulation.\n\n"
           f"INCIDENT CONTEXT:\n{json.dumps(ctx, indent=2, default=str)}")
    try:
        m = chat([{"role": "system", "content": sys}, {"role": "user", "content": message}],
                 thinking=False, temperature=0.3, max_tokens=700)
        return m.content.strip()
    except Exception as e:
        return f"(copilot error: {e})"


with gr.Blocks(title="NOC Agentic Copilot") as demo:
    gr.HTML(HERO)
    sim = gr.Button("\u26a1 Simulate Outage", elem_id="simbtn")
    surface = gr.HTML(board())
    gr.HTML(CHAT_HEAD)
    gr.ChatInterface(fn=copilot,
                     examples=["Why did this incident happen?",
                               "Is the auto-remediation safe?",
                               "Resolve this ticket and add a note that BGP was restored",
                               "Reassign this incident to the Core Network team and set priority P2"])
    sim.click(simulate, outputs=surface)


if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860, share=True,
                        css=CSS, theme=gr.themes.Soft())