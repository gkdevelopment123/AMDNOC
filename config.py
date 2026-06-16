# config.py - Central configuration for the NOC Copilot system

VLLM_BASE_URL = "http://localhost:8000/v1"
MODEL_NAME = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
API_KEY = "EMPTY"

# Service ports
ROUTER_API_PORT = 8001
ITSM_API_PORT = 8002
DASHBOARD_PORT = 7860

ROUTER_API_URL = f"http://localhost:{ROUTER_API_PORT}"
ITSM_API_URL = f"http://localhost:{ITSM_API_PORT}"

# Paths
CHROMA_DB_PATH = "./chroma_db"
TOPOLOGY_PATH = "data/topology.json"
RUNBOOKS_PATH = "data/runbooks"

# SLA (seconds) - the breach window for the demo
SLA_SECONDS = 300