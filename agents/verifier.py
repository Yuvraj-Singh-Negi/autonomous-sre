from typing import Dict
from tools.integration import run_integration_test

def verify() -> Dict:
    """
    Runs the integration test suite and evaluates whether the bug is fixed.
    Returns structured results for the Orchestrator's state machine.
    """
    print("[Verifier] Executing live integration test against application endpoints...")
    test_results = run_integration_test()
    
    status = test_results.get("status", 500)
    logs = test_results.get("logs", "")
    success = test_results.get("success", False)
    
    if success:
        return {
            "success": True,
            "status": status,
            "logs": "Integration tests passed with HTTP 200 OK."
        }
    else:
        return {
            "success": False,
            "status": status,
            "logs": logs
        }
