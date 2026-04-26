from typing import Any, Literal

from pydantic import BaseModel, Field


class SettingsUpdate(BaseModel):
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o"
    max_rounds: int = Field(default=6, ge=1, le=20)
    pressure_level: int = Field(default=3, ge=1, le=5)
    interviewer_prompt: str = Field(default="", max_length=5000)


class JDCreate(BaseModel):
    title: str
    company: str = ""
    content: str


class ResumeProfileUpdate(BaseModel):
    data: dict[str, Any]


class InterviewCreate(BaseModel):
    resume_id: int | None = None
    jd_id: int | None = None
    mode: Literal["normal", "pressure"] = "normal"
    max_rounds: int = Field(default=6, ge=1, le=20)
    pressure_level: int = Field(default=3, ge=1, le=5)
    interviewer_prompt: str = Field(default="", max_length=5000)


class AnswerCreate(BaseModel):
    content: str


class ApiError(BaseModel):
    detail: str
