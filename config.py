# config.py - Central configuration for the NOC Copilot system

VLLM_BASE_URL = "http://localhost:8000/v1"
MODEL_NAME = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
CHROMA_DB_PATH = "./chroma_db"
TOPOLOGY_PATH = "data/topology.json"
ALARM_GENERATOR_MODULE = "data.alarm_generator"
