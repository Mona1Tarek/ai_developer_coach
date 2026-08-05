"""
Pydantic models for the local Python execution pipeline.

These models form the contract between the sandbox package (which validates
and executes Python code) and the rest of the application. The Tutor module,
for example, will consume :class:`ExecutionResult` to generate explanations
and debugging help without ever executing code itself.
"""

from pydantic import BaseModel, model_validator


class ValidationErrorDetail(BaseModel):
    """Structured, internal description of a single validation failure.

    This is an internal contract between the sandbox and the mapping layer
    (:func:`app.sandbox.validator.validation_user_messages` and
    :func:`app.sandbox.validator.validation_llm_payload`). For security-
    related failures (``blocked_import``, ``forbidden_function``) it may
    contain sandbox implementation details (e.g. restricted module or
    function names) that must never be exposed to the client or the LLM.

    Python-generated errors are stored as structured data (exception type,
    message, line, offset, source line, end position) so that the mapping
    layer can faithfully reproduce the interpreter's own output for humans
    and send clean structured data to the LLM — never a preformatted string.

    Attributes:
        error_type: Machine-readable failure category (``syntax``,
            ``empty``, ``too_long``, ``blocked_import``,
            ``forbidden_function``).
        line: Line number the failure was detected on, when available.
        offset: Column offset (1-based) the failure was detected at, when
            available (Python syntax errors).
        source_line: The offending source line text (Python syntax errors
            only), without trailing newline.
        end_line: End line of the highlighted range (Python syntax errors
            only), when available.
        end_offset: End column of the highlighted range (Python syntax
            errors only), when available.
        exception_type: Name of the originating Python exception (e.g.
            ``SyntaxError``, ``IndentationError``) when the failure is a
            Python-generated error.
        message: Original message of the originating Python exception.
        detail: Technical detail for backend logging and debugging. For
            non-security errors (``syntax``, ``empty``, ``too_long``) this
            is the original, non-sensitive message; for security errors it
            must never be exposed.
    """

    error_type: str
    line: int | None = None
    offset: int | None = None
    source_line: str | None = None
    end_line: int | None = None
    end_offset: int | None = None
    exception_type: str | None = None
    message: str | None = None
    detail: str = ""


class ValidationResult(BaseModel):
    """Internal outcome of validating a Python snippet before execution.

    ``errors`` holds structured, internal details intended for backend
    logging only. Derive user-facing messages with
    :func:`app.sandbox.validator.validation_user_messages` before exposing
    validation output to the client or the LLM.

    Attributes:
        valid: True if the snippet passed all static checks.
        errors: Structured internal details describing every failed check.
    """

    valid: bool
    errors: list[ValidationErrorDetail] = []


class ExecutionRequest(BaseModel):
    """Payload for requesting local execution of a Python snippet.

    Attributes:
        code: The Python source code to execute.
        timeout_seconds: Overrides the default sandbox timeout for this
            request. When None, the executor falls back to the configured
            sandbox default.
    """

    code: str
    timeout_seconds: float | None = None


class ExecutionResult(BaseModel):
    """Outcome of executing a Python snippet in the local sandbox.

    ``success`` is derived from the other fields by the model validator,
    guaranteeing the result is always internally consistent.

    Attributes:
        success: True if execution completed without timing out and exited
            with return code 0. Derived from the other fields by the model
            validator.
        stdout: Captured standard output of the executed code.
        stderr: Captured standard error of the executed code.
        return_code: Exit code of the subprocess, or None if it could not
            start or was killed by a timeout.
        execution_time_ms: Wall-clock execution time in milliseconds.
        timed_out: True if execution was terminated by the timeout.
        validation: The ValidationResult produced before execution, if the
            code was validated first. Enables a single object to describe
            the full pipeline.
    """

    success: bool = False
    stdout: str = ""
    stderr: str = ""
    return_code: int | None = None
    execution_time_ms: float = 0.0
    timed_out: bool = False
    validation: ValidationResult | None = None

    @model_validator(mode="after")
    def _derive_success(self) -> "ExecutionResult":
        self.success = not self.timed_out and self.return_code == 0
        return self
