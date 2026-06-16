# data/alarm_generator.py
# Generates synthetic telecom NOC alarms. The hero scenario is generate_storm():
# ONE root fault on the core router cascades into ~40 downstream alarms.
# The model reasons ABOUT this data; the generator just produces realistic events.

import json
import os
import random
from datetime import datetime, timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
TOPOLOGY_FILE = os.path.join(_HERE, "topology.json")


def load_topology():
    with open(TOPOLOGY_FILE) as f:
        return json.load(f)


def _descendants(topo, device_id):
    """All devices topologically below device_id (children, grandchildren...)."""
    out = []
    stack = list(topo["devices"][device_id]["downstream"])
    while stack:
        d = stack.pop()
        out.append(d)
        stack.extend(topo["devices"][d]["downstream"])
    return out


def _alarm(aid, ts, device_id, topo, alarm_type, severity, description, kpis):
    dev = topo["devices"][device_id]
    return {
        "alarm_id": aid,
        "timestamp": ts.isoformat(),
        "device_id": device_id,
        "device_type": dev["type"],
        "site": dev["site"],
        "alarm_type": alarm_type,
        "severity": severity,
        "description": description,
        "kpis": kpis,
    }


def generate_storm(seed=42):
    """The scripted demo scenario.

    Root fault: Router-Core-01 BGP peering collapses (CRITICAL) at t=0.
    Cascade: every downstream PE router, aggregation switch and base station
    raises symptomatic alarms (packet loss, link down, high latency,
    sync loss) over the following ~60 seconds.

    Returns a list of ~40 alarms, root first, ordered by time.
    """
    random.seed(seed)
    topo = load_topology()
    t0 = datetime(2026, 6, 16, 9, 0, 0)
    alarms = []
    n = 1

    # 1) ROOT EVENT
    alarms.append(_alarm(
        f"ALM-{n:03d}", t0, "Router-Core-01", topo,
        "BGP_PEER_DOWN", "CRITICAL",
        "BGP session lost with upstream peer 10.0.0.1; route table withdrawal in progress",
        {"cpu": 94, "packet_loss": 0, "latency_ms": 0},
    ))
    n += 1

    affected = _descendants(topo, "Router-Core-01")

    # 2) PE routers react first (~10-25s)
    for dev in [d for d in affected if topo["devices"][d]["type"] == "pe"]:
        offset = random.randint(8, 25)
        for atype, sev, desc, kpis in [
            ("BGP_PEER_DOWN", "CRITICAL",
             f"BGP session to Router-Core-01 down; lost default route",
             {"cpu": random.randint(70, 88), "packet_loss": random.randint(40, 80), "latency_ms": random.randint(120, 400)}),
            ("PACKET_LOSS", "MAJOR",
             f"Elevated packet loss on uplink toward core",
             {"cpu": random.randint(40, 60), "packet_loss": random.randint(30, 70), "latency_ms": random.randint(80, 300)}),
        ]:
            alarms.append(_alarm(f"ALM-{n:03d}", t0 + timedelta(seconds=offset), dev, topo, atype, sev, desc, kpis))
            n += 1
            offset += random.randint(1, 4)

    # 3) Aggregation switches (~20-40s)
    for dev in [d for d in affected if topo["devices"][d]["type"] == "switch"]:
        offset = random.randint(20, 40)
        for atype, sev, desc, kpis in [
            ("LINK_DOWN", "MAJOR",
             f"Uplink interface to PE router went down",
             {"cpu": random.randint(20, 45), "packet_loss": random.randint(50, 100), "latency_ms": 0}),
            ("HIGH_LATENCY", "MINOR",
             f"Round-trip latency above threshold on aggregation uplink",
             {"cpu": random.randint(20, 40), "packet_loss": random.randint(10, 40), "latency_ms": random.randint(200, 600)}),
        ]:
            alarms.append(_alarm(f"ALM-{n:03d}", t0 + timedelta(seconds=offset), dev, topo, atype, sev, desc, kpis))
            n += 1
            offset += random.randint(1, 5)

    # 4) Base stations lose service (~35-60s) - two symptoms each
    for dev in [d for d in affected if topo["devices"][d]["type"] == "bts"]:
        offset = random.randint(35, 55)
        for atype, sev, desc, kpis in [
            ("SERVICE_DEGRADED", "MAJOR",
             "Cell site lost backhaul connectivity; subscribers dropping",
             {"cpu": random.randint(10, 30), "packet_loss": random.randint(60, 100), "latency_ms": random.randint(300, 900)}),
            ("SYNC_LOSS", "MINOR",
             "Loss of timing synchronisation from backhaul",
             {"cpu": random.randint(10, 25), "packet_loss": random.randint(40, 90), "latency_ms": random.randint(200, 700)}),
        ]:
            alarms.append(_alarm(f"ALM-{n:03d}", t0 + timedelta(seconds=offset), dev, topo, atype, sev, desc, kpis))
            n += 1
            offset += random.randint(1, 4)

    alarms.sort(key=lambda a: a["timestamp"])
    return alarms


def generate_normal_alarms(n=5, seed=None):
    """A few unrelated, low-priority alarms (no common root) for contrast."""
    if seed is not None:
        random.seed(seed)
    topo = load_topology()
    devices = list(topo["devices"].keys())
    types = [
        ("HIGH_CPU", "MINOR", "CPU utilisation above 80% threshold"),
        ("INTERFACE_FLAP", "WARNING", "Interface flapped once and recovered"),
        ("CONFIG_CHANGE", "WARNING", "Configuration change committed by operator"),
        ("TEMPERATURE_WARN", "MINOR", "Chassis temperature above nominal"),
    ]
    t0 = datetime(2026, 6, 16, 8, 0, 0)
    out = []
    for i in range(n):
        dev = random.choice(devices)
        atype, sev, desc = random.choice(types)
        out.append(_alarm(
            f"NRM-{i+1:03d}", t0 + timedelta(minutes=random.randint(0, 50)),
            dev, topo, atype, sev, desc,
            {"cpu": random.randint(20, 85), "packet_loss": random.randint(0, 5), "latency_ms": random.randint(1, 30)},
        ))
    return out


if __name__ == "__main__":
    storm = generate_storm()
    print(f"Generated {len(storm)} alarms in the storm scenario.\n")
    print("Root event:")
    print(json.dumps(storm[0], indent=2))
    print("\nFirst 3 cascading alarms:")
    for a in storm[1:4]:
        print(f"  {a['alarm_id']} | {a['timestamp'][11:19]} | {a['device_id']:16} | {a['severity']:8} | {a['alarm_type']}")
    print(f"\nDevices involved: {len(set(a['device_id'] for a in storm))}")
    assert 30 <= len(storm) <= 45, f"expected ~40 alarms, got {len(storm)}"
    assert storm[0]["device_id"] == "Router-Core-01", "root should be the core router"
    print("Alarm generator test passed.")