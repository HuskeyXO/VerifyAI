
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.article import Article
from app.models.evidence import Evidence

MIN_RELEVANCE_SCORE = 0.6


def normalize_text(text: str) -> str:
    """Normalize whitespace for quotation matching."""
    return " ".join(text.split())


def save_evidence(
    claim: Claim,
    articles: list[Article],
    ai_evidence: list[dict],
    db: Session,
):
    saved_evidence = []

    for item in ai_evidence:
        relation = item.get("relation")

        if relation not in {"supports", "contradicts"}:
            continue

        article_index = item.get("article_index")

        if not isinstance(article_index, int) or isinstance(
            article_index, bool
        ):
            continue

        article_position = article_index - 1

        if not 0 <= article_position < len(articles):
            continue

        score = item.get("relevance_score")

        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not MIN_RELEVANCE_SCORE <= score <= 1.0
        ):
            continue

        reason = item.get("reason")

        if not isinstance(reason, str) or not reason.strip():
            continue

        quoted_text = item.get("quoted_text")

        if not isinstance(quoted_text, str) or not quoted_text.strip():
            continue

        article = articles[article_position]

        # Check the article title and stored text, not the AI's explanation.
        source_text = "\n".join(
            part
            for part in (article.title, article.content)
            if part
        )

        normalized_quote = normalize_text(quoted_text)
        normalized_source = normalize_text(source_text)

        if normalized_quote not in normalized_source:
            # Reject quotations that cannot be verified against stored text.
            continue

        evidence = Evidence(
            claim_id=claim.id,
            article_id=article.id,
            excerpt=quoted_text.strip(),
            supports_claim=(relation == "supports"),
            relevance_score=float(score),
        )

        db.add(evidence)
        saved_evidence.append(evidence)

    db.flush()

    return saved_evidence
