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


def generate_scenario(scenario="p1", seed=None):
    import random as _r
    if seed is not None:
        _r.seed(seed)
    if scenario == "p1":
        return generate_storm(seed=seed if seed is not None else 42)
    topo = load_topology()
    t0 = datetime(2026, 6, 16, 9, 0, 0)
    pe = [d for d in topo["devices"] if topo["devices"][d]["type"] == "pe"]
    sw = [d for d in topo["devices"] if topo["devices"][d]["type"] == "switch"]
    bts = [d for d in topo["devices"] if topo["devices"][d]["type"] == "bts"]
    alts = {
        "fiber_cut": {"root_dev": (_r.choice(pe) if pe else "PE-Router-07"),
            "root_type": "LINK_DOWN", "root_sev": "MAJOR",
            "root_desc": "Fiber uplink cut detected; interface down, no carrier signal",
            "root_kpis": {"cpu": 30, "packet_loss": 100, "latency_ms": 0},
            "child_type": "PACKET_LOSS", "child_sev": "MINOR",
            "child_desc": "Increased packet loss on rerouted path"},
        "cpu_exhaustion": {"root_dev": (_r.choice(sw) if sw else "Switch-AGG-03"),
            "root_type": "HIGH_CPU", "root_sev": "MAJOR",
            "root_desc": "Control-plane CPU sustained at 97%; forwarding degraded",
            "root_kpis": {"cpu": 97, "packet_loss": 15, "latency_ms": 220},
            "child_type": "HIGH_LATENCY", "child_sev": "MINOR",
            "child_desc": "Latency rising on switched paths due to CPU saturation"},
        "bts_sync": {"root_dev": (_r.choice(bts) if bts else "BTS-1021"),
            "root_type": "SYNC_LOSS", "root_sev": "MINOR",
            "root_desc": "Loss of timing synchronisation at cell site; GPS reference unstable",
            "root_kpis": {"cpu": 18, "packet_loss": 5, "latency_ms": 60},
            "child_type": "SERVICE_DEGRADED", "child_sev": "MINOR",
            "child_desc": "Minor service degradation at single cell site"},
        "port_flap": {"root_dev": (_r.choice(sw) if sw else "Switch-AGG-04"),
            "root_type": "INTERFACE_FLAP", "root_sev": "MINOR",
            "root_desc": "Access port flapping repeatedly; intermittent link",
            "root_kpis": {"cpu": 25, "packet_loss": 8, "latency_ms": 40},
            "child_type": "HIGH_LATENCY", "child_sev": "MINOR",
            "child_desc": "Brief latency spikes during flap events"},
    }
    if scenario == "random":
        scenario = _r.choice(list(alts.keys()))
    cfg = alts.get(scenario, alts["fiber_cut"])
    alarms = []; n = 1
    alarms.append(_alarm(f"ALM-{n:03d}", t0, cfg["root_dev"], topo,
                         cfg["root_type"], cfg["root_sev"], cfg["root_desc"], cfg["root_kpis"]))
    n += 1
    neighbours = (topo["devices"][cfg["root_dev"]].get("downstream") or [])[:4]
    for dev in neighbours:
        off = _r.randint(5, 25)
        alarms.append(_alarm(f"ALM-{n:03d}", t0 + timedelta(seconds=off), dev, topo,
                             cfg["child_type"], cfg["child_sev"], cfg["child_desc"],
                             {"cpu": _r.randint(20, 60), "packet_loss": _r.randint(5, 40),
                              "latency_ms": _r.randint(40, 300)}))
        n += 1
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