import time
import json
import http.client
import urllib.parse
import subprocess
from pathlib import Path
from typing import Dict, Optional


_SERVICE_URL = "http://localhost:8000"
_SERVICE_PROCESS: Optional[subprocess.Popen] = None


def _ensure_service_running() -> bool:
    global _SERVICE_PROCESS
    if _check_health():
        return True
    try:
        with open("service_stdout.log", "a") as fout, open("service_stderr.log", "a") as ferr:
            _SERVICE_PROCESS = subprocess.Popen(
                ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
                cwd=Path.cwd(),
                stdout=fout,
                stderr=ferr,
                start_new_session=True
            )
        time.sleep(3)
        if _SERVICE_PROCESS.poll() is not None:
            return False
        return _check_health()
    except Exception:
        return False


def _check_health() -> bool:
    try:
        parsed = urllib.parse.urlparse(_SERVICE_URL)
        conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 8000, timeout=5)
        conn.request("GET", "/health")
        response = conn.getresponse()
        response.read()
        conn.close()
        return response.status == 200
    except Exception:
        return False


def _get_logs() -> str:
    try:
        with open("service_stderr.log", "r") as f:
            return f.read()
    except Exception:
        return ""


def run_integration_test() -> Dict:
    _ensure_service_running()
    try:
        conn = http.client.HTTPConnection("localhost", 8000, timeout=10)
        conn.request("GET", "/crash?total=100&count=0")
        response = conn.getresponse()
        status = response.status
        body = response.read().decode("utf-8", errors="ignore")
        conn.close()
        logs = _get_logs()
        return {"status": status, "logs": body or logs[-2000:]}
    except Exception as e:
        return {"status": 500, "logs": f"Connection failed: {e}"}


def restart_service() -> bool:
    global _SERVICE_PROCESS
    if _SERVICE_PROCESS:
        try:
            _SERVICE_PROCESS.terminate()
            _SERVICE_PROCESS.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _SERVICE_PROCESS.kill()
        _SERVICE_PROCESS = None
    # Wait for port to be free
    import socket
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            s = socket.create_connection(("localhost", 8000), timeout=1)
            s.close()
            time.sleep(1)
        except (ConnectionRefusedError, OSError):
            break
    return _ensure_service_running()


def stop_service():
    global _SERVICE_PROCESS
    if _SERVICE_PROCESS:
        try:
            _SERVICE_PROCESS.terminate()
            _SERVICE_PROCESS.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _SERVICE_PROCESS.kill()
        _SERVICE_PROCESS = None