# pyrefly: ignore [missing-import]
import httpx
import base64
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class GitHubClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-Developer-Story-Platform",
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=15.0)

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def get_user_details(self) -> Dict[str, Any]:
        """Fetch details of the authenticated user."""
        r = await self.client.get("https://api.github.com/user")
        r.raise_for_status()
        return r.json()

    async def list_repositories(self) -> List[Dict[str, Any]]:
        """List repositories for the authenticated user."""
        repos = []
        page = 1
        while True:
            # Fetch both public and private repos owned by user or where they contribute
            r = await self.client.get(
                "https://api.github.com/user/repos",
                params={"per_page": 100, "page": page, "sort": "pushed"},
            )
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            repos.extend(data)
            if len(data) < 100:
                break
            page += 1
        return repos

    async def get_repo_details(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository metadata."""
        r = await self.client.get(f"https://api.github.com/repos/{owner}/{repo}")
        r.raise_for_status()
        return r.json()

    async def get_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """Get repository language distribution in bytes."""
        r = await self.client.get(
            f"https://api.github.com/repos/{owner}/{repo}/languages"
        )
        r.raise_for_status()
        return r.json()

    async def get_readme(self, owner: str, repo: str) -> Optional[str]:
        """Fetch and decode repository README."""
        try:
            r = await self.client.get(
                f"https://api.github.com/repos/{owner}/{repo}/readme"
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json()
            content_b64 = data.get("content", "")
            # Remove newlines before decoding
            decoded = base64.b64decode(content_b64.replace("\n", "")).decode(
                "utf-8", errors="ignore"
            )
            return decoded
        except Exception as e:
            logger.warning(f"Error fetching README for {owner}/{repo}: {e}")
            return None

    async def get_file_tree(
        self, owner: str, repo: str, default_branch: str
    ) -> List[str]:
        """Retrieve list of paths for files in the repository using the Git Trees API."""
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}"
            r = await self.client.get(url, params={"recursive": "1"})
            r.raise_for_status()
            tree_data = r.json()
            paths = [
                item["path"]
                for item in tree_data.get("tree", [])
                if item.get("type") == "blob"
            ]
            return paths
        except Exception as e:
            logger.warning(
                f"Git trees API failed for {owner}/{repo}: {e}. Falling back to root contents."
            )
            # Fallback to listing contents of root
            try:
                r = await self.client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/contents"
                )
                r.raise_for_status()
                return [item["path"] for item in r.json() if item.get("type") == "file"]
            except Exception:
                return []

    async def get_file_content(self, owner: str, repo: str, path: str) -> str:
        """Fetch and decode the raw content of a specific file."""
        try:
            r = await self.client.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
            )
            if r.status_code == 404:
                return ""
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                return ""
            content_b64 = data.get("content", "")
            return base64.b64decode(content_b64.replace("\n", "")).decode(
                "utf-8", errors="ignore"
            )
        except Exception as e:
            logger.warning(f"Error reading file {path} from {owner}/{repo}: {e}")
            return ""
