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
    """Remove the English thinking block between 〈think〉 and 〈/think〉 tags"""
    pattern = r"〈think〉.*?〈/think〉"
    return re.sub(pattern, "", text, flags=re.DOTALL)

def parse_json(text: str) -> dict:
    """Strip thinking blocks and markdown fences, then parse JSON with one retry"""
    # First pass: extract JSON content between braces
    clean_text = strip_think(text)
    # Ensure we have valid content to process
    if not clean_text:
        return {"error": "Empty response after stripping"}
    start_idx = clean_text.find('{')
    end_idx = clean_text.rfind('}')
    if start_idx != -1 and end_idx != -1:
        clean_text = clean_text[start_idx:end_idx+1]
    else:
        # Fallback if no braces found
        clean_text = text
    
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
    extra_body = {
        "chat_template_kwargs": {"enable_thinking": thinking}
    }

    kwargs = dict(
        model=MODEL_NAME,
        messages=messages,
        stream=False,
        extra_body=extra_body
    )

    if tools is not None:
        kwargs["tools"] = tools

    return client.chat.completions.create(**kwargs)

if __name__ == "__main__":
    # Test: Ask for JSON and verify parsing
    test_prompt = "Return this as JSON: {\"key\": \"value\"}"
    response = chat([
        {"role": "user", "content": test_prompt}
    ], thinking=False)
    
    parsed = parse_json(response.choices[0].message.content)
    print("Parsed JSON:", parsed)