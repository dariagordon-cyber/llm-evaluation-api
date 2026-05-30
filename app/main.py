from contextlib import asynccontextmanager
from collections import Counter
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from app.database import create_tables, get_db
from app.evaluator import EvaluationError, evaluate_response
from app.models import EvaluationRecord, evaluation_to_record, record_to_evaluation
from app.schemas import (
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    EvaluationListResponse,
    EvaluationRequest,
    EvaluationResult,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="LLM Evaluation API",
    description="A beginner-friendly API for evaluating LLM responses.",
    version="0.3.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/evaluate",
    response_model=EvaluationResult,
    status_code=status.HTTP_201_CREATED,
)
def create_evaluation(
    payload: EvaluationRequest,
    db: Session = Depends(get_db),
) -> EvaluationResult:
    try:
        result = evaluate_response(payload)
    except EvaluationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    _save_evaluation(db, result)
    return result


@app.post(
    "/batch-evaluate",
    response_model=BatchEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_batch_evaluation(
    payload: BatchEvaluationRequest,
    db: Session = Depends(get_db),
) -> BatchEvaluationResponse:
    results = []

    try:
        for item in payload.items:
            result = evaluate_response(
                EvaluationRequest(
                    task=item.task,
                    model_answer=item.model_answer,
                    reference_answer=item.reference_answer,
                    criteria=payload.criteria,
                    evaluation_mode=payload.evaluation_mode,
                )
            )
            results.append(result)
    except EvaluationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    for result in results:
        db.add(evaluation_to_record(result))

    db.commit()
    return _build_batch_response(results)


@app.get("/evaluations", response_model=EvaluationListResponse)
def list_evaluations(db: Session = Depends(get_db)) -> EvaluationListResponse:
    records = db.query(EvaluationRecord).order_by(EvaluationRecord.created_at.desc()).all()
    return EvaluationListResponse(
        evaluations=[record_to_evaluation(record) for record in records]
    )


@app.get("/evaluations/{evaluation_id}", response_model=EvaluationResult)
def get_evaluation(
    evaluation_id: str,
    db: Session = Depends(get_db),
) -> EvaluationResult:
    record = db.get(EvaluationRecord, evaluation_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found",
        )

    return record_to_evaluation(record)


def _save_evaluation(db: Session, result: EvaluationResult) -> None:
    db.add(evaluation_to_record(result))
    db.commit()


def _build_batch_response(results: list[EvaluationResult]) -> BatchEvaluationResponse:
    total_items = len(results)
    average_score = sum(result.overall_score for result in results) / total_items
    pass_rate = sum(result.passed for result in results) / total_items
    error_counts = Counter(
        error_type
        for result in results
        for error_type in result.error_types
    )
    most_common_error_types = [
        error_type for error_type, _ in error_counts.most_common()
    ]

    return BatchEvaluationResponse(
        batch_id=str(uuid4()),
        total_items=total_items,
        average_score=round(average_score, 4),
        pass_rate=round(pass_rate, 4),
        results=results,
        most_common_error_types=most_common_error_types,
    )
