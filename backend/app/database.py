from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession 
from app.config import settings
from sqlalchemy.orm import declarative_base

# Create async engine
print(f"Connecting to database at: {settings.DATABASE_URL}")
engine = create_async_engine(settings.DATABASE_URL, echo=False)

# Create session factory
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


Base = declarative_base()


async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
