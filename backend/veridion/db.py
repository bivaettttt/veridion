import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

engine = create_engine(
    os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://veridion:local_veridion@localhost/veridion",
    ),
    pool_pre_ping=True,
)


def session() -> Iterator[Session]:
    with Session(engine) as db:
        yield db
