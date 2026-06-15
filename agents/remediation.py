import json
from typing import Dict, List, Any
from llm import chat, parse_json, strip_think

def remediation_agent(root_cause: Dict[str, Any], incident: Dict[str, Any], available_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Remediation Agent - proposes remediation steps ranked by risk and decides which 
    automated actions to take based on risk level.
    
    Args:
        root_cause: The identified root cause from the Root Cause Analysis agent
        incident: The correlated incident information
        available_tools: List of available tools for remediation
        
    Returns:
        Dictionary containing remediation_plan, auto_executable_steps, approval_required_steps, and manual_fallback
    """
    
    # Prepare the system prompt based on PROMPTS.md
    system_prompt = f"""
You are the Remediation Agent in a Telecom NOC. Given a root cause, propose a
remediation plan and decide which automated actions to take.

Rules:
- Rank steps from lowest to highest risk. Prefer the least invasive fix that
  resolves the issue.
- Each step has a risk level: low, medium, high.
- "low" risk actions (e.g. clear a BGP session, restart an interface) may be
  auto-executed.
- "medium"/"high" risk actions (e.g. reboot a core router, failover) MUST be
  marked requires_approval=true and NOT auto-executed.
- Only call tools that exist in the provided tool list. Only use device IDs that
  appear in the incident's affected_devices.
- Always include a manual fallback step in case automation fails.

OUTPUT RULES:
- Respond with ONE valid JSON object and NOTHING else.
- No markdown code fences. No prose before or after. No explanation.
- If you are unsure, still return valid JSON with your best estimate.
- Do not include your reasoning in the output; keep it inside 〈think〉 only.

Root Cause: {root_cause.get('root_cause', 'No root cause provided')}
Incident Severity: {incident.get('severity', 'Unknown')}
Affected Devices: {incident.get('affected_devices', [])}
Available Tools: {available_tools}
"""

    # Construct user message with the required information
    user_message = f"""
Given the root cause "{root_cause.get('root_cause', 'Unknown')}" and the incident details:
- Affected devices: {incident.get('affected_devices', [])}
- Incident severity: {incident.get('severity', 'Unknown')}

Propose a remediation plan with steps ranked by risk level. Consider the available tools:
{json.dumps(available_tools, indent=2)}

Return a JSON response with:
1. A remediation_plan array with steps that include:
   - step (integer)
   - action (description)
   - tool (tool name if applicable)  
   - tool_args (arguments for the tool if applicable)
   - risk (low/medium/high)
   - requires_approval (boolean)
   - rationale (one sentence explanation)
2. auto_executable_steps (array of step numbers that can be auto-executed)
3. approval_required_steps (array of step numbers requiring human approval)
4. manual_fallback (string describing manual fallback step)
"""

    # Send request to LLM
    response = chat([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ], tools=available_tools, thinking=True)
    
    # Parse the response
    raw_response = response.choices[0].message.content
    cleaned_response = strip_think(raw_response)
    parsed_response = parse_json(cleaned_response)
    
    return parsed_response

# Example usage (for testing purposes)
if __name__ == "__main__":
    # Mock input data
    mock_root_cause = {
        "root_cause": "BGP session flap on core router",
        "confidence": 0.95,
        "evidence": ["BGP_PEER_DOWN alarm", "Router-Core-01"],
        "category": "software",
        "summary_for_ticket": "BGP session is flapping on core router"
    }
    
    mock_incident = {
        "incident_id": "INC-001",
        "root_event_alarm_id": "ALM-001",
        "member_alarm_ids": ["ALM-001", "ALM-002"],
        "affected_devices": ["Router-Core-01", "PE-Router-07"],
        "severity": "CRITICAL",
        "correlation_reason": "Core router BGP failure isolated downstream devices",
        "alarm_count": 2
    }
    
    mock_tools = [
        {
            "type": "function",
            "function": {
                "name": "clear_bgp",
                "description": "Clear/reset a BGP session on a device to recover from a flap.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string"},
                        "peer": {"type": "string", "description": "BGP peer IP"}
                    },
                    "required": ["device_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "restart_interface",
                "description": "Bounce (down/up) a network interface to clear a stuck link.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string"},
                        "interface": {"type": "string"}
                    },
                    "required": ["device_id", "interface"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "reset_router",
                "description": "HIGH RISK. Reboot a router. Requires human approval.",
                "parameters": {
                    "type": "object",
                    "properties": {"device_id": {"type": "string"}},
                    "required": ["device_id"]
                }
            }
        }
    ]
    
    # Run the agent
    result = remediation_agent(mock_root_cause, mock_incident, mock_tools)
    print(json.dumps(result, indent=2))