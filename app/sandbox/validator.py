"""
AST-based static validation of Python snippets before execution.

The validator is purely static (it never executes code) and distinguishes
exactly three categories of validation errors, the architectural boundary
for this module:

1. **Python-generated** — raised by the Python parser (today the
   ``SyntaxError`` family). Handled generically: the original exception's own
   interpreter output goes to the user; its structured fields go to the LLM.
2. **Platform non-security** (``empty``, ``too_long``) — original message.
3. **Platform security** (``blocked_import``, ``forbidden_function``) — only
   generic sanitized messages; raw internal details stay for logging.

Public mapping layer:
- :func:`validation_user_messages` → client-safe messages.
- :func:`validation_llm_payload` → structured data sent to the LLM.
"""

import ast
import logging
import traceback

from app.config.settings import settings
from app.sandbox.security import BLOCKED_MODULES, DANGEROUS_FUNCTIONS
from app.schemas.execution_schema import ValidationErrorDetail, ValidationResult

logger = logging.getLogger(__name__)

_SUBMITTED_FILENAME = "<submitted_code>"

# The three validation error categories. Every downstream branch inspects this
# split — never a specific exception type. See the module docstring.
PYTHON_ERROR_CATEGORY = "python"
PLATFORM_NON_SECURITY_TYPES = frozenset({"empty", "too_long"})
PLATFORM_SECURITY_TYPES = frozenset({"blocked_import", "forbidden_function"})

_SECURITY_USER_MESSAGES: dict[str, str] = {
    "blocked_import": (
        "Your code imports one or more modules that are not available in this execution environment."
    ),
    "forbidden_function": (
        "Your code uses one or more functions that are not available in this execution environment."
    ),
}

_FALLBACK_MESSAGE = (
    "Your code could not be validated. Please review it and try again."
)


def validate_python_code(code: str) -> ValidationResult:
    """Validate a Python snippet without executing it.

    Checks in order: not empty, not too long, valid syntax, no blocked
    imports or dangerous function calls.

    Args:
        code: The Python source code to validate.

    Returns:
        A ValidationResult with structured ValidationErrorDetail entries
        belonging to one of the three error categories.
    """
    if not code.strip():
        return ValidationResult(
            valid=False,
            errors=[ValidationErrorDetail(error_type="empty", detail="Code is empty.")],
        )

    if len(code) > settings.sandbox_max_code_length:
        return ValidationResult(
            valid=False,
            errors=[
                ValidationErrorDetail(
                    error_type="too_long",
                    detail=(
                        f"Code exceeds the maximum allowed length of "
                        f"{settings.sandbox_max_code_length} characters."
                    ),
                )
            ],
        )

    try:
        tree = ast.parse(code, filename=_SUBMITTED_FILENAME)
    except SyntaxError as exc:
        # ast.parse raises the SyntaxError family (e.g. SyntaxError,
        # IndentationError). We catch it here and map it into the generic
        # Python-generated validation-exception category used downstream.
        logger.debug("Rejected snippet due to a Python-generated error: %s", exc.msg)
        return ValidationResult(
            valid=False,
            errors=[_python_exception_detail(exc)],
        )

    errors = _check_forbidden_nodes(tree)

    if errors:
        logger.warning("Rejected snippet with %d validation error(s)", len(errors))
    return ValidationResult(valid=not errors, errors=errors)


def validation_user_messages(validation: ValidationResult) -> list[str]:
    """Map internal validation details to client-safe user messages.

    Python-generated validation exceptions use the preserved interpreter
    output; non-security errors surface their ``detail`` verbatim; security
    errors use one generic message per category. Not the representation sent
    to the LLM.
    """
    messages: list[str] = []
    reported_security_types: set[str] = set()
    for detail in validation.errors:
        if detail.error_type == PYTHON_ERROR_CATEGORY:
            messages.append(_python_exception_user_message(detail))
            continue

        if detail.error_type in PLATFORM_NON_SECURITY_TYPES:
            messages.append(detail.detail)
            continue

        if detail.error_type in PLATFORM_SECURITY_TYPES:
            if detail.error_type in reported_security_types:
                continue
            reported_security_types.add(detail.error_type)
            template = _SECURITY_USER_MESSAGES.get(detail.error_type)
            if template is None:
                logger.warning(
                    "Unknown security error_type '%s'; using fallback message.",
                    detail.error_type,
                )
                messages.append(_FALLBACK_MESSAGE)
                continue
            messages.append(template)
            continue

        logger.warning(
            "Unknown validation error_type '%s'; using fallback message.",
            detail.error_type,
        )
        messages.append(_FALLBACK_MESSAGE)
    return messages


