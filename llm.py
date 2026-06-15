# llm.py - Qwen3-32B client with JSON parsing and thinking block stripping

import os
import json
import re
from openai import OpenAI

# Import config values
from config import VLLM_BASE_URL, MODEL_NAME

client = OpenAI(
    base_url=VLLM_BASE_URL,
    api_key="EMPTY"
)

def strip_think(text: str) -> str:
    """Remove the thinking block between 《思考》 and 《回答》 tags"""
    pattern = r"《思考》.*?《回答》"
    return re.sub(pattern, "", text, flags=re.DOTALL)

def parse_json(text: str) -> dict:
    """Strip thinking blocks and markdown fences, then parse JSON with one retry"""
    # First pass: strip thinking blocks and markdown
    clean_text = strip_think(text)
    clean_text = re.sub(r'```json.*?```', '', clean_text, flags=re.DOTALL).strip()
    
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        # Second pass: try to fix common issues
        fixed_text = clean_text.replace("'", '"').replace("None", "null")
        return json.loads(fixed_text)

def chat(
    messages: list,
    tools: list = None,
    response_format: dict = None,
    thinking: bool = True
) -> dict:
    """Send a chat request to vLLM with proper configuration"""
    extra_body = {}
    if not thinking:
        extra_body["chat_template_kwargs"] = {"enable_thinking": False}
    
    if response_format:
        extra_body["response_format"] = response_format

    return client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        tools=tools,
        response_format=response_format,
        extra_body=extra_body
    )

if __name__ == "__main__":
    # Test: Ask for JSON and verify parsing
    test_prompt = "Return this as JSON: {\"key\": \"value\"}"
    response = chat([
        {"role": "user", "content": test_prompt}
    ], thinking=False)
    
    parsed = parse_json(response.choices[0].message.content)
    print("Parsed JSON:", parsed)
