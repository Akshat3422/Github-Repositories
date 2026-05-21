import json
import logging
from typing import Dict, Any, List
from app.agents.base import get_provider, LLMResponse

logger = logging.getLogger(__name__)


class RepoIntelligenceAgent:
    def __init__(self):
        self.provider = get_provider()

    async def analyze(
        self, repo_name: str, file_tree: List[str], languages: Dict[str, int]
    ) -> Dict[str, Any]:
        """Analyzes file tree and tech stack. Uses 'fast' model tier."""

        # Format input data
        languages_str = ", ".join(
            [f"{lang} ({bytes_} bytes)" for lang, bytes_ in languages.items()]
        )

        # Limit file tree size for prompt tokens safety
        if len(file_tree) > 200:
            formatted_tree = (
                "\n".join(file_tree[:150])
                + f"\n... and {len(file_tree) - 150} more files"
            )
        else:
            formatted_tree = "\n".join(file_tree)

        prompt = f"""You are the Repo Intelligence Agent (Agent 1). Your goal is to analyze the file tree and languages of a repository to understand its stack, architecture, and structural layout.

Repository: {repo_name}
Languages: {languages_str}

File Tree:
{formatted_tree}

Analyze this repository and output a structured JSON object with the following keys:
- "tech_stack": list of frameworks, databases, primary libraries, and developer tools detected (e.g. ["Next.js", "FastAPI", "PostgreSQL", "TailwindCSS"]).
- "architecture": a short description of the application's architecture (e.g., "Full-stack client-server architecture with Next.js frontend and FastAPI backend").
- "primary_modules": a list of objects describing key directories or components, e.g., [{{"path": "backend/app/routes", "description": "API route handlers"}}, {{"path": "frontend/components", "description": "Reusable UI components"}}].
- "complexity": "low", "medium", or "high" (complexity rating based on structure).

Ensure you ONLY return a valid JSON block. Do not include markdown wraps, comments, or explanations outside the JSON.
"""

        try:
            response = await self.provider.complete(
                prompt, model="fast", max_tokens=1000
            )

            # Clean JSON
            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            analysis = json.loads(cleaned_text)

            # Include token usage and model for cost tracking
            analysis["_meta"] = {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "model_name": response.model_name,
            }
            return analysis

        except Exception as e:
            logger.error(f"Repo Intelligence Agent analysis failed: {e}")
            # Fallback structure
            return {
                "tech_stack": list(languages.keys()),
                "architecture": "Undetermined architecture (analysis failed)",
                "primary_modules": [],
                "complexity": "medium",
                "_meta": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "model_name": "fallback",
                },
            }
