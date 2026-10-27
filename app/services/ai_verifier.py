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
1. Use only the supplied article title and text. Do not invent facts
   or use outside knowledge.
2. Evaluate the exact claim, not merely whether the article discusses
   the same general topic.
3. Check the subject, action or predicate, geography, time period,
   and important qualifiers in the claim.
4. Use "supports" when the supplied text directly provides factual
   evidence consistent with the central assertion in the claim.
5. Use "contradicts" when the supplied text directly provides factual
   evidence against the central assertion under the relevant context.
6. Use "irrelevant" when the article does not provide meaningful
   evidence for or against the claim, or when essential information
   is missing.
7. For product claims, distinguish product availability, specifications,
   reviews, rankings, prices, and personal opinions. Do not treat one
   category as proof of another.
8. For claims containing words such as "best", "largest", or "fastest",
   require a meaningful comparison, explicit ranking, or criteria that
   address the superlative. Merely mentioning a product is insufficient.
9. Do not infer that a product is available in a particular country
   unless the supplied text supports that geographic detail.
10. For every included article, return quoted_text as an exact,
    continuous quotation copied from its supplied description or content.
    Do not paraphrase the quotation or invent missing words.
11. If no suitable quotation supports the assigned relationship,
    omit that article from the evidence array.
12. relevance_score measures the direct relevance of the quoted text
    to the claim, not the probability that the claim is true.
13. Do not determine the final verdict. The application evaluates
    the accepted evidence separately.
14. Keep the reason concise and explain how the quotation relates
    to the claim.
15. Return only valid JSON, without Markdown fences.

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
