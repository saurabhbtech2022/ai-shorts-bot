"""FastAPI application for manual control and optional scheduled runs."""

from __future__ import annotations

import traceback
import uuid
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.config import OUTPUT_DIR, get_settings
from app.logger import setup_logging
from app.pipeline import _today_in_tz, run_pipeline
from app.prompts_loader import ScenePrompt, load_prompts
from app.scheduler import start_scheduler, stop_scheduler
from app.state import advance_index, completed_slots_today, read_state, reset_state, write_state

logger = setup_logging()


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str


class HistoryItem(BaseModel):
    date: str | None = None
    slot: str | None = None
    title: str | None = None
    video_id: str | None = None


class StatusResponse(BaseModel):
    index: int
    next_scene_title: str | None
    last_run_date: str | None
    completed_slots_today: list[str]
    history: list[HistoryItem]


class PromptItem(BaseModel):
    index: int
    title_hindi: str
    image_prompt_en: str
    caption_hindi: str


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobDetailResponse(BaseModel):
    job_id: str
    status: JobStatus
    result: dict[str, Any] | None = None
    error: str | None = None


class PreviewResponse(BaseModel):
    image_path: str
    video_path: str
    title: str


class MessageResponse(BaseModel):
    message: str
    index: int | None = None


_jobs: dict[str, dict[str, Any]] = {}


def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    settings = get_settings()
    if not settings.api_key:
        raise HTTPException(status_code=500, detail="API_KEY not configured on server")
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.run_scheduler:
        start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="AI Shorts Bot",
    description="Automated Ramayan/Mahabharat YouTube Shorts pipeline API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    logger.error("Unhandled error on %s: %s", request.url.path, exc)
    logger.debug(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


def _scene_to_item(scene: ScenePrompt) -> PromptItem:
    return PromptItem(
        index=scene.index,
        title_hindi=scene.title_hindi,
        image_prompt_en=scene.image_prompt_en,
        caption_hindi=scene.caption_hindi,
    )


def _run_job(job_id: str, dry_run: bool, force: bool, slot: str | None) -> None:
    _jobs[job_id]["status"] = JobStatus.running
    try:
        result = run_pipeline(dry_run=dry_run, force=force, slot=slot)
        _jobs[job_id]["status"] = JobStatus.completed
        _jobs[job_id]["result"] = result
    except Exception as exc:
        _jobs[job_id]["status"] = JobStatus.failed
        _jobs[job_id]["error"] = str(exc)
        logger.exception("Job %s failed", job_id)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    from app import __version__

    return HealthResponse(status="ok", version=__version__)


@app.get("/status", response_model=StatusResponse, tags=["pipeline"], dependencies=[Depends(verify_api_key)])
def status() -> StatusResponse:
    state = read_state()
    prompts = load_prompts()
    idx = int(state.get("index", 0)) % len(prompts)
    next_title = prompts[idx].title_hindi
    history_raw = state.get("history") or []
    history = [HistoryItem(**h) for h in history_raw[-10:]]
    return StatusResponse(
        index=int(state.get("index", 0)),
        next_scene_title=next_title,
        last_run_date=state.get("last_run_date"),
        completed_slots_today=completed_slots_today(_today_in_tz()),
        history=history,
    )


@app.get("/prompts", response_model=list[PromptItem], tags=["pipeline"], dependencies=[Depends(verify_api_key)])
def list_prompts() -> list[PromptItem]:
    return [_scene_to_item(s) for s in load_prompts()]


@app.post("/run", response_model=JobResponse, tags=["pipeline"], dependencies=[Depends(verify_api_key)])
def trigger_run(
    background_tasks: BackgroundTasks,
    dry_run: bool = Query(default=False),
    force: bool = Query(default=False),
    slot: str | None = Query(default=None, description="morning | afternoon | evening"),
) -> JobResponse:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": JobStatus.pending, "result": None, "error": None}
    background_tasks.add_task(_run_job, job_id, dry_run, force, slot)
    return JobResponse(job_id=job_id, status=JobStatus.pending)


@app.get(
    "/jobs/{job_id}",
    response_model=JobDetailResponse,
    tags=["pipeline"],
    dependencies=[Depends(verify_api_key)],
)
def get_job(job_id: str) -> JobDetailResponse:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetailResponse(
        job_id=job_id,
        status=job["status"],
        result=job.get("result"),
        error=job.get("error"),
    )


@app.post("/preview", response_model=PreviewResponse, tags=["pipeline"], dependencies=[Depends(verify_api_key)])
def preview(slot: str | None = Query(default=None)) -> PreviewResponse:
    result = run_pipeline(dry_run=True, force=True, slot=slot)
    if not result.get("video_path") or not result.get("image_path"):
        raise HTTPException(status_code=500, detail="Preview generation failed")
    return PreviewResponse(
        image_path=result["image_path"],
        video_path=result["video_path"],
        title=result.get("title") or "",
    )


@app.get("/download/latest", tags=["files"], dependencies=[Depends(verify_api_key)])
def download_latest() -> FileResponse:
    if not OUTPUT_DIR.is_dir():
        raise HTTPException(status_code=404, detail="No output yet")
    candidates: list[Path] = []
    for date_dir in OUTPUT_DIR.iterdir():
        if not date_dir.is_dir():
            continue
        slot_video = date_dir / "short.mp4"
        if slot_video.is_file():
            candidates.append(slot_video)
        for slot_dir in date_dir.iterdir():
            if slot_dir.is_dir():
                v = slot_dir / "short.mp4"
                if v.is_file():
                    candidates.append(v)
    for video in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
        return FileResponse(
            path=video,
            media_type="video/mp4",
            filename=f"short-{video.parent.name}.mp4",
        )
    raise HTTPException(status_code=404, detail="No video found")


@app.post("/skip", response_model=MessageResponse, tags=["pipeline"], dependencies=[Depends(verify_api_key)])
def skip_scene() -> MessageResponse:
    count = len(load_prompts())
    state = read_state()
    current = int(state.get("index", 0))
    state["index"] = advance_index(current, count, step=1)
    write_state(state)
    return MessageResponse(message="Skipped to next scene", index=int(state["index"]))


@app.post("/reset", response_model=MessageResponse, tags=["pipeline"], dependencies=[Depends(verify_api_key)])
def reset_index() -> MessageResponse:
    state = reset_state()
    return MessageResponse(message="Index reset to 0", index=int(state["index"]))
