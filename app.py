# app.py - NOC Agentic Copilot dashboard (premium, light-themed, command-center).
# Wired to the REAL pipeline (pipeline.py). No mock/hardcoded data.
# Presentation only - all logic lives in pipeline.py and llm.py.

import time
import io
import base64
import json

import gradio as gr
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from data.alarm_generator import load_topology
import pipeline
from llm import chat
from config import SLA_SECONDS

# Shared live state for the copilot chat to reference
LIVE = {"incident": None, "root_cause": None, "remediation": None,
        "actions": None, "ticket": None, "alarms": None}

SEV_COLOR = {"CRITICAL": "#FF3B6B", "MAJOR": "#FF8A3D", "MINOR": "#FFC23D", "WARNING": "#8AA0C8"}

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');
.gradio-container{background:#F4F7FE !important;font-family:'Inter',sans-serif !important;max-width:100% !important}
.gr-block,.gr-box{border-radius:16px !important}
#hdr{background:linear-gradient(120deg,#4F6BFF,#7A5CFF,#00C2FF);border-radius:18px;padding:20px 26px;margin-bottom:8px;box-shadow:0 12px 32px rgba(79,107,255,.25)}
#hdr h1{color:#fff;font-family:'Space Grotesk';font-size:1.7rem;margin:0;font-weight:700}
#hdr p{color:#E6ECFF;margin:4px 0 0;font-size:.9rem}
.panel{background:#fff;border:1px solid #E4ECF7;border-radius:16px;padding:16px 18px;box-shadow:0 8px 24px rgba(79,107,255,.10)}
.panel h3{font-family:'Space Grotesk';font-size:1rem;margin:0 0 10px;color:#0F1B2D;display:flex;align-items:center;gap:8px}
.metric{font-family:'Space Grotesk';font-size:2.2rem;font-weight:700;background:linear-gradient(120deg,#4F6BFF,#00C2FF);-webkit-background-clip:text;background-clip:text;color:transparent;line-height:1}
.metric-l{font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;color:#5B6B82;font-weight:600}
.sev-pill{display:inline-block;padding:2px 9px;border-radius:99px;color:#fff;font-size:.7rem;font-weight:700;font-family:'JetBrains Mono';margin:1px}
.alarm-row{font-family:'JetBrains Mono';font-size:.74rem;padding:3px 0;border-bottom:1px solid #F0F4FA;color:#3C4B63}
.rc-card{background:linear-gradient(120deg,#F1ECFF,#E2F8FF);border-left:5px solid #7A5CFF;border-radius:0 12px 12px 0;padding:14px 16px}
.rc-card .cause{font-size:1rem;font-weight:600;color:#0F1B2D;margin-bottom:6px}
.conf{font-family:'JetBrains Mono';font-weight:700;color:#18C98D}
.tick{background:linear-gradient(120deg,#E4FAF2,#E2F8FF);border-left:5px solid #18C98D;border-radius:0 12px 12px 0;padding:14px 16px;font-family:'JetBrains Mono';font-size:.85rem}
.audit{font-family:'JetBrains Mono';font-size:.72rem;color:#5B6B82;background:#0F1B2D;border-radius:10px;padding:10px 12px}
.audit .ok{color:#5be4b4}
#simbtn{background:linear-gradient(120deg,#4F6BFF,#7A5CFF) !important;color:#fff !important;font-weight:700 !important;border:none !important;font-size:1rem !important}
.status-ok{color:#18C98D;font-weight:700}.status-crit{color:#FF3B6B;font-weight:700}
"""


def render_alarms(alarms):
    if not alarms:
        return "<div class='panel'><h3>📡 Alarm Feed</h3><p style='color:#5B6B82'>No alarms. Click Simulate Outage.</p></div>"
    counts = {}
    for a in alarms:
        counts[a["severity"]] = counts.get(a["severity"], 0) + 1
    pills = "".join(f"<span class='sev-pill' style='background:{SEV_COLOR.get(s,'#888')}'>{s} {c}</span>" for s, c in counts.items())
    rows = "".join(
        f"<div class='alarm-row'><span style='color:{SEV_COLOR.get(a['severity'],'#888')}'>●</span> "
        f"{a['timestamp'][11:19]} | {a['device_id']:16} | {a['alarm_type']}</div>"
        for a in alarms[:18]
    )
    more = f"<div class='alarm-row' style='color:#9AABC4'>+ {len(alarms)-18} more…</div>" if len(alarms) > 18 else ""
    return f"<div class='panel'><h3>📡 Alarm Feed &nbsp;{pills}</h3>{rows}{more}</div>"


def render_graph(alarms, incident=None):
    """Draw the correlation graph. Before correlation: scattered. After: collapsed to 1 hub."""
    topo = load_topology()
    fig, ax = plt.subplots(figsize=(5.2, 4.0), dpi=110)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    G = nx.Graph()

    if incident:
        # Collapsed view: incident hub + affected devices
        hub = "INCIDENT"
        G.add_node(hub)
        for d in incident.get("affected_devices", []):
            G.add_node(d)
            G.add_edge(hub, d)
        pos = nx.spring_layout(G, seed=3, k=0.9)
        node_colors = ["#18C98D" if n == hub else "#4F6BFF" for n in G.nodes()]
        node_sizes = [1400 if n == hub else 350 for n in G.nodes()]
        nx.draw_networkx_edges(G, pos, edge_color="#B9C6DE", width=1.5, ax=ax)
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax)
        labels = {n: ("✓ 1 INCIDENT" if n == hub else "") for n in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight="bold", font_color="#0F1B2D", ax=ax)
        ax.set_title("Correlated → 1 incident", fontsize=11, fontweight="bold", color="#18C98D")
    else:
        # Storm view: every alarm a separate red node
        for i, a in enumerate(alarms or []):
            G.add_node(f"{a['device_id']}-{i}")
        pos = nx.spring_layout(G, seed=5, k=0.4)
        nx.draw_networkx_nodes(G, pos, node_color="#FF3B6B", node_size=160, alpha=0.85, ax=ax)
        ax.set_title(f"{len(alarms or [])} alarms — uncorrelated storm", fontsize=11, fontweight="bold", color="#FF3B6B")

    ax.axis("off")
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", facecolor="#FFFFFF", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    from PIL import Image
    return Image.open(buf)


def render_rc(rc):
    if not rc:
        return "<div class='panel'><h3>🔍 Root Cause</h3><p style='color:#5B6B82'>Awaiting analysis…</p></div>"
    conf = int(rc.get("confidence", 0) * 100)
    ev = "".join(f"<li>{e}</li>" for e in rc.get("evidence", [])[:4])
    return (f"<div class='panel'><h3>🔍 Root Cause</h3><div class='rc-card'>"
            f"<div class='cause'>{rc.get('root_cause','')}</div>"
            f"<div class='metric-l'>Confidence <span class='conf'>{conf}%</span> · "
            f"Category: {rc.get('category','?')}</div>"
            f"<ul style='margin:8px 0 0 16px;font-size:.8rem;color:#3C4B63'>{ev}</ul></div></div>")


def render_actions(rem, actions):
    if not rem:
        return "<div class='panel'><h3>🔧 Remediation &amp; Actions</h3><p style='color:#5B6B82'>Awaiting plan…</p></div>"
    rows = ""
    for s in rem.get("remediation_plan", []):
        risk = s.get("risk", "low")
        rc = {"low": "#18C98D", "medium": "#FF8A3D", "high": "#FF3B6B"}.get(risk, "#888")
        gate = " 🔒 needs approval" if s.get("requires_approval") else " ⚡ auto"
        rows += (f"<div class='alarm-row'><span class='sev-pill' style='background:{rc}'>{risk}</span> "
                 f"{s.get('action','')}<span style='color:#9AABC4'>{gate}</span></div>")
    done = ""
    for a in (actions or []):
        st = a.get("result", {}).get("status", "SUCCESS")
        done += f"<div class='alarm-row'>✅ {a.get('tool')} → <span class='status-ok'>{st}</span></div>"
    return (f"<div class='panel'><h3>🔧 Remediation &amp; Actions</h3>{rows}"
            f"<div style='margin-top:8px'>{done}</div></div>")


def render_ticket(ticket):
    if not ticket:
        return "<div class='panel'><h3>🎫 ITSM Ticket</h3><p style='color:#5B6B82'>No ticket yet.</p></div>"
    return (f"<div class='panel'><h3>🎫 ITSM Ticket</h3><div class='tick'>"
            f"<b>{ticket.get('ticket_id','')}</b> · {ticket.get('priority','')}<br>"
            f"Status: {ticket.get('status','')}<br>"
            f"<span style='color:#5B6B82'>{ticket.get('url','')}</span></div></div>")


def render_audit(audit):
    if not audit:
        return "<div class='panel'><h3>🛡️ Audit Log</h3><div class='audit'>No actions yet.</div></div>"
    lines = "<br>".join(f"{e['ts']} | {e['action']} | <span class='ok'>{e['result']}</span>" for e in audit)
    return f"<div class='panel'><h3>🛡️ Audit Log</h3><div class='audit'>{lines}</div></div>"


def render_sla(remaining, breached=False):
    color = "#FF3B6B" if breached else "#18C98D"
    label = "SLA BREACHED" if breached else "WITHIN SLA"
    mins = max(0, remaining) // 60
    secs = max(0, remaining) % 60
    return (f"<div class='panel' style='text-align:center'><h3 style='justify-content:center'>⏱️ SLA Timer</h3>"
            f"<div class='metric' style='color:{color};-webkit-text-fill-color:{color}'>{mins:02d}:{secs:02d}</div>"
            f"<div class='metric-l' style='color:{color}'>{label}</div></div>")


def simulate_outage():
    """Run the real pipeline, yielding UI updates after each stage."""
    alarms_html = render_alarms(None)
    graph = render_graph(None)
    rc_html = render_rc(None)
    act_html = render_actions(None, None)
    tick_html = render_ticket(None)
    audit_html = render_audit(None)
    sla_html = render_sla(SLA_SECONDS)
    start = time.time()

    for stage, payload in pipeline.run_pipeline_streaming():
        if stage == "alarms":
            LIVE["alarms"] = payload["alarms"]
            alarms_html = render_alarms(payload["alarms"])
            graph = render_graph(payload["alarms"])
        elif stage == "incident":
            LIVE["incident"] = payload
            graph = render_graph(LIVE["alarms"], payload)
        elif stage == "root_cause":
            LIVE["root_cause"] = payload
            rc_html = render_rc(payload)
        elif stage == "remediation":
            LIVE["remediation"] = payload
            act_html = render_actions(payload, None)
        elif stage == "actions":
            LIVE["actions"] = payload["actions_taken"]
            act_html = render_actions(LIVE["remediation"], payload["actions_taken"])
            audit_html = render_audit(payload["audit_log"])
        elif stage == "ticket":
            LIVE["ticket"] = payload["ticket"]
            tick_html = render_ticket(payload["ticket"])
            audit_html = render_audit(payload["audit_log"])
        elif stage == "done":
            elapsed = int(time.time() - start)
            sla_html = render_sla(SLA_SECONDS - elapsed, breached=False)

        yield alarms_html, graph, rc_html, act_html, tick_html, audit_html, sla_html


def copilot_chat(message, history):
    """Incident-aware chat. Answers grounded in the live pipeline state."""
    context = {
        "incident": LIVE.get("incident"),
        "root_cause": LIVE.get("root_cause"),
        "remediation": LIVE.get("remediation"),
        "actions_taken": LIVE.get("actions"),
        "ticket": LIVE.get("ticket"),
    }
    sys = (
        "You are the NOC Copilot, assisting a network operations engineer. "
        "Answer concisely and practically, grounded ONLY in the current incident context below. "
        "If no incident has run yet, say so and invite them to simulate an outage.\n\n"
        f"CURRENT INCIDENT CONTEXT:\n{json.dumps(context, indent=2, default=str)}"
    )
    try:
        msg = chat(
            [{"role": "system", "content": sys}, {"role": "user", "content": message}],
            thinking=False, temperature=0.3, max_tokens=800,
        )
        return msg.content.strip()
    except Exception as e:
        return f"(copilot error: {e})"


with gr.Blocks(title="NOC Agentic Copilot") as demo:
    gr.HTML("<div id='hdr'><h1>🛰️ Telecom NOC Agentic Copilot</h1>"
            "<p>Multi-agent incident response · running on AMD Instinct MI300X · 100% on-prem</p></div>")

    with gr.Row():
        sim_btn = gr.Button("⚡ Simulate Outage", elem_id="simbtn", scale=2)
        gr.HTML("<div class='panel' style='padding:10px 16px'><span class='metric-l'>Model</span><br>"
                "<b style='font-family:JetBrains Mono;font-size:.8rem'>Qwen3-Coder · vLLM · MI300X</b></div>")

    with gr.Row():
        with gr.Column(scale=3):
            alarms_out = gr.HTML(render_alarms(None))
        with gr.Column(scale=4):
            graph_out = gr.Image(render_graph(None), show_label=False, container=False)
            sla_out = gr.HTML(render_sla(SLA_SECONDS))
        with gr.Column(scale=3):
            rc_out = gr.HTML(render_rc(None))
            tick_out = gr.HTML(render_ticket(None))

    with gr.Row():
        with gr.Column(scale=6):
            act_out = gr.HTML(render_actions(None, None))
        with gr.Column(scale=4):
            audit_out = gr.HTML(render_audit(None))

    gr.HTML("<div class='panel'><h3>💬 Ask the Copilot</h3>"
            "<p style='color:#5B6B82;font-size:.85rem;margin:0'>Ask about the live incident — "
            "why it happened, whether an action is safe, or a summary for your manager.</p></div>")
    gr.ChatInterface(fn=copilot_chat,
                     examples=["Why did this incident happen?",
                               "Is the router reset safe to auto-execute?",
                               "Summarize this incident for my manager"])

    sim_btn.click(simulate_outage, outputs=[alarms_out, graph_out, rc_out, act_out, tick_out, audit_out, sla_out])


if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860, share=True, css=CSS, theme=gr.themes.Soft())