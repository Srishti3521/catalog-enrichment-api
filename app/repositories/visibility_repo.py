import uuid
from sqlalchemy.orm import Session
from app.repositories.models import VisibilityCheckDB


class VisibilityRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, query: str, watched_brands: str, raw_response: str, mentioned_brands: str, reasoning: str):
        record = VisibilityCheckDB(
            id=str(uuid.uuid4()),
            query=query,
            watched_brands=watched_brands,
            raw_response=raw_response,
            mentioned_brands=mentioned_brands,
            reasoning=reasoning,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_all(self):
        return self.db.query(VisibilityCheckDB).all()

    def get_by_id(self, check_id: str):
        return self.db.query(VisibilityCheckDB).filter(VisibilityCheckDB.id == check_id).first()

    def get_history_for_brand(self, brand: str):
        all_checks = self.db.query(VisibilityCheckDB).all()
        return [
            check for check in all_checks
            if brand.lower() in [b.strip().lower() for b in check.watched_brands.split(",")]
        ]