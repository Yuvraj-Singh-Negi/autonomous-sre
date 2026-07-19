import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from tools.file_tools import read_file


def _call_llm(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[Detective Error] OPENAI_API_KEY environment variable is missing.")
        return ""
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert software detective and log analyzer. You only output valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1 # Very low temp for analytical precision
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[Detective API Error] LLM generation failed: {e}")
        return ""


def _add_line_numbers(code: str) -> str:
    """Helper to give the LLM spatial awareness of exact line numbers."""
    lines = code.split('\n')
    return '\n'.join(f"{idx:4d} | {line}" for idx, line in enumerate(lines, 1))


def investigate(target_file: str, stack_trace: str, history: Optional[List[Dict]] = None) -> Dict:
    try:
        source_code = read_file(target_file)
    except Exception as e:
        print(f"[Detective Error] Could not read target file {target_file}: {e}")
        return {"file": target_file, "problem": f"File read error: {e}", "old_code": "", "suggested_fix": ""}

    # 1. FIX BACKWARDS LOG SLICING: Grab the TAIL of the logs where the actual error lives!
    tail_trace = stack_trace[-3000:] if len(stack_trace) > 3000 else stack_trace
    numbered_code = _add_line_numbers(source_code)

    # Format attempt history
    history_context = ""
    if history and len(history) > 0:
        history_context = "\n\nPREVIOUS FAILED DIAGNOSES & PATCHES (DO NOT REPEAT):\n"
        for idx, attempt in enumerate(history, 1):
            history_context += f"Attempt {idx} Failed Patch: `{attempt.get('attempted_code')}`\n"
            history_context += f"Resulting Error: {attempt.get('failure_reason')}\n---\n"

    prompt_path = Path("prompts/detective.txt")
    if prompt_path.exists():
        prompt_template = prompt_path.read_text(encoding="utf-8")
        prompt = prompt_template.replace("{stack_trace}", tail_trace)
        prompt = prompt.replace("{source_code}", numbered_code)
        prompt += history_context
    else:
        prompt = f"""Analyze this stack trace and source code to identify the exact root cause of the bug.

Stack trace (Tail end showing root cause):"""
