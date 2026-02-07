# Junior Gold Miner Decision Intelligence

Multi-company gold miner analysis platform tracking **DC**, **PPTA**, and **HYMC**.

**Live App:** [dc-gold.streamlit.app](https://dc-gold.streamlit.app)

## Quick Start

```bash
cd JuniorGoldIntel-Tucker
pip install -r requirements.txt
streamlit run run_dashboard.py
```

## What's Here

| Path | Description |
|------|-------------|
| `JuniorGoldIntel-Tucker/` | Main application (Streamlit dashboard + engines) |
| `Dakota_Gold_Script*.gs` | Google Sheets Apps Script for live data in Sheets |

## Dashboard Pages

- **Executive Summary** - Portfolio health, what changed/matters/worries us, export report
- **Company Comparison** - Side-by-side metrics and charts
- **NPV & Sensitivity** - DCF valuation with interactive scenario analysis
- **Capital & Risk** - Cash runway, dilution modeling, risk scoring
- **Signals Feed** - Material changes and alerts
- **About** - Data sources and methodology

## Data Sources

- **Live:** Yahoo Finance (stock prices, gold spot, balance sheets)
- **Configured:** YAML files in `JuniorGoldIntel-Tucker/config/` (project assumptions from company filings)
