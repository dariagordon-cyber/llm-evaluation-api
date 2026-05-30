from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

EvaluationMode = Literal[
    "general_answer",
    "constraint_following",
    "ambiguity_handling",
    "educational_answer",
    "summarization",
]

ErrorType = Literal[
    "factual_error",
    "missing_information",
    "irrelevant_information",
    "unclear_explanation",
    "constraint_violation",
    "unsupported_assumption",
    "hallucination",
    "format_error",
    "overconfident_answer",
]

Score = Annotated[float, Field(ge=0, le=1)]


class Criterion(BaseModel):
    name: str = Field(..., min_length=1, examples=["accuracy"])
    description: str = Field(
        ...,
        min_length=1,
        examples=["The answer should be factually correct."],
    )
    weight: float = Field(
        default=1.0,
        gt=0,
        examples=[0.6],
        description="Relative importance for this criterion.",
    )


class EvaluationRequest(BaseModel):
    task: str = Field(..., min_length=1, examples=["Explain photosynthesis."])
    model_answer: str = Field(
        ...,
        min_length=1,
        examples=["Photosynthesis is how plants make food."],
    )
    reference_answer: str | None = Field(
        default=None,
        examples=[
            "Photosynthesis lets plants use sunlight, water, and carbon dioxide to make glucose and oxygen."
        ],
    )
    criteria: str | list[Criterion] = Field(default="overall quality")
    evaluation_mode: EvaluationMode = "general_answer"

    @field_validator("criteria")
    @classmethod
    def validate_criteria(cls, value: str | list[Criterion]) -> str | list[Criterion]:
        if isinstance(value, str) and not value.strip():
            raise ValueError("criteria cannot be blank")

        if isinstance(value, list) and not value:
            raise ValueError("criteria must include at least one item")

        return value


class BatchEvaluationItem(BaseModel):
    task: str = Field(..., min_length=1)
    model_answer: str = Field(..., min_length=1)
    reference_answer: str | None = None


class BatchEvaluationRequest(BaseModel):
    items: list[BatchEvaluationItem] = Field(..., min_length=1)
    criteria: str | list[Criterion]
    evaluation_mode: EvaluationMode = "general_answer"

    @field_validator("criteria")
    @classmethod
    def validate_criteria(cls, value: str | list[Criterion]) -> str | list[Criterion]:
        if isinstance(value, str) and not value.strip():
            raise ValueError("criteria cannot be blank")

        if isinstance(value, list) and not value:
            raise ValueError("criteria must include at least one item")

        return value


class EvaluationResult(BaseModel):
    evaluation_id: str
    evaluation_mode: EvaluationMode
    overall_score: float = Field(..., ge=0, le=1)
    passed: bool
    criterion_scores: dict[str, Score]
    error_types: list[ErrorType]
    explanation: str
    suggestions: list[str]


class EvaluationListResponse(BaseModel):
    evaluations: list[EvaluationResult]


class BatchEvaluationResponse(BaseModel):
    batch_id: str
    total_items: int
    average_score: Score
    pass_rate: Score
    results: list[EvaluationResult]
    most_common_error_types: list[ErrorType]


class ErrorResponse(BaseModel):
    detail: str
