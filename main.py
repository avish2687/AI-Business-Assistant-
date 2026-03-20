from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.routes.ai_routes import router as ai_router
from app.routes.rag_routes import router as rag_router
from app.routes.auth_routes import router as auth_router
from app.routes.agent_routes import router as agent_router
from app.db.base import create_tables

app = FastAPI(
    title="AI Business Assistant",
    description="AI-powered business platform with RAG, Auth, and Autonomous Agents",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables on startup
@app.on_event("startup")
def on_startup():
    create_tables()

# Mount static files for frontend
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router,  prefix="/api/auth",  tags=["Authentication"])
app.include_router(ai_router,    prefix="/api/ai",    tags=["AI Content Generation"])
app.include_router(rag_router,   prefix="/api/rag",   tags=["RAG Q&A"])
app.include_router(agent_router, prefix="/api/agent", tags=["Autonomous Agent"])

@app.get("/")
def root():
    # Serve dashboard if it exists
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "AI Business Assistant v2.0 is running!", "docs": "/docs"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0"}
