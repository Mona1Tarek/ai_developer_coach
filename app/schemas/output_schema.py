"""Pydantic output models for the execute-review pipeline.

The execute-review endpoint runs the user's code in the sandbox and asks the
LLM to explain the *actual* execution result. These models describe that
combined response. The request body is :class:`ExecutionRequest` (defined in
``execution_schema``); everything the client receives back is modeled here.
"""

from pydantic import BaseModel

from app.schemas.execution_schema import ExecutionResult


class Mistake(BaseModel):
    title: str
    explanation: str


class ErrorExplanation(BaseModel):
    error_type: str
    explanation: str


class Suggestion(BaseModel):
    title: str
    explanation: str


class ReviewResponse(BaseModel):
    """LLM-written review of the executed code."""

    errors_count: int = 0
    error_explanation: list[ErrorExplanation]
    mistakes: list[Mistake]
    strengths: list[str]
    suggestions: list[Suggestion]


class ExecutionResultInfo(BaseModel):
    """Execution facts reported back to the client.

    Mirrors :class:`ExecutionResult` but exposes wall-clock time in seconds
    (``execution_time``) to match the public contract of this endpoint.
    """

    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int | None = None
    execution_time: float = 0.0
    timed_out: bool = False

    @classmethod
    def from_execution_result(cls, result: ExecutionResult) -> "ExecutionResultInfo":
        """Build a response-ready snapshot from a sandbox execution result."""
        return cls(
            success=result.success,
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.return_code,
            execution_time=round(result.execution_time_ms / 1000.0, 3),
            timed_out=result.timed_out,
        )


class ValidationFeedback(BaseModel):
    """User-facing outcome of static validation.

    Carries only generic, sanitized messages produced by
    :func:`app.sandbox.validator.validation_user_messages`, so sandbox
    internals (restricted module/function names, validation rules, security
    policies) are never exposed to the client.

    Attributes:
        valid: True if the snippet passed all static checks.
        errors: Generic, human-readable reasons the snippet was rejected.
        validation_explanation: Optional LLM-written explanation of the
            validation outcome, intended to be educational. This is None when
            validation passes or the LLM pass is disabled.
    """

    valid: bool
    errors: list[str] = []
    validation_explanation: str | None = None


class ExecuteReviewResponse(BaseModel):
    """Combined execution + review result for ``POST /tutor/python/execute-review``.

    ``execution`` and ``review`` are None when static validation fails, in
    which case ``validation`` carries generic rejection reasons. When enabled,
    ``validation.validation_explanation`` holds an LLM-written, educational
    explanation of that failure; it is None when validation passes or the LLM
    pass is disabled.
    """

    validation: ValidationFeedback
    execution: ExecutionResultInfo | None = None
    review: ReviewResponse | None = None
