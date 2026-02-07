# Junior Gold Miner Decision Intelligence System

Multi-company gold miner analysis platform tracking **DC**, **PPTA**, and **HYMC**.

**Live App:** [dc-gold.streamlit.app](https://dc-gold.streamlit.app)

## Companies Tracked
- **Dakota Gold (DC)** - Richmond Hill project, South Dakota
- **Perpetua Resources (PPTA)** - Stibnite Gold Project, Idaho
- **Hycroft Mining (HYMC)** - Hycroft Mine, Nevada

## Quick Start

```bash
cd JuniorGoldIntel-Tucker
pip install -r requirements.txt
streamlit run run_dashboard.py
```

The dashboard will open at `http://localhost:8501`

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

## Features

### 1. Executive Summary
- Portfolio health overview
- What changed? What matters? What worries us?
- Company ranking by risk-adjusted returns

### 2. Company Comparison
- Side-by-side metrics for all companies
- Visual comparisons (market cap, AISC, runway)
- Risk profile radar charts

### 3. NPV & Sensitivity Analysis
- DCF valuation with adjustable inputs
- Gold price vs discount rate sensitivity matrix
- Probability-weighted expected NPV
- Breakeven gold price calculation

### 4. Capital & Risk Analysis
- Cash runway gauges
- Dilution scenario modeling (Low/Base/High)
- Risk score breakdown by category
- Cross-company risk comparison

### 5. Signals Feed
- Material changes and alerts
- Price movement signals (>5% moves)
- Funding alerts (runway < 12 months)
- Risk profile warnings

## Project Structure

```
JuniorGoldIntel-Tucker/
├── config/                    # YAML configuration files
│   ├── companies.yaml         # Company & project details
│   ├── assumptions.yaml       # Gold prices, discount rates
│   ├── risk_weights.yaml      # Risk scoring criteria
│   └── benchmarks.yaml        # Self-storage benchmark
├── data_ingestion/            # Data fetching
│   ├── yfinance_fetcher.py    # Stock data via Yahoo Finance
│   ├── gold_price_fetcher.py  # Gold spot price (GC=F)
│   ├── data_normalizer.py     # Standardize across companies
│   └── cache_manager.py       # 15-minute TTL caching
├── financial_models/          # Financial calculations
│   ├── cash_analysis.py       # Runway, burn rate
│   ├── capital_structure.py   # Shares, debt, EV
│   ├── dilution_scenarios.py  # 10%/30%/60% scenarios
│   └── metrics_calculator.py  # Unified metrics interface
├── scenario_engine/           # Valuation models
│   ├── npv_calculator.py      # DCF/NPV calculations
│   ├── sensitivity_matrix.py  # Gold x discount rate grid
│   └── probability_weighting.py # Expected value calcs
├── risk_engine/               # Risk assessment
│   ├── risk_scorer.py         # Composite scoring (1-5)
│   └── categories/            # Category-specific scoring
├── benchmarks/                # Investment comparisons
│   ├── self_storage_model.py  # 18% IRR benchmark
│   └── adjusted_return.py     # Control-adjusted returns
├── dashboard/                 # Streamlit application
│   ├── app.py                 # Main app entry
│   ├── pages/                 # Individual page views
│   │   ├── executive_summary.py
│   │   ├── company_comparison.py
│   │   ├── npv_sensitivity.py
│   │   ├── capital_risk.py
│   │   └── signals_feed.py
│   ├── components/            # Reusable UI components
│   └── styles/custom.css      # Dashboard styling
├── utils/                     # Utilities
│   └── logger.py              # Centralized logging
├── data/                      # Data storage
│   ├── cache/                 # Cached API responses
│   └── exports/               # Generated reports
├── run_dashboard.py           # Main entry point
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Data Sources

- **Live:** Yahoo Finance (stock prices, gold spot, balance sheets)
- **Configured:** YAML files in `JuniorGoldIntel-Tucker/config/` (project assumptions from company filings)

## Configuration

### companies.yaml
Define company details and project parameters:
- Ticker symbol and exchange
- Project: production oz, AISC, mine life, capex, start year
- Control factor for benchmark comparison

### assumptions.yaml
Set market assumptions:
- Gold price scenarios (Bear/Base/Bull/Super Bull)
- Discount rates (5%/8%/10%/12%)
- Tax rates

### risk_weights.yaml
Configure risk scoring:
- Category weights (Funding 25%, Execution 25%, etc.)
- Scoring thresholds
- Company-specific overrides

### benchmarks.yaml
Define comparison benchmarks:
- Self-storage: 18% IRR, 2.5 year timeline
- Control factors by company
- Alternative benchmarks (S&P 500, GDX, GDXJ)

## Key Calculations

### NPV Calculation
```
NPV = Sum(FCF_t / (1+r)^t) - Capex
where FCF = (Revenue - Costs) * (1 - Tax)
```

### Risk Score (1-5 scale)
- **Funding (25%)**: Based on cash runway months
- **Execution (25%)**: Based on project stage
- **Commodity (20%)**: Based on AISC level
- **Control (15%)**: Management quality assessment
- **Timing (15%)**: Years to production

### Control-Adjusted Return
```
Adjusted Return = Mining Return - (Control Factor × Benchmark IRR)
```

## Dependencies

- streamlit>=1.28.0
- yfinance>=0.2.28
- pandas>=2.0.0
- numpy>=1.24.0
- plotly>=5.18.0
- pyyaml>=6.0
- matplotlib>=3.7.0

## Verification Checklist

1. [ ] Dashboard loads: `streamlit run run_dashboard.py`
2. [ ] All 3 tickers show current prices
3. [ ] NPV calculations match expectations (~$2B for DC at base case)
4. [ ] Sensitivity matrix shows breakeven ~$1,400/oz for DC
5. [ ] Risk scores differentiate between companies
6. [ ] Comparison view shows all companies side-by-side
7. [ ] Self-storage benchmark calculates control-adjusted returns

## Notes

- Data is cached for 15 minutes to reduce API calls
- Risk scores are subjective and should be validated
- NPV calculations are simplified and don't account for all factors
- This is not financial advice - conduct your own due diligence
