from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from analytics import executive_summary, region_aggregate, trends
from models import (
    AggFunc,
    DatasetInfo,
    DeleteResponse,
    ExecutiveSummaryResponse,
    HealthResponse,
    IngestResponse,
    PreviewResponse,
    RegionRow,
    RegionsAnalyticsResponse,
    SchemaResponse,
    TrendsResponse,
)
from store import SAMPLE_DATASET_ID, STORE

logger = logging.getLogger("geo_analytics.routes")

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> Dict[str, str]:
    return {"status": "ok"}


@router.get("/datasets", response_model=List[DatasetInfo])
def list_datasets() -> List[Dict[str, Any]]:
    return [m.__dict__ for m in STORE.list()]


@router.get("/datasets/{dataset_id}/schema", response_model=SchemaResponse)
def dataset_schema(dataset_id: str) -> Dict[str, Any]:
    try:
        df = STORE.get(dataset_id)
    except KeyError as e:
        raise HTTPException(
            status_code=404, detail=f"Unknown dataset_id: {dataset_id}"
        ) from e
    return {
        "dataset_id": dataset_id,
        "columns": [str(c) for c in df.columns.to_list()],
        "rows": int(len(df)),
    }


@router.get("/datasets/{dataset_id}/preview", response_model=PreviewResponse)
def dataset_preview(
    dataset_id: str, limit: int = Query(10, ge=1, le=200)
) -> Dict[str, Any]:
    try:
        df = STORE.get(dataset_id)
    except KeyError as e:
        raise HTTPException(
            status_code=404, detail=f"Unknown dataset_id: {dataset_id}"
        ) from e
    preview = df.head(int(limit)).to_dict(orient="records")
    return {"dataset_id": dataset_id, "rows": int(len(df)), "preview": preview}


@router.post("/datasets/json", response_model=IngestResponse)
def ingest_json(
    records: List[Dict[str, Any]], name: Optional[str] = Query(None)
) -> Dict[str, Any]:
    if not records:
        raise HTTPException(status_code=400, detail="No records provided.")
    meta = STORE.put_records(records, name=name)
    logger.info("Ingested JSON dataset %s (%d rows)", meta.dataset_id, meta.rows)
    return {
        "dataset_id": meta.dataset_id,
        "name": meta.name,
        "rows": meta.rows,
        "columns": meta.columns,
    }


@router.post("/datasets/csv", response_model=IngestResponse)
async def ingest_csv(
    file: UploadFile = File(...), name: Optional[str] = Query(None)
) -> Dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv file.")
    raw = await file.read()
    try:
        df = pd.read_csv(pd.io.common.BytesIO(raw))
    except Exception as e:  # noqa: BLE001 - surface parse errors to user
        raise HTTPException(status_code=400, detail=f"CSV parse error: {e}") from e

    meta = STORE.put_dataframe(df, name=name or file.filename)
    logger.info("Ingested CSV dataset %s (%d rows)", meta.dataset_id, meta.rows)
    return {
        "dataset_id": meta.dataset_id,
        "name": meta.name,
        "rows": meta.rows,
        "columns": meta.columns,
    }


@router.delete("/datasets/{dataset_id}", response_model=DeleteResponse)
def delete_dataset(dataset_id: str) -> Dict[str, str]:
    """Remove a dataset from the store."""
    if dataset_id == SAMPLE_DATASET_ID:
        raise HTTPException(
            status_code=400, detail="Cannot delete the built-in sample dataset."
        )
    try:
        STORE.delete(dataset_id)
    except KeyError as e:
        raise HTTPException(
            status_code=404, detail=f"Unknown dataset_id: {dataset_id}"
        ) from e
    logger.info("Deleted dataset %s", dataset_id)
    return {"deleted": dataset_id, "message": "Dataset deleted."}


