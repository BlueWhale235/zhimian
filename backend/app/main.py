import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .ai import AIConfigError, AIServiceError, extract_jd_requirements, generate_question, generate_report
from .db import DEFAULT_INTERVIEWER_PROMPT, STATIC_DIR, decode_json, get_conn, get_settings, init_db, row_to_dict
from .pdf_utils import export_profile_pdf, make_thumbnail, rel
from .schemas import AnswerCreate, InterviewCreate, JDCreate, ResumeProfileUpdate, SettingsUpdate

app = FastAPI(title="职面 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def public(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for key in ("file_path", "thumbnail_path"):
        if out.get(key):
            out[f"{key}_url"] = f"/{out[key]}"
    return out


def _settings_response() -> dict[str, Any]:
    settings = get_settings()
    return {
        "base_url": settings.get("base_url", ""),
        "api_key": settings.get("api_key", ""),
        "model": settings.get("model", "gpt-4o"),
        "max_rounds": int(settings.get("max_rounds", "6")),
        "pressure_level": int(settings.get("pressure_level", "3")),
        "interviewer_prompt": settings.get("interviewer_prompt", DEFAULT_INTERVIEWER_PROMPT),
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/settings")
def read_settings() -> dict[str, Any]:
    return _settings_response()


@app.put("/api/settings")
def update_settings(payload: SettingsUpdate) -> dict[str, Any]:
    with get_conn() as conn:
        for key, value in payload.model_dump().items():
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value)),
            )
        conn.commit()
    return _settings_response()


@app.get("/api/resumes")
def list_resumes() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM resumes ORDER BY created_at DESC").fetchall()
    return [public(dict(row)) for row in rows]


@app.post("/api/resumes")
async def upload_resume(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "仅支持上传 PDF 简历。")
    filename = f"{uuid.uuid4().hex}.pdf"
    target = STATIC_DIR / "resumes" / filename
    with target.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    thumbnail = make_thumbnail(target)
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO resumes (filename, original_name, file_path, thumbnail_path, source_type)
            VALUES (?, ?, ?, ?, 'upload')
            """,
            (filename, file.filename, rel(target), thumbnail),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM resumes WHERE id = ?", (cur.lastrowid,)).fetchone()
    return public(dict(row))


@app.delete("/api/resumes/{resume_id}")
def delete_resume(resume_id: int) -> dict[str, bool]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,)).fetchone()
        if not row:
            raise HTTPException(404, "简历不存在。")
        data = dict(row)
        conn.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
        conn.commit()
    for key in ("file_path", "thumbnail_path"):
        if data.get(key):
            path = STATIC_DIR.parent / data[key]
            if path.exists():
                path.unlink()
    return {"ok": True}


@app.get("/api/profile")
def get_profile() -> dict[str, Any]:
    empty = {"personal": {}, "education": [], "internships": [], "projects": [], "summary": ""}
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM resume_profiles WHERE id = 1").fetchone()
    return {"data": decode_json(row["data_json"], empty) if row else empty}


@app.put("/api/profile")
def save_profile(payload: ResumeProfileUpdate) -> dict[str, Any]:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO resume_profiles (id, data_json, updated_at)
            VALUES (1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET data_json = excluded.data_json, updated_at = CURRENT_TIMESTAMP
            """,
            (json.dumps(payload.data, ensure_ascii=False),),
        )
        conn.commit()
    return {"data": payload.data}


@app.post("/api/profile/export")
def export_profile() -> dict[str, Any]:
    profile = get_profile()["data"]
    filename, file_path, thumbnail = export_profile_pdf(profile)
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO resumes (filename, original_name, file_path, thumbnail_path, source_type)
            VALUES (?, ?, ?, ?, 'generated')
            """,
            (filename, "在线简历.pdf", file_path, thumbnail),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM resumes WHERE id = ?", (cur.lastrowid,)).fetchone()
    return public(dict(row))


@app.get("/api/jds")
def list_jds() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM job_descriptions ORDER BY created_at DESC").fetchall()
    data = []
    for row in rows:
        item = dict(row)
        item["requirements"] = decode_json(item.pop("requirements_json"), {})
        data.append(item)
    return data


@app.post("/api/jds")
async def create_jd(payload: JDCreate) -> dict[str, Any]:
    requirements = {}
    try:
        requirements = await extract_jd_requirements(get_settings(), payload.content)
    except AIConfigError:
        requirements = {"skills": [], "responsibilities": [], "keywords": [], "seniority": "待配置模型后提取"}
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO job_descriptions (title, company, content, requirements_json)
            VALUES (?, ?, ?, ?)
            """,
            (payload.title, payload.company, payload.content, json.dumps(requirements, ensure_ascii=False)),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM job_descriptions WHERE id = ?", (cur.lastrowid,)).fetchone()
    item = dict(row)
    item["requirements"] = decode_json(item.pop("requirements_json"), {})
    return item


