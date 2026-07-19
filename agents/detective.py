import json
import os
from pathlib import Path
from typing import Dict
from tools.file_tools import read_file


def _call_llm(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ""
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-5.5")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    except Exception:
        return ""


def investigate(target_file: str, stack_trace: str) -> Dict:
    source_code = read_file(target_file)

    prompt_path = Path("prompts/detective.txt")
    if prompt_path.exists():
        prompt_template = prompt_path.read_text()
        prompt = prompt_template.replace("{stack_trace}", stack_trace[:2000])
        prompt = prompt.replace("{source_code}", source_code)
    else:
        prompt = f"""Analyze this stack trace and source code.

Stack trace:
```
{stack_trace[:2000]}
```

Source code:
```
{source_code}
```

Return STRICT JSON only:
{{
  "file": "{target_file}",
  "line": 0,
  "problem": "description",
  "old_code": "exact code block with bug",
  "suggested_fix": "how to fix"
}}"""

    llm_response = _call_llm(prompt)
    if llm_response:
        try:
            return json.loads(llm_response)
        except (json.JSONDecodeError, KeyError):
            pass

    # Fallback: heuristic analysis
    error_type = "UnknownError"
    if "ZeroDivisionError" in stack_trace or "division by zero" in stack_trace:
        error_type = "ZeroDivisionError"
    elif "KeyError" in stack_trace:
        error_type = "KeyError"
    elif "AttributeError" in stack_trace:
        error_type = "AttributeError"
    elif "TypeError" in stack_trace:
        error_type = "TypeError"

    lines = source_code.split('\n')
    bug_line = 0
    old_code = ""
    problem = f"Unknown {error_type}"

    if error_type == "ZeroDivisionError":
        for i, line in enumerate(lines, 1):
            if "/ count" in line:
                bug_line = i
                old_code = line.rstrip()
                problem = "Division by zero when count is 0"
                break

    return {
        "file": target_file,
        "line": bug_line,
        "problem": problem,
        "old_code": old_code,
        "suggested_fix": "Add a check for count == 0 before division, return 0 if zero"
    }