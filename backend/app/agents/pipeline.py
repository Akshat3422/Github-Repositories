import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, User
from app.security import decrypt_token
from app.github import GitHubClient
from app.agents.router import RouterAgent
from app.agents.intelligence import RepoIntelligenceAgent
from app.agents.extraction import EngineeringInsightAgent
from app.agents.generator import LinkedInPostGeneratorAgent

logger = logging.getLogger(__name__)


class PipelineBlockedException(Exception):
    pass


class PipelineWarningException(Exception):
    pass


class PipelineOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.router_agent = RouterAgent()
        self.intel_agent = RepoIntelligenceAgent()
        self.insight_agent = EngineeringInsightAgent()
        self.gen_agent = LinkedInPostGeneratorAgent()

    async def run(self, job_id: str, bypass_warning: bool = False):
        """Runs the multi-agent pipeline with checkpoint recovery and caching."""

        # 1. Fetch Job from database
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        job = result.scalars().first()
        if not job:
            logger.error(f"Job {job_id} not found in database.")
            return

        if job.status == "done":
            logger.info(f"Job {job_id} already marked as done. Skipping.")
            return

        # 2. Fetch User and decrypt access token
        user_result = await self.db.execute(select(User).where(User.id == job.user_id))
        user = user_result.scalars().first()
        if not user:
            raise ValueError(f"User for job {job_id} not found.")

        access_token = decrypt_token(user.encrypted_access_token)

        # Parse owner and repo name from full name (e.g. "owner/repo")
        if "/" not in job.repo_full_name:
            raise ValueError(f"Invalid repo full name: {job.repo_full_name}")
        owner, repo_name = job.repo_full_name.split("/", 1)

        # Initialize cost tracking
        input_tokens = job.input_tokens or 0
        output_tokens = job.output_tokens or 0
        model_used = job.model_used or {}

        # Use GitHub Client
        async with GitHubClient(access_token) as github:
            # 3. Check / Verify repository exists and get current status
            repo_details = await github.get_repo_details(owner, repo_name)
            current_pushed_at = repo_details.get("pushed_at", "")
            default_branch = repo_details.get("default_branch", "main")

            # Update job status to running if it was pending or failed
            job.status = "running"
            job.updated_at = datetime.utcnow()
            await self.db.commit()

            # --- ROUTER AGENT (Skip if we already have checkpoints) ---
            if job.checkpoint == "none":
                logger.info(f"[{job_id}] Running Router Agent...")
                # Fetch README content
                readme_content = await github.get_readme(owner, repo_name)
                # Fetch languages
                languages = await github.get_languages(owner, repo_name)

                # Evaluate repository
                decision = await self.router_agent.evaluate_repo(
                    repo_name=repo_name,
                    readme_content=readme_content,
                    languages=languages,
                    bypass_warning=bypass_warning,
                )

                if not decision.approved:
                    if decision.status == "warning":
                        # README is missing and bypass_warning was false
                        raise PipelineWarningException(decision.reason)
                    else:
                        # Repository blocked (e.g. boilerplate or empty)
                        raise PipelineBlockedException(decision.reason)

                # Check Cache for Agent 1:
                # If another successful job exists for this repo with the same pushed_at timestamp, we reuse Agent 1 output
                cache_stmt = (
                    select(Job)
                    .where(
                        Job.repo_id == job.repo_id,
                        Job.status == "done",
                        Job.repo_pushed_at == current_pushed_at,
                        Job.agent1_output.isnot(None),
                    )
                    .order_by(Job.created_at.desc())
                )

                cache_result = await self.db.execute(cache_stmt)
                cached_job = cache_result.scalars().first()

                if cached_job:
                    logger.info(
                        f"[{job_id}] Cache hit for Agent 1! Copying output from completed job {cached_job.id}"
                    )
                    job.agent1_output = cached_job.agent1_output
                    job.checkpoint = "agent1"
                    model_used["agent1"] = {
                        "model": cached_job.model_used.get("agent1", {}).get(
                            "model", "cached"
                        ),
                        "cached": True,
                    }
                    job.model_used = model_used
                    job.updated_at = datetime.utcnow()
                    await self.db.commit()
                else:
                    # Run Agent 1
                    logger.info(f"[{job_id}] Executing Agent 1 (Repo Intelligence)...")
                    file_tree = await github.get_file_tree(
                        owner, repo_name, default_branch
                    )

                    agent1_res = await self.intel_agent.analyze(
                        repo_name=repo_name, file_tree=file_tree, languages=languages
                    )

                    # Track costs
                    meta = agent1_res.pop("_meta", {})
                    input_tokens += meta.get("input_tokens", 0)
                    output_tokens += meta.get("output_tokens", 0)
                    model_used["agent1"] = {"model": meta.get("model_name", "unknown")}

                    # Update checkpoint
                    job.agent1_output = agent1_res
                    job.checkpoint = "agent1"
                    job.input_tokens = input_tokens
                    job.output_tokens = output_tokens
                    job.model_used = model_used
                    job.updated_at = datetime.utcnow()
                    await self.db.commit()

            # --- AGENT 2 (Engineering Insight Extraction) ---
            # Using independent 'if' chain so code resumes correctly.
            if job.checkpoint == "agent1":
                logger.info(
                    f"[{job_id}] Executing Agent 2 (Engineering Insight Extraction)..."
                )
                file_tree = await github.get_file_tree(owner, repo_name, default_branch)

                # Fetch content of key files
                key_files = self._select_key_files(file_tree)
                key_files_content = {}
                for path in key_files:
                    content = await github.get_file_content(owner, repo_name, path)
                    if content:
                        key_files_content[path] = content

                agent2_res = await self.insight_agent.extract_insights(
                    repo_name=repo_name,
                    repo_summary=job.agent1_output,
                    key_files_content=key_files_content,
                )

                meta = agent2_res.pop("_meta", {})
                input_tokens += meta.get("input_tokens", 0)
                output_tokens += meta.get("output_tokens", 0)
                model_used["agent2"] = {"model": meta.get("model_name", "unknown")}

                # Update checkpoint
                job.agent2_output = agent2_res
                job.checkpoint = "agent2"
                job.input_tokens = input_tokens
                job.output_tokens = output_tokens
                job.model_used = model_used
                job.updated_at = datetime.utcnow()
                await self.db.commit()

            # --- AGENT 3 (LinkedIn Content Generation) ---
            if job.checkpoint == "agent2":
                logger.info(
                    f"[{job_id}] Executing Agent 3 (LinkedIn Content Generation)..."
                )

                agent3_res = await self.gen_agent.generate_drafts(
                    repo_name=repo_name,
                    repo_summary=job.agent1_output,
                    insights_summary=job.agent2_output,
                )

                meta = agent3_res.pop("_meta", {})
                input_tokens += meta.get("input_tokens", 0)
                output_tokens += meta.get("output_tokens", 0)
                model_used["agent3"] = {"model": meta.get("model_name", "unknown")}

                # Update Job to finished
                job.agent3_output = agent3_res
                job.checkpoint = "agent3"
                job.status = "done"
                job.input_tokens = input_tokens
                job.output_tokens = output_tokens
                job.model_used = model_used
                job.updated_at = datetime.utcnow()
                await self.db.commit()
                logger.info(f"[{job_id}] Job finished successfully!")

    def _select_key_files(self, file_tree: List[str]) -> List[str]:
        """Filters file tree to locate critical project configuration, entrypoints and model files."""
        # Focus file extensions
        allowed_exts = {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".go",
            ".rs",
            ".json",
            ".yml",
            ".yaml",
            ".md",
        }

        # Folders to ignore completely
        ignored_dirs = {
            "node_modules",
            ".git",
            ".next",
            "dist",
            "build",
            "venv",
            ".venv",
            "env",
            "packages",
            "assets",
            "public",
        }

        candidates = []
        for path in file_tree:
            parts = path.split("/")
            if any(ignored in parts for ignored in ignored_dirs):
                continue

            # Check extension
            if not any(path.endswith(ext) for ext in allowed_exts):
                continue

            candidates.append(path)

        # Score candidates based on significance
        scored_candidates = []
        for path in candidates:
            score = 0
            basename = path.split("/")[-1].lower()

            # Package and dependency config - highest priority
            if basename in [
                "package.json",
                "requirements.txt",
                "go.mod",
                "cargo.toml",
                "pyproject.toml",
                "gemfile",
                "docker-compose.yml",
                "dockerfile",
            ]:
                score += 100
            # Root entrypoint
            elif basename in [
                "main.py",
                "app.py",
                "index.js",
                "server.js",
                "app.ts",
                "index.ts",
                "worker.py",
                "tasks.py",
            ]:
                score += 80
            # NextJS/tailwind config
            elif basename in [
                "next.config.js",
                "tailwind.config.js",
                "components.json",
            ]:
                score += 50
            # Code containing DB models or schemas
            elif (
                "model" in basename
                or "schema" in basename
                or "database" in basename
                or "db" in basename
            ):
                score += 40
            # Standard source code
            elif (
                "src/" in path
                or "app/" in path
                or "lib/" in path
                or "components/" in path
            ):
                score += 20
            # Low importance files (tests, configs, docs)
            elif "test" in basename or basename.endswith(".md"):
                score += 5
            else:
                score += 10

            scored_candidates.append((score, path))

        # Sort by score descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Take up to top 10 key files
        return [path for _, path in scored_candidates[:10]]
