import gradio as gr
import time
import random
import json
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import io
import base64
from collections import defaultdict

# Mock orchestrator for demonstration
class MockOrchestrator:
    def __init__(self):
        self.is_running = False
        self.current_incident = None
        self.alarm_count = 0
        
    def simulate_outage(self):
        self.is_running = True
        self.alarm_count = 42
        self.current_incident = {
            "id": "INC-001",
            "status": "active",
            "severity": "critical",
            "timestamp": datetime.now().isoformat(),
            "root_cause": "Router BGP session flap",
            "confidence": 87,
            "sla_remaining": 3600,
            "remediation_actions": [
                {"action": "Reset BGP session", "status": "pending"},
                {"action": "Check routing table", "status": "pending"}
            ]
        }
        return self.current_incident
    
    def get_status(self):
        return {
            "running": self.is_running,
            "incident": self.current_incident,
            "alarm_count": self.alarm_count
        }

# Initialize orchestrator
orchestrator = MockOrchestrator()

# CSS styling based on DESIGN_SPEC.md
custom_css = """
/* Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

/* Color Tokens */
:root {
    --bg-canvas: #F7F9FC;
    --bg-surface: #FFFFFF;
    --bg-elevated: #FDFEFF;
    --ink: #0F1B2D;
    --ink-soft: #5B6B82;
    --hairline: #E6ECF4;
    --brand-1: #4F6BFF;
    --brand-2: #7A5CFF;
    --brand-3: #00C2FF;
    --brand-grad: linear-gradient(120deg,#4F6BFF,#7A5CFF,#00C2FF);
    --critical: #FF3B6B;
    --major: #FF8A3D;
    --minor: #FFC23D;
    --healthy: #18C98D;
    --info: #00C2FF;
}

/* Base styles */
body {
    background-color: var(--bg-canvas);
    font-family: 'Inter', sans-serif;
    margin: 0;
    padding: 0;
    color: var(--ink);
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Space Grotesk', sans-serif;
}

/* Cards */
.card {
    background-color: var(--bg-surface);
    border-radius: 16px;
    box-shadow: 0 12px 32px rgba(79,107,255,.12);
    border: 1px solid var(--hairline);
    padding: 20px 24px;
    margin: 12px 0;
}

/* Severity Pills */
.severity-pill {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 9999px;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-family: 'Inter', sans-serif;
    color: white;
    margin-right: 8px;
    margin-bottom: 8px;
}

.critical-pill {
    background-color: var(--critical);
}

.major-pill {
    background-color: var(--major);
}

.minor-pill {
    background-color: var(--minor);
}

/* Confidence Ring */
.confidence-ring {
    width: 120px;
    height: 120px;
    position: relative;
    margin: 20px auto;
}

.confidence-circle {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    background: conic-gradient(
        var(--brand-grad) 0% 87%,
        #f0f0f0 87% 100%
    );
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.confidence-text {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-family: 'JetBrains Mono', monospace;
    font-size: 24px;
    font-weight: bold;
    color: var(--ink);
}

/* Agent Stepper */
.agent-stepper {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.agent-step {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    border-radius: 12px;
    background-color: var(--bg-elevated);
    transition: all 0.2s ease;
}

.agent-step.active {
    background-color: var(--brand-1);
    color: white;
}

.agent-step.completed {
    background-color: var(--healthy);
    color: white;
}

.agent-step.inactive {
    opacity: 0.6;
}

.agent-icon {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    font-weight: bold;
}

/* SLA Timer */
.sla-timer {
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 28px;
    font-weight: bold;
}

.sla-timer.warning {
    color: var(--major);
}

.sla-timer.success {
    color: var(--healthy);
}

/* Top Bar */
.top-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    background: linear-gradient(120deg, #4F6BFF, #7A5CFF, #00C2FF);
    color: white;
    border-radius: 0 0 16px 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.logo {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 24px;
}

.clock {
    font-family: 'JetBrains Mono', monospace;
    font-size: 18px;
}

.system-status {
    font-size: 14px;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 8px;
}

.status-indicator {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background-color: var(--healthy);
}

/* Alarm Feed */
.alarm-feed {
    max-height: 400px;
    overflow-y: auto;
}

/* Footer */
.footer {
    text-align: center;
    padding: 16px;
    font-size: 12px;
    color: var(--ink-soft);
    font-family: 'Inter', sans-serif;
    border-top: 1px solid var(--hairline);
    margin-top: 20px;
}

/* Animation for chaos to calm */
.chaos-animation {
    animation: chaosToCalm 8s ease-in-out infinite;
}

@keyframes chaosToCalm {
    0% { filter: hue-rotate(0deg); }
    25% { filter: hue-rotate(20deg); }
    50% { filter: hue-rotate(40deg); }
    75% { filter: hue-rotate(20deg); }
    100% { filter: hue-rotate(0deg); }
}

/* Responsive adjustments */
@media (max-width: 1200px) {
    .card {
        padding: 16px;
    }
}
"""

