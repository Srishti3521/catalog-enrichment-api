# Catalog Intelligence Console

An AI-powered platform that helps brands become discoverable, understandable, and recommendable by AI shopping assistants — not just a catalog cleaner, but a full pipeline: enrich messy product data, diagnose what's missing, benchmark against competitors, and measure whether AI actually recommends you.

**Live demo:** https://catalog-enrichment-api.onrender.com/static/console.html
**API docs:** https://catalog-enrichment-api.onrender.com/docs
*(Free-tier hosting — the first request after inactivity may take 30-50 seconds to wake up.)*

---

## The problem

When someone asks ChatGPT, Gemini, or Perplexity "what's a good waterproof running shoe under $100," the AI can only recommend products it has enough structured information to confidently describe. Most brand catalogs are written for humans skimming a webpage — vague copy, inconsistent formatting, missing facts. Even good products get skipped simply because the AI can't tell what they actually are.

This project addresses the full lifecycle of that problem: **fix the data → diagnose the gaps → benchmark against competitors → measure the real-world outcome.**

---

## What it does

**Enrichment.** Given a product name and raw description, an LLM (Google Gemini) extracts eight semantic attributes — material, use case, size range, gender, weather resistance, key features, target audience, and differentiators — while factual fields (price, currency, colour, URL, availability, rating, available sizes) are passed through untouched, never inferred, since hallucinating a price is far more dangerous than hallucinating a vague attribute.

**Gap diagnosis.** Every enriched product gets a completeness score, a `needs_review` flag, a raw list of missing fields, and a plain-language summary explaining what's missing and why it matters for AI discoverability.

**Structured output.** Any product can be exported as schema.org/Product JSON-LD — the actual vocabulary Google Shopping and AI crawlers parse — ready to paste onto a real site.

**Comparison.** Given two products (or a product and a competitor), an LLM judges which an AI shopping assistant would more likely recommend, and why — referencing both products by their real names, with a gap breakdown on each side.

**Competitor matching.** Paste in a competitor's product name and description; the system embeds it, finds the closest match in your own catalog by cosine similarity (not keywords), and runs the same recommendation comparison — with a confidence flag (strong/moderate/weak) so a weak match doesn't masquerade as a real one. Competitor products are tagged and excluded from future catalog searches, so they can never accidentally pollute your own product data.

**Visibility tracking.** Send a real shopping query to Gemini and see which of your watched brands it actually mentions in a natural, unprompted answer — not a hypothetical, real evidence of current AI behavior.

**Share-of-voice history.** Every visibility check is stored; look up a brand's mention rate across all checks run so far.

**Batch processing.** Upload a CSV of any size; get a job ID back instantly while enrichment runs in the background, with live progress polling and automatic retry-with-backoff on LLM rate limits.

**Export.** Download the full catalog as CSV, or just the products from one specific batch job — every field included, ready to hand to whoever manages the actual storefront.

---

## Architecture

```
Client Request
      │
      ▼
 [API Key Auth]  ──── rejects unauthorized requests immediately
      │
      ▼
 [Route Layer]   ──── thin; only receives requests and calls services
      │
      ▼
 [Dependency Injection] ──── hands routes a real (or fake, in tests) LLM client + DB session
      │
      ▼
 [Service Layer] ──── prompting, parsing, validation, scoring, embedding, comparison
      │
      ▼
 [Repository Layer] ──── the only layer that touches the database
      │
      ▼
   Response / Job created
```

Routes never touch the database or the LLM directly — this is what makes the test suite possible without hitting real infrastructure, and what let each new feature (comparison, visibility, matching) get added without rewriting anything underneath it.

### Async batch processing

Large CSV uploads don't block the client:
1. A `Job` record is created immediately, `job_id` returned right away
2. Rows are processed one at a time in the background, with retry-with-backoff on rate limits
3. The client polls `GET /jobs/{job_id}` for live progress
4. Once complete, results (and a scoped CSV export) are available for that job specifically

---

## Tech stack

