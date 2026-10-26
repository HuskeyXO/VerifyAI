
import json
import re

from app.services.ai.base import AIProvider


class MockAIProvider(AIProvider):
    """Return deterministic test evidence. Not real fact-checking."""

    def generate(self, prompt: str) -> str:
        article_indexes = re.findall(
            r"^ARTICLE\s+(\d+)\s*$",
            prompt,
            flags=re.MULTILINE,
        )

        evidence = []

        for position, article_index in enumerate(article_indexes):
            # Alternate relations solely to exercise both code paths.
            relation = (
                "supports" if position % 2 == 0
                else "contradicts"
            )

            evidence.append({
                "article_index": int(article_index),
                "relation": relation,
                "relevance_score": 0.7,
                "reason": (
                    f"MOCK TEST DATA: simulated {relation} evidence. "
                    "This is not an assessment of the real article."
                ),
            })

        return json.dumps({"evidence": evidence})
