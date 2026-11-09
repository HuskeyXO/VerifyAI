
import json
import re

from app.services.ai.base import AIProvider


class MockAIProvider(AIProvider):
    """Generate deterministic synthetic evidence for testing only."""

    def generate(self, prompt: str) -> str:
        article_pattern = re.compile(
            r"^ARTICLE\s+(\d+)\s*$([\s\S]*?)"
            r"(?=^ARTICLE\s+\d+\s*$|\Z)",
            flags=re.MULTILINE,
        )

        evidence = []

        articles = list(article_pattern.finditer(prompt))

        for position, match in enumerate(articles):
            article_index = int(match.group(1))
            article_block = match.group(2)

            content_match = re.search(
                r"Available article text \(may be truncated\):\s*\n"
                r"(.*?)(?=\n\nURL:|\Z)",
                article_block,
                flags=re.DOTALL,
            )

            title_match = re.search(
                r"^Title:\s*\n(.+)$",
                article_block,
                flags=re.MULTILINE,
            )

            quoted_text = ""

            if content_match:
                quoted_text = content_match.group(1).strip()

            # Fall back to the title if article content is unavailable.
            if not quoted_text and title_match:
                quoted_text = title_match.group(1).strip()

            if not quoted_text:
                continue

            # Alternate relationships to exercise both code paths.
            relation = (
                "supports" if position % 2 == 0
                else "contradicts"
            )

            evidence.append({
                "article_index": article_index,
                "relation": relation,
                "relevance_score": 0.7,
                "quoted_text": quoted_text,
                "reason": (
                    f"MOCK TEST DATA: simulated {relation} evidence. "
                    "This is not a real factual assessment."
                ),
            })

        return json.dumps({"evidence": evidence})
