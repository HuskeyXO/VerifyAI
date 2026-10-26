
import re
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.evidence import Evidence

from difflib import SequenceMatcher


MIN_RELEVANCE_SCORE = 0.6


def _normalize_title(title: str) -> set[str]:
    """Normalize a headline into meaningful tokens."""
    tokens = re.findall(r"[a-z0-9]+", title.lower())

    stop_words = {
        "a", "an", "the", "and", "or", "of", "in", "on",
        "to", "for", "with", "as", "by", "is", "are",
        "was", "were", "its", "it", "this", "that",
    }

    return {token for token in tokens if token not in stop_words}


def _titles_are_near_duplicates(
    first_title: str,
    second_title: str,
) -> bool:
    """Conservatively identify identical or very similar headlines."""
    first = _normalize_title(first_title)
    second = _normalize_title(second_title)

    if not first or not second:
        return False

    if first == second:
        return True

    common = first & second
    combined = first | second

    # Require substantial overlap and several shared terms to reduce
    # accidental grouping of articles about the same broad topic.
    similarity = len(common) / len(combined)

    return len(common) >= 4 and similarity >= 0.8


def _contents_are_near_duplicates(
    first_content: str,
    second_content: str,
) -> bool:
    """Detect strongly overlapping stored article text."""
    def normalize(text: str) -> str:
        return " ".join(
            re.findall(r"[a-z0-9]+", (text or "").lower())
        )

    first = normalize(first_content)
    second = normalize(second_content)

    # Avoid matching short, generic snippets.
    if len(first) < 100 or len(second) < 100:
        return False

    if first == second:
        return True

    similarity = SequenceMatcher(
        None, first, second
    ).ratio()

    if similarity >= 0.90:
        return True

    first_tokens = set(first.split())
    second_tokens = set(second.split())

    shared = len(first_tokens & second_tokens)
    combined = len(first_tokens | second_tokens)

    return (
        shared >= 15
        and combined > 0
        and shared / combined >= 0.80
    )


def _articles_are_near_duplicates(
    first_title: str,
    first_content: str,
    second_title: str,
    second_content: str,
) -> bool:
    """Match duplicates by headline or substantial text overlap."""
    return (
        _titles_are_near_duplicates(first_title, second_title)
        or _contents_are_near_duplicates(
            first_content,
            second_content,
        )
    )



def _source_key(evidence: Evidence) -> str:
    """Identify the publisher associated with an evidence record."""
    article = evidence.article

    if article and article.source and article.source.domain:
        return article.source.domain.strip().lower()

    if article and article.url:
        domain = urlparse(article.url).netloc.lower()
        if domain:
            return domain

    return f"unknown-source-{evidence.id}"


