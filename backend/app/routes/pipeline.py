import json
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bullmq import Queue

from app.database import get_db, SessionLocal
from app.models import Job, User
from app.schemas import JobCreate, JobRead, DraftUpdate
from app.config import settings

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])
logger = logging.getLogger(__name__)

# Parse Redis connection details from settings.REDIS_URL
redis_opts = {}
if settings.REDIS_URL:
    url = settings.REDIS_URL
    if url.startswith("redis://"):
        url = url[8:]
    if "@" in url:
        auth, host_port = url.split("@", 1)
    else:
        host_port = url

    if ":" in host_port:
        host, port_str = host_port.split(":", 1)
        if "/" in port_str:
            port_str = port_str.split("/", 1)[0]
        port = int(port_str)
    else:
        host = host_port
        port = 6379
    redis_opts = {"host": host, "port": port}


@router.post("/trigger", response_model=JobRead)
async def trigger_pipeline(
    payload: JobCreate,
    user_id: str,
    bypass_warning: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Triggers the multi-agent story extraction pipeline for a repository."""
    # Verify User exists
    user_stmt = select(User).where(User.id == user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Check if a running job already exists for this repository to prevent duplicate runs
    stmt = select(Job).where(
        Job.user_id == user_id,
        Job.repo_id == payload.repo_id,
        Job.status.in_(["pending", "running"]),
    )
    res = await db.execute(stmt)
    existing_job = res.scalars().first()
    if existing_job:
        logger.info(
            f"Returning active job {existing_job.id} for repo {payload.repo_name}"
        )
        return existing_job

    # Create new Job record
    new_job = Job(
        user_id=user_id,
        repo_id=payload.repo_id,
        repo_name=payload.repo_name,
        repo_full_name=payload.repo_full_name,
        repo_pushed_at=payload.repo_pushed_at,
        status="pending",
        checkpoint="none",
        retry_count=0,
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    # Queue the job in BullMQ
    try:
        queue = Queue(
                    "story-extraction-queue",
                    {
                        "host": "localhost",
                        "port": 6380,
                    }
                )
        await queue.add(
                    "extract-story",
                    {
                        "job_id": new_job.id,
                        "bypass_warning": bypass_warning
                    }
                )
        await queue.close()
        logger.info(f"Queued story extraction task in BullMQ for job {new_job.id}")
    except Exception as e:
        logger.error(f"Failed to queue task in BullMQ: {e}")
        # Revert job status on queue failure
        new_job.status = "failed"
        new_job.error_message = f"Queueing error: {str(e)}"
        await db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Background queue connection failed. Database entry created but pipeline trigger failed: {e}",
        )

    return new_job


@router.get("/status/{job_id}", response_model=JobRead)
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve full details of a specific job."""
    stmt = select(Job).where(Job.id == job_id)
    res = await db.execute(stmt)
    job = res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.get("/status/{job_id}/stream")
async def stream_job_status(job_id: str):
    """Streams job status and checkpoint changes to the client in real-time via Server-Sent Events (SSE)."""

    async def event_generator():
        last_status = None
        last_checkpoint = None

        while True:
            # Query db for status in an isolated block
            async with SessionLocal() as db:
                stmt = select(Job).where(Job.id == job_id)
                res = await db.execute(stmt)
                job = res.scalars().first()

                if not job:
                    yield f"event: error\ndata: {json.dumps({'error': 'Job not found'})}\n\n"
                    break

                job_data = {
                    "id": job.id,
                    "status": job.status,
                    "checkpoint": job.checkpoint,
                    "error_message": job.error_message,
                    "retry_count": job.retry_count,
                    "input_tokens": job.input_tokens,
                    "output_tokens": job.output_tokens,
                    "model_used": job.model_used,
                }

                # Yield update if status or checkpoint changed
                if job.status != last_status or job.checkpoint != last_checkpoint:
                    last_status = job.status
                    last_checkpoint = job.checkpoint
                    yield f"data: {json.dumps(job_data)}\n\n"

                # Stop streaming if job completed or failed
                if job.status in ["done", "failed"]:
                    break

            await asyncio.sleep(1.0)  # check database every second

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.put("/jobs/{job_id}/draft", response_model=JobRead)
async def update_job_draft(
    job_id: str, payload: DraftUpdate, db: AsyncSession = Depends(get_db)
):
    """Updates one of the generated post drafts within the job's JSONB agent3_output field."""
    stmt = select(Job).where(Job.id == job_id)
    res = await db.execute(stmt)
    job = res.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if not job.agent3_output or "posts" not in job.agent3_output:
        raise HTTPException(
            status_code=400, detail="No drafts generated for this job yet."
        )

    posts = job.agent3_output["posts"]
    if payload.post_index < 0 or payload.post_index >= len(posts):
        raise HTTPException(status_code=400, detail="Invalid post draft index.")

    # Update content in place
    posts[payload.post_index]["content"] = payload.content

    # Re-assign to flag SQLAlchemy JSON tracking
    job.agent3_output = {"posts": posts}
    await db.commit()
    await db.refresh(job)
    return job
