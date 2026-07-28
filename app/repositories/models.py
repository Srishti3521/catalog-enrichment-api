from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime, timezone
from app.core.database import Base


class ProductDB(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    price = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
    colour = Column(String, nullable=True)
    url = Column(String, nullable=True)
    availability = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    available_sizes = Column(String, nullable=True)
    material = Column(String, nullable=True)
    use_case = Column(String, nullable=True)
    size_range = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    weather_resistance = Column(String, nullable=True)
    key_features = Column(String, nullable=True)
    target_audience = Column(String, nullable=True)
    differentiators = Column(String, nullable=True)
    completeness_score = Column(Float, default=0.0)
    needs_review = Column(Boolean, default=False)
    status = Column(String, default="completed")
    missing_fields = Column(String, nullable=True)
    gap_summary = Column(String, nullable=True)
    embedding = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class JobDB(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    status = Column(String, default="pending")
    total = Column(Integer, default=0)
    completed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class VisibilityCheckDB(Base):
    __tablename__ = "visibility_checks"

    id = Column(String, primary_key=True, index=True)
    query = Column(String, nullable=False)
    watched_brands = Column(String, nullable=False)
    raw_response = Column(String, nullable=True)
    mentioned_brands = Column(String, nullable=True)
    reasoning = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))