def validation_llm_payload(validation: ValidationResult) -> list[dict | str]:
    """Map internal validation details to data sent to the LLM.

    Python-generated validation exceptions become a structured dict (never
    formatted output); non-security errors become their original message;
    security errors become the same generic sanitized message as the user
    gets.
    """
    payload: list[dict | str] = []
    for detail in validation.errors:
        if detail.error_type == PYTHON_ERROR_CATEGORY:
            payload.append(_python_exception_llm_data(detail))
            continue

        if detail.error_type in PLATFORM_NON_SECURITY_TYPES:
            payload.append(detail.detail)
            continue

        if detail.error_type in PLATFORM_SECURITY_TYPES:
            payload.append(
                _SECURITY_USER_MESSAGES.get(detail.error_type) or _FALLBACK_MESSAGE
            )
            continue

        payload.append(_FALLBACK_MESSAGE)
    return payload


def _python_exception_detail(exc: SyntaxError) -> ValidationErrorDetail:
    """Internal representation of a Python-generated validation exception.

    Stores the original exception's structured fields for the LLM and its own
    interpreter output (Python's own formatting of the original exception)
    for the user. Written against the generic concept: today the parser
    raises the ``SyntaxError`` family, but the builder does not depend on
    that. Nothing is reconstructed.
    """
    return ValidationErrorDetail(
        error_type=PYTHON_ERROR_CATEGORY,
        exception_type=exc.__class__.__name__,
        message=exc.msg or "",
        line=exc.lineno,
        offset=exc.offset,
        source_line=(exc.text or "").rstrip("\n") or None,
        end_line=getattr(exc, "end_lineno", None),
        end_offset=getattr(exc, "end_offset", None),
        detail=_format_python_exception(exc),
    )


def _python_exception_user_message(detail: ValidationErrorDetail) -> str:
    """Return the preserved interpreter output of a Python-generated validation exception.

    Rendered from the original exception at raise time and stored verbatim in
    ``detail``.
    """
    return detail.detail


def _format_python_exception(exc: Exception) -> str:
    """Render a Python-generated validation exception as the interpreter would.

    Uses Python's own ``traceback.format_exception_only``, which is generic
    over any exception; the filename is already normalized because parsing
    ran with ``_SUBMITTED_FILENAME``.
    """
    return "".join(traceback.format_exception_only(type(exc), exc)).rstrip("\n")


def _python_exception_llm_data(detail: ValidationErrorDetail) -> dict:
    """Structured data for the LLM from a Python-generated validation exception (never formatted output)."""
    return {
        "exception_type": detail.exception_type,
        "message": detail.message,
        "line": detail.line,
        "column": detail.offset,
        "offset": detail.offset,
        "source_line": detail.source_line,
    }


def _check_forbidden_nodes(tree: ast.AST) -> list[ValidationErrorDetail]:
    """Collect internal details for every forbidden construct.

    Covers blocked imports (``import x``, ``from x import y``, including
    submodules) and direct calls to dangerous functions.
    """
    errors: list[ValidationErrorDetail] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".")[0]
                if module in BLOCKED_MODULES:
                    errors.append(
                        ValidationErrorDetail(
                            error_type="blocked_import",
                            line=node.lineno,
                            detail=f"Import of blocked module '{module}'.",
                        )
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            module = node.module.split(".")[0]
            if module in BLOCKED_MODULES:
                errors.append(
                    ValidationErrorDetail(
                        error_type="blocked_import",
                        line=node.lineno,
                        detail=f"Import of blocked module '{module}'.",
                    )
                )
        elif isinstance(node, ast.Call):
            name = _called_function_name(node.func)
            if name in DANGEROUS_FUNCTIONS:
                errors.append(
                    ValidationErrorDetail(
                        error_type="forbidden_function",
                        line=node.lineno,
                        detail=f"Call to forbidden function '{name}'.",
                    )
                )

    return errors


def _called_function_name(func: ast.AST) -> str | None:
    """Resolve an AST call target's name (plain or ``builtins.``-prefixed)."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        if func.value.id == "builtins":
            return func.attr
    return None
