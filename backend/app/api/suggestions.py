import time
from typing import Optional
from fastapi import APIRouter, Query

from ..models import SuggestionRequest, NlpQueryRequest, FeedbackRequest, SuggestionResponse, CommandSuggestion
from ..core.suggestion import suggestion_engine

router = APIRouter(prefix="/suggestions", tags=["Suggestions"])


@router.get("")
async def get_suggestions(
    prefix: str = Query(""),
    limit: int = Query(20, ge=1, le=100),
    session_id: str = Query("default"),
):
    start = time.time()
    results = suggestion_engine.get_suggestions(
        prefix=prefix,
        limit=limit,
        session_id=session_id,
    )
    elapsed_ms = (time.time() - start) * 1000
    return SuggestionResponse(
        suggestions=[CommandSuggestion(**r) for r in results],
        total=len(results),
        elapsed_ms=round(elapsed_ms, 2),
    )


@router.post("/nlp")
async def natural_language_query(req: NlpQueryRequest):
    start = time.time()
    results = suggestion_engine.natural_language_to_command(req.query)
    elapsed_ms = (time.time() - start) * 1000
    return SuggestionResponse(
        suggestions=[CommandSuggestion(**r) for r in results],
        total=len(results),
        elapsed_ms=round(elapsed_ms, 2),
    )


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    suggestion_engine.submit_feedback(
        command=req.command,
        useful=req.useful,
        reason=req.reason or "",
    )
    return {"message": "Feedback recorded", "command": req.command, "useful": req.useful}


@router.get("/collaborative")
async def get_collaborative_suggestions(limit: int = Query(10, ge=1, le=50)):
    start = time.time()
    results = suggestion_engine.get_collaborative_suggestions(limit=limit)
    elapsed_ms = (time.time() - start) * 1000
    return SuggestionResponse(
        suggestions=[CommandSuggestion(**r) for r in results],
        total=len(results),
        elapsed_ms=round(elapsed_ms, 2),
    )


@router.get("/history")
async def get_history(limit: int = Query(50, ge=1, le=200), category: Optional[str] = Query(None)):
    return suggestion_engine.get_history(limit=limit, category=category or "")


@router.get("/profile")
async def get_user_profile():
    return suggestion_engine.get_user_profile()
