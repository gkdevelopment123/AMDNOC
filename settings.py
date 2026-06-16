# settings.py - Runtime-configurable settings store (JSON-backed).
import json, os, threading
_LOCK = threading.Lock()
_HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(_HERE, "runtime_settings.json")
DEFAULTS = {
    "sla_seconds": 300,
    "notification_recipients": [
        {"team": "On-call Network Engineer", "channel": "page", "contact": "oncall@telco.example"},
        {"team": "NOC Tier-2", "channel": "slack", "contact": "#noc-tier2"},
        {"team": "Engineering Manager", "channel": "email", "contact": "eng-manager@telco.example"},
    ],
}
def load_settings():
    s = dict(DEFAULTS)
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE) as f:
                s.update(json.load(f))
    except Exception:
        pass
    return s
def save_settings(new_settings):
    with _LOCK:
        cur = load_settings(); cur.update(new_settings)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(cur, f, indent=2)
    return cur
def get_sla_seconds():
    return int(load_settings().get("sla_seconds", 300))
def get_recipients():
    return load_settings().get("notification_recipients", [])
def add_recipient(team, channel, contact):
    s = load_settings(); recips = s.get("notification_recipients", [])
    recips.append({"team": team, "channel": channel, "contact": contact})
    return save_settings({"notification_recipients": recips})
def remove_recipient(index):
    s = load_settings(); recips = s.get("notification_recipients", [])
    if 0 <= index < len(recips): recips.pop(index)
    return save_settings({"notification_recipients": recips})
