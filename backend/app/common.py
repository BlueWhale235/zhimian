from typing import Any

from .db import DEFAULT_NORMAL_PROMPT, DEFAULT_PRESSURE_PROMPT, get_settings


def public_resume(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for key in ("file_path", "thumbnail_path"):
        if out.get(key):
            out[f"{key}_url"] = f"/{out[key]}"
    parsed_text = out.get("parsed_text") or ""
    out["has_parsed_text"] = len(parsed_text.strip()) >= 80
    return out


def settings_response() -> dict[str, Any]:
    settings = get_settings()
    return {
        "base_url": settings.get("base_url", ""),
        "api_key": settings.get("api_key", ""),
        "model": settings.get("model", "gpt-4o"),
        "jd_model": settings.get("jd_model", ""),
        "url_extract_model": settings.get("url_extract_model", ""),
        "resume_extract_model": settings.get("resume_extract_model", ""),
        "interview_model": settings.get("interview_model", ""),
        "report_model": settings.get("report_model", ""),
        "max_rounds": int(settings.get("max_rounds", "6")),
        "pressure_level": int(settings.get("pressure_level", "3")),
        "normal_interviewer_prompt": settings.get("normal_interviewer_prompt", DEFAULT_NORMAL_PROMPT),
        "pressure_interviewer_prompt": settings.get("pressure_interviewer_prompt", DEFAULT_PRESSURE_PROMPT),
    }
