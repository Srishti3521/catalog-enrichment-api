from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime, timezone
from app.core.database import Base

class ProductDB(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    material = Column(String, nullable=True)
    use_case = Column(String, nullable=True)
    size_range = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    weather_resistance = Column(String, nullable=True)
    completeness_score = Column(Float, default=0.0)
    needs_review = Column(Boolean, default=False)
    status = Column(String, default="completed")  # completed / enrichment_failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class JobDB(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)  # e.g. "abc123"
    status = Column(String, default="pending")  # pending / processing / completed
    total = Column(Integer, default=0)
    completed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))