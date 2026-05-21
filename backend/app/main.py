import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routes import auth, repos, pipeline
from app.models import User, Job

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)



from sqlalchemy import text

@asynccontextmanager
async def lifespan(app: FastAPI):

    async with engine.begin() as conn:

        await conn.run_sync(Base.metadata.create_all)

        result = await conn.execute(
            text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public';
            """)
        )

        print("TABLES:", result.fetchall())

    yield


app = FastAPI(
    title="AI Developer Story Extraction Platform API",
    description="Backend API for extracting developer stories from GitHub repositories.",
    version="1.0.0",
    lifespan=lifespan,
)

# Set up CORS middleware
origins = [settings.FRONTEND_URL, "http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth.router, prefix="/api")
app.include_router(repos.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")


@app.get("/")
def read_root():
    return {
        "app": "AI Developer Story Extraction Platform",
        "status": "online",
        "version": "1.0.0",
    }