- **FastAPI** — REST API, dependency injection, auto-generated docs
- **SQLAlchemy + SQLite** — persistence
- **Google Gemini API** — text generation (`gemini-flash-lite-latest`) and embeddings (`gemini-embedding-001`)
- **Pydantic** — request/response validation, settings management
- **pytest** — unit and integration tests using fake LLM/repository doubles
- **Docker** — containerized deployment
- **Render** — hosting
- **Vanilla HTML/CSS/JS** — a custom console UI (no framework, no build step) covering every endpoint

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/products/enrich` | Enrich a single product, get result immediately |
| GET | `/products/{id}` | Fetch one enriched product |
| GET | `/products` | List all products (filter by `needs_review`) |
| GET | `/products/export` | Download the full catalog as CSV |
| GET | `/products/{id}/schema-org` | Get a product as schema.org/Product JSON-LD |
| GET | `/products/compare` | Compare two catalog products by ID |
| POST | `/products/match` | Match a competitor product to your closest SKU by embedding similarity, then compare |
| POST | `/products/batch` | Upload a CSV, returns a `job_id` instantly |
| GET | `/jobs/{job_id}` | Check batch job progress |
| GET | `/jobs/{job_id}/results` | Fetch full results once a job completes |
| GET | `/jobs/{job_id}/export` | Download only that job's products as CSV |
| POST | `/visibility/check` | Run a real shopping query against Gemini, see which watched brands get mentioned |
| GET | `/visibility/history` | Get a brand's share-of-voice across all past checks |
| GET | `/health` | Health check |

All endpoints except `/health` require an `X-API-Key` header.

---

## The console

A single-file HTML/JS control panel (`/static/console.html`) that replaces Swagger as the actual way to use the product — five tabs (Enrich, Batch, Catalog, Compare, Visibility), every backend field represented, live job progress with a downloadable CSV per batch, and an in-place schema.org viewer per product. No React, no build step — just `fetch()` calls against the API above.

---

## Running locally

```bash
git clone https://github.com/Srishti3521/catalog-enrichment-api.git
cd catalog-enrichment-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:
```
LLM_API_KEY=your_gemini_api_key
DATABASE_URL=sqlite:///./catalog.db
SERVICE_API_KEY=choose-any-secret-string
```

Run it:
```bash
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` or `http://127.0.0.1:8000/static/console.html`.

## Running with Docker

```bash
docker build -t catalog-enrichment-api .
docker run -p 8000:8000 --env-file .env catalog-enrichment-api
```

## Running tests

```bash
pytest tests/ -v
```
15 tests covering scoring logic, response normalization, failure handling, and full API request/response cycles — all using fake LLM and repository doubles, so the suite runs in under a second with no real API calls or cost.

---

## Notable engineering decisions and bugs fixed

- **LLM infers, structured data passes through.** Semantic attributes (material, use case, differentiators) are the LLM's job. Factual fields (price, availability, rating) are never inferred — they're passed straight through from the input, because a hallucinated price is a far more dangerous failure mode than a vague attribute guess.
- **Per-row database sessions in batch processing.** An early version shared a single database session across concurrent batch rows, causing intermittent `IllegalStateChangeError` crashes — SQLAlchemy sessions aren't thread-safe. Fixed by giving each row its own short-lived session.
- **Route ordering.** `/products/compare` and `/products/export` were initially defined *after* the generic `/products/{id}` route, so FastAPI matched the dynamic path first and tried to parse `"compare"` or `"export"` as an integer ID. Fixed by moving literal/specific paths above dynamic ones — a general rule now followed throughout the router.
- **Data isolation between own catalog and competitors.** The embedding-based matcher originally saved competitor products into the same table as the user's own catalog with no distinction, meaning a competitor checked once could later be mistaken for "your own product" in a future match. Fixed with an `is_competitor` flag, excluded by default from catalog searches.
- **Response schema leaking internal fields.** List endpoints originally serialized raw ORM objects, including the full embedding vector (~1500 floats) in every response. Fixed by applying explicit `response_model`s so only intended fields are ever returned.
- **Defensive LLM parsing.** LLMs don't always return clean JSON and don't always respect the requested schema (e.g. returning a list where a single string was expected). The service layer normalizes these cases rather than trusting model output blindly, and retries with exponential backoff on rate-limit errors.
- **Real product names in comparisons.** Early prompts referred to inputs as "Product A"/"Product B" throughout, including in the model's own reasoning. Fixed by labeling inputs with actual names in the prompt and translating the model's internal choice back to the real name before returning it.

## What I'd add with more time

- Scheduled, automatic re-running of visibility checks (currently manual/on-demand)
- Inline catalog editing in the console, feeding back into the same export pipeline
- Multi-model visibility comparison (Gemini vs. GPT vs. Claude on the same queries)
- Postgres instead of SQLite for concurrent write scalability at real catalog size
- GitHub Actions CI running the test suite on every push
