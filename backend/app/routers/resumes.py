import shutil
import uuid
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..ai import AIConfigError, AIServiceError, extract_resume_text
from ..common import public_resume
from ..db import STATIC_DIR, get_conn, get_settings
from ..pdf_utils import extract_pdf_text, make_thumbnail, pdf_page_images_as_data_urls, rel

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


@router.get("")
def list_resumes() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM resumes ORDER BY created_at DESC").fetchall()
    return [public_resume(dict(row)) for row in rows]


@router.post("")
async def upload_resume(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "仅支持上传 PDF 简历。")
    filename = f"{uuid.uuid4().hex}.pdf"
    target = STATIC_DIR / "resumes" / filename
    with target.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    thumbnail = make_thumbnail(target)
    parsed_text = extract_pdf_text(target)
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO resumes (filename, original_name, file_path, thumbnail_path, parsed_text, text_extraction_source, text_extracted_at, source_type)
            VALUES (?, ?, ?, ?, ?, 'local', CURRENT_TIMESTAMP, 'upload')
            """,
            (filename, file.filename, rel(target), thumbnail, parsed_text),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM resumes WHERE id = ?", (cur.lastrowid,)).fetchone()
    return public_resume(dict(row))


@router.post("/{resume_id}/extract-text")
async def extract_resume_text_endpoint(resume_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,)).fetchone()
        if not row:
            raise HTTPException(404, "简历不存在。")
        data = dict(row)
    pdf_path = STATIC_DIR.parent / data["file_path"]
    if not pdf_path.exists():
        raise HTTPException(404, "简历文件不存在。")
    local_text = extract_pdf_text(pdf_path)
    images = pdf_page_images_as_data_urls(pdf_path) if len(local_text.strip()) < 300 else []
    try:
        parsed_text = await extract_resume_text(get_settings(), local_text, images)
    except AIConfigError as exc:
        raise HTTPException(400, str(exc)) from exc
    except AIServiceError as exc:
        raise HTTPException(504, str(exc)) from exc
    if not parsed_text.strip():
        parsed_text = local_text
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE resumes
            SET parsed_text = ?, text_extraction_source = 'ai', text_extracted_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (parsed_text, resume_id),
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,)).fetchone()
    return public_resume(dict(updated))


@router.delete("/{resume_id}")
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
