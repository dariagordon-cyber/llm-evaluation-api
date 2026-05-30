import json
from uuid import uuid4

from pydantic import ValidationError

from app.config import get_settings
from app.schemas import Criterion, EvaluationRequest, EvaluationResult


class EvaluationError(Exception):
    """Raised when evaluation cannot be completed."""


def mock_evaluate(payload: EvaluationRequest) -> EvaluationResult:
    """Return a deterministic mock evaluation for the submitted response."""
    criteria = normalize_criteria(payload.criteria)
    score = _mock_score(payload.model_answer)
    passed = score >= 0.7
    error_types = _mock_error_types(score, payload.model_answer)

    return EvaluationResult(
        evaluation_id=str(uuid4()),
        evaluation_mode=payload.evaluation_mode,
        overall_score=score,
        passed=passed,
        criterion_scores=_mock_criterion_scores(score, criteria),
        error_types=error_types,
        explanation=_mock_explanation(score, payload.criteria),
        suggestions=_mock_suggestions(error_types),
    )


def openai_evaluate(payload: EvaluationRequest) -> EvaluationResult:
    """Evaluate an answer with OpenAI and validate the structured result."""
    settings = get_settings()
    evaluation_id = str(uuid4())
    criteria = normalize_criteria(payload.criteria)
    criteria_text = criteria_to_text(criteria)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You evaluate LLM answers. Return only strict JSON that "
                        "matches the provided schema. Scores must be between 0 and 1."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "evaluation_id": evaluation_id,
                            "task": payload.task,
                            "model_answer": payload.model_answer,
                            "reference_answer": payload.reference_answer,
                            "criteria": [criterion.model_dump() for criterion in criteria],
                            "criteria_text": criteria_text,
                            "evaluation_mode": payload.evaluation_mode,
                            "allowed_error_types": [
                                "factual_error",
                                "missing_information",
                                "irrelevant_information",
                                "unclear_explanation",
                                "constraint_violation",
                                "unsupported_assumption",
                                "hallucination",
                                "format_error",
                                "overconfident_answer",
                            ],
                            "instructions": (
                                "Evaluate the response against the criteria. "
                                "Return the same evaluation_id and evaluation_mode exactly. "
                                "Only use allowed_error_types in error_types."
                            ),
                        }
                    ),
                },
            ],
            response_format=_evaluation_response_format(),
        )
    except Exception as exc:
        raise EvaluationError("OpenAI evaluation request failed.") from exc

    content = completion.choices[0].message.content
    if not content:
        raise EvaluationError("OpenAI returned an empty evaluation.")

    try:
        result = EvaluationResult.model_validate_json(content)
    except (ValueError, ValidationError) as exc:
        raise EvaluationError("OpenAI returned invalid evaluation JSON.") from exc

    if (
        result.evaluation_id != evaluation_id
        or result.evaluation_mode != payload.evaluation_mode
    ):
        raise EvaluationError("OpenAI returned an evaluation with mismatched fields.")

    return result


def evaluate_response(payload: EvaluationRequest) -> EvaluationResult:
    settings = get_settings()
    if not settings.openai_api_key:
        return mock_evaluate(payload)

    return openai_evaluate(payload)


def normalize_criteria(criteria: str | list[Criterion]) -> list[Criterion]:
    if isinstance(criteria, str):
        return [
            Criterion(
                name="overall_quality",
                description=criteria,
                weight=1.0,
            )
        ]

    return criteria


def format_criteria(criteria: list[Criterion]) -> str:
    return "; ".join(
        f"{criterion.name} ({criterion.weight:g}): {criterion.description}"
        for criterion in criteria
    )


def criteria_to_text(criteria: str | list[Criterion]) -> str:
    if isinstance(criteria, str):
        return criteria

    return format_criteria(criteria)


def _mock_score(response: str) -> float:
    word_count = len(response.split())
    length_score = min(word_count / 50, 1.0)
    punctuation_bonus = 0.1 if response.rstrip().endswith((".", "!", "?")) else 0.0
    return round(min(0.4 + length_score * 0.5 + punctuation_bonus, 1.0), 2)


def _mock_explanation(score: float, criteria: str | list[Criterion]) -> str:
    criteria_text = criteria_to_text(criteria)
    if score >= 0.7:
        return f"The response looks solid against the criteria: {criteria_text}."

    return f"The response may need more detail or clarity for the criteria: {criteria_text}."


def _mock_criterion_scores(
    score: float,
    criteria: list[Criterion],
) -> dict[str, float]:
    return {criterion.name: score for criterion in criteria}


def _mock_error_types(score: float, response: str) -> list[str]:
    errors = []
    if score < 0.7:
        errors.append("missing_information")

    if not response.rstrip().endswith((".", "!", "?")):
        errors.append("format_error")

    return errors


def _mock_suggestions(error_types: list[str]) -> list[str]:
    suggestions = []
    if "missing_information" in error_types:
        suggestions.append("Add more detail that directly addresses the criteria.")

    if "format_error" in error_types:
        suggestions.append("End the answer with clear punctuation.")

    return suggestions


def _evaluation_response_format() -> dict[str, object]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "evaluation_result",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "evaluation_id",
                    "evaluation_mode",
                    "overall_score",
                    "passed",
                    "criterion_scores",
                    "error_types",
                    "explanation",
                    "suggestions",
                ],
                "properties": {
                    "evaluation_id": {"type": "string"},
                    "evaluation_mode": {
                        "type": "string",
                        "enum": [
                            "general_answer",
                            "constraint_following",
                            "ambiguity_handling",
                            "educational_answer",
                            "summarization",
                        ],
                    },
                    "overall_score": {"type": "number", "minimum": 0, "maximum": 1},
                    "passed": {"type": "boolean"},
                    "criterion_scores": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                        },
                    },
                    "error_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "factual_error",
                                "missing_information",
                                "irrelevant_information",
                                "unclear_explanation",
                                "constraint_violation",
                                "unsupported_assumption",
                                "hallucination",
                                "format_error",
                                "overconfident_answer",
                            ],
                        },
                    },
                    "explanation": {"type": "string"},
                    "suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
    }
