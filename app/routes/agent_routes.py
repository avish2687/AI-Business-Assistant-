from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.db.base import get_db
from app.db.models import User, AgentSession
from app.services.auth_service import get_current_active_user
from app.services.agent_service import run_business_agent

router = APIRouter()


class AgentRequest(BaseModel):
    task: str = Field(
        ...,
        example="Analyze and create a full business plan for a cloud kitchen targeting office lunch in Pune"
    )
    business_type: str = Field(..., example="cloud kitchen")


class AgentResponse(BaseModel):
    session_id: str
    status: str
    message: str


def _run_agent_task(session_id: str, task: str, business_type: str, db: Session):
    """Background task: run agent and save results to DB."""
    session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    if not session:
        return
    try:
        result = run_business_agent(task, business_type)
        session.status = "completed"
        session.steps = result["steps_log"]
        session.final_output = result["final_report"]
        session.completed_at = datetime.now(timezone.utc)
    except Exception as e:
        session.status = "failed"
        session.error = str(e)
        session.completed_at = datetime.now(timezone.utc)
    finally:
        db.commit()


@router.post("/run", response_model=AgentResponse, status_code=202)
def run_agent(
    req: AgentRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Start autonomous business agent (runs in background).
    Returns session_id to poll for results.
    """
    session = AgentSession(
        user_id=current_user.id,
        task=req.task,
        status="running",
        steps=[],
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    background_tasks.add_task(
        _run_agent_task, session.id, req.task, req.business_type, db
    )

    return {
        "session_id": session.id,
        "status": "running",
        "message": "Agent started. Poll /api/agent/status/{session_id} for results.",
    }


@router.get("/status/{session_id}")
def get_agent_status(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Poll agent session status and results."""
    session = db.query(AgentSession).filter(
        AgentSession.id == session_id,
        AgentSession.user_id == current_user.id,
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.id,
        "status": session.status,
        "task": session.task,
        "steps_completed": len(session.steps or []),
        "steps": session.steps,
        "final_output": session.final_output,
        "error": session.error,
        "created_at": str(session.created_at),
        "completed_at": str(session.completed_at) if session.completed_at else None,
    }


@router.get("/sessions")
def list_sessions(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all agent sessions for the current user."""
    sessions = (
        db.query(AgentSession)
        .filter(AgentSession.user_id == current_user.id)
        .order_by(AgentSession.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "session_id": s.id,
            "task": s.task[:100] + "..." if len(s.task) > 100 else s.task,
            "status": s.status,
            "created_at": str(s.created_at),
        }
        for s in sessions
    ]


@router.post("/run-sync")
def run_agent_sync(
    req: AgentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Run agent synchronously (waits for completion).
    Use for testing or short tasks only.
    """
    try:
        result = run_business_agent(req.task, req.business_type)

        session = AgentSession(
            user_id=current_user.id,
            task=req.task,
            status="completed",
            steps=result["steps_log"],
            final_output=result["final_report"],
            completed_at=datetime.now(timezone.utc),
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        return {
            "session_id": session.id,
            "status": "completed",
            "final_report": result["final_report"],
            "tools_used": result["tools_used"],
            "steps_log": result["steps_log"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
