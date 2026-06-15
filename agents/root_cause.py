# agents/root_cause.py - Root Cause Analysis Agent
import json
from llm import chat, parse_json, strip_think

def analyze_root_cause(incident: dict, alarms: list, runbook_context: str) -> dict:
    """
    Analyze the root cause of a correlated incident using LLM.
    
    Args:
        incident: The correlated incident data
        alarms: List of alarms in the incident
        runbook_context: Retrieved runbook passages
        
    Returns:
        Dictionary with root_cause, confidence, evidence, category, and summary_for_ticket
    """
    
    # Prepare the system prompt from PROMPTS.md
    system_prompt = """
You are the Root Cause Analysis Agent, a senior telecom network engineer. You
receive ONE correlated incident (a root event + its cascading alarms) and
relevant runbook excerpts retrieved from the knowledge base. Determine the most
likely ROOT CAUSE of the incident.

- Ground your reasoning in the provided runbooks; prefer documented causes over
  speculation.
- Give a confidence score between 0 and 1 reflecting how well the evidence
  supports your conclusion.
- List the specific pieces of evidence (alarm facts + runbook references) that
  led to your conclusion.
- If evidence is weak, say so with a low confidence score rather than guessing
  high.
"""

    # Add shared output rules
    output_rules = """
OUTPUT RULES:
- Respond with ONE valid JSON object and NOTHING else.
- No markdown code fences. No prose before or after. No explanation.
- If you are unsure, still return valid JSON with your best estimate.
- Do not include your reasoning in the output; keep it inside 〈think〉 only.
"""

    # Construct the user message
    user_message = f"""
Incident data:
{json.dumps(incident, indent=2)}

Alarms in this incident:
{json.dumps(alarms, indent=2)}

Runbook context:
{runbook_context}

Analyze the root cause of this incident and respond with the specified JSON format.
"""
    
    # Send to LLM
    response = chat([
        {"role": "system", "content": system_prompt + output_rules},
        {"role": "user", "content": user_message}
    ], thinking=True)
    
    # Parse the response
    raw_response = response.choices[0].message.content
    parsed_response = parse_json(raw_response)
    
    return parsed_response


if __name__ == "__main__":
    # Example usage
    sample_incident = {
        "incident_id": "INC-001",
        "root_event_alarm_id": "ALM-001",
        "member_alarm_ids": ["ALM-001", "ALM-002", "ALM-003"],
        "affected_devices": ["Router-Core-01", "PE-Router-07", "Switch-AGG-03"],
        "severity": "CRITICAL",
        "correlation_reason": "Core router BGP failure isolated downstream devices, causing cascading packet loss and link-down alarms.",
        "alarm_count": 3
    }

    sample_alarms = [
        {
            "alarm_id": "ALM-001",
            "timestamp": "2023-05-15T10:00:00Z",
            "device_id": "Router-Core-01",
            "device_type": "core",
            "site": "HQ-Datacenter",
            "alarm_type": "BGP_PEER_DOWN",
            "severity": "CRITICAL",
            "description": "BGP peer with 10.0.0.1 went down",
            "kpis": {"cpu": 95, "packet_loss": 0, "latency_ms": 0}
        },
        {
            "alarm_id": "ALM-002",
            "timestamp": "2023-05-15T10:00:30Z",
            "device_id": "PE-Router-07",
            "device_type": "pe",
            "site": "Branch-01",
            "alarm_type": "PACKET_LOSS",
            "severity": "MAJOR",
            "description": "Packet loss detected on interface Gi0/1",
            "kpis": {"cpu": 45, "packet_loss": 95, "latency_ms": 150}
        }
    ]

    sample_runbook = """
[Runbook: BGP Peer Down]
- Symptom: BGP peer goes down
- Possible causes: 
  1. Physical link failure
  2. Configuration mismatch
  3. Resource exhaustion on router
- Resolution steps:
  1. Check physical connectivity
  2. Verify BGP configuration
  3. Monitor resource usage
"""

    result = analyze_root_cause(sample_incident, sample_alarms, sample_runbook)
    print(json.dumps(result, indent=2))