"""
Pydantic models for the execute-review pipeline.

The execute-review endpoint runs the user's code in the sandbox and asks the
LLM to explain the *actual* execution result. These models describe that
combined response. Existing schemas are reused where possible: the request
body is :class:`ExecutionRequest`, the ``review`` block is
:class:`ReviewResponse`, and validation output is exposed to the client as
the sanitized :class:`ValidationFeedback`.
"""

from pydantic import BaseModel

from app.schemas.execution_schema import ExecutionResult
from app.schemas.review_schema import ReviewResponse


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
    """

    valid: bool
    errors: list[str] = []


class ExecuteReviewResponse(BaseModel):
    """Combined execution + review result for ``POST /tutor/python/execute-review``.

    ``execution`` and ``review`` are None when static validation fails, in
    which case ``validation`` carries generic rejection reasons. When enabled,
    ``validation_explanation`` holds an LLM-written, educational explanation
    of that failure; it is None when validation passes or the LLM pass is
    disabled.
    """

    validation: ValidationFeedback
    execution: ExecutionResultInfo | None = None
    review: ReviewResponse | None = None
    validation_explanation: str | None = None
