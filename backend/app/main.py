from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .db import STATIC_DIR, init_db
from .routers import interviews, jds, profile, resumes, system

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

app.include_router(system.router)
app.include_router(resumes.router)
app.include_router(profile.router)
app.include_router(jds.router)
app.include_router(interviews.router)
