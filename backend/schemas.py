"""
schemas.py — Pydantic models for API request / response contracts.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ROIBox(BaseModel):
    x1: int = Field(..., description="Left pixel coordinate")
    y1: int = Field(..., description="Top pixel coordinate")
    x2: int = Field(..., description="Right pixel coordinate")
    y2: int = Field(..., description="Bottom pixel coordinate")


class FrameSize(BaseModel):
    width: int
    height: int


class ROIResponse(BaseModel):
    id: str
    frame_id: str
    session_id: str
    roi: ROIBox
    frame_size: FrameSize
    confidence: Optional[float] = None
    detected_at: datetime

    class Config:
        from_attributes = True


class ROIListResponse(BaseModel):
    total: int
    items: list[ROIResponse]


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