def _evaluate_evidence(evidence_list: list[Evidence]) -> dict:
    # Count distinct publishers separately from distinct story clusters.
    source_scores: dict[str, dict[str, float]] = {}
    story_clusters: list[dict] = []
    article_ids = set()
    evidence_count = 0

    for evidence in evidence_list:
        score = evidence.relevance_score

        if (
            score is None
            or not MIN_RELEVANCE_SCORE <= score <= 1.0
        ):
            continue

        article = evidence.article
        title = article.title if article else ""

        source_key = _source_key(evidence)
        side = "supports" if evidence.supports_claim else "contradicts"

        if source_key not in source_scores:
            source_scores[source_key] = {
                "supports": 0.0,
                "contradicts": 0.0,
            }

        source_scores[source_key][side] = max(
            source_scores[source_key][side],
            float(score),
        )

        # Group articles with identical or near-duplicate titles.

        # Group near-duplicate headlines or substantially identical text.
        article_content = article.content if article else ""

        cluster = next(
            (
                existing
                for existing in story_clusters
                if _articles_are_near_duplicates(
                    title,
                    article_content,
                    existing["representative_title"],
                    existing["representative_content"],
                )
            ),
            None,
        )

        if cluster is None:
            cluster = {
                "representative_title": title,
                "representative_content": article_content,
                "supports": 0.0,
                "contradicts": 0.0,
            }
            story_clusters.append(cluster)


        # A repeated story contributes only its strongest score
        # for each relationship, rather than adding every duplicate.
        cluster[side] = max(
            cluster[side],
            float(score),
        )

        if evidence.article_id is not None:
            article_ids.add(evidence.article_id)

        evidence_count += 1

    source_count = len(source_scores)
    independent_story_count = len(story_clusters)

    # Use story clusters for the score so duplicate headlines from
    # multiple outlets do not repeatedly inflate the evidence weight.
    support_total = sum(
        cluster["supports"] for cluster in story_clusters
    )
    contradiction_total = sum(
        cluster["contradicts"] for cluster in story_clusters
    )
    combined_total = support_total + contradiction_total

    base_result = {
        "evidence_count": evidence_count,
        "article_count": len(article_ids),
        "source_count": source_count,
        "independent_story_count": independent_story_count,
    }

    if combined_total == 0:
        return {
            **base_result,
            "status": "uncertain",
            "confidence": None,
        }

    # Require both publisher diversity and multiple distinct stories.
    if source_count < 2 or independent_story_count < 2:
        return {
            **base_result,
            "status": "uncertain",
            "confidence": None,
        }

    if support_total > contradiction_total:
        status = "supported"
    elif contradiction_total > support_total:
        status = "contradicted"
    else:
        return {
            **base_result,
            "status": "uncertain",
            "confidence": 0.5,
        }

    all_scores = [
        score
        for cluster in story_clusters
        for score in (
            cluster["supports"],
            cluster["contradicts"],
        )
        if score > 0
    ]

    mean_relevance = sum(all_scores) / len(all_scores)

    balance = (
        abs(support_total - contradiction_total) / combined_total
    )

    source_factor = min(source_count / 3.0, 1.0)
    confidence = round(
        0.5 + 0.5 * balance * mean_relevance * source_factor,
        2,
    )

    return {
        **base_result,
        "status": status,
        "confidence": confidence,
    }


def generate_verification_result(
    verification_id: int,
    db: Session,
):
    claims = (
        db.query(Claim)
        .filter(Claim.verification_id == verification_id)
        .all()
    )

    if not claims:
        return {
            "status": "uncertain",
            "confidence": None,
            "summary": "No claims were found for this verification.",
        }

    all_evidence = []

    for claim in claims:
        evidence_list = (
            db.query(Evidence)
            .filter(Evidence.claim_id == claim.id)
            .all()
        )

        claim_result = _evaluate_evidence(evidence_list)

        claim.status = claim_result["status"]
        claim.confidence = claim_result["confidence"]

        all_evidence.extend(evidence_list)

    result = _evaluate_evidence(all_evidence)

    if result["evidence_count"] == 0:
        summary = (
            "Verification result: uncertain. "
            "No relevant evidence with valid relevance scores was found."
        )
    elif (
        result["source_count"] < 2
        or result["independent_story_count"] < 2
    ):
        summary = (
            "Verification result: uncertain. "
            f"Evaluated {result['evidence_count']} evidence records "
            f"across {result['article_count']} articles, "
            f"{result['source_count']} distinct sources, and "
            f"{result['independent_story_count']} story clusters. "
            "Multiple sources and distinct stories are required "
            "for a verdict."
        )
    else:
        summary = (
            f"Verification result: {result['status']}. "
            f"Evaluated {result['evidence_count']} evidence records "
            f"across {result['article_count']} articles, "
            f"{result['source_count']} distinct sources, and "
            f"{result['independent_story_count']} story clusters. "
            "Confidence is a heuristic evidence-strength score, "
            "not a calibrated probability."
        )

    return {
        "status": result["status"],
        "confidence": result["confidence"],
        "summary": summary,
    }
