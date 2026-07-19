from pathlib import Path


def read_file(filepath: str) -> str:
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    return p.read_text()


def patch_file(filepath: str, old_code: str, new_code: str) -> bool:
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    content = p.read_text()
    if old_code not in content:
        return False
    if content.count(old_code) > 1:
        raise ValueError(f"Multiple matches for old_code in {filepath}")
    new_content = content.replace(old_code, new_code, 1)
    p.write_text(new_content)
    return True