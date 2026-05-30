from os import getenv

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = getenv("DATABASE_URL", "sqlite:///./evaluations.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    _add_missing_sqlite_columns()


def _add_missing_sqlite_columns() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "evaluations" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("evaluations")
    }
    columns_to_add = {
        "evaluation_mode": "VARCHAR DEFAULT 'general_answer' NOT NULL",
        "passed": "VARCHAR DEFAULT 'false' NOT NULL",
        "verdict": "VARCHAR DEFAULT 'needs_review' NOT NULL",
        "criterion_scores": "TEXT DEFAULT '{}' NOT NULL",
        "error_types": "TEXT DEFAULT '[]' NOT NULL",
        "suggestions": "TEXT DEFAULT '[]' NOT NULL",
    }

    with engine.begin() as connection:
        for column_name, column_sql in columns_to_add.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE evaluations ADD COLUMN {column_name} {column_sql}")
                )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
