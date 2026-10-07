"""
Pydantic models for weather function parameters and validation.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .enum import WeatherUnits


class WeatherRequestModel(BaseModel):
    """
    Pydantic model for validating weather function parameters.
    """

    location: str = Field(..., description="City and state, e.g. San Francisco, CA")
    unit: Optional[str] = Field(default=None, description="Unit system")

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Location must be a non-empty string")
        return v.strip()

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in WeatherUnits.all():
            raise ValueError(f"Invalid unit. Supported: {WeatherUnits.all()}")
        return v
