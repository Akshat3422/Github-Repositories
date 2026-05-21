import json
import logging
from typing import Dict, Any, Optional
from app.agents.base import get_provider

logger = logging.getLogger(__name__)


class RouterDecision:
    def __init__(
        self, approved: bool, status: str, reason: str, readme_missing: bool = False
    ):
        self.approved = approved
        self.status = status  # "approved", "blocked", "warning"
        self.reason = reason
        self.readme_missing = readme_missing

    def to_dict(self):
        return {
            "approved": self.approved,
            "status": self.status,
            "reason": self.reason,
            "readme_missing": self.readme_missing,
        }


class RouterAgent:
    def __init__(self):
        self.provider = get_provider()

    async def evaluate_repo(
        self,
        repo_name: str,
        readme_content: Optional[str],
        languages: Dict[str, int],
        bypass_warning: bool = False,
    ) -> RouterDecision:
        """Evaluates whether the repository is a good candidate for generating developer stories.

        Rules:
        - If README is missing, return warning (or block if not bypassed).
        - If language stats are empty, block (empty repo).
        - Use LLM to analyze the README + stats to detect boilerplates, empty forks, or useless codebases.
        """
        if not languages:
            return RouterDecision(
                approved=False,
                status="blocked",
                reason="The repository is empty or has no language statistics.",
                readme_missing=readme_content is None,
            )

        readme_missing = not readme_content or not readme_content.strip()

        if readme_missing:
            if bypass_warning:
                # User chose to bypass readme warning, we evaluate just language stats or pass it
                return RouterDecision(
                    approved=True,
                    status="approved",
                    reason="Bypassed missing README warning by user override.",
                    readme_missing=True,
                )
            else:
                return RouterDecision(
                    approved=False,
                    status="warning",
                    reason="README is missing. If you want to analyze this repository anyway, please override the warning.",
                    readme_missing=True,
                )

        # Prepare prompt for LLM evaluation (using the "fast" model tier)
        languages_str = ", ".join(
            [f"{lang} ({bytes_} bytes)" for lang, bytes_ in languages.items()]
        )
        prompt = f"""You are a repository router agent. Your job is to analyze the metadata of a repository and determine if it is suitable for extracting a professional developer story or LinkedIn post.
Useful repositories usually contain custom application logic, libraries, packages, tools, or complex projects written by developers.
Useless repositories for story generation are boilerplates (e.g. "create-react-app" unmodified), empty setups, basic homework assignments, or trivial scripts.

Repository Name: {repo_name}
Languages: {languages_str}
README snippet (first 1500 chars):
{readme_content[:1500]}

You must return a JSON response with the following keys:
- "approved": boolean (true if suitable, false if it's too trivial/boilerplate/useless)
- "reason": string (brief justification for approval or rejection)

Respond ONLY with a valid JSON block, no markdown, no comments, no other text.
"""
        try:
            # Router uses "fast" tier
            response = await self.provider.complete(
                prompt, model="fast", max_tokens=150
            )

            # Clean response text in case markdown wrapper was returned
            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            decision_data = json.loads(cleaned_text)
            approved = bool(decision_data.get("approved", True))
            reason = decision_data.get("reason", "Approved by Router Agent.")

            status = "approved" if approved else "blocked"
            return RouterDecision(
                approved=approved, status=status, reason=reason, readme_missing=False
            )

        except Exception as e:
            logger.error(
                f"Router Agent LLM check failed: {e}. Falling back to default approval."
            )
            # Fallback to approve if LLM call fails but README and languages exist
            return RouterDecision(
                approved=True,
                status="approved",
                reason="Automatically approved via fallback (LLM check failed).",
                readme_missing=False,
            )
