from fastapi import APIRouter

from app.schemas.execution_review_schema import ExecuteReviewResponse
from app.schemas.execution_schema import ExecutionRequest
from app.schemas.review_schema import ReviewRequest, ReviewResponse
from app.tutor.execution import execute_review
from app.tutor.python import review_python_code

router = APIRouter(prefix="/tutor", tags=["tutor"])


@router.post("/python/review", response_model=ReviewResponse)
async def python_review(body: ReviewRequest):
    return review_python_code(body.code)


@router.post("/python/execute-review", response_model=ExecuteReviewResponse)
async def python_execute_review(body: ExecutionRequest):
    return execute_review(body.code, timeout_seconds=body.timeout_seconds)
