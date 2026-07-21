import uuid
from sqlalchemy.orm import Session
from app.repositories.models import JobDB

class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_job(self, total: int) -> JobDB:
        job = JobDB(id=str(uuid.uuid4()), status="pending", total=total, completed=0, failed=0)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_job(self, job_id: str) -> JobDB | None:
        return self.db.query(JobDB).filter(JobDB.id == job_id).first()

    def update_progress(self, job_id: str, completed: int = 0, failed: int = 0, status: str | None = None):
        job = self.get_job(job_id)
        if job:
            job.completed += completed
            job.failed += failed
            if status:
                job.status = status
            self.db.commit()
            self.db.refresh(job)
        return job