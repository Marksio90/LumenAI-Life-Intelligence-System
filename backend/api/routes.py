from fastapi import APIRouter
from core.state import GlobalState
from core.orchestrator import AgentOrchestrator

router = APIRouter()
state = GlobalState()
orch = AgentOrchestrator()

@router.get("/state")
def get_state():
    return state.export()

@router.post("/event")
def push_event(event: dict):
    state.add_event(event)
    return {"status": "event_received"}

@router.get("/agents")
def list_agents():
    return orch.list_agents()
