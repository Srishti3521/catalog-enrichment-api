import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from app.schemas.product import RawProduct, EnrichedProduct, VisibilityCheckRequest, CompetitorMatchRequest
from app.core.dependencies import get_product_repo, get_llm_client, get_job_repo, get_visibility_repo
from app.core.security import verify_api_key
from app.repositories.product_repo import ProductRepository
from app.repositories.job_repo import JobRepository
from app.repositories.visibility_repo import VisibilityRepository
from app.llm.client import LLMClient
from fastapi.responses import StreamingResponse
from app.services.enrichment import (
    enrich_and_save,
    process_batch,
    to_schema_org,
    compare_products,
    check_product_visibility,
    get_brand_visibility_history,
    match_and_compare,
)

router = APIRouter()

# --- Specific/literal paths FIRST ---

@router.get("/products/compare", dependencies=[Depends(verify_api_key)])
def compare_two_products(
    product_a_id: int,
    product_b_id: int,
    llm: LLMClient = Depends(get_llm_client),
    repo: ProductRepository = Depends(get_product_repo),
):
    product_a = repo.get_by_id(product_a_id)
    product_b = repo.get_by_id(product_b_id)
    if not product_a or not product_b:
        raise HTTPException(status_code=404, detail="One or both products not found")
    return compare_products(product_a, product_b, llm)


@router.post("/products/match", dependencies=[Depends(verify_api_key)])
def match_competitor_product(
    request: CompetitorMatchRequest,
    llm: LLMClient = Depends(get_llm_client),
    repo: ProductRepository = Depends(get_product_repo),
):
    return match_and_compare(request.name, request.description, llm, repo)


@router.post("/visibility/check", dependencies=[Depends(verify_api_key)])
def visibility_check(
    request: VisibilityCheckRequest,
    llm: LLMClient = Depends(get_llm_client),
    repo: VisibilityRepository = Depends(get_visibility_repo),
):
    return check_product_visibility(request.query, request.watched_brands, llm, repo)


@router.get("/visibility/history", dependencies=[Depends(verify_api_key)])
def visibility_history(
    brand: str,
    repo: VisibilityRepository = Depends(get_visibility_repo),
):
    return get_brand_visibility_history(brand, repo)


@router.get("/products", dependencies=[Depends(verify_api_key)],response_model=list[EnrichedProduct])
def list_products(needs_review: bool | None = None, repo: ProductRepository = Depends(get_product_repo)):
    return repo.get_all(needs_review=needs_review)


@router.post("/products/enrich", dependencies=[Depends(verify_api_key)], response_model=EnrichedProduct)
def enrich_product(
    product: RawProduct,
    llm: LLMClient = Depends(get_llm_client),
    repo: ProductRepository = Depends(get_product_repo),
):
    return enrich_and_save(
        product.name, product.description, llm, repo,
        price=product.price, currency=product.currency, colour=product.colour,
        url=product.url, availability=product.availability,
        rating=product.rating, available_sizes=product.available_sizes,
    )


@router.post("/products/batch", dependencies=[Depends(verify_api_key)])
async def batch_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    llm: LLMClient = Depends(get_llm_client),
    job_repo: JobRepository = Depends(get_job_repo),
):
    file_bytes = await file.read()
    try:
        decoded = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        decoded = file_bytes.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))
    row_count = sum(1 for _ in reader)

    job = job_repo.create_job(total=row_count)
    background_tasks.add_task(process_batch, file_bytes, job.id, llm)

    return {"job_id": job.id, "status": job.status, "total": job.total}


@router.get("/jobs/{job_id}", dependencies=[Depends(verify_api_key)])
def get_job_status(job_id: str, job_repo: JobRepository = Depends(get_job_repo)):
    job = job_repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/results", dependencies=[Depends(verify_api_key)], response_model=list[EnrichedProduct] | dict)
def get_job_results(
    job_id: str,
    job_repo: JobRepository = Depends(get_job_repo),
    product_repo: ProductRepository = Depends(get_product_repo),
):
    job = job_repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        return {"status": job.status, "message": "Job still processing"}
    return product_repo.get_all()


@router.get("/products/{product_id}/schema-org", dependencies=[Depends(verify_api_key)])
def get_product_schema_org(product_id: int, repo: ProductRepository = Depends(get_product_repo)):
    product = repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return to_schema_org(product)


# --- Generic/dynamic path LAST ---
@router.get("/products/export", dependencies=[Depends(verify_api_key)])
def export_products_csv(repo: ProductRepository = Depends(get_product_repo)):
    products = repo.get_all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "name", "description", "price", "currency", "colour", "url",
        "availability", "rating", "available_sizes",
        "material", "use_case", "size_range", "gender", "weather_resistance",
        "key_features", "target_audience", "differentiators",
        "completeness_score", "needs_review", "missing_fields", "gap_summary",
    ])
    for p in products:
        writer.writerow([
            p.id, p.name, p.description, p.price, p.currency, p.colour, p.url,
            p.availability, p.rating, p.available_sizes,
            p.material, p.use_case, p.size_range, p.gender, p.weather_resistance,
            p.key_features, p.target_audience, p.differentiators,
            p.completeness_score, p.needs_review, p.missing_fields, p.gap_summary,
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=catalog_export.csv"},
    )

@router.get("/products/{product_id}", dependencies=[Depends(verify_api_key)], response_model=EnrichedProduct)
def get_product(product_id: int, repo: ProductRepository = Depends(get_product_repo)):
    product = repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/jobs/{job_id}/export", dependencies=[Depends(verify_api_key)])
def export_job_csv(job_id: str, repo: ProductRepository = Depends(get_product_repo)):
    products = repo.get_by_job_id(job_id)
    if not products:
        raise HTTPException(status_code=404, detail="No products found for this job")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "name", "description", "price", "currency", "colour", "url",
        "availability", "rating", "available_sizes",
        "material", "use_case", "size_range", "gender", "weather_resistance",
        "key_features", "target_audience", "differentiators",
        "completeness_score", "needs_review", "missing_fields", "gap_summary",
    ])
    for p in products:
        writer.writerow([
            p.id, p.name, p.description, p.price, p.currency, p.colour, p.url,
            p.availability, p.rating, p.available_sizes,
            p.material, p.use_case, p.size_range, p.gender, p.weather_resistance,
            p.key_features, p.target_audience, p.differentiators,
            p.completeness_score, p.needs_review, p.missing_fields, p.gap_summary,
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=job_{job_id}_export.csv"},
    )