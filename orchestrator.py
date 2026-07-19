from agents.planner import plan
from agents.detective import investigate
from agents.engineer import fix as apply_fix
from agents.verifier import verify
from tools.integration import run_integration_test, stop_service
from tools.file_tools import read_file
import time
import json


MAX_RETRIES = 3


def run_pipeline(stack_trace: str) -> bool:
    retry = 0
    while retry < MAX_RETRIES:
        print(f"\n[Orchestrator] Cycle {retry + 1}/{MAX_RETRIES}")

        # Run integration test
        print("[Orchestrator] Running integration test...")
        test_result = run_integration_test()
        status = test_result.get("status", 500)
        logs = test_result.get("logs", "")

        if status == 200:
            print("[Orchestrator] Service is healthy!")
            return True

        print(f"[Orchestrator] Test failed with status {status}")

        # If we have a stack trace from the test, use it; otherwise use the passed one
        trace = logs or stack_trace

        # Planner
        print("[Planner] Analyzing stack trace...")
        planner_result = plan(trace)
        target_file = planner_result.get("target_file", "app/buggy_service.py")
        print(f"[Planner] Target: {target_file} | Reason: {planner_result.get('reason', 'Unknown')}")

        # Detective
        print("[Detective] Investigating source code...")
        detective_result = investigate(target_file, trace)
        print(f"[Detective] Problem: {detective_result.get('problem', 'Unknown')}")

        # Engineer
        print("[Engineer] Generating fix...")
        engineer_result = apply_fix(detective_result)
        if engineer_result.get("old_code"):
            print("[Engineer] Fix applied successfully")
        else:
            print("[Engineer] Fix generation failed")
            retry += 1
            time.sleep(2)
            continue

        # Verifier
        print("[Verifier] Running verification...")
        verifier_result = verify()
        if verifier_result.get("success"):
            print("[Verifier] Verification PASSED!")
            return True
        else:
            print("[Verifier] Verification FAILED")
            print(f"[Verifier] Logs: {verifier_result.get('logs', '')[:200]}")

        retry += 1
        time.sleep(2)

    print("[Orchestrator] Max retries reached. Pipeline failed.")
    return False


if __name__ == "__main__":
    import sys
    stack_trace = sys.argv[1] if len(sys.argv) > 1 else ""
    success = run_pipeline(stack_trace)
    print(f"\n[Orchestrator] Pipeline {'succeeded' if success else 'failed'}")
    stop_service()