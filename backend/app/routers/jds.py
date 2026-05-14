import json
from typing import Any

from fastapi import APIRouter, HTTPException

from ..ai import AIConfigError, AIServiceError, extract_jd_from_url, extract_jd_requirements
from ..db import decode_json, get_conn, get_settings
from ..schemas import JDCreate, JDUpdate, JDUrlExtract

router = APIRouter(prefix="/api/jds", tags=["jds"])


def _public_jd(row: Any) -> dict[str, Any]:
    item = dict(row)
    item["requirements"] = decode_json(item.pop("requirements_json"), {})
    item["company_background"] = item.get("company_background") or ""
    return item


@router.get("")
def list_jds() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM job_descriptions ORDER BY created_at DESC").fetchall()
    return [_public_jd(row) for row in rows]


@router.post("")
async def create_jd(payload: JDCreate) -> dict[str, Any]:
    requirements = {}
    try:
        requirements = await extract_jd_requirements(get_settings(), payload.content)
    except AIConfigError:
        requirements = {"skills": [], "responsibilities": [], "keywords": [], "seniority": "待配置模型后提取"}
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO job_descriptions (title, company, content, company_background, requirements_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (payload.title, payload.company, payload.content, payload.company_background, json.dumps(requirements, ensure_ascii=False)),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM job_descriptions WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _public_jd(row)


@router.post("/extract-url")
async def extract_jd_url(payload: JDUrlExtract) -> dict[str, Any]:
    try:
        data = await extract_jd_from_url(get_settings(), payload.url)
    except AIConfigError as exc:
        raise HTTPException(400, str(exc)) from exc
    except AIServiceError as exc:
        raise HTTPException(504, str(exc)) from exc
    return {
        "title": str(data.get("title") or ""),
        "company": str(data.get("company") or ""),
        "content": str(data.get("content") or ""),
        "company_background": str(data.get("company_background") or ""),
    }


@router.post("/{jd_id}/extract")
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


@router.put("/{jd_id}")
def update_jd(jd_id: int, payload: JDUpdate) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM job_descriptions WHERE id = ?", (jd_id,)).fetchone()
        if not row:
            raise HTTPException(404, "JD 不存在。")
        conn.execute(
            """
            UPDATE job_descriptions
            SET title = ?, company = ?, content = ?, company_background = ?
            WHERE id = ?
            """,
            (payload.title, payload.company, payload.content, payload.company_background, jd_id),
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM job_descriptions WHERE id = ?", (jd_id,)).fetchone()
    return _public_jd(updated)


@router.delete("/{jd_id}")
def delete_jd(jd_id: int) -> dict[str, bool]:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM job_descriptions WHERE id = ?", (jd_id,)).fetchone()
        if not row:
            raise HTTPException(404, "JD 不存在。")
        conn.execute("DELETE FROM job_descriptions WHERE id = ?", (jd_id,))
        conn.commit()
    return {"ok": True}
