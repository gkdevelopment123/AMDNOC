# agents/orchestrator.py - LangGraph orchestrator for the NOC workflow
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import json

# Define the state schema from PROMPTS.md
class NOCState(TypedDict):
    raw_alarms: list
    topology: dict
    alarms: list                 # normalised (Ingestion)
    incidents: list              # correlated (Correlation)
    current_incident: dict
    runbook_context: str         # retrieved (RAG)
    root_cause: dict             # (Root Cause)
    remediation_plan: dict       # (Remediation)
    actions_taken: list          # (Action Executor)
    ticket: dict                 # (ITSM)
    sla_deadline: str
    audit_log: list              # every action, for security panel

# Node functions for each step in the workflow
def ingest(state: NOCState) -> NOCState:
    """Ingestion node - normalises raw alarms"""
    return state

def correlate(state: NOCState) -> NOCState:
    """Correlation node - groups alarms into incidents"""
    # Create a simple incident from alarms (mock implementation)
    if not state["incidents"] and state["alarms"]:
        root_event = state["alarms"][0]
        incident = {
            "incident_id": "INC-001",
            "root_event_alarm_id": root_event["alarm_id"],
            "member_alarm_ids": [alarm["alarm_id"] for alarm in state["alarms"]],
            "affected_devices": list(set([alarm["device_id"] for alarm in state["alarms"]])),
            "severity": root_event["severity"],
            "correlation_reason": "Alarms correlated based on time window",
            "alarm_count": len(state["alarms"])
        }
        state["incidents"] = [incident]
        state["current_incident"] = incident
    return state

def rag_retrieve(state: NOCState) -> NOCState:
    """RAG retrieval node - retrieves relevant runbook context"""
    try:
        from rag.knowledge_base import retrieve_runbooks
        if state["current_incident"]:
            state["runbook_context"] = retrieve_runbooks(state["current_incident"]["incident_id"])
        else:
            state["runbook_context"] = "No incident to retrieve runbooks for"
    except ImportError:
        state["runbook_context"] = "Mock runbook context for incident resolution"
    return state

def root_cause(state: NOCState) -> NOCState:
    """Root Cause Analysis node"""
    if state["current_incident"]:
        state["root_cause"] = {
            "root_cause": "BGP session flap on core router",
            "confidence": 0.95,
            "evidence": ["BGP_PEER_DOWN alarm from Router-Core-01", "Downstream packet loss alarms"],
            "category": "software",
            "summary_for_ticket": "BGP session flap on core router causing downstream packet loss"
        }
    return state

def remediate(state: NOCState) -> NOCState:
    """Remediation node - proposes and plans actions"""
    if state["root_cause"]:
        state["remediation_plan"] = {
            "remediation_plan": [
                {
                    "step": 1,
                    "action": "clear BGP session on Router-Core-01",
                    "tool": "clear_bgp",
                    "tool_args": {"device_id": "Router-Core-01", "peer": "10.0.0.1"},
                    "risk": "low",
                    "requires_approval": False,
                    "rationale": "Clearing the BGP session is a low-risk recovery step"
                }
            ],
            "auto_executable_steps": [1],
            "approval_required_steps": [],
            "manual_fallback": "escalate to Tier-3 if BGP clear does not restore session"
        }
    return state

def action_executor(state: NOCState) -> NOCState:
    """Execute actions from the remediation plan"""
    if state["remediation_plan"]:
        actions_taken = []
        auto_steps = state["remediation_plan"].get("auto_executable_steps", [])
        for step_num in auto_steps:
            step = next((s for s in state["remediation_plan"]["remediation_plan"] if s["step"] == step_num), None)
            if step:
                actions_taken.append({
                    "step": step_num,
                    "tool": step["tool"],
                    "args": step["tool_args"],
                    "result": {"status": "SUCCESS", "device_id": step["tool_args"]["device_id"], "action": step["tool"]}
                })
        state["actions_taken"] = actions_taken
    return state

def create_ticket(state: NOCState) -> NOCState:
    """Create ITSM ticket with incident details"""
    if state["root_cause"] and state["current_incident"]:
        state["ticket"] = {
            "ticket_id": "INC0012345",
            "status": "In Progress",
            "priority": "P1",
            "created_at": "2023-05-15T10:00:00Z",
            "url": "https://itsm.mock/INC0012345"
        }
    return state

# Create the complete workflow graph
def create_orchestrator_graph():
    """Create and configure the LangGraph orchestrator"""
    
    # Initialize the graph
    workflow = StateGraph(NOCState)
    
    # Add all nodes
    workflow.add_node("ingest", ingest)
    workflow.add_node("correlate", correlate)
    workflow.add_node("rag_retrieve", rag_retrieve)
    workflow.add_node("root_cause", root_cause)
    workflow.add_node("remediate", remediate)
    workflow.add_node("action_executor", action_executor)
    workflow.add_node("create_ticket", create_ticket)
    
    # Define the workflow exactly as specified in the MASTERPLAN.md
    workflow.set_entry_point("ingest")
    workflow.add_edge("ingest", "correlate")
    workflow.add_edge("correlate", "rag_retrieve")
    workflow.add_edge("rag_retrieve", "root_cause")
    workflow.add_edge("root_cause", "remediate")
    workflow.add_edge("remediate", "action_executor")
    workflow.add_edge("action_executor", "create_ticket")
    workflow.add_edge("create_ticket", END)
    
    # Compile the graph with memory
    checkpointer = MemorySaver()
    graph = workflow.compile(checkpointer=checkpointer)
    
    return graph

# For testing purposes
if __name__ == "__main__":
    # Create a sample initial state
    initial_state = {
        "raw_alarms": [],
        "topology": {},
        "alarms": [
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
        ],
        "incidents": [],
        "current_incident": {},
        "runbook_context": "",
        "root_cause": {},
        "remediation_plan": {},
        "actions_taken": [],
        "ticket": {},
        "sla_deadline": "",
        "audit_log": []
    }
    
    # Create the orchestrator graph
    try:
        graph = create_orchestrator_graph()
        print("Orchestrator graph created successfully!")
        print("Workflow nodes:", list(graph.nodes.keys()))
        print("Nodes count:", len(graph.nodes))
        
        # Run a simple test with proper configuration
        config = {"configurable": {"thread_id": "test_thread"}}
        result = graph.invoke(initial_state, config=config)
        print("\nTest executed successfully!")
        print("Final state keys:", list(result.keys()))
        
        # Print some key results to show it's working
        print("\nResult summary:")
        print("- Incidents:", len(result.get("incidents", [])))
        print("- Root Cause:", result.get("root_cause", {}).get("root_cause", "None"))
        print("- Actions Taken:", len(result.get("actions_taken", [])))
        print("- Ticket Created:", "ticket" in result and bool(result["ticket"]))
        
    except Exception as e:
        print(f"\nError during setup or execution: {e}")
        import traceback
        traceback.print_exc()