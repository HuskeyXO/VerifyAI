# VerifyAI

VerifyAI is an AI-assisted news verification API that evaluates claims using retrieved news articles, identifies supporting and contradicting evidence, and generates traceable verification reports.

The system combines external news retrieval, AI-based evidence classification, quotation validation, and evidence-strength scoring to produce transparent assessments of news claims.

## Features

- REST API built with FastAPI.
- Asynchronous verification jobs using Celery and Redis.
- PostgreSQL persistence using SQLAlchemy and Alembic migrations.
- News retrieval using Tavily, with GNews as an alternative provider.
- AI-powered evidence classification using Google Gemini.
- Evidence quotation validation and relevance filtering.
- Duplicate-story detection and source independence heuristics.
- Traceable verification reports with confidence scores.
- Redis caching for repeated news searches (10-minute TTL).
- API-key authentication and request rate limiting.
- Request ID tracking, structured JSON logging, and health checks.
- Docker Compose support for the API, worker, and Redis.
- Automated tests using pytest and isolated SQLite databases.

## Tech Stack

**Backend:** Python 3.14, FastAPI, Pydantic, SQLAlchemy, REST API

**Database:** PostgreSQL, Neon, Alembic

**AI and Search:** Google Gemini, Hugging Face, Tavily, GNews, Trafilatura

**Background Processing and Caching:** Celery, Redis

**Security and Observability:** API-key authentication, SlowAPI, Python logging

**Infrastructure and Testing:** Docker, Docker Compose, pytest, GitHub Actions

## Prerequisites

- Python 3.14 and pip
- PostgreSQL database (Neon supported)
- Redis
- Tavily API key for live news retrieval
- Gemini API key for live AI classification

Docker Desktop and Docker Compose are required for the containerized setup.

## Local Setup

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

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the environment file:

```bash
cp .env.example .env
```

Configure `.env` with:

- `DATABASE_URL`: PostgreSQL connection string using the `postgresql+psycopg://` driver format.
- `REDIS_URL`: Redis connection URL.
- `API_KEY`: A secure randomly generated API key.
- `GEMINI_API_KEY`: Google Gemini API key.
- `TAVILY_API_KEY`: Tavily API key.
- `GNEWS_API_KEY`: Optional alternative news-provider API key.

Never commit `.env` or expose credentials.

For live providers:

```env
AI_PROVIDER=gemini
NEWS_PROVIDER=tavily
```

For local testing without external AI or news API requests:

```env
AI_PROVIDER=mock
NEWS_PROVIDER=mock
```

Mock mode uses fictional test data and must not be used to present real-world fact-checking results.

## Run Locally

Ensure PostgreSQL and Redis are running.

Apply database migrations:

```bash
alembic upgrade head
```

Start the FastAPI application:

```bash
uvicorn app.main:app --reload
```

Start the Celery worker in a separate terminal:

```bash
celery -A app.core.celery_app:celery_app worker --loglevel=INFO --pool=solo
```

The API will be available at:

`http://127.0.0.1:8000`

Interactive API documentation:

`http://127.0.0.1:8000/docs`

## Docker Setup

VerifyAI includes a Docker Compose configuration containing three services:

| Service | Responsibility |
|---|---|
| API | FastAPI application |
| Worker | Background verification processing |
| Redis | Celery message broker and news-search cache |

PostgreSQL remains hosted externally using Neon.

Create your `.env` file and configure `DATABASE_URL` with your Neon connection string. Do not use `localhost` for Neon connections inside Docker containers.

Build the images:

```bash
docker compose build
```

Apply database migrations:

```bash
docker compose run --rm api alembic upgrade head
```

Start all services:

```bash
docker compose up -d
```

Check container status:

```bash
docker compose ps
```

View application and worker logs:

```bash
docker compose logs -f api worker
```

Stop the services:

```bash
docker compose down
```

Redis data is persisted through a Docker volume.

## API Authentication

Business API endpoints require an API key.

Include the following header in protected requests:

```http
X-API-Key: YOUR_API_KEY
```

The API uses constant-time key comparison and rejects missing or invalid credentials.

The `/`, `/health`, and `/ready` endpoints remain publicly accessible.

Requests are limited to 60 per minute per client IP per route. Rate-limit counters use in-memory storage.

## Verification Workflow

1. Create a verification request using `POST /verifications/`.
2. Submit the job using `POST /verifications/{verification_id}/run`.
3. Celery processes the verification asynchronously.
4. Check job status using `GET /verifications/{verification_id}`.
5. Retrieve the report using `GET /verifications/{verification_id}/report`.
6. Retrieve accepted evidence using `GET /evidence/verification/{verification_id}`.

The verification report includes a verdict, summary, and optional confidence score.

The confidence score is a heuristic evidence-strength measure, not a calibrated probability that a claim is true.

## Redis Caching

Tavily and GNews search results are cached using Redis.

- Cache duration: 10 minutes.
- Cache keys include the provider, search query, and requested result count.
- Cached results reduce repeated external search requests.
- If Redis is unavailable, the application bypasses caching and continues with the news provider.

Mock-provider responses are not cached.

## Testing

Run the complete test suite:

```bash
python -m pytest -q
```

Tests cover API workflows, authentication, rate limiting, input validation, Redis caching, evidence persistence, quotation validation, article extraction, relevance filtering, and duplicate-story heuristics.

## Deployment

Existing API deployment:

- **API Base URL:** https://verifyai-api.onrender.com
- **API Documentation:** https://verifyai-api.onrender.com/docs
- **Health Check:** https://verifyai-api.onrender.com/health

The complete API, Celery worker, and Redis Docker setup is validated locally. A separate hosted Celery worker and shared production Redis deployment are not currently provisioned.

## Limitations

- Results depend on the relevance and completeness of retrieved reporting.
- Article extraction is best-effort; some publishers may block access or provide partial text.
- Headline and content similarity are heuristics, not proof of independent reporting.
- A valid quotation shows that text appears in the stored article; it does not prove the statement is true.
- Confidence scores are heuristic assessments rather than calibrated probabilities.
- Redis cache data and rate-limit counters have different persistence characteristics; rate-limit counters reset when the API process restarts.
- Mock providers generate fictional test data and are not suitable for real-world verification.

## Security

- Store API keys and database credentials in environment variables.
- Never commit `.env` or other files containing secrets.
- Use a secure API key for protected endpoints.
- Keep database credentials and external provider keys private.
