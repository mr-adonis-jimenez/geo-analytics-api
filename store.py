from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pandas as pd


@dataclass(frozen=True)
class DatasetMeta:
    dataset_id: str
    name: str
    rows: int
    columns: List[str]


class DatasetStore:
    """
    Simple in-memory dataset store.

    Notes:
    - Designed for demos / single-instance deployments.
    - Not durable across restarts.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._data: Dict[str, pd.DataFrame] = {}
        self._names: Dict[str, str] = {}

    def list(self) -> List[DatasetMeta]:
        with self._lock:
            out: List[DatasetMeta] = []
            for dataset_id, df in self._data.items():
                out.append(
                    DatasetMeta(
                        dataset_id=dataset_id,
                        name=self._names.get(dataset_id, dataset_id),
                        rows=int(len(df)),
                        columns=[str(c) for c in df.columns.to_list()],
                    )
                )
            return sorted(out, key=lambda m: m.name.lower())

    def get(self, dataset_id: str) -> pd.DataFrame:
        with self._lock:
            if dataset_id not in self._data:
                raise KeyError(dataset_id)
            return self._data[dataset_id]

    def put_dataframe(
        self, df: pd.DataFrame, *, name: Optional[str] = None
    ) -> DatasetMeta:
        dataset_id = uuid4().hex[:12]
        with self._lock:
            self._data[dataset_id] = df.reset_index(drop=True)
            self._names[dataset_id] = name or dataset_id
            meta = DatasetMeta(
                dataset_id=dataset_id,
                name=self._names[dataset_id],
                rows=int(len(df)),
                columns=[str(c) for c in df.columns.to_list()],
            )
        return meta

    def put_records(
        self, records: List[Dict[str, Any]], *, name: Optional[str] = None
    ) -> DatasetMeta:
        df = pd.DataFrame.from_records(records)
        return self.put_dataframe(df, name=name)

    def delete(self, dataset_id: str) -> None:
        with self._lock:
            if dataset_id not in self._data:
                raise KeyError(dataset_id)
            del self._data[dataset_id]
            self._names.pop(dataset_id, None)


def _sample_dataset() -> pd.DataFrame:
    # Minimal sample dataset used by the dashboard demo + analytics examples.
    # Columns:
    # - region: str
    # - lat/lon: float (for mapping)
    # - date: ISO date string (for trends)
    # - revenue: numeric KPI
    return pd.DataFrame.from_records(
        [
            {
                "region": "North America",
                "lat": 37.09,
                "lon": -95.71,
                "date": "2025-10-01",
                "revenue": 410000,
            },
            {
                "region": "North America",
                "lat": 37.09,
                "lon": -95.71,
                "date": "2025-11-01",
                "revenue": 390000,
            },
            {
                "region": "North America",
                "lat": 37.09,
                "lon": -95.71,
                "date": "2025-12-01",
                "revenue": 420000,
            },
            {
                "region": "Europe",
                "lat": 54.52,
                "lon": 15.25,
                "date": "2025-10-01",
                "revenue": 270000,
            },
            {
                "region": "Europe",
                "lat": 54.52,
                "lon": 15.25,
                "date": "2025-11-01",
                "revenue": 280000,
            },
            {
                "region": "Europe",
                "lat": 54.52,
                "lon": 15.25,
                "date": "2025-12-01",
                "revenue": 300000,
            },
            {
                "region": "South America",
                "lat": -14.24,
                "lon": -51.93,
                "date": "2025-10-01",
                "revenue": 120000,
            },
            {
                "region": "South America",
                "lat": -14.24,
                "lon": -51.93,
                "date": "2025-11-01",
                "revenue": 125000,
            },
            {
                "region": "South America",
                "lat": -14.24,
                "lon": -51.93,
                "date": "2025-12-01",
                "revenue": 130000,
            },
            {
                "region": "APAC",
                "lat": 34.05,
                "lon": 100.62,
                "date": "2025-10-01",
                "revenue": 310000,
            },
            {
                "region": "APAC",
                "lat": 34.05,
                "lon": 100.62,
                "date": "2025-11-01",
                "revenue": 330000,
            },
            {
                "region": "APAC",
                "lat": 34.05,
                "lon": 100.62,
                "date": "2025-12-01",
                "revenue": 340000,
            },
        ]
    )


STORE = DatasetStore()
SAMPLE_DATASET_ID = "sample"

# Load sample dataset deterministically under a stable ID.
with STORE._lock:  # noqa: SLF001 - module-level bootstrap
    STORE._data[SAMPLE_DATASET_ID] = _sample_dataset()
    STORE._names[SAMPLE_DATASET_ID] = "Sample dataset"
