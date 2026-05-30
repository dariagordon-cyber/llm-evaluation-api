# LLM Evaluation API

## Short Project Description

LLM Evaluation API is a FastAPI-based API for structured, rubric-based evaluation of LLM-generated answers.

The API supports single-answer evaluation, batch evaluation, SQLite logging, optional OpenAI-based evaluation when `OPENAI_API_KEY` is available, and a deterministic mock fallback when no API key is configured.

## Motivation

LLM applications need more than simple pass/fail checks. This project demonstrates how to evaluate model answers using explicit criteria, evaluation modes, controlled error labels, structured scores, and persistent logs. It is designed as a backend API project that shows practical API design, validation, persistence, testing, Docker configuration, and CI.

## Features

- Single evaluation through `POST /evaluate`
- Batch evaluation through `POST /batch-evaluate`
- Structured rubric criteria with optional weights
- Evaluation modes for different answer types
- Controlled error taxonomy
- OpenAI evaluator when `OPENAI_API_KEY` is set
- Mock evaluator fallback when `OPENAI_API_KEY` is missing
- SQLite persistence for evaluation results
- Retrieval endpoints for saved evaluations
- Pytest test suite that does not require a real OpenAI API key
- Dockerfile and GitHub Actions CI workflow

## Tech Stack

- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy
- SQLite
- OpenAI Python SDK
- Pytest
- Uvicorn
- Docker
- GitHub Actions

## Project Structure

```text
app/
  __init__.py
  config.py
  database.py
  evaluator.py
  main.py
  models.py
  schemas.py
tests/
  test_evaluate.py
.github/
  workflows/
    ci.yml
Dockerfile
requirements.txt
README.md
```

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check endpoint |
| `POST` | `/evaluate` | Evaluate one model answer |
| `POST` | `/batch-evaluate` | Evaluate multiple model answers with shared criteria |
| `GET` | `/evaluations?limit=20&offset=0` | List saved evaluations from SQLite with pagination |
| `GET` | `/evaluations/{evaluation_id}` | Retrieve one saved evaluation |

## Request/Response Examples

### Single Evaluation Request

```bash
curl -X POST "http://127.0.0.1:8000/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "What is FastAPI?",
    "model_answer": "FastAPI is a Python framework for building APIs quickly.",
    "reference_answer": "FastAPI is a modern Python web framework for building APIs.",
    "evaluation_mode": "educational_answer",
    "criteria": [
      {
        "name": "accuracy",
        "description": "The answer should be technically correct.",
        "weight": 0.7
      },
      {
        "name": "clarity",
        "description": "The answer should be beginner-friendly.",
        "weight": 0.3
      }
    ]
  }'
```

### Single Evaluation Response

Scores are returned on a `0.0` to `1.0` scale, where higher scores indicate stronger answers against the supplied criteria.

```json
{
  "evaluation_id": "f4a7ec0a-8ef2-4827-82f0-3d96e85d6d72",
  "evaluation_mode": "educational_answer",
  "overall_score": 0.6,
  "passed": false,
  "criterion_scores": {
    "accuracy": 0.6,
    "clarity": 0.6
  },
  "error_types": ["missing_information"],
  "explanation": "The response may need more detail or clarity for the criteria.",
  "suggestions": ["Add more detail that directly addresses the criteria."]
}
```

## Evaluation Modes

The optional `evaluation_mode` field defaults to `general_answer`.

Supported values:

- `general_answer`
- `constraint_following`
- `ambiguity_handling`
- `educational_answer`
- `summarization`

## Error Taxonomy

The evaluator returns only controlled error types:

- `factual_error`
- `missing_information`
- `irrelevant_information`
- `unclear_explanation`
- `constraint_violation`
- `unsupported_assumption`
- `hallucination`
- `format_error`
- `overconfident_answer`

## Example Evaluation Cases

The `examples/` directory contains realistic, illustrative scenarios for trying the API and thinking through LLM error analysis. These are usage examples, not benchmark results or human-validated evaluation data.

- [Evaluation cases](examples/evaluation_cases.md)
- [Sample single-evaluation requests](examples/sample_single_requests.json)
- [Sample batch request](examples/sample_batch_request.json)

## Running Locally

Create a virtual environment, install dependencies, and run the API:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Environment Variables

Set `OPENAI_API_KEY` to enable OpenAI-based evaluation:

```bash
export OPENAI_API_KEY="your-api-key"
```

Optionally set the OpenAI model:

```bash
export OPENAI_MODEL="gpt-4o-mini"
```

If `OPENAI_API_KEY` is not set, the API automatically uses the mock evaluator. Tests and CI are designed to pass without a real OpenAI API key.

## Running Tests

```bash
python -m pytest
```

The tests use isolated temporary SQLite databases and do not call the real OpenAI API.

## SQLite Persistence

Evaluation results are saved to a local SQLite database named `evaluations.db`.