def update_clock():
    """Update the real-time clock"""
    return datetime.now().strftime("%H:%M:%S")

def generate_alarm_feed():
    """Generate mock alarm feed"""
    severities = ["critical", "major", "minor"]
    descriptions = [
        "BGP session flap",
        "Interface down",
        "High CPU utilization",
        "Memory threshold exceeded",
        "Link congestion",
        "Authentication failure",
        "Configuration drift",
        "Network partition",
        "Service degradation",
        "Bandwidth saturation"
    ]
    
    alarms = []
    for i in range(random.randint(10, 30)):
        severity = random.choice(severities)
        description = random.choice(descriptions)
        
        # Generate severity pill class
        pill_class = ""
        if severity == "critical":
            pill_class = "critical-pill"
        elif severity == "major":
            pill_class = "major-pill"
        else:
            pill_class = "minor-pill"
            
        alarm_html = f'''
        <div class="severity-pill {pill_class}">
            {severity.upper()} - {description}
        </div>
        '''
        alarms.append(alarm_html)
    
    return "".join(alarms)

def create_correlation_graph():
    """Create the correlation graph visualization"""
    # Create a NetworkX graph
    G = nx.Graph()
    
    # Add nodes (representing network devices)
    nodes = [
        "Router-1", "Router-2", "Switch-1", "Switch-2", 
        "Firewall-1", "Firewall-2", "Server-1", "Server-2",
        "LoadBalancer-1", "LoadBalancer-2", "Database-1", "Database-2"
    ]
    
    # Add edges (network connections)
    edges = [
        ("Router-1", "Switch-1"), ("Router-1", "Firewall-1"),
        ("Router-2", "Switch-2"), ("Router-2", "Firewall-2"),
        ("Switch-1", "Server-1"), ("Switch-1", "LoadBalancer-1"),
        ("Switch-2", "Server-2"), ("Switch-2", "LoadBalancer-2"),
        ("Firewall-1", "Database-1"), ("Firewall-2", "Database-2"),
        ("LoadBalancer-1", "Database-1"), ("LoadBalancer-2", "Database-2")
    ]
    
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)
    
    # Create positional layout
    pos = nx.spring_layout(G, k=1, iterations=50)
    
    # Draw the graph
    plt.figure(figsize=(8, 6), facecolor='#FFFFFF')
    ax = plt.gca()
    ax.set_facecolor('#FFFFFF')
    
    # Draw nodes with different colors based on their proximity to central point
    node_colors = []
    for node in G.nodes():
        node_x, node_y = pos[node]
        # Color based on distance from center
        distance_to_center = ((node_x - 0.5)**2 + (node_y - 0.5)**2)**0.5
        if distance_to_center < 0.5:
            node_colors.append('#18C98D')  # Healthy green
        elif distance_to_center < 0.7:
            node_colors.append('#FF8A3D')  # Major orange
        else:
            node_colors.append('#FF3B6B')  # Critical red
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color='#E6ECF4', alpha=0.7)
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, 
                          node_size=500, alpha=0.9)
    
    # Draw labels
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=8, 
                           font_family='JetBrains Mono')
    
    # Remove axes
    ax.set_axis_off()
    
    # Save to base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='#FFFFFF')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return f'<img src="data:image/png;base64,{img_str}" style="width:100%;height:auto;">'

