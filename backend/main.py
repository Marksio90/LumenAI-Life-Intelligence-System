from fastapi import FastAPI
from api.routes import router as api_router
from core.orchestrator import AgentOrchestrator

app = FastAPI(title="Aurora AI Backend", version="1.0")

# Inicjalizacja głównego orchestratora
orchestrator = AgentOrchestrator()

@app.on_event("startup")
async def startup_event():
    print("🔄 Starting Aurora backend...")
    await orchestrator.start()

@app.on_event("shutdown")
async def shutdown_event():
    print("🔻 Stopping Aurora backend...")
    await orchestrator.stop()

# Routing API
app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {"status": "running", "agents": orchestrator.list_agents()}