@app.post("/api/jds/{jd_id}/extract")
async def extract_jd(jd_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM job_descriptions WHERE id = ?", (jd_id,)).fetchone()
        if not row:
            raise HTTPException(404, "JD 不存在。")
    try:
        requirements = await extract_jd_requirements(get_settings(), row["content"])
    except AIConfigError as exc:
        raise HTTPException(400, str(exc)) from exc
    except AIServiceError as exc:
        raise HTTPException(504, str(exc)) from exc
    with get_conn() as conn:
        conn.execute(
            "UPDATE job_descriptions SET requirements_json = ? WHERE id = ?",
            (json.dumps(requirements, ensure_ascii=False), jd_id),
        )
        conn.commit()
    return {"requirements": requirements}


@app.delete("/api/jds/{jd_id}")
def delete_jd(jd_id: int) -> dict[str, bool]:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM job_descriptions WHERE id = ?", (jd_id,)).fetchone()
        if not row:
            raise HTTPException(404, "JD 不存在。")
        conn.execute("DELETE FROM job_descriptions WHERE id = ?", (jd_id,))
        conn.commit()
    return {"ok": True}


def _session_context(conn, session_id: int) -> tuple[dict[str, Any], str, str, list[dict[str, str]]]:
    session = row_to_dict(conn.execute("SELECT * FROM interview_sessions WHERE id = ?", (session_id,)).fetchone())
    if not session:
        raise HTTPException(404, "面试场次不存在。")
    resume = row_to_dict(conn.execute("SELECT * FROM resumes WHERE id = ?", (session["resume_id"],)).fetchone())
    jd = row_to_dict(conn.execute("SELECT * FROM job_descriptions WHERE id = ?", (session["jd_id"],)).fetchone())
    messages = [
        {"role": row["role"], "content": row["content"]}
        for row in conn.execute(
            "SELECT role, content FROM interview_messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    ]
    resume_hint = resume["original_name"] if resume else "未选择简历"
    jd_hint = f"{jd['title']} {jd['company']} {jd['content'][:1200]}" if jd else "未选择 JD"
    return session, resume_hint, jd_hint, messages


@app.post("/api/interviews")
async def create_interview(payload: InterviewCreate) -> dict[str, Any]:
    settings = get_settings()
    interviewer_prompt = payload.interviewer_prompt.strip() or settings.get("interviewer_prompt", DEFAULT_INTERVIEWER_PROMPT)
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO interview_sessions (resume_id, jd_id, mode, max_rounds, pressure_level, interviewer_prompt)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (payload.resume_id, payload.jd_id, payload.mode, payload.max_rounds, payload.pressure_level, interviewer_prompt),
        )
        session_id = cur.lastrowid
        session, resume_hint, jd_hint, history = _session_context(conn, session_id)
        try:
            question = await generate_question(
                settings,
                mode=payload.mode,
                pressure_level=payload.pressure_level,
                resume_hint=resume_hint,
                jd_hint=jd_hint,
                history=history,
                interviewer_prompt=interviewer_prompt,
            )
        except AIConfigError as exc:
            conn.rollback()
            raise HTTPException(400, str(exc)) from exc
        except AIServiceError as exc:
            conn.rollback()
            raise HTTPException(504, str(exc)) from exc
        conn.execute(
            "INSERT INTO interview_messages (session_id, role, content) VALUES (?, 'assistant', ?)",
            (session_id, question),
        )
        conn.commit()
    return get_interview(session_id)


@app.get("/api/interviews")
def list_interviews() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT s.*, r.original_name AS resume_name, j.title AS jd_title
            FROM interview_sessions s
            LEFT JOIN resumes r ON r.id = s.resume_id
            LEFT JOIN job_descriptions j ON j.id = s.jd_id
            ORDER BY s.created_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/interviews/{session_id}")
def get_interview(session_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        session = row_to_dict(conn.execute(
            """
            SELECT s.*, r.original_name AS resume_name, j.title AS jd_title
            FROM interview_sessions s
            LEFT JOIN resumes r ON r.id = s.resume_id
            LEFT JOIN job_descriptions j ON j.id = s.jd_id
            WHERE s.id = ?
            """,
            (session_id,),
        ).fetchone())
        if not session:
            raise HTTPException(404, "面试场次不存在。")
        messages = [dict(row) for row in conn.execute(
            "SELECT * FROM interview_messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()]
        report = row_to_dict(conn.execute("SELECT * FROM feedback_reports WHERE session_id = ?", (session_id,)).fetchone())
    if report:
        report["star"] = decode_json(report.pop("star_json"), [])
        report["highlights"] = decode_json(report.pop("highlights_json"), [])
        report["improvements"] = decode_json(report.pop("improvements_json"), [])
    return {"session": session, "messages": messages, "report": report}


@app.delete("/api/interviews/{session_id}")
def delete_interview(session_id: int) -> dict[str, bool]:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM interview_sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            raise HTTPException(404, "面试场次不存在。")
        conn.execute("DELETE FROM feedback_reports WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM interview_messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM interview_sessions WHERE id = ?", (session_id,))
        conn.commit()
    return {"ok": True}


@app.post("/api/interviews/{session_id}/answer")
async def answer_interview(session_id: int, payload: AnswerCreate) -> dict[str, Any]:
    if not payload.content.strip():
        raise HTTPException(400, "回答不能为空。")
    with get_conn() as conn:
        session, resume_hint, jd_hint, history = _session_context(conn, session_id)
        if session["status"] != "active":
            raise HTTPException(400, "面试已结束。")
        conn.execute(
            "INSERT INTO interview_messages (session_id, role, content) VALUES (?, 'user', ?)",
            (session_id, payload.content),
        )
        user_count = conn.execute(
            "SELECT COUNT(*) AS n FROM interview_messages WHERE session_id = ? AND role = 'user'",
            (session_id,),
        ).fetchone()["n"]
        if user_count >= session["max_rounds"]:
            conn.execute(
                "UPDATE interview_sessions SET status = 'ready_to_finish' WHERE id = ?",
                (session_id,),
            )
        else:
            history = history + [{"role": "user", "content": payload.content}]
            try:
                question = await generate_question(
                    get_settings(),
                    mode=session["mode"],
                    pressure_level=session["pressure_level"],
                    resume_hint=resume_hint,
                    jd_hint=jd_hint,
                    history=history,
                    interviewer_prompt=session.get("interviewer_prompt") or "",
                )
            except AIConfigError as exc:
                raise HTTPException(400, str(exc)) from exc
            except AIServiceError as exc:
                raise HTTPException(504, str(exc)) from exc
            conn.execute(
                "INSERT INTO interview_messages (session_id, role, content) VALUES (?, 'assistant', ?)",
                (session_id, question),
            )
        conn.commit()
    return get_interview(session_id)


@app.post("/api/interviews/{session_id}/finish")
async def finish_interview(session_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        session, _, _, transcript = _session_context(conn, session_id)
        try:
            report = await generate_report(get_settings(), transcript)
        except AIConfigError as exc:
            raise HTTPException(400, str(exc)) from exc
        except AIServiceError as exc:
            raise HTTPException(504, str(exc)) from exc
        conn.execute(
            "UPDATE interview_sessions SET status = 'finished', ended_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO feedback_reports
            (session_id, summary, star_json, highlights_json, improvements_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                str(report.get("summary", "")),
                json.dumps(report.get("star", []), ensure_ascii=False),
                json.dumps(report.get("highlights", [])[:3], ensure_ascii=False),
                json.dumps(report.get("improvements", [])[:3], ensure_ascii=False),
            ),
        )
        conn.commit()
    return get_interview(session_id)
