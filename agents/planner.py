import json
import os
from typing import Dict, List, Optional


def _call_llm(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[Planner Warning] OPENAI_API_KEY not set, using heuristic fallback")
        return ""
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert SRE planner. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[Planner API Error] {e}")
        return ""


def plan(stack_trace: str, history: Optional[List[Dict]] = None) -> Dict:
    prompt = f"""Analyze this stack trace and identify the failing file, function, and line.

Stack trace:
```
{stack_trace[:2000]}
```

Return STRICT JSON only:
{{
  "target_file": "relative/path/to/file.py",
  "reason": "Brief description of the failure",
  "next_agent": "detective"
}}"""

    llm_response = _call_llm(prompt)
    if llm_response:
        try:
            return json.loads(llm_response)
        except (json.JSONDecodeError, KeyError):
            pass

    # Fallback: extract info from traceback directly
    lines = stack_trace.split('\n')
    target_file = "app/buggy_service.py"
    reason = "Unknown failure"

    for line in lines:
        if "buggy_service.py" in line and "line" in line:
            target_file = "app/buggy_service.py"
            reason = f"Error in {line.strip()}"
            break
        if "app/" in line and "line" in line:
            parts = line.strip().split(',')
            for p in parts:
                p = p.strip()
                if p.startswith("File "):
                    fstart = p.find('"')
                    fend = p.rfind('"')
                    if fstart != -1 and fend != -1:
                        target_file = p[fstart+1:fend]

    if "ZeroDivisionError" in stack_trace:
        reason = "ZeroDivisionError - division by zero"
    elif "KeyError" in stack_trace:
        reason = "KeyError - missing dictionary key"
    elif "AttributeError" in stack_trace:
        reason = "AttributeError - accessing missing attribute"
    elif "TypeError" in stack_trace:
        reason = "TypeError - invalid operation"

    return {
        "target_file": target_file,
        "reason": reason,
        "next_agent": "detective"
    }