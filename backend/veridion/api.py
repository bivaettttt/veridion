import os
import re
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from veridion import access, contracts, evaluation, lab, lifecycle, research, sources
from veridion.db import session
from veridion.documents import MAX_BYTES

app = FastAPI(
    title="Veridion",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
api = APIRouter(prefix="/api/v1")
DB = Annotated[Session, Depends(session)]
PAGE = Annotated[int, Query(ge=0, le=100_000)]
WRITE = ("RESEARCHER", "ADMIN")


@app.middleware("http")
async def request_context(request: Request, call_next):
    supplied = request.headers.get("x-request-id", "")
    request.state.correlation = (
        supplied if re.fullmatch(r"[A-Za-z0-9_-]{1,80}", supplied) else uuid4().hex
    )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.correlation
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(StarletteHTTPException)
async def request_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        {
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "request_id": request.state.correlation,
            }
        },
        status_code=exc.status_code,
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    fields = [{"path": item["loc"], "message": item["msg"]} for item in exc.errors()]
    return JSONResponse(
        {
            "error": {
                "code": "INVALID_INPUT",
                "message": "Check request fields",
                "fields": fields,
                "request_id": request.state.correlation,
            }
        },
        status_code=422,
    )


@api.get("/health", tags=["Operations"])
def health(db: DB):
    db.execute(text("SELECT vector_dims('[1,2]'::vector)"))
    return {"status": "ready"}


@api.post("/auth/login", tags=["Access"])
def login(data: contracts.Login, db: DB, response: Response):
    token = access.sign_in(db, data.email, data.password)
    response.set_cookie(
        "veridion_session",
        token,
        httponly=True,
        samesite="strict",
        secure=os.getenv("VERIDION_SECURE_COOKIES") == "1",
        max_age=43200,
    )
    return {"status": "authenticated"}


@api.post("/auth/logout", status_code=204, tags=["Access"])
def logout(db: DB, request: Request, response: Response):
    access.identity(db, request)
    db.execute(
        text("DELETE FROM sessions WHERE digest=:hash"),
        {"hash": access.digest(request.cookies["veridion_session"])},
    )
    db.commit()
    response.delete_cookie("veridion_session")


@api.get("/auth/me", tags=["Access"])
def me(db: DB, request: Request):
    return access.identity(db, request)


@api.post("/users", status_code=201, tags=["Access"])
def new_user(data: contracts.NewUser, db: DB, request: Request):
    actor = access.identity(db, request)
    if not actor["is_admin"]:
        raise HTTPException(403, "Administrator required")
    if len(data.password) < 12:
        raise HTTPException(422, "Use a password of at least 12 characters")
    user = db.scalar(
        text("""
        INSERT INTO users(email,name,password) VALUES (:email,:name,:password)
        ON CONFLICT(email) DO NOTHING RETURNING id
    """),
        {
            "email": data.email.casefold(),
            "name": data.name,
            "password": access.password_hash(data.password),
        },
    )
    if user is None:
        raise HTTPException(409, "Email already registered")
    db.commit()
    return {"id": user}


@api.get("/projects", tags=["Projects"])
def projects(db: DB, request: Request, offset: PAGE = 0):
    actor = access.identity(db, request)
    return (
        db.execute(
            text("""
        SELECT p.id,p.name,p.description,p.lab,m.role FROM projects p JOIN members m ON m.project_id=p.id
        WHERE m.user_id=:user ORDER BY p.created_at,p.id LIMIT 50 OFFSET :offset
    """),
            {"user": actor["id"], "offset": offset},
        )
        .mappings()
        .all()
    )


@api.post("/projects", status_code=201, tags=["Projects"])
def create_project(data: contracts.Project, db: DB, request: Request):
    actor = access.identity(db, request)
    project = db.scalar(
        text("""
        INSERT INTO projects(name,description,owner_id) VALUES (:name,:description,:user) RETURNING id
    """),
        data.model_dump() | {"user": actor["id"]},
    )
    db.execute(
        text("INSERT INTO members VALUES (:project,:user,'ADMIN')"),
        {"project": project, "user": actor["id"]},
    )
    access.event(
        db, project, actor["id"], "project.created", project, request.state.correlation
    )
    db.commit()
    return {"id": project}


