from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.evaluator as evaluator
from app.database import Base, get_db
from app.evaluator import EvaluationError
from app.main import app
from app.schemas import EvaluationRequest, EvaluationResult

client = TestClient(app)


def setup_function(function) -> None:
    app.dependency_overrides.clear()


def fake_openai_evaluate(payload: EvaluationRequest) -> EvaluationResult:
    return EvaluationResult(
        evaluation_id="eval-test-123",
        evaluation_mode=payload.evaluation_mode,
        overall_score=0.86,
        passed=True,
        criterion_scores={"accuracy": 0.9, "clarity": 0.82},
        error_types=[],
        explanation="The response is accurate and clear.",
        suggestions=[],
    )


def use_test_database(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'test_evaluations.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_evaluation_uses_mock_without_api_key(monkeypatch, tmp_path) -> None:
    use_test_database(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    evaluator.get_settings.cache_clear()

    payload = {
        "task": "What is FastAPI?",
        "model_answer": "FastAPI is a Python framework for building APIs quickly.",
        "criteria": "accuracy and clarity",
    }

    response = client.post("/evaluate", json=payload)
    data = response.json()

    assert response.status_code == 201
    assert data["evaluation_id"]
    assert 0 <= data["overall_score"] <= 1
    assert isinstance(data["passed"], bool)
    assert data["explanation"]
    assert data["evaluation_mode"] == "general_answer"
    assert set(data["criterion_scores"]) == {"overall_quality"}
    assert isinstance(data["error_types"], list)
    assert isinstance(data["suggestions"], list)
    assert "id" not in data
    assert "score" not in data
    assert "verdict" not in data
    assert "feedback" not in data
    assert "prompt" not in data
    assert "response" not in data


def test_create_evaluation_uses_openai_when_api_key_exists(monkeypatch, tmp_path) -> None:
    use_test_database(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    evaluator.get_settings.cache_clear()
    monkeypatch.setattr(evaluator, "openai_evaluate", fake_openai_evaluate)

    payload = {
        "task": "What is FastAPI?",
        "model_answer": "FastAPI is a Python framework for building APIs quickly.",
        "criteria": "accuracy and clarity",
    }

    response = client.post("/evaluate", json=payload)
    data = response.json()

    assert response.status_code == 201
    assert data["evaluation_id"] == "eval-test-123"
    assert data["explanation"] == "The response is accurate and clear."


def test_supported_evaluation_mode_and_weighted_criteria(monkeypatch, tmp_path) -> None:
    use_test_database(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    evaluator.get_settings.cache_clear()

    response = client.post(
        "/evaluate",
        json={
            "task": "Summarize this paragraph.",
            "model_answer": "It explains the main idea.",
            "evaluation_mode": "summarization",
            "criteria": [
                {
                    "name": "coverage",
                    "description": "Covers the important points.",
                    "weight": 0.7,
                },
                {
                    "name": "brevity",
                    "description": "Keeps the summary concise.",
                    "weight": 0.3,
                },
            ],
        },
    )
    data = response.json()

    assert response.status_code == 201
    assert data["evaluation_mode"] == "summarization"
    assert set(data["criterion_scores"]) == {"coverage", "brevity"}


def test_invalid_evaluation_mode_fails_validation(tmp_path) -> None:
    use_test_database(tmp_path)

    response = client.post(
        "/evaluate",
        json={
            "task": "What is FastAPI?",
            "model_answer": "FastAPI is a Python framework.",
            "criteria": "accuracy",
            "evaluation_mode": "not_supported",
        },
    )

    assert response.status_code == 422


def test_controlled_error_types(monkeypatch, tmp_path) -> None:
    use_test_database(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    evaluator.get_settings.cache_clear()

    response = client.post(
        "/evaluate",
        json={
            "task": "Explain FastAPI.",
            "model_answer": "Too short",
            "criteria": "accuracy and completeness",
        },
    )
    data = response.json()
    allowed_error_types = {
        "factual_error",
        "missing_information",
        "irrelevant_information",
        "unclear_explanation",
        "constraint_violation",
        "unsupported_assumption",
        "hallucination",
        "format_error",
        "overconfident_answer",
    }

    assert response.status_code == 201
    assert set(data["error_types"]).issubset(allowed_error_types)


def test_list_and_get_saved_evaluation(monkeypatch, tmp_path) -> None:
    use_test_database(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    evaluator.get_settings.cache_clear()

    create_response = client.post(
        "/evaluate",
        json={
            "task": "What is FastAPI?",
            "model_answer": "FastAPI is a Python framework.",
            "criteria": "accuracy",
        },
    )
    created = create_response.json()

    list_response = client.get("/evaluations")
    get_response = client.get(f"/evaluations/{created['evaluation_id']}")

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    assert get_response.status_code == 200
    assert list_response.json()["evaluations"][0]["evaluation_id"] == created["evaluation_id"]
    assert get_response.json()["evaluation_id"] == created["evaluation_id"]
    assert get_response.json()["criterion_scores"] == created["criterion_scores"]
    assert get_response.json()["error_types"] == created["error_types"]


def test_unknown_evaluation_id_returns_404(tmp_path) -> None:
    use_test_database(tmp_path)
    response = client.get("/evaluations/missing-id")

    assert response.status_code == 404
    assert response.json() == {"detail": "Evaluation not found"}


def test_evaluator_failure_returns_500(monkeypatch, tmp_path) -> None:
    use_test_database(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    evaluator.get_settings.cache_clear()

    def failing_evaluate_response(payload: EvaluationRequest) -> EvaluationResult:
        raise EvaluationError("OpenAI evaluation request failed.")

    monkeypatch.setattr("app.main.evaluate_response", failing_evaluate_response)

    response = client.post(
        "/evaluate",
        json={
            "task": "What is FastAPI?",
            "model_answer": "FastAPI is a Python framework.",
            "criteria": "accuracy",
        },
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "OpenAI evaluation request failed."}


def test_batch_evaluate_returns_summary(monkeypatch, tmp_path) -> None:
    use_test_database(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    evaluator.get_settings.cache_clear()

    response = client.post(
        "/batch-evaluate",
        json={
            "items": [
                {
                    "task": "Explain overfitting.",
                    "model_answer": "Overfitting happens when a model memorizes training data.",
                    "reference_answer": "Overfitting means a model fits training data too closely.",
                },
                {
                    "task": "Explain underfitting.",
                    "model_answer": "Underfitting happens when a model is too simple",
                    "reference_answer": "Underfitting means a model misses important patterns.",
                },
            ],
            "criteria": [
                {
                    "name": "correctness",
                    "description": "Does the answer explain the concept accurately?",
                    "weight": 0.5,
                },
                {
                    "name": "clarity",
                    "description": "Is the answer easy to understand?",
                    "weight": 0.3,
                },
                {
                    "name": "completeness",
                    "description": "Does the answer cover the essential points?",
                    "weight": 0.2,
                },
            ],
            "evaluation_mode": "general_answer",
        },
    )
    data = response.json()

    assert response.status_code == 201
    assert data["batch_id"]
    assert data["total_items"] == 2
    assert 0 <= data["average_score"] <= 1
    assert 0 <= data["pass_rate"] <= 1
    assert len(data["results"]) == 2
    assert isinstance(data["most_common_error_types"], list)


def test_batch_results_use_evaluation_response_schema(monkeypatch, tmp_path) -> None:
    use_test_database(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    evaluator.get_settings.cache_clear()

    response = client.post(
        "/batch-evaluate",
        json={
            "items": [
                {
                    "task": "Explain precision.",
                    "model_answer": "Precision measures how many predicted positives are correct.",
                }
            ],
            "criteria": "accuracy and clarity",
        },
    )
    result = response.json()["results"][0]

    assert response.status_code == 201
    assert set(result) == {
        "evaluation_id",
        "evaluation_mode",
        "overall_score",
        "passed",
        "criterion_scores",
        "error_types",
        "explanation",
        "suggestions",
    }


def test_batch_evaluations_are_saved(monkeypatch, tmp_path) -> None:
    use_test_database(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    evaluator.get_settings.cache_clear()

    batch_response = client.post(
        "/batch-evaluate",
        json={
            "items": [
                {
                    "task": "Explain bias.",
                    "model_answer": "Bias is error from overly simple assumptions.",
                },
                {
                    "task": "Explain variance.",
                    "model_answer": "Variance is sensitivity to training data.",
                },
            ],
            "criteria": "accuracy",
        },
    )
    batch_data = batch_response.json()
    saved_response = client.get("/evaluations")
    saved_ids = {
        item["evaluation_id"] for item in saved_response.json()["evaluations"]
    }

    assert batch_response.status_code == 201
    assert saved_response.status_code == 200
    assert {item["evaluation_id"] for item in batch_data["results"]}.issubset(saved_ids)


def test_batch_empty_items_returns_validation_error(tmp_path) -> None:
    use_test_database(tmp_path)

    response = client.post(
        "/batch-evaluate",
        json={
            "items": [],
            "criteria": "accuracy",
        },
    )

    assert response.status_code == 422


def test_batch_invalid_evaluation_mode_returns_422(tmp_path) -> None:
    use_test_database(tmp_path)

    response = client.post(
        "/batch-evaluate",
        json={
            "items": [
                {
                    "task": "Explain recall.",
                    "model_answer": "Recall measures found positives.",
                }
            ],
            "criteria": "accuracy",
            "evaluation_mode": "not_supported",
        },
    )

    assert response.status_code == 422


def test_batch_empty_criteria_returns_validation_error(tmp_path) -> None:
    use_test_database(tmp_path)

    response = client.post(
        "/batch-evaluate",
        json={
            "items": [
                {
                    "task": "Explain recall.",
                    "model_answer": "Recall measures found positives.",
                }
            ],
            "criteria": [],
        },
    )

    assert response.status_code == 422
