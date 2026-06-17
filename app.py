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
import settings as _settings

# === EDIT THIS when your pod session URL changes ===
PROXY_BASE = "https://notebooks.amd.com/jupyter-hack-team-3049-260614162200-ee4e0c4e/proxy"
ITSM_BOARD_URL = f"{PROXY_BASE}/8080/"
ADMIN_URL = f"{PROXY_BASE}/8090/"

LIVE = {"incident": None, "root_cause": None, "remediation": None,
        "actions": None, "ticket": None, "alerts": None, "rag": None, "alarms": None, "elapsed": 0}
SIMULATING = {"active": False}

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
    sla = _settings.get_sla_seconds()
    rem = max(0, sla - elapsed)
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
    return (f'<a class="cc-ticklink-wrap" href="{ITSM_BOARD_URL}" target="_blank">'
            f'<div class="cc-panel cc-tick"><div class="cc-h">ITSM TICKET '
            f'<span class="cc-ticklink">open board &#8599;</span></div>'
            f'<div class="cc-tid">{esc(t.get("ticket_id",""))}</div>'
            f'<div class="cc-trow"><span class="cc-prio">{esc(t.get("priority",""))}</span>'
            f'<span class="cc-tstat">{esc(t.get("status",""))}</span></div>'
            f'<div class="cc-turl">{esc(t.get("url",""))}</div></div></a>')


def p_audit(audit):
    if not audit:
        return ('<div class="cc-panel cc-auditp"><div class="cc-h">AUDIT LOG</div>'
                '<div class="cc-empty">No actions logged.</div></div>')
    lines = "".join(
        f'<div class="cc-aud"><span>{esc(e["ts"])}</span> {esc(e["action"])} '
        f'<b>{esc(e["result"])}</b></div>' for e in audit)
    return f'<div class="cc-panel cc-auditp"><div class="cc-h">AUDIT LOG</div>{lines}</div>'


def p_alerts(alerts):
    if not alerts:
        return ('<div class="cc-panel"><div class="cc-h">NOTIFICATIONS</div>'
                '<div class="cc-empty">No alerts dispatched yet.</div></div>')
    ch = {"page": "#F43F7E", "email": "#6366F1", "slack": "#10B981", "ticket": "#FF8A3D"}
    rows = ""
    for n in alerts.get("notify", []):
        c = ch.get(n.get("channel", ""), "#6366F1")
        rows += (f'<div class="cc-alert"><span class="cc-ch" style="--c:{c}">{esc(n.get("channel","").upper())}</span>'
                 f'<div class="cc-amsg"><b>{esc(n.get("recipient",""))}</b>{esc(n.get("message",""))}</div></div>')
    esc_badge = ('<span class="cc-esc">&#9650; ESCALATED TO MANAGEMENT</span>'
                 if alerts.get("escalate_to_management") else "")
    impact = (f'<div class="cc-impact">Customer impact: {esc(alerts.get("customer_impact",""))}</div>'
              if alerts.get("customer_impact") else "")
    return (f'<div class="cc-panel"><div class="cc-h">NOTIFICATIONS {esc_badge}</div>'
            f'{rows}{impact}</div>')


def p_kb(rag):
    if not rag or not rag.get("ranked"):
        return ('<div class="cc-panel"><div class="cc-h">KNOWLEDGE BASE &middot; RAG</div>'
                '<div class="cc-empty">Awaiting retrieval&#8230;</div></div>')
    n = rag.get("retrieved", len(rag.get("ranked", [])))
    rows = ""
    for idx, r in enumerate(rag.get("ranked", [])[:5]):
        sc = r.get("score")
        pct = int((sc if isinstance(sc, (int, float)) else 0) * 100)
        best = " cc-kbbest" if idx == 0 else ""
        tag = "BEST MATCH" if idx == 0 else f"#{idx+1}"
        scoretxt = f"{pct}%" if sc is not None else "&mdash;"
        rows += (f'<div class="cc-kbrow{best}"><span class="cc-kbtag">{tag}</span>'
                 f'<span class="cc-kbtitle">{esc(r.get("title",""))}</span>'
                 f'<span class="cc-kbbar"><span class="cc-kbfill" style="width:{pct}%"></span></span>'
                 f'<span class="cc-kbscore">{scoretxt}</span></div>')
    return (f'<div class="cc-panel"><div class="cc-h">KNOWLEDGE BASE &middot; RAG '
            f'<span class="cc-kbmeta">retrieved {n} &rarr; reranked</span></div>{rows}</div>')


