import json
import logging
from typing import Dict, Any, List
from app.agents.base import get_provider

logger = logging.getLogger(__name__)


class LinkedInPostGeneratorAgent:
    def __init__(self):
        self.provider = get_provider()

    async def generate_drafts(
        self,
        repo_name: str,
        repo_summary: Dict[str, Any],
        insights_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generates 3 LinkedIn posts in distinct styles. Uses 'best' model tier."""

        tech_stack = repo_summary.get("tech_stack", [])
        architecture = repo_summary.get("architecture", "Undetermined")
        insights = insights_summary.get("insights", [])

        # Format insights for LLM input
        insights_str = ""
        for i, insight in enumerate(insights, 1):
            insights_str += f"\nInsight {i}: {insight.get('title')}\n"
            insights_str += f"Description: {insight.get('description')}\n"
            insights_str += f"File: {insight.get('file_path')} (Pattern: `{insight.get('code_pattern')}`)\n"

        prompt = f"""You are the LinkedIn Content Generation Agent (Agent 3). Your goal is to write 2 to 3 engaging, professional LinkedIn post drafts based on the engineering profile of a repository.

Repository Name: {repo_name}
Tech Stack: {json.dumps(tech_stack)}
Architecture: {architecture}
Key Code-Grounded Insights:
{insights_str}

Please generate exactly 3 LinkedIn post drafts in the following specific styles:
1. "Technical Deep Dive": Focuses on technical architecture, coding details, patterns, and framework integrations. Tailored for senior developers and architects.
2. "Builder Journey": Written in first-person ("I" / "we"), sharing the story of why this was built, the process, and the learnings. Great for building in public.
3. "Problem-Solution": Starts with a painful developer problem, explains how it was solved in this repo, and summarizes the results.

Rules:
- Make them sound human, professional, and interesting.
- Do not use cheesy emojis excessively. Use them naturally (1-2 per post max).
- Ensure the posts reflect the actual grounded code facts from the insights.
- Do not use hashtags excessively (3-4 relevant ones max).

Format your output as a JSON object containing a list of posts with keys:
{{
  "posts": [
    {{
      "style": "Technical Deep Dive",
      "content": "Full post markdown content here..."
    }},
    {{
      "style": "Builder Journey",
      "content": "Full post markdown content here..."
    }},
    {{
      "style": "Problem-Solution",
      "content": "Full post markdown content here..."
    }}
  ]
}}

Ensure you ONLY return a valid JSON block. Do not include markdown wraps, comments, or explanations outside the JSON.
"""

        try:
            # Agent 3 uses the "best" tier
            response = await self.provider.complete(
                prompt, model="best", max_tokens=2500
            )

            # logger.error(f"RAW GENERATOR RESPONSE:\n{response}")
            cleaned_text = str(response.text).strip()
            # logger.error(f"RAW GENERATOR RESPONSE:\n{cleaned_text}")
            
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text.split("```", 1)[1]

            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text.rsplit("```", 1)[0]

            cleaned_text = cleaned_text.strip()

            posts_data = json.loads(cleaned_text)

            # Metadata tracking for token usage & cost
            posts_data["_meta"] = {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "model_name": response.model_name,
            }
            return posts_data

        except Exception as e:
            logger.error(f"LinkedIn Content Generation Agent failed: {e}")
            return {
                "posts": [
                    {
                        "style": "Technical Deep Dive",
                        "content": f"Failed to generate post. Tech stack: {', '.join(tech_stack)}.",
                    }
                ],
                "_meta": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "model_name": "fallback",
                },
            }
