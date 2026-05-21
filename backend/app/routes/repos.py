from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.models import User
from app.schemas import RepoRead
from app.security import decrypt_token
from app.github import GitHubClient

router = APIRouter(prefix="/repos", tags=["Repositories"])


@router.get("", response_model=List[RepoRead])
async def list_user_repos(user_id: str, db: AsyncSession = Depends(get_db)):
    """Fetches user repositories from GitHub using the user's OAuth credentials."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    try:
        access_token = decrypt_token(user.encrypted_access_token)
    except ValueError as e:
        raise HTTPException(
            status_code=401, detail="Invalid token. Please re-authenticate."
        )

    async with GitHubClient(access_token) as github:
        try:
            github_repos = await github.list_repositories()

            repos = []
            for r in github_repos:
                # Convert GitHub API response to RepoRead Pydantic model
                repos.append(
                    RepoRead(
                        id=str(r["id"]),
                        name=r["name"],
                        full_name=r["full_name"],
                        description=r.get("description"),
                        html_url=r["html_url"],
                        pushed_at=r.get("pushed_at", ""),
                        language=r.get("language"),
                        stargazers_count=r.get("stargazers_count", 0),
                        has_readme=True,  # Assumed True; Router Agent will perform verification
                    )
                )

            return repos
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch repositories from GitHub: {e}"
            )
