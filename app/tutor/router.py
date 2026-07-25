from fastapi import APIRouter

from app.schemas.review import ReviewRequest, ReviewResponse
from app.tutor.python import review_python_code

router = APIRouter(prefix="/tutor", tags=["tutor"])


@router.post("/python/review", response_model=ReviewResponse)
async def python_review(body: ReviewRequest):
    return review_python_code(body.code)
