import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..ai import AIConfigError, AIServiceError, generate_question, generate_report, stream_question
from ..db import DEFAULT_NORMAL_PROMPT, DEFAULT_PRESSURE_PROMPT, decode_json, get_conn, get_settings, row_to_dict
from ..schemas import AnswerCreate, InterviewCreate

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


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
    if resume:
        parsed_text = (resume.get("parsed_text") or "").strip()
        resume_hint = (
            f"简历文件：{resume['original_name']}\n简历原文：\n{parsed_text[:12000]}"
            if len(parsed_text) >= 80
            else f"简历文件：{resume['original_name']}。未提取到有效简历文本，请降低对简历细节的依赖。"
        )
    else:
        resume_hint = "未选择简历"
    jd_hint = (
        f"{jd['title']} {jd['company']} {jd['content'][:3000]}"
        if jd
        else "未选择 JD。请进入通用求职/职业闲聊式模拟，围绕候选人的自我介绍、经历、职业规划和通用能力提问。"
    )
    company_background = jd["company_background"] if jd and jd.get("company_background") else ""
    if company_background:
        jd_hint = f"{jd_hint}\n公司背景：{company_background[:2000]}"
    return session, resume_hint, jd_hint, messages


@router.post("")
async def create_interview(payload: InterviewCreate) -> dict[str, Any]:
    settings = get_settings()
    default_prompt = (
        settings.get("pressure_interviewer_prompt", DEFAULT_PRESSURE_PROMPT)
        if payload.mode == "pressure"
        else settings.get("normal_interviewer_prompt", DEFAULT_NORMAL_PROMPT)
    )
    interviewer_prompt = payload.interviewer_prompt.strip() or default_prompt
    company_background = ""
    if payload.jd_id:
        with get_conn() as lookup_conn:
            jd_row = lookup_conn.execute(
                "SELECT company_background FROM job_descriptions WHERE id = ?",
                (payload.jd_id,),
            ).fetchone()
            company_background = jd_row["company_background"] if jd_row and jd_row["company_background"] else ""
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO interview_sessions (resume_id, jd_id, mode, max_rounds, pressure_level, interviewer_prompt, company_background)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (payload.resume_id, payload.jd_id, payload.mode, payload.max_rounds, payload.pressure_level, interviewer_prompt, company_background),
        )
        session_id = cur.lastrowid
        _, resume_hint, jd_hint, history = _session_context(conn, session_id)
        try:
            question = await generate_question(
                settings,
                mode=payload.mode,
                pressure_level=payload.pressure_level,
                resume_hint=resume_hint,
                jd_hint=jd_hint,
                history=history,
                interviewer_prompt=interviewer_prompt,
                company_background=company_background,
                current_round=0,
                max_rounds=payload.max_rounds,
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


@router.get("")
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


@router.get("/{session_id}")
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


@router.delete("/{session_id}")
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


@router.post("/{session_id}/answer")
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
        is_final_turn = user_count >= session["max_rounds"]
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
                company_background=session.get("company_background") or "",
                current_round=user_count,
                max_rounds=session["max_rounds"],
                is_final_turn=is_final_turn,
            )
        except AIConfigError as exc:
            raise HTTPException(400, str(exc)) from exc
        except AIServiceError as exc:
            raise HTTPException(504, str(exc)) from exc
        conn.execute(
            "INSERT INTO interview_messages (session_id, role, content) VALUES (?, 'assistant', ?)",
            (session_id, question),
        )
        if is_final_turn:
            conn.execute(
                "UPDATE interview_sessions SET status = 'ready_to_finish' WHERE id = ?",
                (session_id,),
            )
        conn.commit()
    return get_interview(session_id)


@router.post("/{session_id}/answer/stream")
async def answer_interview_stream(session_id: int, payload: AnswerCreate) -> StreamingResponse:
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
        conn.commit()

    history = history + [{"role": "user", "content": payload.content}]
    settings = get_settings()
    is_final_turn = user_count >= session["max_rounds"]

    async def event_stream():
        chunks: list[str] = []
        used_stream = True
        try:
            async for delta in stream_question(
                settings,
                mode=session["mode"],
                pressure_level=session["pressure_level"],
                resume_hint=resume_hint,
                jd_hint=jd_hint,
                history=history,
                interviewer_prompt=session.get("interviewer_prompt") or "",
                company_background=session.get("company_background") or "",
                current_round=user_count,
                max_rounds=session["max_rounds"],
                is_final_turn=is_final_turn,
            ):
                chunks.append(delta)
                yield json.dumps({"type": "delta", "content": delta}, ensure_ascii=False) + "\n"
        except Exception:
            used_stream = False
            question = await generate_question(
                settings,
                mode=session["mode"],
                pressure_level=session["pressure_level"],
                resume_hint=resume_hint,
                jd_hint=jd_hint,
                history=history,
                interviewer_prompt=session.get("interviewer_prompt") or "",
                company_background=session.get("company_background") or "",
                current_round=user_count,
                max_rounds=session["max_rounds"],
                is_final_turn=is_final_turn,
            )
            chunks = [question]
            yield json.dumps({"type": "delta", "content": question}, ensure_ascii=False) + "\n"

        content = "".join(chunks).strip()
        if content:
            with get_conn() as conn:
                conn.execute(
                    "INSERT INTO interview_messages (session_id, role, content) VALUES (?, 'assistant', ?)",
                    (session_id, content),
                )
                if is_final_turn:
                    conn.execute(
                        "UPDATE interview_sessions SET status = 'ready_to_finish' WHERE id = ?",
                        (session_id,),
                    )
                conn.commit()
        yield json.dumps(
            {"type": "done", "stream": used_stream, "interview": get_interview(session_id)},
            ensure_ascii=False,
        ) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.post("/{session_id}/finish")
async def finish_interview(session_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        _, _, _, transcript = _session_context(conn, session_id)
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
