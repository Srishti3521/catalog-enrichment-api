from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime, timezone
from app.core.database import Base


class ProductDB(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)

    # Commerce/offer data — not GS1 product attributes, kept separate
    price = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
    availability = Column(String, nullable=True)
    rating = Column(Float, nullable=True)

    # GS1-aligned factual fields — passed through untouched, never inferred
    gs1_colour_description = Column(String, nullable=True)
    gs1_size = Column(String, nullable=True)
    gs1_referenced_file = Column(String, nullable=True)
    gs1_brand = Column(String, nullable=True)
    gs1_country_of_origin = Column(String, nullable=True)
    gs1_season_name = Column(String, nullable=True)
    gs1_net_weight = Column(String, nullable=True)

    # GS1-aligned narrative fields — inferred by the LLM from the description
    gs1_upper_material_type = Column(String, nullable=True)
    gs1_sporting_activity_type = Column(String, nullable=True)
    gs1_target_consumer_gender = Column(String, nullable=True)
    gs1_is_waterproof = Column(Boolean, nullable=True)
    gs1_product_feature_benefit = Column(String, nullable=True)
    gs1_consumer_lifestage = Column(String, nullable=True)
    gs1_fastening_type = Column(String, nullable=True)
    gs1_footwear_upper_type = Column(String, nullable=True)
    gs1_is_patterned = Column(Boolean, nullable=True)
    gs1_is_thermal = Column(Boolean, nullable=True)
    gs1_style_description = Column(String, nullable=True)
    gs1_storage_instructions = Column(String, nullable=True)
    gs1_recycling_instructions = Column(String, nullable=True)

    # Not a GS1 concept — our own AI-reasoning field, kept as-is
    differentiators = Column(String, nullable=True)

    completeness_score = Column(Float, default=0.0)
    needs_review = Column(Boolean, default=False)
    status = Column(String, default="completed")
    missing_fields = Column(String, nullable=True)
    gap_summary = Column(String, nullable=True)
    embedding = Column(String, nullable=True)
    is_competitor = Column(Boolean, default=False)
    job_id = Column(String, nullable=True)
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