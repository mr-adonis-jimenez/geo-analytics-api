from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


@dataclass(frozen=True)
class RegionValue:
    region: str
    value: float


def _require_columns(df: pd.DataFrame, cols: List[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def region_aggregate(
    df: pd.DataFrame,
    *,
    region_col: str,
    value_col: str,
    agg: str = "sum",
    lat_col: Optional[str] = None,
    lon_col: Optional[str] = None,
) -> pd.DataFrame:
    _require_columns(df, [region_col, value_col])
    grouped = df.groupby(region_col, dropna=False)[value_col].agg(agg).reset_index()
    grouped = grouped.rename(columns={region_col: "region", value_col: "value"})

    if lat_col and lon_col and lat_col in df.columns and lon_col in df.columns:
        # Use mean coordinate per region for mapping.
        coords = (
            df.groupby(region_col, dropna=False)[[lat_col, lon_col]]
            .mean(numeric_only=True)
            .reset_index()
        )
        coords = coords.rename(
            columns={region_col: "region", lat_col: "lat", lon_col: "lon"}
        )
        grouped = grouped.merge(coords, on="region", how="left")

    grouped["value"] = pd.to_numeric(grouped["value"], errors="coerce")
    grouped = grouped.dropna(subset=["value"])
    grouped = grouped.sort_values(
        "value", ascending=False, kind="mergesort"
    ).reset_index(drop=True)
    return grouped


def rankings(
    df: pd.DataFrame,
    *,
    region_col: str,
    value_col: str,
    agg: str = "sum",
    top_n: int = 5,
) -> Tuple[List[RegionValue], List[RegionValue]]:
    agg_df = region_aggregate(df, region_col=region_col, value_col=value_col, agg=agg)
    values = [
        RegionValue(region=str(r["region"]), value=float(r["value"]))
        for r in agg_df[["region", "value"]].to_dict(orient="records")
    ]
    top = values[: max(0, int(top_n))]
    bottom = list(reversed(values[-max(0, int(top_n)) :])) if top_n > 0 else []
    return top, bottom


def trends(
    df: pd.DataFrame,
    *,
    date_col: str,
    region_col: str,
    value_col: str,
    agg: str = "sum",
    freq: str = "M",
) -> pd.DataFrame:
    _require_columns(df, [date_col, region_col, value_col])

    tmp = df[[date_col, region_col, value_col]].copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce", utc=True)
    tmp[value_col] = pd.to_numeric(tmp[value_col], errors="coerce")
    tmp = tmp.dropna(subset=[date_col, value_col])

    # Pandas deprecated "M" in favor of month-end "ME".
    # Accept "M" from callers but normalize to keep logs clean.
    if freq == "M":
        freq = "ME"

    tmp = tmp.set_index(date_col)
    out = (
        tmp.groupby([pd.Grouper(freq=freq), region_col], dropna=False)[value_col]
        .agg(agg)
        .reset_index()
        .rename(columns={region_col: "region", value_col: "value"})
    )

    # Ensure output always includes a "date" string column, even if the caller's
    # input date column is also named "date".
    bucket_col = "__bucket__"
    out = out.rename(columns={date_col: bucket_col})
    out["date"] = out[bucket_col].dt.date.astype(str)
    out = (
        out.drop(columns=[bucket_col])
        .sort_values(["date", "region"])
        .reset_index(drop=True)
    )
    return out


def executive_summary(
    df: pd.DataFrame,
    *,
    metric: str,
    region_col: str,
    value_col: str,
    agg: str = "sum",
    top_n: int = 3,
) -> Dict[str, Any]:
    """
    Deterministic, executive-friendly summary without any LLM dependency.
    """
    agg_df = region_aggregate(df, region_col=region_col, value_col=value_col, agg=agg)
    if agg_df.empty:
        return {
            "summary": "No analyzable data after validation (missing/invalid numeric values).",
            "key_findings": [],
            "regional_comparison": {},
        }

    total = float(agg_df["value"].sum())
    top, bottom = rankings(
        df, region_col=region_col, value_col=value_col, agg=agg, top_n=top_n
    )

    best = top[0]
    worst = bottom[0] if bottom else top[-1]

    def pct(v: float) -> float:
        return 0.0 if total == 0 else (v / total) * 100.0

    key_findings: List[str] = [
        f"Top region: {best.region} ({best.value:,.2f} {metric}, {pct(best.value):.1f}% of total).",
        f"Bottom region: {worst.region} ({worst.value:,.2f} {metric}, {pct(worst.value):.1f}% of total).",
        f"Total across regions: {total:,.2f} {metric}.",
    ]

    regional_comparison: Dict[str, Dict[str, str]] = {}
    for rv in top:
        regional_comparison[rv.region] = {f"{metric}_{agg}": f"{rv.value:,.2f}"}
    for rv in bottom:
        regional_comparison.setdefault(
            rv.region, {f"{metric}_{agg}": f"{rv.value:,.2f}"}
        )

    return {
        "summary": f"{best.region} leads on {metric} ({agg}), while {worst.region} lags.",
        "key_findings": key_findings,
        "regional_comparison": regional_comparison,
    }
