
from datetime import datetime
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.verification import VerificationRequest
from app.models.report import VerificationReport
from app.models.claim import Claim
from app.models.article import Article
from app.models.source import Source

from app.services.news.service import get_news_provider
from app.services.ai_verifier import analyze_claim
from app.services.evidence import save_evidence
from app.services.verification_report import generate_verification_result

import re
import requests

from app.services.verification_errors import (
    VerificationNotFoundError,
    VerificationAlreadyRunError,
    NoNewsArticlesError,
    NewsProviderUnavailableError,
    AIProviderUnavailableError,
)


from sqlalchemy.exc import IntegrityError


from app.services.article_extractor import (
    extract_article_text,
    MIN_ARTICLE_CHARS,
)

MAX_ARTICLE_EXTRACTIONS = 3

def parse_published_at(value):
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        # Store a naive datetime to match the current model.
        return parsed.replace(tzinfo=None)

    except (ValueError, TypeError, AttributeError):
        return None


def run_verification(
    verification_id: int,
    db: Session,
    max_results: int = 10,
):
    try:
        verification = (
            db.query(VerificationRequest)
            .filter(VerificationRequest.id == verification_id)
            .first()
        )

        if verification is None:
            raise VerificationNotFoundError(
                "Verification request not found"
            )

        existing_report = (
            db.query(VerificationReport)
            .filter(
                VerificationReport.verification_id == verification_id
            )
            .first()
        )

        if existing_report:
            raise VerificationAlreadyRunError(
                "A report already exists for this verification"
            )

        # 1. Retrieve news articles.

        provider = get_news_provider()
        search_query = build_news_query(verification.claim)

        print("News search query:", search_query)

        try:
            raw_articles = provider.search_articles(
                search_query,
                max_results=max_results,
            )
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 429:
                raise NewsProviderUnavailableError(
                    "News provider rate limit reached. Retry later."
                ) from exc

            raise NewsProviderUnavailableError(
                "News provider returned an HTTP error."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise NewsProviderUnavailableError(
                "Could not connect to the news provider."
            ) from exc

        print("News articles returned:", len(raw_articles))

        if not raw_articles:
            raise NoNewsArticlesError(
                "No news articles were found for this claim."
            )



        # 2. Create the database claim.
        claim = Claim(
            verification_id=verification.id,
            claim_text=verification.claim,
        )
        db.add(claim)
        db.flush()

        saved_articles = []
        analysis_articles = []
        extraction_attempts = 0

        # 3. Save or reuse articles and their sources.
        for item in raw_articles:
            article_url = item.get("url")
            title = item.get("title")

            if not article_url or not title:
                continue

            parsed_article_url = urlparse(article_url)
            source_data = item.get("source") or {}

            source_name = source_data.get("name") or (
                parsed_article_url.netloc
            )

            source_url = source_data.get("url") or article_url
            source_domain = urlparse(source_url).netloc.lower()

            if not source_domain:
                source_domain = parsed_article_url.netloc.lower()

            if not source_domain:
                continue

            source = (
                db.query(Source)
                .filter(Source.domain == source_domain)
                .first()
            )

            if source is None:
                source = Source(
                    name=source_name,
                    domain=source_domain,
                )
                db.add(source)
                db.flush()

            article = (
                db.query(Article)
                .filter(Article.url == article_url)
                .first()
            )



            description = (item.get("description") or "").strip()
            provider_content = (item.get("content") or "").strip()
            existing_content = (
                (article.content or "").strip()
                if article is not None
                else ""
            )

            # Prefer whichever available text is most complete.
            text_candidates = [
                text for text in (
                    provider_content,
                    description,
                    existing_content,
                )
                if text
            ]
            best_text = max(text_candidates, key=len, default="")

            # Fetch full page text only when the available text is short.
            # Limit extraction attempts per verification.
            if (
                len(best_text) < MIN_ARTICLE_CHARS
                and extraction_attempts < MAX_ARTICLE_EXTRACTIONS
            ):
                extraction_attempts += 1

                extracted_text = extract_article_text(article_url)

                if extracted_text and len(extracted_text) > len(best_text):
                    best_text = extracted_text.strip()

            if article is None:
                article = Article(
                    source_id=source.id,
                    title=title,
                    url=article_url,
                    author=item.get("author"),
                    content=best_text or description,
                    published_at=parse_published_at(
                        item.get("publishedAt")
                    ),
                )
                db.add(article)
                db.flush()

            elif len(best_text) > len(article.content or ""):
                article.content = best_text

            article_text = article.content or best_text or description


            # Keep both lists in exactly the same order because
            # the AI returns 1-based article indexes.
            saved_articles.append(article)

            analysis_articles.append({
                "title": article.title,
                "source": source.name,
                "published_at": (
                    article.published_at.isoformat()
                    if article.published_at
                    else None
                ),
                "description": description,
                "content": article_text,
                "url": article.url,
            })

        # 4. Classify the retrieved articles with AI.
        try:
            ai_result = analyze_claim(
                claim=claim.claim_text,
                articles=analysis_articles,
            )
        except Exception as exc:
            raise AIProviderUnavailableError(
                "AI analysis failed. Check provider availability and configuration."
            ) from exc

        # 5. Persist supporting and contradicting evidence.
        save_evidence(
            claim=claim,
            articles=saved_articles,
            ai_evidence=ai_result.get("evidence", []),
            db=db,
        )

        # 6. Calculate and save the report.
        result = generate_verification_result(
            verification_id=verification.id,
            db=db,
        )

        report = VerificationReport(
            verification_id=verification.id,
            status=result["status"],
            confidence=result["confidence"],
            summary=result["summary"],
        )

        db.add(report)
        verification.status = result["status"]

        db.commit()
        db.refresh(report)

        return report

    except IntegrityError as exc:
        db.rollback()

        # Another request may have created the report first.
        existing_report = (
            db.query(VerificationReport)
            .filter(
                VerificationReport.verification_id == verification_id
            )
            .first()
        )

        if existing_report:
            raise VerificationAlreadyRunError(
                "A report already exists for this verification"
            ) from exc

        # Other integrity errors should not be mislabeled as duplicates.
        raise

    except Exception:
        db.rollback()
        raise

def build_news_query(claim: str) -> str:
    """Extract useful search terms from a claim."""

    ignored_words = {
        "a", "an", "the", "of", "in", "on", "at", "to",
        "for", "with", "by", "is", "are", "was", "were",
        "be", "been", "being", "has", "have", "had",
        "do", "does", "did", "it", "its", "that", "this",
        "according", "whether", "claim", "claimed",
        "claims", "selected", "product", "products",
        "increased", "increase", "increases", "raising",
        "raised", "decreased", "decrease", "decreases",
        "reported", "reports", "announced", "announces",
    }

    words = re.findall(r"[A-Za-z0-9]+", claim)

    keywords = [
        word for word in words
        if word.lower() not in ignored_words
    ]

    # Avoid sending the same keyword more than once.
    unique_keywords = list(dict.fromkeys(keywords))

    return " ".join(unique_keywords[:6])
