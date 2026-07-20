import time
import http.client
import urllib.parse
from datetime import datetime
from pathlib import Path
from shutil import copyfile
from orchestrator import run_pipeline


TARGET_URL = "http://localhost:8000/crash"
BUGGY_FILE = Path("app/buggy_service.py")
BUGGY_TEMPLATE = Path("app/buggy_original.py")

HEALTHY_THRESHOLD = 5


def _reset_bug():
    copyfile(BUGGY_TEMPLATE, BUGGY_FILE)
    print("[Monitor] Buggy service reset to original buggy state")


def _restart_server():
    from tools.integration import restart_app_server
    restart_app_server()


def poll():
    print("[Monitor] Starting SRE monitor...")
    print(f"[Monitor] Polling {TARGET_URL}")

    from tools.integration import stop_service

    _reset_bug()
    _restart_server()

    consecutive_healthy = 0

    while True:
        try:
            parsed = urllib.parse.urlparse(TARGET_URL)
            conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 8000, timeout=10)
            conn.request("GET", "/crash?total=100&count=0")
            response = conn.getresponse()
            status = response.status
            body = response.read().decode("utf-8", errors="ignore")
            conn.close()

            timestamp = datetime.now().isoformat()
            print(f"[Monitor] {timestamp} - Status: {status}")

            if status >= 500:
                consecutive_healthy = 0
                print(f"[Monitor] Detected {status} error!")
                print(f"[Monitor] Running SRE pipeline...")

                success = run_pipeline(body)

                if success:
                    print("[Monitor] Pipeline succeeded, service is fixed!")
                    break
                else:
                    print("[Monitor] Pipeline failed after max retries")
                    break
            else:
                consecutive_healthy += 1
                if consecutive_healthy >= HEALTHY_THRESHOLD:
                    print(f"[Monitor] Service returned 200 for {HEALTHY_THRESHOLD} consecutive checks. No bug detected.")
                    print(f"[Monitor] Service is already healthy. Exiting.")
                    break

            time.sleep(10)

        except KeyboardInterrupt:
            print("[Monitor] Stopped by user")
            break
        except Exception as e:
            print(f"[Monitor] Error: {e}")
            time.sleep(5)

    stop_service()


if __name__ == "__main__":
    poll()