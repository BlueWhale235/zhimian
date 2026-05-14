import json
import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "app.db"
STATIC_DIR = BASE_DIR / "static"
DEFAULT_NORMAL_PROMPT = (
    "你是中文模拟面试官。风格温和、引导式，重点考察候选人简历内容、项目经历、"
    "岗位匹配度、沟通表达和基础专业能力。一次只提出一个清晰问题，不要替候选人作答。"
)
DEFAULT_PRESSURE_PROMPT = (
    "你是中文压力面试官。风格直接、犀利，重点追问技术细节、逻辑漏洞、结果真实性、"
    "数据支撑和候选人在被质疑时的表达稳定性。一次只提出一个清晰问题，不要替候选人作答。"
)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def decode_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def init_db() -> None:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("resumes", "thumbnails", "generated"):
        (STATIC_DIR / name).mkdir(parents=True, exist_ok=True)

    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                original_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                thumbnail_path TEXT,
                parsed_text TEXT,
                text_extraction_source TEXT,
                text_extracted_at TEXT,
                source_type TEXT NOT NULL DEFAULT 'upload',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS resume_profiles (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                data_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS job_descriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT,
                content TEXT NOT NULL,
                company_background TEXT,
                requirements_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS interview_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER,
                jd_id INTEGER,
                mode TEXT NOT NULL,
                max_rounds INTEGER NOT NULL,
                pressure_level INTEGER NOT NULL DEFAULT 3,
                interviewer_prompt TEXT,
                company_background TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT,
                FOREIGN KEY (resume_id) REFERENCES resumes(id),
                FOREIGN KEY (jd_id) REFERENCES job_descriptions(id)
            );

            CREATE TABLE IF NOT EXISTS interview_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                audio_path TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS feedback_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL UNIQUE,
                summary TEXT NOT NULL,
                star_json TEXT NOT NULL,
                highlights_json TEXT NOT NULL,
                improvements_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )

        defaults = {
            "base_url": "https://api.openai.com/v1",
            "api_key": "",
            "model": "gpt-4o",
            "jd_model": "",
            "url_extract_model": "",
            "resume_extract_model": "",
            "interview_model": "",
            "report_model": "",
            "max_rounds": "6",
            "pressure_level": "3",
            "normal_interviewer_prompt": DEFAULT_NORMAL_PROMPT,
            "pressure_interviewer_prompt": DEFAULT_PRESSURE_PROMPT,
        }
        session_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(interview_sessions)").fetchall()
        }
        if "interviewer_prompt" not in session_columns:
            conn.execute("ALTER TABLE interview_sessions ADD COLUMN interviewer_prompt TEXT")
        if "company_background" not in session_columns:
            conn.execute("ALTER TABLE interview_sessions ADD COLUMN company_background TEXT")
        jd_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(job_descriptions)").fetchall()
        }
        if "company_background" not in jd_columns:
            conn.execute("ALTER TABLE job_descriptions ADD COLUMN company_background TEXT")
        resume_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(resumes)").fetchall()
        }
        if "parsed_text" not in resume_columns:
            conn.execute("ALTER TABLE resumes ADD COLUMN parsed_text TEXT")
        if "text_extraction_source" not in resume_columns:
            conn.execute("ALTER TABLE resumes ADD COLUMN text_extraction_source TEXT")
        if "text_extracted_at" not in resume_columns:
            conn.execute("ALTER TABLE resumes ADD COLUMN text_extracted_at TEXT")
        existing_legacy = conn.execute(
            "SELECT value FROM settings WHERE key = 'interviewer_prompt'"
        ).fetchone()
        if existing_legacy:
            defaults["normal_interviewer_prompt"] = existing_legacy["value"]
        for key, value in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        conn.commit()


def get_settings() -> dict[str, str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: row["value"] for row in rows}
