import json
from typing import Dict
from tools.integration import run_integration_test, restart_service


def verify() -> Dict:
    restart_service()
    import time
    time.sleep(3)

    result = run_integration_test()
    status = result.get("status", 500)

    if status == 200:
        return {"success": True}
    else:
        logs = result.get("logs", "")
        return {"success": False, "logs": logs[-2000:]}