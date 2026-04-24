from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# ==========================================
# ROLE 1: LEAD DATA ARCHITECT
# ==========================================
# v1 of the Unified Schema for all sources.
# NOTE: A breaking change (v2 migration) may rename fields later.

class UnifiedDocument(BaseModel):
    """
    Unified schema for all ingested documents across all source types.
    Supports: PDF, Video, HTML, CSV, Code
    """
    document_id: str = Field(..., description="Unique identifier for the document")
    content: str = Field(..., description="Main text content of the document")
    source_type: str = Field(..., description="Type of source: 'PDF', 'Video', 'HTML', 'CSV', 'Code'")
    author: Optional[str] = Field(default="Unknown", description="Author of the document")
    timestamp: Optional[datetime] = Field(default=None, description="Creation or sale timestamp")

    # Flexible dict for source-specific fields (e.g., price, stock, region_code)
    source_metadata: dict = Field(default_factory=dict, description="Source-specific metadata")

    class Config:
        # Allow extra fields to be flexible during schema migration
        extra = "allow"