@router.get("/regions", response_model=List[RegionRow])
def get_regions(
    dataset_id: str = Query(SAMPLE_DATASET_ID),
    metric: str = Query("revenue"),
    region_col: str = Query("region"),
    lat_col: str = Query("lat"),
    lon_col: str = Query("lon"),
    agg: AggFunc = Query(AggFunc.sum),
) -> List[Dict[str, Any]]:
    """
    Backwards-compatible endpoint used by the Leaflet dashboard demo.
    Returns one row per region with a single numeric value.
    """
    try:
        df = STORE.get(dataset_id)
    except KeyError as e:
        raise HTTPException(
            status_code=404, detail=f"Unknown dataset_id: {dataset_id}"
        ) from e

    if metric not in df.columns:
        # Fallback to legacy "value" column if present.
        if "value" in df.columns:
            value_col = "value"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Metric column '{metric}' not found. Available columns: {df.columns.to_list()}",
            )
    else:
        value_col = metric

    try:
        agg_df = region_aggregate(
            df,
            region_col=region_col,
            value_col=value_col,
            agg=agg.value,
            lat_col=lat_col,
            lon_col=lon_col,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    out: List[Dict[str, Any]] = []
    for r in agg_df.to_dict(orient="records"):
        out.append(
            {
                "region": r["region"],
                "metric": metric,
                "value": float(r["value"]),
                "lat": None if "lat" not in r or pd.isna(r["lat"]) else float(r["lat"]),
                "lon": None if "lon" not in r or pd.isna(r["lon"]) else float(r["lon"]),
            }
        )
    return out


@router.get("/analytics/regions", response_model=RegionsAnalyticsResponse)
def analytics_regions(
    dataset_id: str = Query(SAMPLE_DATASET_ID),
    value_col: str = Query("revenue"),
    region_col: str = Query("region"),
    agg: AggFunc = Query(AggFunc.sum),
) -> Dict[str, Any]:
    try:
        df = STORE.get(dataset_id)
    except KeyError as e:
        raise HTTPException(
            status_code=404, detail=f"Unknown dataset_id: {dataset_id}"
        ) from e
    try:
        out = region_aggregate(
            df, region_col=region_col, value_col=value_col, agg=agg.value
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "dataset_id": dataset_id,
        "value_col": value_col,
        "agg": agg.value,
        "regions": out.to_dict(orient="records"),
    }


@router.get("/analytics/trends", response_model=TrendsResponse)
def analytics_trends(
    dataset_id: str = Query(SAMPLE_DATASET_ID),
    date_col: str = Query("date"),
    region_col: str = Query("region"),
    value_col: str = Query("revenue"),
    agg: AggFunc = Query(AggFunc.sum),
    freq: str = Query("M"),
) -> Dict[str, Any]:
    try:
        df = STORE.get(dataset_id)
    except KeyError as e:
        raise HTTPException(
            status_code=404, detail=f"Unknown dataset_id: {dataset_id}"
        ) from e
    try:
        out = trends(
            df,
            date_col=date_col,
            region_col=region_col,
            value_col=value_col,
            agg=agg.value,
            freq=freq,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "dataset_id": dataset_id,
        "value_col": value_col,
        "agg": agg.value,
        "freq": freq,
        "series": out.to_dict(orient="records"),
    }


@router.get("/analytics/executive-summary", response_model=ExecutiveSummaryResponse)
def analytics_executive_summary(
    dataset_id: str = Query(SAMPLE_DATASET_ID),
    metric: str = Query("revenue"),
    region_col: str = Query("region"),
    value_col: str = Query("revenue"),
    agg: AggFunc = Query(AggFunc.sum),
    top_n: int = Query(3, ge=1, le=10),
) -> Dict[str, Any]:
    try:
        df = STORE.get(dataset_id)
    except KeyError as e:
        raise HTTPException(
            status_code=404, detail=f"Unknown dataset_id: {dataset_id}"
        ) from e
    try:
        out = executive_summary(
            df,
            metric=metric,
            region_col=region_col,
            value_col=value_col,
            agg=agg.value,
            top_n=int(top_n),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    out["dataset_id"] = dataset_id
    return out
