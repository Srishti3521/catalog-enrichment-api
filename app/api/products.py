import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from app.schemas.product import RawProduct
from app.core.dependencies import get_product_repo, get_llm_client, get_job_repo
from app.core.security import verify_api_key
from app.repositories.product_repo import ProductRepository
from app.repositories.job_repo import JobRepository
from app.llm.client import LLMClient
from app.services.enrichment import enrich_and_save, process_batch

router = APIRouter()

@router.get("/products/{product_id}", dependencies=[Depends(verify_api_key)])
def get_product(product_id: int, repo: ProductRepository = Depends(get_product_repo)):
    product = repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/products", dependencies=[Depends(verify_api_key)])
def list_products(needs_review: bool | None = None, repo: ProductRepository = Depends(get_product_repo)):
    return repo.get_all(needs_review=needs_review)

@router.post("/products/enrich", dependencies=[Depends(verify_api_key)])
def enrich_product(
    product: RawProduct,
    llm: LLMClient = Depends(get_llm_client),
    repo: ProductRepository = Depends(get_product_repo),
):
    return enrich_and_save(product.name, product.description, llm, repo)

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

@router.get("/jobs/{job_id}/results", dependencies=[Depends(verify_api_key)])
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