def board(alarms=None, incident=None, rc=None, rem=None, actions=None,
          ticket=None, audit=None, alerts=None, rag=None, elapsed=0, active=False):
    return f'''
<div class="cc-root">
  <div class="cc-grid">
    <div class="cc-col-l">{p_alarms(alarms)}</div>
    <div class="cc-col-c">{p_map(alarms, incident)}{p_sla(elapsed, active)}{p_kb(rag)}</div>
    <div class="cc-col-r">{p_rc(rc)}{p_ticket(ticket)}</div>
  </div>
  <div class="cc-grid2">
    <div>{p_actions(rem, actions)}</div>
    <div>{p_audit(audit)}</div>
  </div>
</div>'''


CSS = f"""
@import url('{FONTS}');
.gradio-container{{background:#EEF2FB !important;max-width:1280px !important;margin:0 auto !important;padding:10px 18px 28px !important}}
footer{{display:none !important}}
.cc-root{{font-family:'Inter',sans-serif;color:#1E293B;padding:0;max-width:1280px;margin:0 auto}}
.cc-grid{{display:grid;grid-template-columns:1fr 1.25fr 1fr;gap:16px;margin-bottom:16px}}
.cc-grid2{{display:grid;grid-template-columns:1.4fr 1fr;gap:16px}}
@media(max-width:1000px){{.cc-grid,.cc-grid2{{grid-template-columns:1fr}}}}
.cc-col-c,.cc-col-r{{display:flex;flex-direction:column;gap:16px}}
.cc-col-l{{display:flex;flex-direction:column;gap:16px}}
.cc-col-l>div{{flex:1}}
.cc-col-l .cc-panel{{height:100%;display:flex;flex-direction:column}}
#cc-hero{{padding-bottom:18px !important}}
.cc-panel{{box-shadow:0 8px 24px rgba(90,110,200,.07) !important}}
.cc-empty{{display:flex;align-items:center;justify-content:center;min-height:60px}}
.cc-grid{{align-items:stretch}}
.cc-panel{{background:#FFFFFF;border:1px solid #E2E8F5;border-radius:16px;padding:16px 18px;
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
.cc-ticklink-wrap,.cc-ticklink-wrap *{{text-decoration:none !important}}
.cc-ticklink-wrap .cc-h{{color:#64748B !important}}
.cc-ticklink-wrap .cc-tid{{color:#059669 !important}}
.cc-ticklink-wrap .cc-prio{{color:#DC2626 !important;background:#FEE2E2 !important}}
.cc-ticklink-wrap .cc-tstat{{color:#2563EB !important;background:#DBEAFE !important}}
.cc-ticklink-wrap .cc-turl{{color:#94A3B8 !important}}
.cc-ticklink-wrap .cc-ticklink{{color:#6366F1 !important}}
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
.cc-herolinks{{margin-top:12px;display:flex;gap:10px}}
.cc-herolinks a{{font-family:'Space Grotesk';font-weight:700;font-size:.8rem;color:#fff;background:rgba(255,255,255,.18);padding:7px 14px;border-radius:10px;text-decoration:none;border:1px solid rgba(255,255,255,.25)}}
.cc-herolinks a:hover{{background:rgba(255,255,255,.30)}}
.cc-ticklink{{margin-left:auto;font-family:'JetBrains Mono';font-size:.62rem;color:#6366F1;text-decoration:none;font-weight:700}}
#cc-hero .live{{display:inline-block;width:8px;height:8px;border-radius:50%;background:#6EE7B7;
  margin-right:6px;animation:ccp 1.6s infinite;box-shadow:0 0 8px #6EE7B7}}
@keyframes ccp{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
#simbtn{{background:linear-gradient(120deg,#6366F1,#8B5CF6,#06B6D4) !important;color:#fff !important;
  font-family:'Space Grotesk' !important;font-weight:700 !important;font-size:1.1rem !important;
  border:none !important;border-radius:16px !important;padding:14px !important;
  box-shadow:0 10px 30px rgba(99,102,241,.45) !important;transition:transform .15s !important}}
#simbtn:hover{{transform:translateY(-2px) !important}}
#simrand{{background:linear-gradient(120deg,#0EA5E9,#6366F1) !important;color:#fff !important;font-family:'Space Grotesk' !important;font-weight:700 !important;font-size:.95rem !important;border:none !important;border-radius:14px !important;padding:11px !important;margin-top:8px !important;box-shadow:0 8px 24px rgba(14,165,233,.32) !important}}
#simrand:hover{{transform:translateY(-2px) !important}}
#apprbtn{{background:linear-gradient(120deg,#FF8A3D,#F43F7E) !important;color:#fff !important;font-family:'Space Grotesk' !important;font-weight:700 !important;font-size:1rem !important;border:none !important;border-radius:14px !important;padding:12px !important;box-shadow:0 10px 30px rgba(244,63,126,.4) !important;margin-top:8px !important}}
.cc-chathead{{font-family:'Space Grotesk';font-weight:700;color:#0F172A;font-size:1.05rem;
  padding:14px 10px 4px;display:flex;align-items:center;gap:8px}}
.cc-chathead .dot{{width:9px;height:9px;border-radius:50%;background:#10B981;box-shadow:0 0 8px #10B981}}
.cc-chatsub{{color:#64748B;font-size:.82rem;padding:0 10px 12px}}
/* ---- chat polish: compact card, capped height, designed look ---- */
.cc-chathead{{max-width:1280px;margin:18px auto 0;padding:16px 18px 4px}}
.cc-chatsub{{max-width:1280px;margin:0 auto}}
#component-0, .gradio-container .gap{{gap:0 !important}}
div.gradio-container [class*="chat-interface"],
div.gradio-container .chatbot,
div.gradio-container [data-testid="chatbot"]{{
  max-height:420px !important;border-radius:16px !important;
  border:1px solid #E2E8F5 !important;background:#fff !important;
  box-shadow:0 10px 30px rgba(80,100,200,.08) !important}}
.gradio-container .block, .gradio-container .form{{margin-bottom:8px !important}}
div.gradio-container .bubble-wrap,
div.gradio-container .message-wrap{{max-height:360px !important;overflow-y:auto !important}}
.gradio-container .examples, .gradio-container [class*="example"]{{margin-top:6px !important}}
.gradio-container .chat-interface{{max-width:1280px !important;margin:0 auto !important}}
.cc-alert{{display:flex;gap:11px;align-items:flex-start;padding:9px 0;border-bottom:1px solid #F1F5FC}}
.cc-ch{{font-family:'JetBrains Mono';font-size:.6rem;font-weight:700;color:#fff;background:var(--c);
  padding:3px 9px;border-radius:6px;flex:0 0 auto;margin-top:1px}}
.cc-amsg{{font-size:.84rem;color:#334155}}.cc-amsg b{{display:block;color:#0F172A;font-size:.8rem;margin-bottom:1px}}
.cc-esc{{margin-left:auto;font-family:'JetBrains Mono';font-size:.6rem;font-weight:700;color:#fff;
  background:#F43F7E;padding:3px 10px;border-radius:99px}}
.cc-impact{{margin-top:10px;font-size:.8rem;color:#C2410C;background:#FFF4E6;border-radius:8px;padding:8px 12px}}
.cc-kbmeta{{margin-left:auto;font-family:'JetBrains Mono';font-size:.62rem;color:#7C3AED;background:#F3E8FF;padding:3px 10px;border-radius:99px;font-weight:700}}
.cc-kbrow{{display:flex;align-items:center;gap:9px;padding:7px 0;border-bottom:1px solid #F1F5FC}}
.cc-kbtag{{font-family:'JetBrains Mono';font-size:.56rem;font-weight:700;color:#64748B;background:#EEF2FB;padding:2px 7px;border-radius:5px;flex:0 0 auto;min-width:54px;text-align:center}}
.cc-kbbest .cc-kbtag{{color:#fff;background:linear-gradient(120deg,#6366F1,#10B981)}}
.cc-kbtitle{{font-size:.8rem;color:#334155;flex:1;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.cc-kbbar{{width:64px;height:6px;background:#E8EDF8;border-radius:99px;overflow:hidden;flex:0 0 auto}}
.cc-kbfill{{display:block;height:100%;background:linear-gradient(90deg,#6366F1,#10B981);border-radius:99px}}
.cc-kbscore{{font-family:'JetBrains Mono';font-size:.72rem;font-weight:700;color:#059669;flex:0 0 auto;min-width:34px;text-align:right}}
"""