The database is created automatically when the app starts. It is runtime data and is ignored by git.

`GET /evaluations` supports pagination so clients do not need to load too many records at once:

```text
GET /evaluations?limit=20&offset=0
```

Query parameters:

- `limit`: number of evaluations to return, default `20`, minimum `1`, maximum `100`
- `offset`: number of evaluations to skip, default `0`, minimum `0`

## Batch Evaluation

Use `POST /batch-evaluate` to evaluate multiple answers with shared criteria and a shared evaluation mode. Each item is evaluated with the same internal logic used by `POST /evaluate`, and each result is saved to SQLite.

### Batch Evaluation Request

```bash
curl -X POST "http://127.0.0.1:8000/batch-evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "task": "Explain overfitting.",
        "model_answer": "Overfitting happens when a model memorizes training data.",
        "reference_answer": "Overfitting means a model fits training data too closely."
      },
      {
        "task": "Explain underfitting.",
        "model_answer": "Underfitting happens when a model is too simple.",
        "reference_answer": "Underfitting means a model misses important patterns."
      }
    ],
    "criteria": [
      {
        "name": "correctness",
        "description": "Does the answer explain the concept accurately?",
        "weight": 0.5
      },
      {
        "name": "clarity",
        "description": "Is the answer easy to understand?",
        "weight": 0.3
      },
      {
        "name": "completeness",
        "description": "Does the answer cover the essential points?",
        "weight": 0.2
      }
    ],
    "evaluation_mode": "general_answer"
  }'
```

### Batch Evaluation Response

```json
{
  "batch_id": "d32b1ec0-78d2-4fb5-8bb4-5fa698ff0d8d",
  "total_items": 2,
  "average_score": 0.68,
  "pass_rate": 0.5,
  "results": [
    {
      "evaluation_id": "7e2f82b9-99a7-4d52-a75a-33fb6af95bb2",
      "evaluation_mode": "general_answer",
      "overall_score": 0.74,
      "passed": true,
      "criterion_scores": {
        "correctness": 0.74,
        "clarity": 0.74,
        "completeness": 0.74
      },
      "error_types": [],
      "explanation": "The response looks solid against the criteria.",
      "suggestions": []
    },
    {
      "evaluation_id": "0e6dc39e-f006-4f4d-8dd6-3a55f3edb6f2",
      "evaluation_mode": "general_answer",
      "overall_score": 0.62,
      "passed": false,
      "criterion_scores": {
        "correctness": 0.62,
        "clarity": 0.62,
        "completeness": 0.62
      },
      "error_types": ["missing_information", "format_error"],
      "explanation": "The response may need more detail or clarity for the criteria.",
      "suggestions": [
        "Add more detail that directly addresses the criteria.",
        "End the answer with clear punctuation."
      ]
    }
  ],
  "most_common_error_types": ["missing_information", "format_error"]
}
```

Batch summary fields are calculated as follows:

- `average_score`: average of all `overall_score` values
- `pass_rate`: number of passed evaluations divided by `total_items`
- `most_common_error_types`: error types sorted by frequency, most frequent first

## Docker

Build the image:

```bash
docker build -t llm-evaluation-api .
```

Run the container:

```bash
docker run --rm -p 8000:8000 llm-evaluation-api
```

Run with OpenAI evaluation enabled:

```bash
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY="your-api-key" \
  -e OPENAI_MODEL="gpt-4o-mini" \
  llm-evaluation-api
```

Local Docker build and execution were not tested during development because Docker Desktop was not installed on the development machine.

## GitHub Actions CI

The project includes a workflow at `.github/workflows/ci.yml`.

Tests run automatically on pushes and pull requests. The workflow uses Python 3.12, installs dependencies from `requirements.txt`, and runs:

```bash
python -m pytest
```

The CI workflow does not require `OPENAI_API_KEY`.

## Current Limitations

- SQLite is suitable for local development, but a production deployment would likely use PostgreSQL or another managed database.
- There is no authentication or rate limiting.
- The mock evaluator is deterministic and intentionally simple.
- The OpenAI evaluator depends on prompt/schema compliance and should be monitored in production.
- Docker configuration is present, but local Docker execution was not verified during development.
- The API is not currently deployed.

## Future Improvements

- Add Alembic migrations for database schema changes.
- Add authentication and API keys for external clients.
- Add pagination and filtering for `GET /evaluations`.
- Add batch-level persistence and batch retrieval endpoints.
- Add richer reporting and export formats.
- Add request tracing and structured logging.
- Add production deployment configuration.

## Portfolio Summary

Built a FastAPI-based backend API for structured, rubric-based evaluation of LLM-generated answers, supporting configurable criteria, evaluation modes, controlled error taxonomy, single and batch evaluation, SQLite logging, pagination, optional OpenAI-based evaluation with mock fallback, pytest coverage, Docker configuration, and GitHub Actions CI.
