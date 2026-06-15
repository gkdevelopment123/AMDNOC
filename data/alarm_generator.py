# data/alarm_generator.py - Generate synthetic network alarms for testing
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Mock network topology data
TOPOLOGY_DATA = {
    "devices": [
        {"id": "router-01", "type": "router", "location": "Data Center A", "status": "online"},
        {"id": "switch-01", "type": "switch", "location": "Data Center A", "status": "online"},
        {"id": "server-01", "type": "server", "location": "Data Center B", "status": "online"},
        {"id": "firewall-01", "type": "firewall", "location": "Data Center A", "status": "online"},
        {"id": "loadbalancer-01", "type": "loadbalancer", "location": "Data Center B", "status": "online"}
    ],
    "links": [
        {"from": "router-01", "to": "switch-01", "status": "up"},
        {"from": "switch-01", "to": "server-01", "status": "up"},
        {"from": "router-01", "to": "firewall-01", "status": "up"},
        {"from": "firewall-01", "to": "loadbalancer-01", "status": "up"}
    ]
}

# Alarm templates
ALARM_TEMPLATES = [
    {
        "severity": "critical",
        "category": "network",
        "description": "Interface {interface} on {device} is down",
        "impact": "Service disruption affecting multiple applications",
        "probability": 0.1
    },
    {
        "severity": "major",
        "category": "network",
        "description": "High packet loss detected on {interface} of {device}",
        "impact": "Degraded service quality",
        "probability": 0.2
    },
    {
        "severity": "minor",
        "category": "network",
        "description": "CPU utilization on {device} exceeded 80%",
        "impact": "Potential performance degradation",
        "probability": 0.3
    },
    {
        "severity": "warning",
        "category": "security",
        "description": "Unusual traffic pattern detected on {interface}",
        "impact": "Possible security threat",
        "probability": 0.4
    }
]

def generate_synthetic_alarm(device=None, timestamp=None) -> Dict[str, Any]:
    """
    Generate a single synthetic alarm
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    # Select a random device if none specified
    if device is None:
        device = random.choice(TOPOLOGY_DATA["devices"])
    
    # Select a random alarm template
    template = random.choice(ALARM_TEMPLATES)
    
    # Get a random interface for the device
    interface = f"eth{random.randint(0, 3)}"
    
    # Fill in the template
    description = template["description"].format(interface=interface, device=device["id"])
    
    alarm = {
        "timestamp": timestamp.isoformat(),
        "alarm_id": f"ALARM-{random.randint(10000, 99999)}",
        "device_id": device["id"],
        "severity": template["severity"],
        "category": template["category"],
        "description": description,
        "impact": template["impact"],
        "status": "active",
        "acknowledged": False,
        "resolved": False
    }
    
    return alarm

def generate_storm_of_alarms(num_alarms: int = 10) -> List[Dict[str, Any]]:
    """
    Generate a storm of alarms with timestamps spread over time
    """
    alarms = []
    base_time = datetime.now() - timedelta(minutes=num_alarms)
    
    for i in range(num_alarms):
        # Spread the alarms over time
        timestamp = base_time + timedelta(seconds=i*30)
        
        # Randomly select a device for this alarm
        device = random.choice(TOPOLOGY_DATA["devices"])
        
        alarm = generate_synthetic_alarm(device, timestamp)
        alarms.append(alarm)
    
    return alarms

def generate_alarms_with_pattern(num_alarms: int = 10, pattern: str = "random") -> List[Dict[str, Any]]:
    """
    Generate alarms with specific patterns
    
    Args:
        num_alarms: Number of alarms to generate
        pattern: Pattern type - "random", "sequential", "burst"
    """
    if pattern == "burst":
        # All alarms happen at once
        return generate_storm_of_alarms(num_alarms)
    elif pattern == "sequential":
        # Alarms generated sequentially but with increasing severity
        alarms = []
        for i in range(num_alarms):
            timestamp = datetime.now() + timedelta(seconds=i*60)
            device = random.choice(TOPOLOGY_DATA["devices"])
            # Gradually increase severity
            severity_order = ["warning", "minor", "major", "critical"]
            severity = severity_order[i % len(severity_order)]
            
            # Modify template to match severity
            template = next(t for t in ALARM_TEMPLATES if t["severity"] == severity)
            interface = f"eth{random.randint(0, 3)}"
            description = template["description"].format(interface=interface, device=device["id"])
            
            alarm = {
                "timestamp": timestamp.isoformat(),
                "alarm_id": f"ALARM-{random.randint(10000, 99999)}",
                "device_id": device["id"],
                "severity": severity,
                "category": template["category"],
                "description": description,
                "impact": template["impact"],
                "status": "active",
                "acknowledged": False,
                "resolved": False
            }
            alarms.append(alarm)
        return alarms
    else:
        # Default to random pattern
        return generate_storm_of_alarms(num_alarms)

if __name__ == "__main__":
    # Test the alarm generator
    print("Generating 5 synthetic alarms:")
    alarms = generate_storm_of_alarms(5)
    for alarm in alarms:
        print(json.dumps(alarm, indent=2))