from fastapi import APIRouter

from app.schemas.execution_schema import ExecutionRequest
from app.schemas.output_schema import ExecuteReviewResponse
from app.tutor.execution import execute_review

router = APIRouter(prefix="/tutor", tags=["tutor"])


@router.post("/python/execute-review", response_model=ExecuteReviewResponse)
async def python_execute_review(body: ExecutionRequest):
    return execute_review(body.code, timeout_seconds=body.timeout_seconds)
