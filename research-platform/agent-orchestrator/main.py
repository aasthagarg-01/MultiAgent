# agent-orchestrator/main.py
import logging
import os
import sys
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from graph import research_graph, ResearchState
from config import Config

# Setup logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Orchestrator")

# Startup validation
@app.on_event("startup")
def startup_validation():
    """Validate environment and dependencies on startup."""
    logger.info("=== Agent Orchestrator Startup ===")
    
    if not Config.validate_on_startup():
        logger.critical("Environment validation failed - cannot start")
        sys.exit(1)
    
    if not research_graph:
        logger.critical("Research graph initialization failed - cannot start")
        sys.exit(1)
    
    logger.info("Startup validation passed")

# Request/Response models
class RunResearchRequest(BaseModel):
    task_id: str
    query: str

class RunResearchResponse(BaseModel):
    task_id: str
    status: str
    message: str
    error: Optional[str] = None

# Health check endpoint
@app.get("/health")
def health():
    return {"service": "orchestrator", "status": "ok"}

# Orchestration endpoint
@app.post("/run")
async def run_research(req: RunResearchRequest, background_tasks: BackgroundTasks):
    """
    Execute research workflow for a given query.
    Runs in background and updates task status via task-service.
    """
    if not research_graph:
        logger.error("Research graph not initialized")
        raise HTTPException(500, "Graph initialization failed")

    # Validate input
    if not req.query or not req.query.strip():
        raise HTTPException(400, "Query cannot be empty")

    try:
        # Initial state
        initial_state: ResearchState = {
            "task_id": req.task_id,
            "query": req.query,
            "subtasks": [],
            "retrieved": [],
            "web_results": [],
            "findings": [],
            "report": None,
            "status": "running",
            "error": None
        }

        # Run graph in background
        background_tasks.add_task(execute_research_workflow, initial_state)

        return RunResearchResponse(
            task_id=req.task_id,
            status="accepted",
            message="Research workflow started"
        )

    except Exception as e:
        logger.error(f"Failed to start research: {str(e)}")
        raise HTTPException(500, f"Failed to start research: {str(e)}")

async def execute_research_workflow(initial_state: ResearchState):
    """Execute the research workflow and update task status."""
    import httpx
    from datetime import datetime

    task_id = initial_state["task_id"]
    task_service_url = os.getenv("TASK_SERVICE_URL")

    try:
        # Execute the graph
        logger.info(f"Starting research workflow for task {task_id}")
        final_state = research_graph.invoke(initial_state)

        # Update task with results
        async with httpx.AsyncClient() as client:
            update_payload = {
                "status": "DONE",
                "report": final_state.get("report", "No report generated")
            }
            await client.patch(
                f"{task_service_url}/tasks/{task_id}",
                json=update_payload,
                timeout=10.0
            )
        logger.info(f"Task {task_id} completed successfully")

    except Exception as e:
        logger.error(f"Workflow error for task {task_id}: {str(e)}")
        try:
            async with httpx.AsyncClient() as client:
                update_payload = {
                    "status": "FAILED",
                    "report": f"Error: {str(e)}"
                }
                await client.patch(
                    f"{task_service_url}/tasks/{task_id}",
                    json=update_payload,
                    timeout=10.0
                )
        except Exception as update_error:
            logger.error(f"Failed to update task status: {str(update_error)}")