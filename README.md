## Release Pipeline

- ✔ OIDC-based publishing (no secrets)
- ✔ Verified supply-chain provenance
- ✔ Automated quality gates (lint, test, audit)
- ✔ Reusable CI workflows

## Contributing / Branch protection

Direct pushes to `main` should be avoided. See `CONTRIBUTING.md` to enable the repo's `pre-push` hook that blocks direct pushes to `main` locally.

## Release & Security Architecture

- OIDC-based trusted publishing (no secrets)
- Canary & RC release channels
- SBOM generation (CycloneDX)
- CodeQL static analysis
- Dependabot automated updates

This pipeline enforces supply-chain integrity and production-grade quality gates.

![CI](https://github.com/mr-adonis-jimenez/geo-analytics-api/actions/workflows/ci-cd.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

# 🌎 Geo-Analytics API/Dashboard

**Geospatial Intelligence · Data Visualization · Operational Insight**

The **Geo-Analytics API/Dashboard** is a data-driven analytics platform designed to transform raw geographic and regional datasets into clear, actionable intelligence. It enables organizations to analyze performance by location, identify trends, and support strategic decision-making through interactive visualizations and automated data workflows.

This project reflects a traditional analytics discipline—**clean data in, meaningful insight out**—implemented with modern tooling and forward-looking design.

---

## 🎯 Purpose & Use Cases

This dashboard is built to answer questions executives and operators actually ask:

- Which regions are outperforming or underperforming?  
- How does demand, activity, or revenue vary geographically?  
- Where should resources, sales efforts, or infrastructure be prioritized?  
- How do regional trends evolve over time?  

### Ideal For
- Business intelligence & operations teams  
- Sales & marketing analytics  
- Logistics & territory planning  
- Public-sector or urban analytics  
- Portfolio and case-study demonstrations  

---

## 🧠 Core Features

### Geospatial Visualization
- Interactive regional maps (choropleths, markers, heat layers)  
- Location-based comparisons and drill-downs  

### Analytics & KPIs
- Region-level performance metrics  
- Trend analysis across time and geography  

### Automated Data Pipeline
- Data ingestion and transformation using Python  
- Structured outputs for repeatable analysis  

### Dashboard-Ready Outputs
- Clean datasets optimized for visualization layers  
- Exportable formats (**CSV / JSON**)  

### Scalable Architecture
- Modular design for future API integration  
- Ready for cloud deployment or embedding into BI tools  

---

## 🚀 Quickstart (Geo Analytics API)

### Run the API

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open interactive docs at `http://localhost:8000/docs`.

### Try the sample dataset

```bash
curl -s "http://localhost:8000/api/datasets" | jq
curl -s "http://localhost:8000/api/regions" | jq
curl -s "http://localhost:8000/api/analytics/regions?dataset_id=sample&value_col=revenue&agg=sum" | jq
curl -s "http://localhost:8000/api/analytics/trends?dataset_id=sample&date_col=date&value_col=revenue&freq=M" | jq
curl -s "http://localhost:8000/api/analytics/executive-summary?dataset_id=sample&metric=revenue&value_col=revenue" | jq
```

### Ingest your own dataset (JSON)

```bash
curl -s -X POST "http://localhost:8000/api/datasets/json?name=my-dataset" \
  -H "Content-Type: application/json" \
  -d '[{"region":"North","lat":1.0,"lon":2.0,"date":"2025-01-01","revenue":100}]' | jq
```

### Ingest your own dataset (CSV)

```bash
curl -s -X POST "http://localhost:8000/api/datasets/csv?name=my-csv" \
  -F "file=@regional_data.csv" | jq
```
