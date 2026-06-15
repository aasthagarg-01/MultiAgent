# agent-orchestrator/main.py
from fastapi import FastAPI
app = FastAPI(title="Agent Orchestrator")

@app.get("/health")
def health():
    return {"service": "orchestrator", "status": "ok"}