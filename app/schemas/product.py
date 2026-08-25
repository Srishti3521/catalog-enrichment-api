from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class RawProduct(BaseModel):
    name: str
    description: str
    price: Optional[float] = None
    currency: Optional[str] = None
    availability: Optional[str] = None
    rating: Optional[float] = None
    gs1_colour_description: Optional[str] = None
    gs1_size: Optional[str] = None
    gs1_referenced_file: Optional[str] = None
    gs1_brand: Optional[str] = None
    gs1_country_of_origin: Optional[str] = None
    gs1_season_name: Optional[str] = None
    gs1_net_weight: Optional[str] = None


class EnrichedProduct(BaseModel):
    id: int
    name: str
    description: str
    price: Optional[float] = None
    currency: Optional[str] = None
    availability: Optional[str] = None
    rating: Optional[float] = None
    gs1_colour_description: Optional[str] = None
    gs1_size: Optional[str] = None
    gs1_referenced_file: Optional[str] = None
    gs1_brand: Optional[str] = None
    gs1_country_of_origin: Optional[str] = None
    gs1_season_name: Optional[str] = None
    gs1_net_weight: Optional[str] = None
    gs1_upper_material_type: Optional[str] = None
    gs1_sporting_activity_type: Optional[str] = None
    gs1_target_consumer_gender: Optional[str] = None
    gs1_is_waterproof: Optional[bool] = None
    gs1_product_feature_benefit: Optional[str] = None
    gs1_consumer_lifestage: Optional[str] = None
    gs1_fastening_type: Optional[str] = None
    gs1_footwear_upper_type: Optional[str] = None
    gs1_is_patterned: Optional[bool] = None
    gs1_is_thermal: Optional[bool] = None
    gs1_style_description: Optional[str] = None
    gs1_storage_instructions: Optional[str] = None
    gs1_recycling_instructions: Optional[str] = None
    differentiators: Optional[str] = None
    completeness_score: float = 0.0
    needs_review: bool = False
    status: str = "completed"
    missing_fields: Optional[str] = None
    created_at: datetime
    gap_summary: Optional[str] = None

    model_config = {"from_attributes": True}


class VisibilityCheckRequest(BaseModel):
    query: str
    watched_brands: List[str]


class CompetitorMatchRequest(BaseModel):
    name: str
    description: str


class BenchmarkReportRequest(BaseModel):
    brands: List[str]
    queries: List[str]