from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from app.buggy_service import process_data, validate_input
import traceback

app = FastAPI(title="Buggy Service", version="1.0.0")


class CrashRequest(BaseModel):
    total: int
    count: int


@app.get("/crash")
async def crash_endpoint(total: int = 100, count: int = 0):
    """Endpoint that intentionally crashes with division by zero."""
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
    """Return traceback for debugging."""
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return Response(content=tb, status_code=500, media_type="text/plain")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)