import json
import logging
from typing import Dict, Any, List
from app.agents.base import get_provider

logger = logging.getLogger(__name__)


class EngineeringInsightAgent:
    def __init__(self):
        self.provider = get_provider()

    async def extract_insights(
        self,
        repo_name: str,
        repo_summary: Dict[str, Any],
        key_files_content: Dict[str, str],
    ) -> Dict[str, Any]:
        """Extracts code-grounded insights from key files. Uses 'mid' model tier."""

        # Prepare file contents string for LLM
        formatted_files = ""
        for path, content in key_files_content.items():
            formatted_files += f"\n--- File: {path} ---\n"
            # Truncate large files to fit token budgets (e.g., 2000 chars per key file max)
            if len(content) > 3000:
                formatted_files += content[:3000] + "\n... [truncated] ..."
            else:
                formatted_files += content
            formatted_files += "\n"

        prompt = f"""You are the Engineering Insight Extraction Agent (Agent 2). Your goal is to extract engineering insights from a repository based on its summary and the actual content of key files.

Repository: {repo_name}
Architecture Summary: {repo_summary.get('architecture', 'Unknown')}
Tech Stack: {json.dumps(repo_summary.get('tech_stack', []))}

Key File Contents:
{formatted_files}

Extract 3-5 high-quality engineering insights from this repository.
CRITICAL GROUNDEDNESS RULE:
- Every single insight must cite a specific file path and a code pattern (exact class, function name, setup pattern, or code snippet) present in the key file contents above.
- If there is no specific code evidence in the key files to back up an insight, DO NOT include that insight. Do not hallucinate or guess.
- If no evidence exists at all, return an empty list of insights.

Output a structured JSON object containing a list of insights, with the following format:
{{
  "insights": [
    {{
      "title": "Brief title of the insight (e.g. Symmetric encryption for tokens at rest)",
      "description": "Detailed explanation of what the implementation does and why it is good practice.",
      "file_path": "backend/app/security.py",
      "code_pattern": "fernet_cipher.encrypt(token.encode())"
    }}
  ]
}}

Ensure you ONLY return a valid JSON block. Do not include markdown wraps, comments, or explanations outside the JSON.
"""

        try:
            # Agent 2 uses the "mid" tier
            response = await self.provider.complete(
                prompt, model="mid", max_tokens=1500
            )

            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            logger.error(f"RAW RESPONSE:\n{cleaned_text}")
            insights_data = json.loads(cleaned_text)

            # Ensure insights are grounded
            valid_insights = []
            for insight in insights_data.get("insights", []):
                file_path = insight.get("file_path")
                pattern = insight.get("code_pattern")
                # Groundedness checks
                if file_path and pattern:
                    # Verify if the file is in the key files list
                    if file_path in key_files_content:
                        valid_insights.append(insight)
                    else:
                        # Also check if it's a substring match for safety
                        matched = False
                        for kp in key_files_content.keys():
                            if file_path in kp or kp in file_path:
                                insight["file_path"] = kp  # normalize path
                                valid_insights.append(insight)
                                matched = True
                                break
                        if not matched:
                            logger.warning(
                                f"Removing ungrounded insight (file path not in key files): {insight}"
                            )
                else:
                    logger.warning(f"Removing incomplete insight: {insight}")

            result = {"insights": valid_insights}

            # Metadata tracking for token usage & cost
            result["_meta"] = {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "model_name": response.model_name,
            }
            return result

        except Exception as e:
            logger.error(f"Engineering Insight Agent failed: {e}")
            return {
                "insights": [],
                "_meta": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "model_name": "fallback",
                },
            }
