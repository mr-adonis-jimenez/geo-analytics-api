from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AggFunc(str, Enum):
    """Supported aggregation functions."""

    sum = "sum"
    mean = "mean"
    min = "min"
    max = "max"
    count = "count"
    median = "median"


# ---------------------------------------------------------------------------
# Request / shared helpers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])


class DatasetInfo(BaseModel):
    dataset_id: str
    name: str
    rows: int
    columns: List[str]


class SchemaResponse(BaseModel):
    dataset_id: str
    columns: List[str]
    rows: int


class PreviewResponse(BaseModel):
    dataset_id: str
    rows: int
    preview: List[Dict[str, Any]]


class IngestResponse(BaseModel):
    dataset_id: str
    name: str
    rows: int
    columns: List[str]


class RegionRow(BaseModel):
    region: str
    metric: str
    value: float
    lat: Optional[float] = None
    lon: Optional[float] = None


class RegionsAnalyticsResponse(BaseModel):
    dataset_id: str
    value_col: str
    agg: str
    regions: List[Dict[str, Any]]


class TrendPoint(BaseModel):
    date: str
    region: str
    value: float


class TrendsResponse(BaseModel):
    dataset_id: str
    value_col: str
    agg: str
    freq: str
    series: List[Dict[str, Any]]


class ExecutiveSummaryResponse(BaseModel):
    dataset_id: str
    summary: str
    key_findings: List[str]
    regional_comparison: Dict[str, Dict[str, str]]


class DeleteResponse(BaseModel):
    deleted: str
    message: str
