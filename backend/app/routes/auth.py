import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.config import settings
from app.database import get_db
from app.models import User
from app.security import encrypt_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/login")
def login(redirect_uri: Optional[str] = None):
    """Redirects the client to GitHub OAuth login page."""
    client_id = settings.GITHUB_CLIENT_ID

    # We request the 'repo' scope so the agent can read private/public repo structures.
    # Note: GitHub doesn't have a read-only scope for OAuth; we enforce read-only actions in our code.
    scope = "repo"

    target_redirect = redirect_uri or settings.GITHUB_REDIRECT_URI

    github_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={target_redirect}"
        f"&scope={scope}"
    )
    return RedirectResponse(url=github_url)


@router.get("/callback")
async def callback(code: str, db: AsyncSession = Depends(get_db)):
    """Handles OAuth callback, exchanges code for access token, and creates/updates User."""
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code.")

    # 1. Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
        )

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to retrieve access token: {token_data.get('error_description', 'Unknown error')}",
            )

        # 2. Fetch User Profile
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "AI-Developer-Story-Platform",
            },
        )
        user_response.raise_for_status()
        user_data = user_response.json()

        github_id = user_data["id"]
        username = user_data["login"]
        avatar_url = user_data.get("avatar_url")

        # 3. Encrypt access token
        encrypted_token = encrypt_token(access_token)

        # 4. Check if User exists in database
        stmt = select(User).where(User.github_id == github_id)
        result = await db.execute(stmt)
        db_user = result.scalars().first()

        if db_user:
            # Update user info and token
            db_user.username = username
            db_user.avatar_url = avatar_url
            db_user.encrypted_access_token = encrypted_token
        else:
            # Create new user
            db_user = User(
                github_id=github_id,
                username=username,
                avatar_url=avatar_url,
                encrypted_access_token=encrypted_token,
            )
            db.add(db_user)

        await db.commit()
        await db.refresh(db_user)

    # 5. Redirect user to the frontend dashboard with session data
    redirect_url = (
        f"{settings.FRONTEND_URL}/auth/callback"
        f"?user_id={db_user.id}"
        f"&username={username}"
        f"&avatar_url={avatar_url}"
    )
    return RedirectResponse(url=redirect_url)


@router.post("/disconnect")
async def disconnect(user_id: str, db: AsyncSession = Depends(get_db)):
    """Disconnects account: deletes user, associated jobs, and encrypted tokens from database."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    await db.delete(user)
    await db.commit()

    return {
        "status": "disconnected",
        "message": "Account and access tokens deleted successfully.",
    }
