import asyncio
import csv
import io
from app.llm.client import LLMClient
from app.repositories.product_repo import ProductRepository
from app.repositories.job_repo import JobRepository
from app.core.database import SessionLocal

ENRICHED_FIELDS = ["material", "use_case", "size_range", "gender", "weather_resistance"]


def _to_string(value):
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return value


def compute_completeness_score(enriched_data: dict) -> float:
    filled = sum(1 for field in ENRICHED_FIELDS if enriched_data.get(field))
    return round(filled / len(ENRICHED_FIELDS), 2)


def flag_needs_review(enriched_data: dict) -> bool:
    vague_values = {"various", "unknown", "n/a", "unclear", "assorted"}
    for field in ENRICHED_FIELDS:
        value = enriched_data.get(field)
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        if value and str(value).strip().lower() in vague_values:
            return True
    return False


def enrich_and_save(name: str, description: str, llm: LLMClient, repo: ProductRepository) -> dict:
    enriched_data = llm.enrich(name, description)

    if enriched_data.get("_parse_failed"):
        product_record = {
            "name": name,
            "description": description,
            "material": None,
            "use_case": None,
            "size_range": None,
            "gender": None,
            "weather_resistance": None,
            "completeness_score": 0.0,
            "needs_review": True,
            "status": "enrichment_failed",
        }
        return repo.save(product_record)

    score = compute_completeness_score(enriched_data)
    needs_review = flag_needs_review(enriched_data)

    product_record = {
        "name": name,
        "description": description,
        "material": _to_string(enriched_data.get("material")),
        "use_case": _to_string(enriched_data.get("use_case")),
        "size_range": _to_string(enriched_data.get("size_range")),
        "gender": _to_string(enriched_data.get("gender")),
        "weather_resistance": _to_string(enriched_data.get("weather_resistance")),
        "completeness_score": score,
        "needs_review": needs_review,
        "status": "completed",
    }

    return repo.save(product_record)


async def process_batch(file_bytes: bytes, job_id: str, llm: LLMClient):
    db = SessionLocal()
    JobRepository(db).update_progress(job_id, status="processing")
    db.close()

    try:
        decoded = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        decoded = file_bytes.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))
    rows = list(reader)

    semaphore = asyncio.Semaphore(1)

    def process_row_sync(row):
        db = SessionLocal()
        try:
            repo = ProductRepository(db)
            job_repo = JobRepository(db)
            try:
                name = row.get("name", "").strip()
                description = row.get("description", "").strip()
                if not name or not description:
                    raise ValueError("Missing name or description")
                enrich_and_save(name, description, llm, repo)
                job_repo.update_progress(job_id, completed=1)
            except Exception as e:
                print(f"ROW FAILED: {row.get('name', 'unknown')} — {type(e).__name__}: {e}")
                db.rollback()
                job_repo.update_progress(job_id, failed=1)
        finally:
            db.close()

    async def process_row(row):
        async with semaphore:
            await asyncio.to_thread(process_row_sync, row)

    await asyncio.gather(*(process_row(row) for row in rows))

    db = SessionLocal()
    JobRepository(db).update_progress(job_id, status="completed")
    db.close()

   