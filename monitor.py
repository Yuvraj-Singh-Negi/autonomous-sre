import time
import http.client
import urllib.parse
from datetime import datetime
from orchestrator import run_pipeline


TARGET_URL = "http://localhost:8000/crash"


def poll():
    print("[Monitor] Starting SRE monitor...")
    print(f"[Monitor] Polling {TARGET_URL}")

    from tools.integration import _ensure_service_running, stop_service

    # Ensure service is running
    if not _ensure_service_running():
        print("[Monitor] Failed to start service")
        return

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

            if status == 500:
                print(f"[Monitor] Detected 500 error!")
                print(f"[Monitor] Captured traceback")

                # Pass to orchestrator
                success = run_pipeline(body)

                if success:
                    print("[Monitor] Pipeline succeeded, service is fixed!")
                    break
                else:
                    print("[Monitor] Pipeline failed after max retries")
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