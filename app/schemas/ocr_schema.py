from typing import List, Optional
from pydantic import BaseModel
from .asset_schema import CycleStatusInfo


class OcrResponse(BaseModel):
    message: str
    found: bool
    asset_number: Optional[str] = None
    asset_name: Optional[str] = None
    raw_text: Optional[List[str]] = None
    status: Optional[CycleStatusInfo] = None
