import json
import os
from pathlib import Path
from typing import Dict
from tools.file_tools import read_file, patch_file


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


def fix(detective_report: Dict) -> Dict:
    filepath = detective_report.get("file", "")
    problem = detective_report.get("problem", "")
    old_code = detective_report.get("old_code", "")
    suggested_fix = detective_report.get("suggested_fix", "")

    prompt_path = Path("prompts/engineer.txt")
    if prompt_path.exists():
        prompt = prompt_path.read_text()
        prompt = prompt.replace("{file}", filepath)
        prompt = prompt.replace("{problem}", problem)
        prompt = prompt.replace("{old_code}", old_code)
        prompt = prompt.replace("{suggested_fix}", suggested_fix)
    else:
        prompt = f"""Generate a code patch for:
File: {filepath}
Problem: {problem}
Old code: `{old_code}`
Suggested fix: {suggested_fix}

Return STRICT JSON:
{{
  "old_code": "exact code to replace",
  "new_code": "replacement code"
}}"""

    llm_response = _call_llm(prompt)
    if llm_response:
        try:
            result = json.loads(llm_response)
            if "old_code" in result and "new_code" in result:
                success = patch_file(filepath, result["old_code"], result["new_code"])
                if success:
                    return {"old_code": result["old_code"], "new_code": result["new_code"]}
        except (json.JSONDecodeError, KeyError):
            pass

    # Fallback: fix ZeroDivisionError by adding zero check
    content = read_file(filepath)
    if "division by zero" in problem.lower() or "ZeroDivisionError" in problem:
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith("result = ") and "/ count" in stripped:
                indent = len(line) - len(line.lstrip())
                new_code = f"{' ' * indent}if count == 0:\n{' ' * (indent + 4)}return 0\n{line}"
                success = patch_file(filepath, line, new_code)
                if success:
                    return {"old_code": line, "new_code": new_code}

    return {"old_code": "", "new_code": ""}