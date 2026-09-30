from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    """Operational health status schema."""
    status: str = Field(
        ...,
        description="Current operational status of the service",
        examples=["healthy"]
    )