def update_dashboard():
    """Update the entire dashboard"""
    status = orchestrator.get_status()
    
    # Update clock
    clock_text = update_clock()
    
    # Update alarm feed
    alarm_feed = generate_alarm_feed()
    
    # Update correlation graph (will be animated during outage)
    correlation_graph = create_correlation_graph()
    
    # Status indicator
    if status["running"]:
        status_text = f"● {status['alarm_count']} Active Alarms"
        status_color = "#FF3B6B"
    else:
        status_text = "● System Operational"
        status_color = "#18C98D"
    
    # Update agent stepper
    agent_stepper = '''
    <div class="agent-stepper">
        <div class="agent-step completed">
            <div class="agent-icon">1</div>
            <div>Ingest</div>
        </div>
        <div class="agent-step active">
            <div class="agent-icon">2</div>
            <div>Correlate</div>
        </div>
        <div class="agent-step inactive">
            <div class="agent-icon">3</div>
            <div>RCA</div>
        </div>
        <div class="agent-step inactive">
            <div class="agent-icon">4</div>
            <div>Remediate</div>
        </div>
    </div>
    '''
    
    # SLA Timer
    sla_timer = f'''
    <div class="sla-timer">
        {status['incident']['sla_remaining'] if status['incident'] else 3600} sec
    </div>
    '''
    
    # ITSM Ticket Card
    ticket_card = '''
    <div class="card">
        <div style="display:flex;justify-content:space-between;">
            <div><strong>Ticket ID:</strong> INC-001</div>
            <div style="color:#18C98D;font-weight:bold;">RESOLVED</div>
        </div>
        <div style="margin-top:10px;"><strong>Status:</strong> Resolved</div>
        <div style="margin-top:10px;"><strong>Resolved At:</strong> 2024-01-15 14:30:00</div>
    </div>
    '''
    
    # Audit Log Panel
    audit_log_entries = [
        "2024-01-15 14:28:45 - Alert received: BGP session flap",
        "2024-01-15 14:28:46 - Correlation engine activated",
        "2024-01-15 14:28:47 - Root cause identified: Router BGP session flap",
        "2024-01-15 14:28:49 - Remediation started: Reset BGP session",
        "2024-01-15 14:29:00 - Issue resolved: BGP session restored",
        "2024-01-15 14:29:05 - Ticket created: INC-001"
    ]
    
    audit_log_html = "<div>"
    for entry in audit_log_entries:
        audit_log_html += f"<div style='font-family:JetBrains Mono;font-size:12px;margin-top:5px;'>{entry}</div>"
    audit_log_html += "</div>"
    
    # Root Cause Card
    if status['incident']:
        root_cause_card = f'''
        <div class="card">
            <div style="font-weight:bold;font-size:16px;margin-bottom:10px;">Root Cause Analysis</div>
            <div>{status['incident']['root_cause']}</div>
            <div style="margin-top:10px;">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-weight:bold;">Confidence:</span>
                    <span style="font-family:JetBrains Mono;font-weight:bold;">{status['incident']['confidence']}%</span>
                </div>
            </div>
        </div>
        '''
    else:
        root_cause_card = '<div class="card">No active incident</div>'
    
    # Remedy Actions
    remedy_actions = '<div class="card">'
    if status['incident']:
        for action in status['incident']['remediation_actions']:
            status_icon = "⏳" if action['status'] == "pending" else "✅"
            remedy_actions += f"<div>{status_icon} {action['action']}</div>"
    else:
        remedy_actions += "<div>No active actions</div>"
    remedy_actions += "</div>"
    
    return (
        clock_text,
        alarm_feed,
        correlation_graph,
        agent_stepper,
        sla_timer,
        ticket_card,
        audit_log_html,
        root_cause_card,
        remedy_actions,
        status_text,
        status_color
    )

