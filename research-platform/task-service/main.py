# task-service/main.py
from fastapi import FastAPI
app = FastAPI(title="Task Service")

@app.get("/health")
def health():
    return {"service": "task-service", "status": "ok"}