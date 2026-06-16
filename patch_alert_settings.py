f = "pipeline.py"
s = open(f).read()

# 1) make stage_alert pass the configured recipients into the prompt + fallback
old = "def stage_alert(incident, root_cause, actions, ticket):"
if old in s and "import settings as _settings" not in s:
    new = '''def stage_alert(incident, root_cause, actions, ticket):
    try:
        import settings as _settings
        _recipients = _settings.get_recipients()
    except Exception:
        _recipients = []'''
    s = s.replace(old, new, 1)

# 2) inject recipients into the payload so the model routes to the real configured teams
s = s.replace(
    '''    payload = {
        "severity": incident.get("severity", ""),
        "affected_devices": incident.get("affected_devices", []),
        "root_cause": root_cause.get("root_cause", ""),
        "actions_taken": [a.get("tool") for a in (actions or [])],
        "ticket_id": (ticket or {}).get("ticket_id", ""),
    }''',
    '''    payload = {
        "severity": incident.get("severity", ""),
        "affected_devices": incident.get("affected_devices", []),
        "root_cause": root_cause.get("root_cause", ""),
        "actions_taken": [a.get("tool") for a in (actions or [])],
        "ticket_id": (ticket or {}).get("ticket_id", ""),
        "available_recipients": _recipients,
    }''')

open(f, "w").write(s)
print("Step 3b: alerting agent now uses configured recipients.")
