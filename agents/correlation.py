# agents/correlation.py - Correlation Agent for collapsing alarm storms
import json
from typing import List, Dict, Any
from llm import chat, parse_json, strip_think

SYSTEM_PROMPT = """
You are the Correlation Agent in a Telecom NOC. You receive a list of normalised
alarms that arrived in a short time window. Many are symptoms of the SAME
underlying fault. Your job:
1. Group alarms that belong to the same incident, using device topology,
   timing, and causal patterns (e.g. a core router failure causes downstream
   BGP, link, and packet-loss alarms on connected devices).
2. Identify the single ROOT EVENT alarm — the earliest, highest-in-topology,
   most-causal alarm that best explains the rest.
3. Mark every other alarm as a cascading effect of that root.

You will be given the network topology to reason about device relationships.
Be decisive: collapse aggressively into as few incidents as the evidence
supports. A storm of 40 alarms is usually 1–2 real incidents.

OUTPUT RULES:
- Respond with ONE valid JSON object and NOTHING else.
- No markdown code fences. No prose before or after. No explanation.
- If you are unsure, still return valid JSON with your best estimate.
- Do not include your reasoning in the output; keep it inside 〈think〉 only.
"""

def correlate_alarms(alarms: List[Dict[str, Any]], topology: Dict[str, Any]) -> Dict[str, Any]:
    """Main function to correlate alarms into incidents using LLM"""
    
    # Sort alarms by timestamp to establish temporal order
    sorted_alarms = sorted(alarms, key=lambda x: x['timestamp'])
    
    # Prepare the prompt for the LLM
    prompt = f"""
    You are given a list of alarms and network topology. 
    Alarms: {json.dumps(sorted_alarms, indent=2)}
    Topology: {json.dumps(topology, indent=2)}
    
    Group alarms into incidents based on device topology, timing, and causal relationships.
    Identify the root event for each incident, and mark others as cascading effects.
    Return the result in the EXACT JSON format specified:
    {{
      "incidents": [
        {{
          "incident_id": "string",
          "root_event_alarm_id": "string",
          "member_alarm_ids": ["string"],
          "affected_devices": ["string"],
          "severity": "CRITICAL|MAJOR|MINOR|WARNING",
          "correlation_reason": "string",
          "alarm_count": integer
        }}
      ]
    }}
    """
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    
    # Call the LLM with thinking enabled
    response = chat(messages, thinking=True)
    
    # Parse the response using our helper functions
    raw_response = response.choices[0].message.content
    clean_response = strip_think(raw_response)
    parsed_response = parse_json(clean_response)
    
    return parsed_response