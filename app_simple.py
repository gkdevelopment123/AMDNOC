import gradio as gr
import time
import random
from datetime import datetime

# Simple CSS styling for the dashboard
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

def simulate_outage():
    """Simulate outage trigger"""
    return (
        "● 42 Active Alarms",
        "#FF3B6B", 
        "42"
    )

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
            correlation_graph = gr.HTML("<div style='height:300px;background:#f0f0f0;display:flex;align-items:center;justify-content:center;'>NetworkX Graph Visualization</div>")
            gr.HTML('<div class="card"><h3>ROOT CAUSE CARD</h3></div>')
            root_cause_card = gr.HTML('<div class="card"><div style="font-weight:bold;font-size:16px;margin-bottom:10px;">Root Cause Analysis</div><div>Router BGP session flap</div><div style="margin-top:10px;"><div style="display:flex;align-items:center;gap:8px;"><span style="font-weight:bold;">Confidence:</span><span style="font-family:JetBrains Mono;font-weight:bold;">87%</span></div></div></div>')
            with gr.Row():
                with gr.Column(scale=1):
                    gr.HTML('<div class="card"><h3>REMEDIATION ACTIONS</h3></div>')
                    remedy_actions = gr.HTML('<div class="card"><div>⏳ Reset BGP session</div><div>⏳ Check routing table</div></div>')
                with gr.Column(scale=1):
                    gr.HTML('<div class="card"><h3>SLA TIMER</h3></div>')
                    sla_timer = gr.HTML('<div class="sla-timer" style="font-size:28px;font-family:JetBrains Mono;font-weight:bold;color:#18C98D;">3600 sec</div>')
        
        # Right panel - Agent Pipeline Stepper (25%)
        with gr.Column(scale=2):
            gr.HTML('<div class="card"><h3>AGENT PIPELINE STEPPER</h3></div>')
            agent_stepper = gr.HTML('''
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
            ''')
            gr.HTML('<div class="card"><h3>ITSM TICKET CARD</h3></div>')
            ticket_card = gr.HTML('''
                <div class="card">
                    <div style="display:flex;justify-content:space-between;">
                        <div><strong>Ticket ID:</strong> INC-001</div>
                        <div style="color:#18C98D;font-weight:bold;">RESOLVED</div>
                    </div>
                    <div style="margin-top:10px;"><strong>Status:</strong> Resolved</div>
                    <div style="margin-top:10px;"><strong>Resolved At:</strong> 2024-01-15 14:30:00</div>
                </div>
            ''')
            gr.HTML('<div class="card"><h3>AUDIT LOG</h3></div>')
            audit_log = gr.HTML('''
                <div class="card">
                    <div style="font-family:JetBrains Mono;font-size:12px;margin-top:5px;">2024-01-15 14:28:45 - Alert received: BGP session flap</div>
                    <div style="font-family:JetBrains Mono;font-size:12px;margin-top:5px;">2024-01-15 14:28:46 - Correlation engine activated</div>
                    <div style="font-family:JetBrains Mono;font-size:12px;margin-top:5px;">2024-01-15 14:28:47 - Root cause identified: Router BGP session flap</div>
                    <div style="font-family:JetBrains Mono;font-size:12px;margin-top:5px;">2024-01-15 14:28:49 - Remediation started: Reset BGP session</div>
                </div>
            ''')
    
    # Simulate Outage Button
    simulate_btn = gr.Button("⚡ Simulate Outage", variant="primary")
    
    # Footer
    gr.HTML('<div class="footer">🔒 100% on-prem · AMD Instinct MI300X · Qwen3-32B · 0 external calls</div>')
    
    # Setup event handlers
    simulate_btn.click(
        fn=simulate_outage,
        inputs=[],
        outputs=[
            gr.components.HTML(),
            gr.components.HTML(),
            gr.components.HTML(),
        ]
    )

if __name__ == "__main__":
    try:
        # Launch the app with custom CSS
        app.queue().launch(server_name="0.0.0.0", server_port=7860, share=False, css=custom_css)
    except Exception as e:
        print(f"Error launching app: {e}")