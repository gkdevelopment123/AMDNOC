f = "pipeline.py"
s = open(f).read()
changed = False
anchor = "def run_pipeline_streaming(seed=42):"
alert_code = '''ALERTING_PROMPT = """You are the Alerting Agent in a Telecom NOC. Given a resolved/handled
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
    payload = {
        "severity": incident.get("severity", ""),
        "affected_devices": incident.get("affected_devices", []),
        "root_cause": root_cause.get("root_cause", ""),
        "actions_taken": [a.get("tool") for a in (actions or [])],
        "ticket_id": (ticket or {}).get("ticket_id", ""),
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


'''
if anchor in s and "def stage_alert(" not in s:
    s = s.replace(anchor, alert_code + anchor, 1); changed = True
ticket_yield = '''    ticket = create_ticket(incident, rc, audit_log)
    yield ("ticket", {"ticket": ticket, "audit_log": list(audit_log)})
'''
alert_yield = '''    ticket = create_ticket(incident, rc, audit_log)
    yield ("ticket", {"ticket": ticket, "audit_log": list(audit_log)})

    alerts = stage_alert(incident, rc, actions, ticket)
    audit_log.append({"ts": time.strftime("%H:%M:%S"), "action": "alert_dispatch",
                      "args": {"recipients": len(alerts.get("notify", []))}, "result": "SENT"})
    yield ("alerts", {"alerts": alerts, "audit_log": list(audit_log)})
'''
if ticket_yield in s and '("alerts"' not in s:
    s = s.replace(ticket_yield, alert_yield, 1); changed = True
done_old = '''    yield ("done", {"incident": incident, "root_cause": rc, "remediation": rem,
                    "actions": actions, "ticket": ticket, "audit_log": audit_log,
                    "alarm_count": len(alarms)})'''
done_new = '''    yield ("done", {"incident": incident, "root_cause": rc, "remediation": rem,
                    "actions": actions, "ticket": ticket, "alerts": alerts,
                    "audit_log": audit_log, "alarm_count": len(alarms)})'''
if done_old in s:
    s = s.replace(done_old, done_new, 1); changed = True
open(f, "w").write(s)
print("Alerting agent added to pipeline." if changed else "WARNING: anchors not found.")
