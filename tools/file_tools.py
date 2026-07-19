from pathlib import Path
import shutil

# Define the absolute sandbox root. The agent is strictly forbidden from leaving this folder.
# Change "app" to whatever directory your target service actually lives in.
WORKSPACE_ROOT = Path("app").resolve()

def _validate_and_jail_path(filepath: str) -> Path:
    """Ensures the filepath exists and is strictly inside the sandbox directory."""
    p = Path(filepath).resolve()
    
    # 1. Sandbox Jail Check
    if not p.is_relative_to(WORKSPACE_ROOT):
        raise PermissionError(
            f"[Security Violation] Agent attempted to escape sandbox: {filepath}. "
            f"Access strictly restricted to {WORKSPACE_ROOT}"
        )
        
    # 2. Existence Check
    if not p.exists():
        raise FileNotFoundError(f"File not found inside workspace: {filepath}")
        
    return p


def read_file(filepath: str) -> str:
    p = _validate_and_jail_path(filepath)
    return p.read_text(encoding="utf-8")


def patch_file(filepath: str, old_code: str, new_code: str) -> bool:
    p = _validate_and_jail_path(filepath)
    content = p.read_text(encoding="utf-8")

    # 1. Whitespace resilience check
    if old_code not in content:
        # Check if it was just a trailing/leading whitespace mismatch
        if old_code.strip() in content:
            raise ValueError(
                f"Patch failed in {filepath}: Exact match failed due to whitespace/indentation. "
                "Ensure you copy the exact whitespace from read_file."
            )
        return False

    if content.count(old_code) > 1:
        raise ValueError(
            f"Multiple matches for old_code in {filepath}. "
            "Include more surrounding lines in old_code to make the target unique."
        )

    # 2. CREATE BACKUP BEFORE MUTATING (The bulletproof rollback mechanism)
    backup_path = p.with_suffix(p.suffix + ".bak")
    shutil.copy(p, backup_path)

    # 3. Apply Patch
    new_content = content.replace(old_code, new_code, 1)
    p.write_text(new_content, encoding="utf-8")
    return True


def rollback_file(filepath: str, *args, **kwargs) -> bool:
    """
    Restores the file from its .bak backup created during patch_file.
    Accepts *args/**kwargs so it won't break if your orchestrator passes old_code/new_code arguments.
    """
    try:
        p = _validate_and_jail_path(filepath)
        backup_path = p.with_suffix(p.suffix + ".bak")
        
        if backup_path.exists():
            shutil.copy(backup_path, p)
            backup_path.unlink()  # Clean up the backup file
            print(f"[FileTools] Successfully rolled back {filepath} from backup.")
            return True
        else:
            print(f"[FileTools] No backup file (.bak) found for {filepath}. Rollback aborted.")
            return False
    except Exception as e:
        print(f"[FileTools] Rollback failed: {e}")
        return False
