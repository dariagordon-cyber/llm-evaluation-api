import json
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, String, Text

from app.database import Base
from app.schemas import EvaluationResult


class EvaluationRecord(Base):
    __tablename__ = "evaluations"

    evaluation_id = Column("id", String, primary_key=True, index=True)
    task = Column("prompt", Text, nullable=False)
    model_answer = Column("response", Text, nullable=False)
    criteria = Column(Text, nullable=False)
    evaluation_mode = Column(String, nullable=False, default="general_answer")
    overall_score = Column("score", Float, nullable=False)
    passed = Column(String, nullable=False)
    legacy_verdict = Column("verdict", String, nullable=False, default="pass")
    criterion_scores = Column(Text, nullable=False, default="{}")
    error_types = Column(Text, nullable=False, default="[]")
    explanation = Column("feedback", Text, nullable=False)
    suggestions = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime(timezone=True), nullable=False)
    evaluator = Column(String, nullable=False)


def evaluation_to_record(evaluation: EvaluationResult) -> EvaluationRecord:
    return EvaluationRecord(
        evaluation_id=evaluation.evaluation_id,
        task="",
        model_answer="",
        criteria="",
        evaluation_mode=evaluation.evaluation_mode,
        overall_score=evaluation.overall_score,
        passed=json.dumps(evaluation.passed),
        legacy_verdict="pass" if evaluation.passed else "needs_review",
        criterion_scores=json.dumps(evaluation.criterion_scores),
        error_types=json.dumps(evaluation.error_types),
        explanation=evaluation.explanation,
        suggestions=json.dumps(evaluation.suggestions),
        created_at=datetime.now(timezone.utc),
        evaluator="mock",
    )


def record_to_evaluation(record: EvaluationRecord) -> EvaluationResult:
    return EvaluationResult(
        evaluation_id=record.evaluation_id,
        evaluation_mode=record.evaluation_mode,
        overall_score=record.overall_score,
        passed=json.loads(record.passed),
        criterion_scores=json.loads(record.criterion_scores),
        error_types=json.loads(record.error_types),
        explanation=record.explanation,
        suggestions=json.loads(record.suggestions),
    )
