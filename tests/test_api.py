import io

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Dataset listing / metadata
# ---------------------------------------------------------------------------


def test_sample_dataset_present():
    res = client.get("/api/datasets")
    assert res.status_code == 200
    datasets = res.json()
    assert any(d["dataset_id"] == "sample" for d in datasets)


def test_dataset_schema():
    res = client.get("/api/datasets/sample/schema")
    assert res.status_code == 200
    body = res.json()
    assert body["dataset_id"] == "sample"
    assert "region" in body["columns"]
    assert "revenue" in body["columns"]
    assert body["rows"] == 12


def test_dataset_schema_not_found():
    res = client.get("/api/datasets/nonexistent/schema")
    assert res.status_code == 404


def test_dataset_preview():
    res = client.get("/api/datasets/sample/preview?limit=3")
    assert res.status_code == 200
    body = res.json()
    assert len(body["preview"]) == 3
    assert body["rows"] == 12


def test_dataset_preview_default_limit():
    res = client.get("/api/datasets/sample/preview")
    assert res.status_code == 200
    assert len(res.json()["preview"]) == 10


def test_dataset_preview_not_found():
    res = client.get("/api/datasets/nonexistent/preview")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Regions (dashboard endpoint)
# ---------------------------------------------------------------------------


def test_regions_works_for_sample():
    res = client.get("/api/regions")
    assert res.status_code == 200
    rows = res.json()
    assert isinstance(rows, list)
    assert len(rows) >= 1
    assert {"region", "metric", "value", "lat", "lon"} <= set(rows[0].keys())


def test_regions_bad_metric():
    res = client.get("/api/regions?metric=nonexistent")
    assert res.status_code == 400


def test_regions_bad_dataset():
    res = client.get("/api/regions?dataset_id=nope")
    assert res.status_code == 404


def test_regions_agg_mean():
    res = client.get("/api/regions?agg=mean")
    assert res.status_code == 200
    rows = res.json()
    # Mean of North America revenue: (410k+390k+420k)/3 = 406666.67
    na = next(r for r in rows if r["region"] == "North America")
    assert abs(na["value"] - 406666.67) < 1


def test_regions_invalid_agg():
    res = client.get("/api/regions?agg=invalid_func")
    assert res.status_code == 422  # validation error from AggFunc enum


# ---------------------------------------------------------------------------
# JSON ingestion
# ---------------------------------------------------------------------------


def test_ingest_json_and_analytics():
    payload = [
        {"region": "A", "lat": 10.0, "lon": 10.0, "date": "2025-01-01", "revenue": 100},
        {"region": "A", "lat": 10.0, "lon": 10.0, "date": "2025-02-01", "revenue": 150},
        {"region": "B", "lat": 20.0, "lon": 20.0, "date": "2025-01-01", "revenue": 90},
    ]
    res = client.post("/api/datasets/json?name=unit-test", json=payload)
    assert res.status_code == 200
    dataset_id = res.json()["dataset_id"]

    res2 = client.get(
        f"/api/analytics/regions?dataset_id={dataset_id}&value_col=revenue&agg=sum"
    )
    assert res2.status_code == 200
    regions = res2.json()["regions"]
    assert [r["region"] for r in regions] == ["A", "B"]
    assert regions[0]["value"] == 250

    res3 = client.get(
        f"/api/analytics/trends?dataset_id={dataset_id}&date_col=date&region_col=region&value_col=revenue"
    )
    assert res3.status_code == 200
    series = res3.json()["series"]
    assert any(p["region"] == "A" for p in series)


def test_ingest_json_empty():
    res = client.post("/api/datasets/json", json=[])
    assert res.status_code == 400
    assert "No records" in res.json()["detail"]


def test_ingest_json_with_name():
    payload = [{"x": 1}]
    res = client.post("/api/datasets/json?name=my-data", json=payload)
    assert res.status_code == 200
    assert res.json()["name"] == "my-data"


# ---------------------------------------------------------------------------
# CSV ingestion
# ---------------------------------------------------------------------------


def test_ingest_csv():
    csv_content = "region,revenue\nAlpha,100\nBeta,200\n"
    file = io.BytesIO(csv_content.encode())
    res = client.post(
        "/api/datasets/csv", files={"file": ("data.csv", file, "text/csv")}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["rows"] == 2
    assert "region" in body["columns"]
    assert "revenue" in body["columns"]


def test_ingest_csv_not_csv_extension():
    file = io.BytesIO(b"data")
    res = client.post(
        "/api/datasets/csv", files={"file": ("data.txt", file, "text/plain")}
    )
    assert res.status_code == 400
    assert ".csv" in res.json()["detail"]


def test_ingest_csv_malformed():
    file = io.BytesIO(b"\x00\x01\x02\x03")
    res = client.post(
        "/api/datasets/csv", files={"file": ("bad.csv", file, "text/csv")}
    )
    # Should still parse (pandas may treat it as single-column) or return 400
    assert res.status_code in (200, 400)


# ---------------------------------------------------------------------------
# Delete dataset
# ---------------------------------------------------------------------------


def test_delete_dataset():
    # First create one
    payload = [{"a": 1}]
    res = client.post("/api/datasets/json?name=to-delete", json=payload)
    assert res.status_code == 200
    did = res.json()["dataset_id"]

    # Delete it
    res2 = client.delete(f"/api/datasets/{did}")
    assert res2.status_code == 200
    assert res2.json()["deleted"] == did

    # Verify it's gone
    res3 = client.get(f"/api/datasets/{did}/schema")
    assert res3.status_code == 404


def test_delete_sample_blocked():
    res = client.delete("/api/datasets/sample")
    assert res.status_code == 400
    assert "sample" in res.json()["detail"].lower()


def test_delete_nonexistent():
    res = client.delete("/api/datasets/does-not-exist")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Analytics: regions
# ---------------------------------------------------------------------------


def test_analytics_regions_sum():
    res = client.get("/api/analytics/regions")
    assert res.status_code == 200
    body = res.json()
    assert body["agg"] == "sum"
    regions = body["regions"]
    assert len(regions) == 4
    # North America total = 410k + 390k + 420k = 1220k
    na = next(r for r in regions if r["region"] == "North America")
    assert na["value"] == 1220000


def test_analytics_regions_missing_column():
    res = client.get("/api/analytics/regions?value_col=nonexistent")
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# Analytics: trends
# ---------------------------------------------------------------------------


def test_analytics_trends_sample():
    res = client.get("/api/analytics/trends")
    assert res.status_code == 200
    body = res.json()
    assert body["freq"] == "M"
    assert len(body["series"]) > 0
    first = body["series"][0]
    assert "date" in first
    assert "region" in first
    assert "value" in first


def test_analytics_trends_missing_date_col():
    res = client.get("/api/analytics/trends?date_col=nonexistent")
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# Analytics: executive summary
# ---------------------------------------------------------------------------


def test_executive_summary():
    res = client.get("/api/analytics/executive-summary")
    assert res.status_code == 200
    body = res.json()
    assert "summary" in body
    assert "key_findings" in body
    assert isinstance(body["key_findings"], list)
    assert len(body["key_findings"]) >= 1
    assert "regional_comparison" in body
    assert "North America" in body["regional_comparison"]


def test_executive_summary_top_n():
    res = client.get("/api/analytics/executive-summary?top_n=2")
    assert res.status_code == 200
    body = res.json()
    assert len(body["regional_comparison"]) <= 4  # at most all regions


def test_executive_summary_bad_dataset():
    res = client.get("/api/analytics/executive-summary?dataset_id=nope")
    assert res.status_code == 404
