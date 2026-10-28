# VerifyAI

VerifyAI is an AI-assisted news verification API that evaluates claims using news articles, identifies supporting or contradicting evidence, and generates traceable verification reports.

## Features

- REST API built with FastAPI.
- PostgreSQL persistence using SQLAlchemy.
- Database migrations managed with Alembic.
- Web search using Tavily, with GNews as an alternative news provider.
- AI-based evidence classification using Google Gemini.
- Duplicate-story detection and traceable verification reports.
- Article text extraction using Trafilatura, with fallback to provider-supplied text.
- Evidence quotation validation and relevance filtering.
- Automated tests using pytest and isolated SQLite databases.

## Tech Stack

Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Alembic, Google Gemini, Tavily, GNews, Hugging Face, Trafilatura, pytest.
## Prerequisites

- Python and pip
- PostgreSQL
- Tavily API key for live news retrieval
- Gemini API key for live AI classification

## Setup

Clone the repository:

```bash
git clone https://github.com/HuskeyXO/VerifyAI.git
cd VerifyAI
```

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Install dependencies and configure your environment:

```bash
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your database URL and API keys. Never commit this file.

Create a PostgreSQL database and configure `DATABASE_URL` using the format shown in `.env.example`.

For live providers, use:

```env
AI_PROVIDER=gemini
NEWS_PROVIDER=tavily
```

For local testing without external API requests, use:

```env
AI_PROVIDER=mock
NEWS_PROVIDER=mock
```

Mock mode uses fictional test data and must not be used to present real-world fact-checking results.

## Run the Application

Apply database migrations:

```bash
alembic upgrade head
```

Start the API:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.


## Live Deployment

VerifyAI is deployed on Render and uses Neon PostgreSQL for persistent storage.

- **API Base URL:** https://verifyai-api.onrender.com
- **Interactive API Documentation:** https://verifyai-api.onrender.com/docs
- **Health Check:** https://verifyai-api.onrender.com/health



## Verification Workflow

1. Create a verification request using `POST /verifications/`.
2. Run the verification using `POST /verifications/{verification_id}/run`.
3. Retrieve the report using `GET /verifications/{verification_id}/report`.
4. Retrieve accepted evidence using `GET /evidence/verification/{verification_id}`.

The report contains a verdict, summary, and optional confidence score.
The confidence score is a heuristic evidence-strength measure, not a
calibrated probability that a claim is true.
## Run Tests

```bash
python -m pytest -q
```

The automated tests cover the API workflow, evidence persistence, quotation validation, article extraction fallback, relevance filtering, and duplicate-story heuristics.

## Limitations

- Results depend on the relevance and completeness of retrieved reporting.
- Article extraction is best-effort; some publishers may block access or provide partial text.
- Headline and content similarity are heuristics, not proof of independent reporting.
- A valid quotation shows that text appears in the stored article; it does not prove the statement is true.
- Verdicts are evidence-based assessments, not guarantees of factual accuracy.

## Security

Store API keys and database credentials in environment variables. Never commit `.env` or other files containing secrets.