from agents.planner import plan
from agents.detective import investigate
from agents.engineer import fix as apply_fix
from agents.verifier import verify
from tools.integration import restart_app_server
from tools.file_tools import rollback_file

MAX_RETRIES = 3

def run_pipeline(initial_trace: str) -> bool:
    retry = 0
    current_trace = initial_trace
    # 1. MEMORY: Keep track of failed attempts to feed back into the agents
    attempt_history = [] 

    while retry < MAX_RETRIES:
        print(f"\n[Orchestrator] Cycle {retry + 1}/{MAX_RETRIES}")

        # Planner (Now receives history so it doesn't repeat mistakes!)
        print("[Planner] Analyzing stack trace...")
        planner_result = plan(current_trace, history=attempt_history)
        target_file = planner_result.get("target_file", "app/buggy_service.py")
        print(f"[Planner] Target: {target_file} | Reason: {planner_result.get('reason')}")

        # Detective
        print("[Detective] Investigating source code...")
        detective_result = investigate(target_file, current_trace, history=attempt_history)
        print(f"[Detective] Problem: {detective_result.get('problem')}")

        # Engineer
        print("[Engineer] Generating fix...")
        engineer_result = apply_fix(detective_result, history=attempt_history)
        
        if not engineer_result.get("old_code"):
            print("[Engineer] Fix generation failed. Retrying...")
            retry += 1
            continue

        print("[Engineer] Fix applied to disk.")

        # 2. RACE CONDITION FIX: Force server restart and wait for warm-up
        print("[Orchestrator] Restarting application server to apply patch...")
        restart_app_server()

        # Verifier
        print("[Verifier] Running verification test suite...")
        verifier_result = verify()

        if verifier_result.get("success"):
            print("[Verifier] Verification PASSED! Bug eradicated.")
            return True
        else:
            print("[Verifier] Verification FAILED.")
            new_logs = verifier_result.get("logs", "")
            print(f"[Verifier] New Error: {new_logs[:200]}")

            # 3. ROLLBACK: Revert the bad patch so the next attempt starts from clean state
            print(f"[Orchestrator] Rolling back failed patch on {target_file}...")
            rollback_file(target_file)
            restart_app_server()

            # Record failure in memory
            attempt_history.append({
                "cycle": retry + 1,
                "attempted_code": engineer_result.get("new_code"),
                "failure_reason": new_logs
            })

            # Update trace to the latest error
            current_trace = new_logs or current_trace
            retry += 1

    print("[Orchestrator] Max retries reached. System hard-failing to human alert.")
    return False
