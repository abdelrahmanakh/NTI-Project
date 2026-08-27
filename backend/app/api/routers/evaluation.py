from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.dependencies import evaluator

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])

class EvalRequest(BaseModel):
    session_id: str

@router.post("/run")
async def run_evaluation(request: EvalRequest):
    try:
        results = evaluator.run_evaluation(session_id=request.session_id)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))