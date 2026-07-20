from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from app.buggy_service import process_data, validate_input
import traceback
import logging

app = FastAPI(title="Buggy Service", version="1.0.0")
logger = logging.getLogger("buggy-service")


@app.get("/crash")
async def crash_endpoint(total: int = 100, count: int = 0):
    data = {"total": total, "count": count}

    if not validate_input(data):
        raise HTTPException(status_code=400, detail="Invalid input")

    result = process_data(data)
    return {"result": result}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error("Unhandled exception:\n%s", tb)
    return JSONResponse(
        status_code=500,
        content={"error": type(exc).__name__, "detail": str(exc), "traceback": tb}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)