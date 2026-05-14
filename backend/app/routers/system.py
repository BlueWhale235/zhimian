from typing import Any

from fastapi import APIRouter

from ..common import settings_response
from ..db import get_conn
from ..schemas import SettingsUpdate

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/settings")
def read_settings() -> dict[str, Any]:
    return settings_response()


@router.put("/settings")
def update_settings(payload: SettingsUpdate) -> dict[str, Any]:
    with get_conn() as conn:
        for key, value in payload.model_dump().items():
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value)),
            )
        conn.commit()
    return settings_response()
