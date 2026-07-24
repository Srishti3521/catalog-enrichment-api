from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from typing import List
class RawProduct(BaseModel):
    name: str
    description: str
    price: Optional[float] = None
    currency: Optional[str] = None
    colour: Optional[str] = None
    url: Optional[str] = None
    availability: Optional[str] = None
    rating: Optional[float] = None
    available_sizes: Optional[str] = None

class EnrichedProduct(BaseModel):
    id: int
    name: str
    description: str
    material: Optional[str] = None
    use_case: Optional[str] = None
    size_range: Optional[str] = None
    gender: Optional[str] = None
    weather_resistance: Optional[str] = None
    key_features: Optional[str] = None
    target_audience: Optional[str] = None
    differentiators: Optional[str] = None
    completeness_score: float = 0.0
    needs_review: bool = False
    status: str = "completed"
    missing_fields: Optional[str] = None
    created_at: datetime
    gap_summary: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    colour: Optional[str] = None
    url: Optional[str] = None
    availability: Optional[str] = None
    rating: Optional[float] = None
    available_sizes: Optional[str] = None

    model_config = {"from_attributes": True}
    

class VisibilityCheckRequest(BaseModel):
    query: str
    watched_brands: List[str]