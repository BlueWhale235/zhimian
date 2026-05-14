import json
from typing import Any

from fastapi import APIRouter

from ..common import public_resume
from ..db import STATIC_DIR, decode_json, get_conn
from ..pdf_utils import export_profile_pdf, extract_pdf_text
from ..schemas import ResumeProfileUpdate

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("")
def get_profile() -> dict[str, Any]:
    empty = {"personal": {}, "education": [], "internships": [], "projects": [], "summary": ""}
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM resume_profiles WHERE id = 1").fetchone()
    return {"data": decode_json(row["data_json"], empty) if row else empty}


@router.put("")
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


@router.post("/export")
def export_profile() -> dict[str, Any]:
    profile = get_profile()["data"]
    filename, file_path, thumbnail = export_profile_pdf(profile)
    parsed_text = extract_pdf_text(STATIC_DIR.parent / file_path) if file_path else ""
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO resumes (filename, original_name, file_path, thumbnail_path, parsed_text, text_extraction_source, text_extracted_at, source_type)
            VALUES (?, ?, ?, ?, ?, 'local', CURRENT_TIMESTAMP, 'generated')
            """,
            (filename, "在线简历.pdf", file_path, thumbnail, parsed_text),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM resumes WHERE id = ?", (cur.lastrowid,)).fetchone()
    return public_resume(dict(row))
