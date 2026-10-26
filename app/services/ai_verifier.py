import json

from app.services.ai.service import get_ai_service


ai_service = get_ai_service()


def analyze_claim(claim: str, articles: list[dict]) -> dict:

    evidence_text = ""

    for i, article in enumerate(articles, start=1):

        evidence_text += f"""
ARTICLE {i}

Title:
{article.get("title")}

Source:
{article.get("source")}

Published:
{article.get("published_at")}

Available article text (may be truncated):
{article.get("content") or article.get("description")}

URL:
{article.get("url")}
"""


    prompt = f"""
You are a cautious news-evidence analyst.

CLAIM TO EVALUATE:
{claim}

ARTICLES:
{evidence_text}

For each article, decide whether its supplied text directly supports,
directly contradicts, or is irrelevant to the exact claim.

Allowed relations:
- supports
- contradicts
- irrelevant

Rules:
1. Use only the supplied article title and text. Do not use outside knowledge.
2. A matching topic or headline alone is not enough to prove a claim.
3. Check the subject, geography, product, and time period.

4. Distinguish official retail prices from resale prices, discounts,
   forecasts, rumors, and general market commentary.
5. Opinion, editorial, and analysis articles may provide context, but
   do not treat them as independent factual confirmation merely because
   they say prices are rising.
6. Use "supports" only when the supplied text directly reports a price
   increase relevant to the claim. Use "contradicts" only when the text
   directly reports facts against the claim.
7. If an article merely says prices are "climbing sharply", discusses
   a "price shock", or makes a broad market observation without
   sufficiently specific factual reporting, classify it as "irrelevant".
8. Do not infer an official price change from resale prices, demand,
   shortages, or comparisons with competitors.
9. Do not invent products, dates, old prices, new prices, or sources.
10. For every included article, provide quoted_text as an exact,
    continuous quotation from its supplied description or content.
    If no suitable exact quotation exists, exclude the article.

11. relevance_score measures how directly the quoted text relates to
    the claim, not the probability that the claim is true.
12. Do not determine the final verdict. The application evaluates
    the evidence separately.
13. Keep the reason concise and explain the link between the quotation
    and the claim.
14. Return only valid JSON. Do not use Markdown fences.

Required JSON structure:
{{
    "evidence": [
        {{
            "article_index": 1,
            "relation": "supports",
            "relevance_score": 0.85,
            "quoted_text": "An exact quotation from the supplied article text.",
            "reason": "Brief explanation of why this quotation supports the claim."
        }}
    ]
}}
"""

    response = ai_service.generate(prompt)

    try:
        result = json.loads(response)
    except json.JSONDecodeError:
        return {"evidence": []}

    if not isinstance(result, dict) or not isinstance(
        result.get("evidence"), list
    ):
        return {"evidence": []}

    return result