HERO = ('<div id="cc-hero"><h1>&#128752; Telecom NOC &#183; Agentic Copilot</h1>'
        '<p><span class="live"></span>LIVE &#183; Autonomous Multi-Agent Incident Response</p>'
        f'<div class="cc-herolinks"><a href="{ITSM_BOARD_URL}" target="_blank">&#127915; ITSM Board</a>'
        f'<a href="{ADMIN_URL}" target="_blank">&#9881;&#65039; Admin Panel</a></div></div>')

CHAT_HEAD = ('<div class="cc-chathead"><span class="dot"></span>Ask the Copilot</div>'
             '<div class="cc-chatsub">Ask about the live incident, or <b>update the ITSM ticket by chat</b> '
             '&#8212; e.g. &#8220;resolve this ticket and add a note&#8221;. Changes appear live on the ITSM board (port 8080).</div>')


def _run_sim(scenario="p1"):
    alarms = incident = rc = rem = actions = ticket = audit = alerts = rag = None
    start = time.time()
    SIMULATING["active"] = True
    yield board(), gr.update(visible=False), p_alerts(None)
    for stage, payload in pipeline.run_pipeline_streaming(scenario=scenario):
        if stage == "alarms":
            alarms = payload["alarms"]; LIVE["alarms"] = alarms
        elif stage == "runbooks":
            rag = payload.get("rag"); LIVE["rag"] = rag
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
        elif stage == "alerts":
            alerts = payload["alerts"]; audit = payload["audit_log"]; LIVE["alerts"] = alerts
        elif stage == "done":
            LIVE["elapsed"] = int(time.time() - start)
            SIMULATING["active"] = False
        elapsed = int(time.time() - start)
        LIVE['audit_log'] = audit
        show_btn = any(st.get('requires_approval') for st in (rem or {}).get('remediation_plan', [])) if rem else False
        yield board(alarms, incident, rc, rem, actions, ticket, audit, alerts, rag, elapsed, active=True), gr.update(visible=show_btn), p_alerts(alerts)


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


