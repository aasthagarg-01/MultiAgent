from fastapi import FastAPI
import httpx, os

app = FastAPI(title="Gateway Service")
TASK_SVC = os.getenv("TASK_SERVICE_URL")

@app.get("/health")
def health():
    return {"service": "gateway", "status": "ok"}

@app.get("/ping-task")
async def ping_task():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{TASK_SVC}/health")
    return {"gateway_called_task_service": r.json()}