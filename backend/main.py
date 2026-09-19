"""
SDIT Tech-Bot — FastAPI Backend
Entry point. Defines all API routes.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import uuid
import time
import logging

try:
    from .config import settings
    from .rag import run_rag_pipeline
except ImportError:
    from config import settings
    from rag import run_rag_pipeline
from supabase import create_client

# ──────────────────────────────────────────────
# App setup
# ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sdit-techbot")

app = FastAPI(
    title="SDIT Tech-Bot API",
    description="AI-powered campus assistant for Shree Devi Institute of Technology",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_supabase = create_client(settings.supabase_url, settings.supabase_key)


# ──────────────────────────────────────────────
# Request / Response Models
# ──────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: str = Field(..., min_length=1, max_length=2000)
    user_type: Optional[str] = "student"  # student | faculty | visitor


class SourceItem(BaseModel):
    title: str
    source: str
    source_url: str
    similarity: float


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[SourceItem]
    response_time_ms: int


class FeedbackRequest(BaseModel):
    session_id: str
    question: str
    answer: str
    rating: int  # 1 = helpful, -1 = not helpful
    comment: Optional[str] = None


class ComplaintRequest(BaseModel):
    student_name: Optional[str] = None
    student_id: Optional[str] = None
    category: str  # academic | facility | hostel | other
    description: str = Field(..., min_length=10, max_length=2000)


# ──────────────────────────────────────────────
# In-memory session store (replace with Redis for production scale)
# ──────────────────────────────────────────────
_sessions: dict[str, list[dict]] = {}


# ──────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "SDIT Tech-Bot"}


# ──────────────────────────────────────────────
# Main chat endpoint
# ──────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    start = time.time()

    # Validate input
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Get or create session history
    session_id = req.session_id
    history = _sessions.get(session_id, [])

    try:
        # Run RAG pipeline
        answer, sources = await run_rag_pipeline(
            user_query=message,
            conversation_history=history,
        )
    except Exception as e:
        logger.error(f"RAG pipeline error: {e}")
        raise HTTPException(
            status_code=503,
            detail="The assistant is temporarily unavailable. Please try again in a moment, or call +91 9353619812 for immediate assistance.",
        )

    # Update session history (keep last 10 turns)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": answer})
    _sessions[session_id] = history[-10:]

    elapsed_ms = int((time.time() - start) * 1000)
    logger.info(f"[{session_id}] Query answered in {elapsed_ms}ms")

    return ChatResponse(
        session_id=session_id,
        answer=answer,
        sources=[SourceItem(**s) for s in sources],
        response_time_ms=elapsed_ms,
    )


# ──────────────────────────────────────────────
# Clear session / new conversation
# ──────────────────────────────────────────────
@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    _sessions.pop(session_id, None)
    return {"message": "Session cleared."}


# ──────────────────────────────────────────────
# Feedback endpoint
# ──────────────────────────────────────────────
@app.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    if req.rating not in (1, -1):
        raise HTTPException(status_code=400, detail="Rating must be 1 or -1.")
    try:
        _supabase.table("feedback").insert({
            "session_id": req.session_id,
            "question": req.question,
            "answer": req.answer,
            "rating": req.rating,
            "comment": req.comment,
        }).execute()
    except Exception as e:
        logger.error(f"Feedback save error: {e}")
        # Don't fail the user — feedback is non-critical
    return {"message": "Thank you for your feedback!"}


# ──────────────────────────────────────────────
# Complaint submission endpoint
# ──────────────────────────────────────────────
@app.post("/complaint")
async def submit_complaint(req: ComplaintRequest):
    valid_categories = {"academic", "facility", "hostel", "other"}
    if req.category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Category must be one of: {valid_categories}")
    try:
        _supabase.table("complaints").insert({
            "student_name": req.student_name,
            "student_id": req.student_id,
            "category": req.category,
            "description": req.description,
            "status": "submitted",
        }).execute()
    except Exception as e:
        logger.error(f"Complaint save error: {e}")
        raise HTTPException(status_code=503, detail="Could not save your complaint. Please try again or call the helpdesk.")
    return {"message": "Your complaint has been submitted. The college will review it and get back to you."}
