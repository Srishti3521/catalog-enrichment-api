from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.product_repo import ProductRepository
from app.repositories.job_repo import JobRepository
from app.repositories.visibility_repo import VisibilityRepository

def get_product_repo(db: Session = Depends(get_db)) -> ProductRepository:
    return ProductRepository(db)

def get_job_repo(db: Session = Depends(get_db)) -> JobRepository:
    return JobRepository(db)

from app.llm.client import LLMClient

def get_llm_client() -> LLMClient:
    return LLMClient()

def get_visibility_repo(db: Session = Depends(get_db)) -> VisibilityRepository:
    return VisibilityRepository(db)