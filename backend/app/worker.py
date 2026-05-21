import asyncio
import logging
from sqlalchemy import select
from bullmq import Worker, Queue

from app.config import settings
from app.database import SessionLocal
from app.models import Job
from app.agents.pipeline import (
    PipelineOrchestrator,
    PipelineBlockedException,
    PipelineWarningException,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Parse Redis connection details from settings.REDIS_URL
# redis://localhost:6379 -> host="localhost", port=6379
# We'll use a clean connection parser
redis_opts = {}
if settings.REDIS_URL:
    url = settings.REDIS_URL
    if url.startswith("redis://"):
        url = url[8:]
    if "@" in url:
        # handle auth if present
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
        port = 6380
    redis_opts = {"host": host, "port": port}


async def process(job_data, job_token) -> str:
    """Processes a background story extraction job."""
    data = job_data.data or {}
    job_id = data.get("job_id")
    bypass_warning = data.get("bypass_warning", False)

    if not job_id:
        logger.error("Job skipped: No job_id provided.")
        return "failed_no_id"

    logger.info(f"Worker picked up job {job_id} (Bypass Warning: {bypass_warning})")

    # Create DB Session
    async with SessionLocal() as db:
        try:
            # Query Job
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalars().first()
            if not job:
                logger.error(f"Job {job_id} not found in DB.")
                return "job_not_found"

            # Create Orchestrator
            orchestrator = PipelineOrchestrator(db)

            # Execute Pipeline
            await orchestrator.run(job_id, bypass_warning=bypass_warning)

            # Re-fetch or refresh job state to confirm completion
            await db.refresh(job)
            if job.status == "done":
                return "success"
            return "incomplete"

        except (PipelineBlockedException, PipelineWarningException) as e:
            # Domain failures - update database and stop
            logger.warning(f"Job {job_id} halted due to domain rule: {e}")
            job.status = "failed"
            job.error_message = str(e)
            await db.commit()
            return "failed_domain"

        except Exception as e:
            logger.error(f"Job {job_id} failed with exception: {e}", exc_info=True)

            # Re-query inside new transaction block if session is corrupted
            job.retry_count = (job.retry_count or 0) + 1
            job.error_message = str(e)

            if job.retry_count >= 3:
                job.status = "failed"
                logger.error(
                    f"Job {job_id} exceeded maximum retries (3) and is marked failed."
                )
            else:
                job.status = (
                    "pending"  # Mark as pending so it can be picked up or retried
                )
                logger.info(
                    f"Job {job_id} marked for retry. Current attempts: {job.retry_count}/3"
                )

                # Re-queue the job with a 10 second delay for recovery
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
                        {"job_id": job_id, "bypass_warning": bypass_warning},
                        {"delay": 10000},  # 10s delay
                    )
                    await queue.close()
                except Exception as q_err:
                    logger.error(f"Failed to auto-requeue job {job_id}: {q_err}")

            await db.commit()
            return "failed_retry"


async def main():
    logger.info(
        f"Initializing BullMQ Worker on queue 'story-extraction-queue' with Redis config: {redis_opts}"
    )
    # Initialize BullMQ Worker
    worker = Worker(
        "story-extraction-queue",
        process,
        {
            "connection": {
                "host": "localhost",
                "port": 6380,
                # optional:
                # "db": 0
            }
        }
    )

    # Keep worker running
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("Worker shutting down...")
    finally:
        await worker.close()


if __name__ == "__main__":
    asyncio.run(main())
