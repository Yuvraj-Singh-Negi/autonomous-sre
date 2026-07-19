# Autonomous SRE

An autonomous multi-agent system for Site Reliability Engineering that detects backend failures, reads source code, identifies bugs, writes patches, applies them, and retests automatically.

## Architecture

```
HTTP Request → 500 Error → Monitor → Planner → Detective → Engineer → Patch File → Verifier → Run Integration Test → 200? Done / 500? Retry (max 3)
```

## Project Structure

```
autonomous-sre/
├── app/
│   ├── main.py              # FastAPI app with /crash endpoint
│   ├── buggy_service.py     # Buggy service (division by zero)
│   └── __init__.py
├── agents/
│   ├── planner.py           # Receives stack trace, identifies failing file/function/line
│   ├── detective.py         # Reads failing source, analyzes bug
│   ├── engineer.py          # Generates and applies code patch
│   ├── verifier.py          # Runs integration test, checks result
│   └── __init__.py
├── tools/
│   ├── file_tools.py        # read_file, patch_file
│   ├── integration.py       # run_integration_test (build, restart, call /crash)
│   └── __init__.py
├── prompts/
│   ├── detective.txt        # LLM prompt for detective agent
│   └── engineer.txt         # LLM prompt for engineer agent
├── orchestrator.py          # Coordinates the full pipeline
├── monitor.py               # Polls /crash, triggers orchestrator on 500
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Installation

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set your OpenAI API key (optional, fallback uses heuristic analysis):

```
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.5
```

## Usage

### Run the monitor (autonomous mode)

```bash
python monitor.py
```

This starts the buggy service, polls `/crash` for 500 errors, and runs the full SRE pipeline automatically.

### Run the orchestrator directly

```bash
python orchestrator.py
```

### Docker

```bash
docker-compose up --build
```

## How It Works

1. **Monitor** polls `GET /crash?count=0` and detects HTTP 500 (ZeroDivisionError)
2. **Planner** analyzes the stack trace to identify the failing file and function
3. **Detective** reads `buggy_service.py`, locates the bug (division by zero), reports old code
4. **Engineer** generates a patch (adds `if count == 0: return 0`) and applies it via `patch_file`
5. **Verifier** restarts the service and runs the integration test
6. If 200 → done. If 500 → retry (max 3)

## Demo Flow

1. Start: `python monitor.py`
2. Monitor triggers `/crash?count=0` → 500 (ZeroDivisionError)
3. Planner extracts failing file: `app/buggy_service.py`
4. Detective reads source → identifies division by zero at line 8
5. Engineer patches: adds zero-check before division
6. Verifier restarts service → `/crash?count=0` → 200
7. Pipeline reports success

## Retry Behavior

- Maximum 3 retries
- If all retries fail, the pipeline terminates with failure
- Each cycle: test → plan → detect → engineer → verify

## Limitations

- Currently handles only ZeroDivisionError in `buggy_service.py`
- LLM integration requires OpenAI API key (falls back to heuristic analysis)
- Docker support requires Docker daemon (falls back to local uvicorn)

## Future Improvements

- Support more error types (KeyError, AttributeError, TypeError)
- Container-based isolation for safe patching
- Git-based rollback with commit history
- Slack/email notifications
- Multi-service monitoring