@api.get("/projects/{project}", tags=["Projects"])
def project_detail(project: UUID, db: DB, request: Request):
    actor = access.identity(db, request)
    role = access.membership(db, project, actor["id"])
    row = (
        db.execute(
            text("SELECT id,name,description,lab FROM projects WHERE id=:id"),
            {"id": project},
        )
        .mappings()
        .one()
    )
    return dict(row) | {"role": role}


@api.get("/projects/{project}/members", tags=["Projects"])
def members(project: UUID, db: DB, request: Request):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"], "ADMIN")
    return (
        db.execute(
            text("""
        SELECT u.id,u.name,u.email,m.role FROM members m JOIN users u ON u.id=m.user_id
        WHERE m.project_id=:project ORDER BY u.email LIMIT 100
    """),
            {"project": project},
        )
        .mappings()
        .all()
    )


@api.put("/projects/{project}/members", tags=["Projects"])
def set_member(project: UUID, data: contracts.Member, db: DB, request: Request):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"], "ADMIN")
    owner = db.scalar(
        text("SELECT owner_id FROM projects WHERE id=:id"), {"id": project}
    )
    uid = db.scalar(
        text("SELECT id FROM users WHERE email=:email"),
        {"email": data.email.casefold()},
    )
    if uid is None:
        raise HTTPException(404, "User not found")
    if uid == owner and data.role != "ADMIN":
        raise HTTPException(409, "The owner retains the admin role")
    db.execute(
        text("""
        INSERT INTO members VALUES (:project,:user,:role)
        ON CONFLICT(project_id,user_id) DO UPDATE SET role=excluded.role
    """),
        {"project": project, "user": uid, "role": data.role},
    )
    access.event(
        db, project, actor["id"], "member.assigned", uid, request.state.correlation
    )
    db.commit()
    return {"id": uid, "role": data.role}


@api.get("/projects/{project}/sources", tags=["Sources"])
def list_sources(
    project: UUID, db: DB, request: Request, offset: PAGE = 0, archived: bool = False
):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"])
    return (
        db.execute(
            text("""
        SELECT s.id,s.title,s.category,s.archived_at,s.created_at,
               (SELECT max(version) FROM source_versions WHERE source_id=s.id) AS version
        FROM sources s WHERE s.project_id=:project AND (:archived OR s.archived_at IS NULL)
        ORDER BY s.title,s.id LIMIT 50 OFFSET :offset
    """),
            {"project": project, "offset": offset, "archived": archived},
        )
        .mappings()
        .all()
    )


@api.post("/projects/{project}/documents", status_code=202, tags=["Sources"])
def upload(
    project: UUID,
    db: DB,
    request: Request,
    file: Annotated[UploadFile, File()],
    title: Annotated[contracts.Label, Form()],
    category: Annotated[contracts.Category, Form()],
):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"], *WRITE)
    job = sources.queue(
        db, project, title, category, file.filename or "", file.file.read(MAX_BYTES + 1)
    )
    access.event(
        db,
        project,
        actor["id"],
        "document.queued",
        job["id"],
        request.state.correlation,
    )
    db.commit()
    return job


@api.delete(
    "/projects/{project}/sources/{source_id}", status_code=204, tags=["Sources"]
)
def archive(project: UUID, source_id: UUID, db: DB, request: Request):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"], *WRITE)
    sources.source(db, project, source_id, lock=True)
    db.execute(
        text(
            "UPDATE sources SET archived_at=coalesce(archived_at,clock_timestamp()) WHERE id=:id"
        ),
        {"id": source_id},
    )
    access.event(
        db,
        project,
        actor["id"],
        "source.archived",
        source_id,
        request.state.correlation,
    )
    db.commit()


@api.get("/projects/{project}/sources/{source_id}/versions", tags=["Sources"])
def versions(
    project: UUID, source_id: UUID, db: DB, request: Request, offset: PAGE = 0
):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"])
    entry = sources.source(db, project, source_id)
    rows = (
        db.execute(
            text("""
        SELECT id,version,filename,media_type,content_hash,created_at
        FROM source_versions WHERE source_id=:source ORDER BY version DESC LIMIT 50 OFFSET :offset
    """),
            {"source": source_id, "offset": offset},
        )
        .mappings()
        .all()
    )
    return {"source": entry, "versions": rows}