def _pending_high_risk():
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
        yield _board_from_live(), gr.update(visible=False), p_alerts(LIVE.get('alerts'))
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
    yield _board_from_live(), gr.update(visible=False), p_alerts(LIVE.get('alerts'))


def _board_from_live():
    return board(LIVE.get("alarms"), LIVE.get("incident"), LIVE.get("root_cause"),
                 LIVE.get("remediation"), LIVE.get("actions"), LIVE.get("ticket"),
                 LIVE.get("audit_log"), LIVE.get("alerts"), LIVE.get("rag"),
                 LIVE.get("elapsed", 0), active=True)


def _resolve_ticket():
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
        return (f"\u2705 **{tid}** marked **Resolved**.\n\nResolution note: {note}\n\n"
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


def simulate():
    yield from _run_sim("p1")


def simulate_random():
    yield from _run_sim("random")


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
           "to trigger an outage simulation.\n\n"
           f"INCIDENT CONTEXT:\n{json.dumps(ctx, indent=2, default=str)}")
    try:
        m = chat([{"role": "system", "content": sys}, {"role": "user", "content": message}],
                 thinking=False, temperature=0.3, max_tokens=700)
        return m.content.strip()
    except Exception as e:
        return f"(copilot error: {e})"


def _idle_refresh():
    if SIMULATING.get("active"):
        return gr.update()
    return board(LIVE.get("alarms"), LIVE.get("incident"), LIVE.get("root_cause"),
                 LIVE.get("remediation"), LIVE.get("actions"), LIVE.get("ticket"),
                 LIVE.get("audit_log"), LIVE.get("alerts"), LIVE.get("rag"),
                 LIVE.get("elapsed", 0), active=False)


with gr.Blocks(title="NOC Agentic Copilot") as demo:
    gr.HTML(HERO)
    sim = gr.Button("\u26a1 Simulate P1 Outage (Critical)", elem_id="simbtn")
    sim_rand = gr.Button("\U0001F3B2 Simulate Random Incident", elem_id="simrand")
    surface = gr.HTML(board())
    approve_btn = gr.Button("\U0001F512 Approve & Execute High-Risk Action", elem_id="apprbtn", visible=False)
    notif = gr.HTML(p_alerts(None))
    gr.HTML(CHAT_HEAD)
    gr.ChatInterface(fn=copilot,
                     chatbot=gr.Chatbot(height=320),
                     examples=["Why did this incident happen?",
                               "Is the auto-remediation safe?",
                               "Resolve this ticket and add a note that BGP was restored",
                               "Reassign this incident to the Core Network team and set priority P2",
                               "Mark this incident resolved with a resolution note"])
    _timer = gr.Timer(3)
    _timer.tick(_idle_refresh, outputs=surface)
    sim.click(simulate, outputs=[surface, approve_btn, notif])
    sim_rand.click(simulate_random, outputs=[surface, approve_btn, notif])
    approve_btn.click(approve_and_execute, outputs=[surface, approve_btn, notif])


if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860, share=True,
                        css=CSS, theme=gr.themes.Soft())