from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Label = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=180)
]
Query = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=2, max_length=500)
]
Role = Literal["RESEARCHER", "ANALYST", "REVIEWER", "ADMIN"]
Mode = Literal["keyword", "semantic", "hybrid"]
Category = Literal[
    "specification", "test", "architecture", "meeting", "advisory", "other"
]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Input):
    email: Label
    password: str = Field(min_length=1, max_length=150)


class NewUser(Login):
    name: Label


class Project(Input):
    name: Label
    description: str = Field("", max_length=2000)


class Member(Input):
    email: Label
    role: Role


class Search(Input):
    query: Query
    mode: Mode = "hybrid"
    limit: int = Field(8, ge=1, le=20)
    as_of: datetime | None = None
    category: Category | None = None
    source_id: UUID | None = None


class Question(Search):
    provider: Literal["extractive", "ollama"] = "extractive"


class Review(Input):
    decision: Literal["IN_REVIEW", "VERIFIED", "REJECTED", "NEEDS_MORE_EVIDENCE"]
    rationale: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=5, max_length=2000)
    ]
    revision: int = Field(ge=0)


class Report(Input):
    answer_id: UUID
    title: Label
    notes: str = Field("", max_length=5000)


class CitationCheck(Input):
    answer_id: UUID
    chunk_id: UUID
    version_id: UUID
    quote: str = Field(min_length=1, max_length=1600)
    content_hash: str = Field(min_length=64, max_length=64)


class Evaluation(Input):
    mode: Mode = "hybrid"
    provider: Literal["extractive", "ollama"] = "extractive"