@api.get("/projects/{project}/sources/{source_id}/versions/{number}", tags=["Sources"])
def version(project: UUID, source_id: UUID, number: int, db: DB, request: Request):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"])
    entry = sources.source(db, project, source_id)
    row = (
        db.execute(
            text("""
        SELECT id,source_id,version,filename,media_type,content_hash,created_at,normalized
        FROM source_versions WHERE source_id=:source AND version=:number
    """),
            {"source": source_id, "number": number},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(404, "Version not found")
    sections = (
        db.execute(
            text("""
        SELECT id,heading,page,start_at,end_at FROM sections WHERE version_id=:id ORDER BY start_at
    """),
            {"id": row["id"]},
        )
        .mappings()
        .all()
    )
    return dict(row) | {"title": entry["title"], "sections": sections}


@api.get(
    "/projects/{project}/sources/{source_id}/versions/{number}/original",
    tags=["Sources"],
)
def download(project: UUID, source_id: UUID, number: int, db: DB, request: Request):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"])
    return sources.original(db, project, source_id, number)


@api.get("/projects/{project}/jobs", tags=["Sources"])
def ingestion(project: UUID, db: DB, request: Request, offset: PAGE = 0):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"])
    return (
        db.execute(
            text("""
        SELECT j.id,j.source_id,s.title,j.filename,j.state,j.version_id,j.error,j.created_at,j.finished_at
        FROM jobs j JOIN sources s ON s.id=j.source_id WHERE s.project_id=:project
        ORDER BY j.created_at DESC,j.id LIMIT 50 OFFSET :offset
    """),
            {"project": project, "offset": offset},
        )
        .mappings()
        .all()
    )


@api.get("/projects/{project}/audit", tags=["Projects"])
def audit(project: UUID, db: DB, request: Request, offset: PAGE = 0):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"], "ADMIN")
    return (
        db.execute(
            text("""
        SELECT a.id,a.action,a.created_at,a.object_id,a.request_id,u.name AS actor
        FROM audit a LEFT JOIN users u ON u.id=a.user_id WHERE a.project_id=:project
        ORDER BY a.id DESC LIMIT 50 OFFSET :offset
    """),
            {"project": project, "offset": offset},
        )
        .mappings()
        .all()
    )


@api.get("/models", tags=["Research"])
def models(db: DB, request: Request):
    access.identity(db, request)
    return {
        "extractive": "veridion-evidence-rules/v1",
        "ollama_enabled": bool(os.getenv("VERIDION_OLLAMA_URL")),
        "ollama_model": os.getenv("VERIDION_OLLAMA_MODEL", "qwen2.5:3b"),
    }


@api.post("/projects/{project}/search", tags=["Research"])
def search(project: UUID, data: contracts.Search, db: DB, request: Request):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"])
    if data.source_id:
        sources.source(db, project, data.source_id)
    run, hits, configuration = research.keep_search(db, project, actor["id"], data)
    db.commit()
    return {"id": run, "hits": hits, "configuration": configuration}


@api.get("/projects/{project}/search/runs", tags=["Research"])
def search_history(project: UUID, db: DB, request: Request, offset: PAGE = 0):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"])
    return (
        db.execute(
            text("""
        SELECT id,query,configuration,created_at FROM search_runs WHERE project_id=:project
        ORDER BY created_at DESC,id LIMIT 50 OFFSET :offset
    """),
            {"project": project, "offset": offset},
        )
        .mappings()
        .all()
    )


@api.post("/projects/{project}/answers", status_code=201, tags=["Research"])
def ask(
    project: UUID,
    data: contracts.Question,
    db: DB,
    request: Request,
    key: Annotated[
        str | None, Header(alias="Idempotency-Key", pattern=r"^[A-Za-z0-9_-]{1,120}$")
    ] = None,
):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"])
    if data.source_id:
        sources.source(db, project, data.source_id)
    key_fields = {
        "project": project,
        "user": actor["id"],
        "key": key,
        "fingerprint": access.digest(data.model_dump_json()),
    }
    if key:
        inserted = db.scalar(
            text("""
            INSERT INTO answer_keys(project_id,user_id,key,fingerprint)
            VALUES (:project,:user,:key,:fingerprint) ON CONFLICT DO NOTHING RETURNING key
        """),
            key_fields,
        )
        if not inserted:
            saved = db.execute(
                text("""
                SELECT fingerprint,answer_id FROM answer_keys
                WHERE project_id=:project AND user_id=:user AND key=:key
            """),
                key_fields,
            ).one()
            if saved.fingerprint != key_fields["fingerprint"]:
                raise HTTPException(
                    409, "Idempotency key was used for a different question"
                )
            return research.detail(db, project, saved.answer_id)
    answer_id = research.answer(db, project, actor["id"], data)
    if key:
        db.execute(
            text("""
            UPDATE answer_keys SET answer_id=:id WHERE project_id=:project AND user_id=:user AND key=:key
        """),
            key_fields | {"id": answer_id},
        )
    access.event(
        db,
        project,
        actor["id"],
        "answer.generated",
        answer_id,
        request.state.correlation,
    )
    db.commit()
    return research.detail(db, project, answer_id)


@api.get("/projects/{project}/answers", tags=["Research"])
def answer_list(project: UUID, db: DB, request: Request, offset: PAGE = 0):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"])
    return (
        db.execute(
            text("""
        SELECT a.id,a.created_at,a.provider,s.query,a.output->>'assessment' AS assessment,
               coalesce(r.decision,'AUTO_ASSESSED') AS decision
        FROM answers a JOIN search_runs s ON s.id=a.search_id
        LEFT JOIN LATERAL (SELECT decision FROM reviews WHERE answer_id=a.id ORDER BY revision DESC LIMIT 1) r ON true
        WHERE s.project_id=:project ORDER BY a.created_at DESC,a.id LIMIT 50 OFFSET :offset
    """),
            {"project": project, "offset": offset},
        )
        .mappings()
        .all()
    )


@api.get("/projects/{project}/answers/{answer_id}", tags=["Research"])
def answer_detail(project: UUID, answer_id: UUID, db: DB, request: Request):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"])
    return research.detail(db, project, answer_id)


@api.post("/projects/{project}/citations/verify", tags=["Evidence"])
def verify(project: UUID, data: contracts.CitationCheck, db: DB, request: Request):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"])
    row = research.get_answer(db, project, data.answer_id)
    return research.check(
        db, project, row, data.chunk_id, data.version_id, data.quote, data.content_hash
    )


@api.post(
    "/projects/{project}/answers/{answer_id}/reviews",
    status_code=201,
    tags=["Evidence"],
)
def review(
    project: UUID, answer_id: UUID, data: contracts.Review, db: DB, request: Request
):
    actor = access.identity(db, request)
    role = access.membership(db, project, actor["id"])
    review_id = lifecycle.add_review(db, project, answer_id, actor["id"], role, data)
    access.event(
        db,
        project,
        actor["id"],
        "review." + data.decision.lower(),
        review_id,
        request.state.correlation,
    )
    db.commit()
    return {"id": review_id}


@api.get("/projects/{project}/reports", tags=["Reports"])
def reports(project: UUID, db: DB, request: Request, offset: PAGE = 0):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"])
    return (
        db.execute(
            text("""
        SELECT id,title,answer_id,created_at FROM reports WHERE project_id=:project
        ORDER BY created_at DESC,id LIMIT 50 OFFSET :offset
    """),
            {"project": project, "offset": offset},
        )
        .mappings()
        .all()
    )


@api.post("/projects/{project}/reports", status_code=201, tags=["Reports"])
def create_report(project: UUID, data: contracts.Report, db: DB, request: Request):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"], *WRITE)
    report = lifecycle.new_report(db, project, actor["id"], data)
    access.event(
        db,
        project,
        actor["id"],
        "report.created",
        report["id"],
        request.state.correlation,
    )
    db.commit()
    return report


@api.get("/projects/{project}/reports/{report_id}", tags=["Reports"])
def report_detail(project: UUID, report_id: UUID, db: DB, request: Request):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"])
    report = lifecycle.get_report(db, project, report_id)
    snapshots = (
        db.execute(
            text("""
        SELECT id,revision,created_at,body FROM snapshots WHERE report_id=:id ORDER BY revision DESC LIMIT 50
    """),
            {"id": report_id},
        )
        .mappings()
        .all()
    )
    return dict(report) | {"snapshots": snapshots}


@api.post(
    "/projects/{project}/reports/{report_id}/snapshots",
    status_code=201,
    tags=["Reports"],
)
def report_snapshot(
    project: UUID,
    report_id: UUID,
    db: DB,
    request: Request,
    notes: Annotated[str, Form(max_length=5000)] = "",
    answer_id: Annotated[UUID | None, Form()] = None,
):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"], *WRITE)
    result = lifecycle.add_snapshot(db, project, report_id, notes, answer_id)
    access.event(
        db,
        project,
        actor["id"],
        "report.snapshot",
        result["id"],
        request.state.correlation,
    )
    db.commit()
    return result


@api.get(
    "/projects/{project}/reports/{report_id}/snapshots/{revision}/export",
    tags=["Reports"],
)
def export_report(
    project: UUID,
    report_id: UUID,
    revision: int,
    db: DB,
    request: Request,
    format: Literal["json", "md"] = "json",
):
    actor = access.identity(db, request)
    access.membership(db, project, actor["id"])
    report = lifecycle.get_report(db, project, report_id)
    body = db.scalar(
        text("SELECT body FROM snapshots WHERE report_id=:id AND revision=:num"),
        {"id": report_id, "num": revision},
    )
    if body is None:
        raise HTTPException(404, "Snapshot not found")
    if format == "md":
        content = lifecycle.markdown(report["title"], revision, body)
        return Response(
            content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="veridion-snapshot-{revision}.md"'
            },
        )
    return JSONResponse(
        {"title": report["title"], "revision": revision, **body},
        headers={
            "Content-Disposition": f'attachment; filename="veridion-snapshot-{revision}.json"'
        },
    )


def lab_scope(db: Session, request: Request, project: UUID):
    actor = access.identity(db, request)
    access.membership(
        db, project, actor["id"], "ADMIN", "RESEARCHER", "ANALYST", "REVIEWER"
    )
    if os.getenv("VERIDION_DEMO") != "1" or not db.scalar(
        text("SELECT lab FROM projects WHERE id=:id"), {"id": project}
    ):
        raise HTTPException(404, "Synthetic lab unavailable")
    return actor


@api.post("/projects/{project}/evaluations", status_code=201, tags=["Evaluation"])
def run_evaluation(project: UUID, data: contracts.Evaluation, db: DB, request: Request):
    actor = lab_scope(db, request, project)
    result = evaluation.evaluate(db, project, actor["id"], data)
    access.event(
        db,
        project,
        actor["id"],
        "evaluation.completed",
        result["id"],
        request.state.correlation,
    )
    db.commit()
    return result


@api.get("/projects/{project}/evaluations", tags=["Evaluation"])
def evaluation_history(project: UUID, db: DB, request: Request, offset: PAGE = 0):
    lab_scope(db, request, project)
    return (
        db.execute(
            text("""
        SELECT id,configuration,results,created_at FROM evaluation_runs WHERE project_id=:project
        ORDER BY created_at DESC,id LIMIT 20 OFFSET :offset
    """),
            {"project": project, "offset": offset},
        )
        .mappings()
        .all()
    )


@api.post("/projects/{project}/lab", status_code=201, tags=["Evaluation"])
def run_lab(project: UUID, db: DB, request: Request):
    actor = lab_scope(db, request, project)
    result = lab.run(db, project, actor["id"])
    access.event(
        db,
        project,
        actor["id"],
        "lab.completed",
        result["id"],
        request.state.correlation,
    )
    db.commit()
    return result


@api.get("/projects/{project}/lab", tags=["Evaluation"])
def lab_history(project: UUID, db: DB, request: Request, offset: PAGE = 0):
    lab_scope(db, request, project)
    return (
        db.execute(
            text("""
        SELECT id,results,created_at FROM lab_runs WHERE project_id=:project
        ORDER BY created_at DESC,id LIMIT 10 OFFSET :offset
    """),
            {"project": project, "offset": offset},
        )
        .mappings()
        .all()
    )


app.include_router(api)
