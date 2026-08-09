# AI Developer Coach

An AI-powered developer coaching assistant that helps learners improve their Python code. Users submit a Python snippet; the service statically validates it, executes it in an isolated sandbox, and uses an LLM to explain the **actual** execution result — turning real runtime behavior into an educational, code-review-style lesson.

Built with FastAPI, Pydantic, and the OpenAI-compatible SDK (currently supporting Groq and Mistral).

## Features

- **Execute-then-review pipeline** — code is really run in an isolated sandbox, and the LLM explains the real output, not a guess about runtime behavior.
- **Static, AST-based validation** — rejects empty/oversized snippets, syntax errors, blocked imports, and dangerous function calls *before* execution.
- **Hardened sandbox** — code runs in a short-lived subprocess with a configurable timeout; blocked modules (`os`, `subprocess`, `socket`, `eval`, `exec`, ...) are rejected statically.
- **Security-aware error surfacing** — internal validation details and sandbox internals are never exposed to the client or the LLM; users get sanitized, educational messages.
- **LLM-written review** — structured feedback with counted runtime errors, error explanations, mistakes, strengths, and concrete improvement suggestions.
- **Multi-provider LLM support** — pluggable Groq and Mistral backends via the OpenAI-compatible API.

## Project structure

```
app/
├── main.py                 # FastAPI app entry point (uvicorn, lifespan logging)
├── api/
│   ├── router.py           # API router aggregation
│   └── routes/
│       ├── health.py       # GET /health
│       └── tutor.py        # POST /tutor/python/execute-review
├── config/
│   ├── settings.py         # Pydantic Settings, loaded from .env
│   └── database.py         # DB connection config (placeholder)
├── core/
│   └── logger.py           # Logging setup
├── sandbox/
│   ├── security.py         # Security policy constants (blocked modules/functions)
│   ├── validator.py        # AST-based static validation + message mapping
│   └── python_executor.py  # Subprocess execution with timeout + temp-file cleanup
├── schemas/
│   ├── execution_schema.py # Sandbox execution contracts (ValidationResult, ExecutionResult, ...)
│   └── output_schema.py    # API response models (ReviewResponse, ExecuteReviewResponse, ...)
├── tutor/
│   ├── llm.py              # Provider-aware OpenAI client + generate_response
│   ├── utils.py            # Shared LLM helpers (prompt loading, JSON extraction)
│   ├── execution.py        # Execute-review orchestration service
│   └── prompts/            # YAML system prompts for the tutor
├── database/               # Placeholder for future DB layers
├── progress/               # Placeholder for learning-profile features
├── retrieval/              # Placeholder for RAG / docs / embeddings / vector store
├── evaluation/             # Placeholder for LLM-as-a-Judge evaluation
└── users/                  # Placeholder for user management

tests/                      # Test suite (empty for now)
docker/                     # Placeholder for containerization
```

## Getting started

### Prerequisites

- Python **>= 3.12** (see `.python-version`)
- [uv](https://docs.astral.sh/uv/) (recommended package manager)

### Installation

```bash
uv sync
```

### Configuration

Copy `.env.example` to `.env` at the project root and fill in your values:

```bash
cp .env.example .env
```

The `.env` file is gitignored, so never commit real keys.

### Running the server

```bash
uv run python -m app.main
```

The API is served at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs` and `/redoc`.

## API reference

### `GET /health`

Liveness check.

```json
{ "status": "healthy" }
```

### `POST /tutor/python/execute-review`

Validates, executes, and LLM-reviews a Python snippet.

**Request body**

| Field | Type | Description |
| --- | --- | --- |
| `code` | `string` | Python source code to execute and review. |
| `timeout_seconds` | `number \| null` | Optional per-request sandbox timeout override. |

```json
{
  "code": "def add(a, b):\n    return a + b\n\nprint(add(2, 3))"
}
```

**Response** — an `ExecuteReviewResponse` with three blocks:

- `validation` — pass/fail, sanitized rejection reasons, and (when enabled) an LLM-written explanation of why validation failed.
- `execution` — real execution facts: `success`, `stdout`, `stderr`, `return_code`, `execution_time` (seconds), `timed_out`.
- `review` — LLM review: `errors_count`, `error_explanation[]`, `mistakes[]`, `strengths[]`, `suggestions[]`.

When static validation fails, `execution` and `review` are omitted and the failure is explained educationally instead.

## How it works

The execute-review pipeline (`app/tutor/execution.py`) runs end to end:

1. **Validate** (`app/sandbox/validator.py`) — parse the code with AST; reject empty/oversized snippets, syntax errors, blocked imports, and `eval`/`exec`/`compile`/`__import__` calls. Errors fall into three categories: *Python-generated*, *platform non-security*, and *platform security* — each mapped to distinct user-facing and LLM-facing outputs so sandbox internals stay hidden.
2. **Execute** (`app/sandbox/python_executor.py`) — write the snippet to a temp `.py` file, run it in a subprocess using the same interpreter, capture stdout/stderr/return code, measure wall-clock time, enforce a timeout, and always clean up the temp file.
3. **Review** (`app/tutor/`) — build a system prompt plus a user prompt carrying the code and its *real* execution facts, then ask the LLM for a structured review (`ReviewResponse`). The prompt makes the execution result the source of truth so the model never invents runtime errors.
4. **Respond** — combine validation, execution facts, and the review into `ExecuteReviewResponse`.

## Testing

The test suite lives in `tests/` (currently just a package stub). As tests are added, run them with:

```bash
uv run pytest
```

## License

Not yet specified.
