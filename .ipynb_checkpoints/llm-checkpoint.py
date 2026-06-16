# llm.py - Shared LLM client for the NOC Copilot
# Talks ONLY to the local vLLM endpoint (internal, no external APIs).
# Handles Qwen3-32B's <think>...</think> blocks and robust JSON extraction.

import json
import re
from openai import OpenAI
from config import VLLM_BASE_URL, MODEL_NAME, API_KEY

client = OpenAI(base_url=VLLM_BASE_URL, api_key=API_KEY)


def strip_think(text: str) -> str:
    """Remove <think>...</think> reasoning blocks that Qwen3 emits.

    Handles the normal case, plus a dangling </think> with no opening tag
    (which can happen when generation is cut off).
    """
    if not text:
        return ""
    # Remove well-formed <think>...</think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # If a stray closing tag remains, drop everything before it
    if "</think>" in text:
        text = text.split("</think>")[-1]
    # Drop any leftover lone opening tag
    text = text.replace("<think>", "")
    return text.strip()


def _extract_json_blob(text: str) -> str:
    """Pull the most likely JSON object/array substring out of free text."""
    text = text.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()

    # Find the outermost { } or [ ]
    first_obj, last_obj = text.find("{"), text.rfind("}")
    first_arr, last_arr = text.find("["), text.rfind("]")

    candidates = []
    if first_obj != -1 and last_obj != -1 and last_obj > first_obj:
        candidates.append(text[first_obj:last_obj + 1])
    if first_arr != -1 and last_arr != -1 and last_arr > first_arr:
        candidates.append(text[first_arr:last_arr + 1])

    # Prefer the longer candidate (usually the full structure)
    if candidates:
        return max(candidates, key=len)
    return text


def parse_json(text: str):
    """Strip thinking blocks + fences, then parse JSON. One repair retry."""
    clean = strip_think(text)
    blob = _extract_json_blob(clean)
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        # Repair pass: common LLM JSON mistakes
        repaired = blob
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)   # trailing commas
        repaired = repaired.replace("'", '"')                # single quotes
        repaired = re.sub(r"\bNone\b", "null", repaired)
        repaired = re.sub(r"\bTrue\b", "true", repaired)
        repaired = re.sub(r"\bFalse\b", "false", repaired)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Could not parse JSON from model output.\n"
                f"--- cleaned text ---\n{clean[:800]}\n--- error ---\n{e}"
            )


def chat(messages, tools=None, thinking=False, temperature=0.3, max_tokens=4000):
    """Send a chat request to the local vLLM and return the message object.

    thinking=False is the default: faster and cleaner JSON for agent work.
    Pass tools=[...] to enable native tool-calling (Remediation agent).
    """
    extra_body = {"chat_template_kwargs": {"enable_thinking": thinking}}

    kwargs = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "extra_body": extra_body,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message


def ask_json(system_prompt, user_payload, thinking=False, temperature=0.2):
    """Convenience: send a system + user(JSON) message, return parsed JSON dict.

    user_payload may be a dict (auto-serialised) or a string.
    """
    if isinstance(user_payload, (dict, list)):
        user_content = json.dumps(user_payload, indent=2)
    else:
        user_content = str(user_payload)

    msg = chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        thinking=thinking,
        temperature=temperature,
    )
    return parse_json(msg.content)


if __name__ == "__main__":
    # Foundation test: prove think-stripping + JSON parsing round-trips cleanly.
    print("Test 1: thinking disabled")
    out = ask_json(
        "You output only JSON. No prose.",
        'Return exactly this JSON: {"status": "ok", "value": 42}',
    )
    print("  Parsed:", out)
    assert out.get("status") == "ok", "unexpected output"

    print("Test 2: strip_think on a synthetic thinking block")
    sample = '<think>Let me think about this carefully...</think>\n{"answer": "clean"}'
    print("  Parsed:", parse_json(sample))
    assert parse_json(sample)["answer"] == "clean"

    print("\nAll foundation tests passed. llm.py is working.")