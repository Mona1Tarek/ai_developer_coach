"""Execute-review service: run code in the sandbox, then ask the LLM to
explain the actual execution result.

This service is framework-independent: it knows nothing about FastAPI. It
reuses the existing sandbox (validator, executor) and the LLM plumbing, and
orchestrates the pipeline described below.
"""

import json
import logging

from app.config.settings import settings
from app.sandbox.python_executor import execute_python_code
from app.sandbox.validator import (
    validate_python_code,
    validation_llm_payload,
    validation_user_messages,
)
from app.schemas.execution_review_schema import (
    ExecuteReviewResponse,
    ExecutionResultInfo,
    ValidationFeedback,
)
from app.schemas.execution_schema import ExecutionResult
from app.schemas.review_schema import ReviewResponse
from app.tutor.utils import (
    call_model_and_parse_json,
    call_model_text,
    load_system_prompt,
)

logger = logging.getLogger(__name__)

_EXECUTION_SYSTEM_PROMPT = "python_execution_system.yaml"
_VALIDATION_SYSTEM_PROMPT = "python_validation_explanation.yaml"


def execute_review(
    code: str,
    timeout_seconds: float | None = None,
) -> ExecuteReviewResponse:
    """Validate, execute, and review a Python snippet end to end.

    Pipeline: validate -> (short-circuit on failure) -> execute ->
    build_prompt -> generate_response -> combine -> return.

    On validation failure the internal (structured) error details are logged
    for debugging only. Users receive interpreter-style output for
    Python-generated failures, the original message for platform non-security
    failures, and generic messages for platform security failures
    (:func:`validation_user_messages`). The LLM receives a separate payload
    (:func:`validation_llm_payload`): structured exception data for
    Python-generated failures, the original message for platform
    non-security failures, and generic messages for platform security
    failures. Raw internal validation errors are never exposed.

    Args:
        code: Python source code to validate and execute.
        timeout_seconds: Optional override of the sandbox timeout.

    Returns:
        An ExecuteReviewResponse. When static validation fails, ``execution``
        and ``review`` are left empty and, unless disabled, the LLM explains
        the validation failure via ``validation.validation_explanation``.
    """
    validation = validate_python_code(code)
    if not validation.valid:
        logger.warning(
            "Snippet rejected by static validation: %s",
            [detail.model_dump() for detail in validation.errors],
        )
        user_messages = validation_user_messages(validation)
        llm_payload = validation_llm_payload(validation)
        return ExecuteReviewResponse(
            validation=ValidationFeedback(
                valid=False,
                errors=user_messages,
                validation_explanation=explain_validation_failure(code, llm_payload),
            ),
        )

    result = execute_python_code(code, timeout_seconds=timeout_seconds)

    system_prompt = load_system_prompt(_EXECUTION_SYSTEM_PROMPT)
    user_prompt = build_execution_review_prompt(code, result)
    data = call_model_and_parse_json(system_prompt, user_prompt)
    review = ReviewResponse.model_validate(data)

    return ExecuteReviewResponse(
        validation=ValidationFeedback(valid=True, errors=[]),
        execution=ExecutionResultInfo.from_execution_result(result),
        review=review,
    )


def explain_validation_failure(
    code: str,
    payload: list[dict | str],
) -> str | None:
    """Ask the LLM to explain a static validation failure, if worthwhile.

    Only the mapped ``payload`` is sent to the LLM — never the raw internal
    validation details. The payload carries structured exception data for
    Python-generated failures, the original message for platform non-security
    failures, and a generic summary for platform security failures. Returns
    None when the LLM pass is disabled or the failure is trivial (empty code,
    code too long) — those messages are already self-explanatory and do not
    justify an LLM call.
    """
    if not settings.explain_validation_errors:
        return None
    if _is_trivial_failure(code):
        return None

    system_prompt = load_system_prompt(_VALIDATION_SYSTEM_PROMPT)
    user_prompt = build_validation_explanation_prompt(code, payload)
    return call_model_text(system_prompt, user_prompt)


def build_validation_explanation_prompt(
    code: str,
    payload: list[dict | str],
) -> str:
    """Compose the user prompt for explaining a validation failure.

    The prompt carries the learner's own code plus the LLM-facing validation
    payload: structured exception data for Python-generated errors, original
    messages for platform validation errors, or generic summaries for
    platform security errors. It deliberately omits internal validation
    details and never includes the human-facing interpreter output.
    """
    sections = [
        "The code below was NOT executed. It was rejected by a static validator.",
        "The validation problem below is one of: structured Python exception data, "
        "an original non-sensitive platform validation message, or a generic summary "
        "of a platform security restriction.",
        "Explain it educationally without revealing any internal implementation details.",
        "",
        "=== ORIGINAL PYTHON CODE ===",
        code,
        "",
    ]
    for item in payload:
        if isinstance(item, dict):
            sections.append("=== EXCEPTION DATA (structured) ===")
            sections.append(json.dumps(item, indent=2))
        else:
            sections.append("=== VALIDATION MESSAGE ===")
            sections.append(item)
    return "\n".join(sections)


def _is_trivial_failure(code: str) -> bool:
    """Return True for failures whose validation message is already clear."""
    return not code.strip() or len(code) > settings.sandbox_max_code_length


def build_execution_review_prompt(code: str, result: ExecutionResult) -> str:
    """Compose the user prompt from the code and its execution facts.

    The prompt makes the source of truth explicit so the model explains the
    real outcome instead of guessing runtime behavior.
    """
    sections = [
        "The code below was executed in an isolated sandbox.",
        "Use the execution result as the source of truth.",
        "",
        "=== ORIGINAL PYTHON CODE ===",
        code,
        "",
        "=== VALIDATION RESULT ===",
        "Passed all static checks (syntax, blocked imports, forbidden functions).",
        "",
        "=== EXECUTION SUCCESS ===",
        "Yes" if result.success else "No",
        "",
        "=== RETURN CODE ===",
        str(result.return_code) if result.return_code is not None else "(n/a)",
        "",
        "=== EXECUTION TIME ===",
        f"{result.execution_time_ms / 1000.0:.3f} seconds",
        "",
        "=== TIMED OUT ===",
        "Yes" if result.timed_out else "No",
        "",
        "=== STDOUT ===",
        result.stdout or "(no output)",
        "",
        "=== STDERR ===",
        result.stderr or "(no errors)",
    ]
    return "\n".join(sections)
