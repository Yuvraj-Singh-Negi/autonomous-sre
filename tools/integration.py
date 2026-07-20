import time
import json
import http.client
import urllib.parse
import subprocess
import os
import signal
import socket
from pathlib import Path
from typing import Dict, Optional

_SERVICE_URL = os.getenv("SERVICE_URL", "http://localhost:8000")
_SERVICE_PROCESS: Optional[subprocess.Popen] = None
_SERVICE_FOUT = None
_SERVICE_FERR = None
LOG_STDOUT = Path("service_stdout.log")
LOG_STDERR = Path("service_stderr.log")


def _clear_logs():
    """Wipes old logs clean so the Detective never analyzes stale errors from Cycle 1."""
    LOG_STDOUT.write_text("", encoding="utf-8")
    LOG_STDERR.write_text("", encoding="utf-8")


def _kill_process_group():
    global _SERVICE_PROCESS, _SERVICE_FOUT, _SERVICE_FERR
    if _SERVICE_PROCESS:
        try:
            if os.name == 'posix':
                os.killpg(os.getpgid(_SERVICE_PROCESS.pid), signal.SIGKILL)
            else:
                _SERVICE_PROCESS.kill()
        except (OSError, ProcessLookupError):
            pass
        _SERVICE_PROCESS = None
    for fh in [_SERVICE_FOUT, _SERVICE_FERR]:
        if fh:
            try:
                fh.close()
            except Exception:
                pass
    _SERVICE_FOUT = None
    _SERVICE_FERR = None


def _ensure_service_running() -> bool:
    global _SERVICE_PROCESS, _SERVICE_FOUT, _SERVICE_FERR
    if _check_health():
        return True

    _clear_logs()
    try:
        _SERVICE_FOUT = open(LOG_STDOUT, "w", encoding="utf-8")
        _SERVICE_FERR = open(LOG_STDERR, "w", encoding="utf-8")

        _SERVICE_PROCESS = subprocess.Popen(
            ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=Path.cwd(),
            stdout=_SERVICE_FOUT,
            stderr=_SERVICE_FERR,
            start_new_session=True
        )

        deadline = time.time() + 5.0
        while time.time() < deadline:
            if _SERVICE_PROCESS.poll() is not None:
                print("[Integration] Uvicorn process died prematurely on startup.")
                return False
            if _check_health():
                print("[Integration] Uvicorn server warmed up and ready!")
                return True
            time.sleep(0.2)

        return _check_health()
    except Exception as e:
        print(f"[Integration Error] Failed to launch Uvicorn: {e}")
        return False


def _check_health() -> bool:
    try:
        parsed = urllib.parse.urlparse(_SERVICE_URL)
        conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 8000, timeout=1)
        conn.request("GET", "/health")
        response = conn.getresponse()
        response.read()
        conn.close()
        return response.status == 200
    except Exception:
        return False


def _get_logs() -> str:
    parts = []
    try:
        if LOG_STDERR.exists():
            content = LOG_STDERR.read_text(encoding="utf-8")
            if content.strip():
                parts.append("=== STDERR ===")
                parts.append(content)
    except Exception:
        pass
    try:
        if LOG_STDOUT.exists():
            content = LOG_STDOUT.read_text(encoding="utf-8")
            if content.strip():
                parts.append("=== STDOUT ===")
                parts.append(content)
    except Exception:
        pass
    return "\n".join(parts)


def run_integration_test() -> Dict:
    """Executes the test suite against the target endpoints and returns structured diagnostic logs."""
    if not _ensure_service_running():
        logs = _get_logs()
        return {
            "status": 500, 
            "logs": f"FATAL: Application failed to boot after patch.\nStartup Logs:\n{logs[-2000:]}",
            "success": False
        }

    try:
        conn = http.client.HTTPConnection("localhost", 8000, timeout=5)
        # Hit the buggy route
        conn.request("GET", "/crash?total=100&count=0")
        response = conn.getresponse()
        status = response.status
        body = response.read().decode("utf-8", errors="ignore")
        conn.close()

        logs = _get_logs()
        success = (status == 200)
        
        return {
            "status": status,
            "logs": body if body and status != 200 else logs[-2000:],
            "success": success
        }
    except Exception as e:
        logs = _get_logs()
        return {
            "status": 500,
            "logs": f"HTTP Connection failed: {e}\nServer Logs:\n{logs[-2000:]}",
            "success": False
        }


def restart_app_server() -> bool:
    print("[Integration] Stopping server for hot-reload...")
    _kill_process_group()

    deadline = time.time() + 5.0
    while time.time() < deadline:
        try:
            s = socket.create_connection(("localhost", 8000), timeout=0.5)
            s.close()
            time.sleep(0.2)
        except (ConnectionRefusedError, OSError):
            time.sleep(0.1)
            break

    return _ensure_service_running()


def stop_service():
    """Clean teardown for script exit."""
    _kill_process_group()
