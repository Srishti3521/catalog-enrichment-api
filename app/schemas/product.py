from pydantic import BaseModel
from typing import Optional

class RawProduct(BaseModel):
    name: str
    description: str

class EnrichedProduct(BaseModel):
    name: str
    description: str
    material: Optional[str] = None
    use_case: Optional[str] = None
    size_range: Optional[str] = None
    gender: Optional[str] = None
    weather_resistance: Optional[str] = None
    completeness_score: float = 0.0
    needs_review: bool = False