def simulate_outage():
    """Trigger the outage simulation"""
    incident = orchestrator.simulate_outage()
    return update_dashboard()

# Create Gradio app
with gr.Blocks() as app:
    
    # Top bar
    with gr.Row():
        with gr.Column(scale=1):
            gr.HTML("""
                <div class="top-bar">
                    <div class="logo">NOC Copilot</div>
                    <div class="clock" id="clock">Loading...</div>
                    <div class="system-status">
                        <div class="status-indicator"></div>
                        <span id="status-text">● System Operational</span>
                    </div>
                </div>
            """)
    
    # Main content area
    with gr.Row():
        # Left panel - Alarm Feed (30%)
        with gr.Column(scale=3):
            gr.HTML('<div class="card"><h3>ALARM FEED</h3></div>')
            alarm_feed = gr.HTML(elem_id="alarm-feed")
            gr.HTML('<div class="card" style="text-align:center;"><div style="font-size:24px;font-family:JetBrains Mono;font-weight:bold;">42</div><div>ACTIVE ALARMS</div></div>')
        
        # Center panel - Incident Correlation Graph (45%)
        with gr.Column(scale=4):
            gr.HTML('<div class="card"><h3>INCIDENT CORRELATION GRAPH</h3></div>')
            correlation_graph = gr.HTML(elem_id="correlation-graph")
            gr.HTML('<div class="card"><h3>ROOT CAUSE CARD</h3></div>')
            root_cause_card = gr.HTML(elem_id="root-cause-card")
            with gr.Row():
                with gr.Column(scale=1):
                    gr.HTML('<div class="card"><h3>REMEDIATION ACTIONS</h3></div>')
                    remedy_actions = gr.HTML(elem_id="remedy-actions")
                with gr.Column(scale=1):
                    gr.HTML('<div class="card"><h3>SLA TIMER</h3></div>')
                    sla_timer = gr.HTML(elem_id="sla-timer")
        
        # Right panel - Agent Pipeline Stepper (25%)
        with gr.Column(scale=2):
            gr.HTML('<div class="card"><h3>AGENT PIPELINE STEPPER</h3></div>')
            agent_stepper = gr.HTML(elem_id="agent-stepper")
            gr.HTML('<div class="card"><h3>ITSM TICKET CARD</h3></div>')
            ticket_card = gr.HTML(elem_id="ticket-card")
            gr.HTML('<div class="card"><h3>AUDIT LOG</h3></div>')
            audit_log = gr.HTML(elem_id="audit-log")
    
    # Simulate Outage Button
    simulate_btn = gr.Button("⚡ Simulate Outage", variant="primary")
    
    # Footer
    gr.HTML('<div class="footer">🔒 100% on-prem · AMD Instinct MI300X · Qwen3-32B · 0 external calls</div>')
    
    # Setup event handlers
    simulate_btn.click(
        fn=simulate_outage,
        inputs=[],
        outputs=[
            # Clock and status
            gr.components.HTML(),
            gr.components.HTML(),
            gr.components.HTML(),
            gr.components.HTML(),
            gr.components.HTML(),
            gr.components.HTML(),
            gr.components.HTML(),
            gr.components.HTML(),
            gr.components.HTML(),
            # Status text and color
            gr.components.HTML(),
            gr.components.HTML()
        ]
    )

if __name__ == "__main__":
    # Start with initial values
    try:
        # Launch the app with custom CSS
        app.queue().launch(server_name="0.0.0.0", server_port=7860, share=False, css=custom_css)
    except Exception as e:
        print(f"Error launching app: {e}")