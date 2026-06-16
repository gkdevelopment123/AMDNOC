f = "app.py"
s = open(f).read()
panel_fn = '''def p_alerts(alerts):
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


def board('''
if "def p_alerts(" not in s:
    s = s.replace("def board(", panel_fn, 1)
s = s.replace("          ticket=None, audit=None, elapsed=0, active=False):",
              "          ticket=None, audit=None, alerts=None, elapsed=0, active=False):")
s = s.replace(
'''  <div class="cc-grid2">
    <div>{p_actions(rem, actions)}</div>
    <div>{p_audit(audit)}</div>
  </div>
</div>\'\'\'''',
'''  <div class="cc-grid2">
    <div>{p_actions(rem, actions)}</div>
    <div>{p_audit(audit)}</div>
  </div>
  <div style="margin-top:16px">{p_alerts(alerts)}</div>
</div>\'\'\'''')
s = s.replace("    alarms = incident = rc = rem = actions = ticket = audit = None",
              "    alarms = incident = rc = rem = actions = ticket = audit = alerts = None")
s = s.replace(
'''        elif stage == "ticket":
            ticket = payload["ticket"]; audit = payload["audit_log"]; LIVE["ticket"] = ticket
        elif stage == "done":''',
'''        elif stage == "ticket":
            ticket = payload["ticket"]; audit = payload["audit_log"]; LIVE["ticket"] = ticket
        elif stage == "alerts":
            alerts = payload["alerts"]; audit = payload["audit_log"]; LIVE["alerts"] = alerts
        elif stage == "done":''')
s = s.replace(
"        yield board(alarms, incident, rc, rem, actions, ticket, audit, elapsed, active=True)",
"        yield board(alarms, incident, rc, rem, actions, ticket, audit, alerts, elapsed, active=True)")
s = s.replace('"ticket": None, "alarms": None, "elapsed": 0}',
              '"ticket": None, "alerts": None, "alarms": None, "elapsed": 0}')
alert_css = '''.cc-alert{{display:flex;gap:11px;align-items:flex-start;padding:9px 0;border-bottom:1px solid #F1F5FC}}
.cc-ch{{font-family:'JetBrains Mono';font-size:.6rem;font-weight:700;color:#fff;background:var(--c);
  padding:3px 9px;border-radius:6px;flex:0 0 auto;margin-top:1px}}
.cc-amsg{{font-size:.84rem;color:#334155}}.cc-amsg b{{display:block;color:#0F172A;font-size:.8rem;margin-bottom:1px}}
.cc-esc{{margin-left:auto;font-family:'JetBrains Mono';font-size:.6rem;font-weight:700;color:#fff;
  background:#F43F7E;padding:3px 10px;border-radius:99px}}
.cc-impact{{margin-top:10px;font-size:.8rem;color:#C2410C;background:#FFF4E6;border-radius:8px;padding:8px 12px}}
"""'''
s = s.replace('.cc-chatsub{{color:#64748B;font-size:.82rem;padding:0 10px 12px}}\n"""',
              '.cc-chatsub{{color:#64748B;font-size:.82rem;padding:0 10px 12px}}\n' + alert_css)
open(f, "w").write(s)
print("Dashboard patched: NOTIFICATIONS panel added.")
