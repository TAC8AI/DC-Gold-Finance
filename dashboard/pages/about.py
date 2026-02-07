"""
About page: Data sources, methodology, and transparency
"""
import streamlit as st
from datetime import datetime


def render_about():
    """Render the about/data sources page"""

    st.markdown("## About This Dashboard")
    st.markdown("Understanding where the data comes from and how it's calculated")

    st.markdown("---")

    # Data Sources Section
    st.markdown("### Data Sources")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style="background: #f0fdf4; border-left: 4px solid #22c55e; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
            <h4 style="color: #166534; margin: 0 0 8px 0;">LIVE DATA</h4>
            <p style="color: #15803d; margin: 0; font-size: 0.9rem;">Updated in real-time from Yahoo Finance</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        **Stock Prices & Market Data**
        - Source: **Yahoo Finance API** (via `yfinance` library)
        - Tickers: `DC`, `PPTA`, `HYMC`
        - Updates: Every page load (cached 15 minutes)
        - Data includes:
            - Current share price
            - Previous close
            - Daily change %
            - Market capitalization
            - 52-week high/low
            - Trading volume

        **Gold Spot Price**
        - Source: **Yahoo Finance** (`GC=F` futures ticker)
        - Updates: Every page load (cached 15 minutes)
        - Represents COMEX gold futures

        **Company Financials**
        - Source: **Yahoo Finance** quarterly reports
        - Data includes:
            - Cash & cash equivalents
            - Total debt
            - Free cash flow (for burn rate)
        """)

    with col2:
        st.markdown("""
        <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
            <h4 style="color: #1e40af; margin: 0 0 8px 0;">CONFIGURED DATA</h4>
            <p style="color: #1d4ed8; margin: 0; font-size: 0.9rem;">Set in YAML config files, based on company disclosures</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        **Project Parameters** (from `config/companies.yaml`)
        - Annual production (oz/year)
        - AISC (All-In Sustaining Cost)
        - Mine life (years)
        - Initial capex ($M)
        - Production start year
        - Project stage

        *These come from company presentations, feasibility studies, and SEC filings.*

        **Assumptions** (from `config/assumptions.yaml`)
        - Gold price scenarios (Bear/Base/Bull)
        - Discount rates (5%, 8%, 10%, 12%)
        - Tax rate (25%)

        **Risk Weights** (from `config/risk_weights.yaml`)
        - Category weights
        - Scoring thresholds
        - Management quality scores
        """)

    st.markdown("---")

    # Page-by-Page Breakdown
    st.markdown("### What Each Page Shows")

    with st.expander("Executive Summary", expanded=True):
        st.markdown("""
        | Element | Data Source | Live? |
        |---------|-------------|-------|
        | Gold Price | Yahoo Finance `GC=F` | Yes |
        | Company Prices | Yahoo Finance | Yes |
        | Market Cap | Yahoo Finance | Yes |
        | Cash Runway | Calculated from Yahoo Finance (cash / burn rate) | Yes |
        | Risk Scores | Calculated from live + config data | Mixed |
        | "What Changed" | Price movements from Yahoo Finance | Yes |
        | "What Worries Us" | Based on thresholds in config | Mixed |
        """)

    with st.expander("Company Comparison"):
        st.markdown("""
        | Element | Data Source | Live? |
        |---------|-------------|-------|
        | Price, Market Cap | Yahoo Finance | Yes |
        | Cash Position | Yahoo Finance balance sheet | Yes |
        | Runway | Calculated (cash / quarterly burn) | Yes |
        | AISC, Production | Config files (company disclosures) | No |
        | Margin | Live gold price - configured AISC | Mixed |
        | Risk Radar Chart | Calculated from mixed sources | Mixed |
        | Timeline Chart | Config files | No |
        """)

    with st.expander("NPV & Sensitivity"):
        st.markdown("""
        | Element | Data Source | Live? |
        |---------|-------------|-------|
        | Current Gold Price | Yahoo Finance | Yes |
        | Project NPV | **Calculated** using DCF model | Calculated |
        | Sensitivity Matrix | **Calculated** across gold/discount scenarios | Calculated |
        | Expected NPV | **Calculated** with probability weighting | Calculated |
        | Breakeven Gold | **Calculated** via binary search | Calculated |
        | Cash Flow Chart | **Calculated** from project parameters | Calculated |
        | IRR, Payback | **Calculated** from cash flows | Calculated |

        **NPV Formula:**
        ```
        NPV = Σ(FCF_t / (1+r)^t) - Capex

        Where:
        FCF = (Production × Gold Price - Production × AISC) × (1 - Tax Rate)
        ```

        *Project parameters (production, AISC, capex, mine life) come from config files based on company disclosures.*
        """)

    with st.expander("Capital & Risk"):
        st.markdown("""
        | Element | Data Source | Live? |
        |---------|-------------|-------|
        | Cash on Hand | Yahoo Finance balance sheet | Yes |
        | Quarterly Burn | Yahoo Finance cash flow statement | Yes |
        | Runway Gauge | Calculated (cash / burn) | Yes |
        | Shares Outstanding | Yahoo Finance | Yes |
        | Funding Gap | Capex (config) - Cash (live) | Mixed |
        | Dilution Scenarios | **Modeled** (10%/30%/60% scenarios) | Calculated |
        | Risk Scores | **Calculated** from thresholds | Mixed |

        **Risk Score Categories:**
        - **Funding (25%)**: Based on cash runway months (live)
        - **Execution (25%)**: Based on project stage (config)
        - **Commodity (20%)**: Based on AISC level (config)
        - **Control (15%)**: Management quality (config, manual)
        - **Timing (15%)**: Years to production (config)
        """)

    with st.expander("Signals Feed"):
        st.markdown("""
        | Signal Type | Trigger | Data Source |
        |-------------|---------|-------------|
        | Price Movement | >5% daily change | Yahoo Finance (live) |
        | Gold Move | >1.5% daily change | Yahoo Finance GC=F (live) |
        | Runway Alert | <12 months runway | Calculated from live data |
        | Critical Runway | <6 months runway | Calculated from live data |
        | Risk Alert | Composite score <2.0 | Calculated |
        | Margin Alert | <$500/oz margin | Live gold - config AISC |
        | 52-Week Proximity | Near high or >40% below | Yahoo Finance (live) |

        *Signals are generated fresh on each page load based on current data.*
        """)

    st.markdown("---")

    # Caching & Refresh
    st.markdown("### Data Freshness & Caching")

    st.markdown("""
    <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 8px;">
        <h4 style="color: #92400e; margin: 0 0 8px 0;">CACHING</h4>
        <p style="color: #a16207; margin: 0;">
            API responses are cached for <strong>15 minutes</strong> to reduce load on Yahoo Finance.
            Click <strong>"Refresh Data"</strong> in the sidebar to clear cache and fetch fresh data.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    **Cache Details:**
    - Location: `data/cache/` folder
    - TTL: 15 minutes
    - Cleared on: "Refresh Data" button click

    **Market Hours Note:**
    - US stock data updates during market hours (9:30 AM - 4:00 PM ET)
    - Gold futures trade nearly 24 hours (Sunday 6 PM - Friday 5 PM ET)
    - Outside market hours, you'll see last closing prices
    """)

    st.markdown("---")

    # Calculations Methodology
    st.markdown("### Calculation Methodology")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Cash Runway**
        ```
        Runway (months) = (Total Cash / Quarterly Burn) × 3
        ```
        - Cash from most recent quarterly balance sheet (annual fallback)
        - Burn rate from free cash flow (quarterly preferred, annual fallback)

        **Dilution Scenarios**
        | Scenario | Dilution | Probability |
        |----------|----------|-------------|
        | Low | 10% | 20% |
        | Base | 30% | 50% |
        | High | 60% | 25% |
        | Extreme | 100% | 5% |

        Expected dilution = weighted average
        """)

    with col2:
        st.markdown("""
        **Control-Adjusted Return**
        ```
        Adjusted = Mining Return - (Control Factor × 18% Benchmark)
        ```
        - Benchmark: Self-storage at 18% IRR
        - Control factors: 0.20-0.30 per company

        **Risk Scoring (1-5 scale)**
        - 1 = Highest risk
        - 5 = Lowest risk
        - Composite = weighted average of 5 categories
        """)

    st.markdown("---")

    # Limitations
    st.markdown("### Limitations & Disclaimers")

    st.warning("""
    **Important Limitations:**

    1. **Yahoo Finance Data**: Free API with occasional delays or gaps. Not suitable for trading decisions.

    2. **Project Parameters**: Based on company disclosures which may be outdated. Always verify against latest filings.

    3. **NPV Calculations**: Simplified model that doesn't account for:
       - Inflation/escalation
       - Working capital
       - Closure costs
       - Resource depletion curves
       - Financing costs

    4. **Risk Scores**: Subjective framework. Weights and thresholds are configurable but arbitrary.

    5. **Cash Burn**: Based on historical cash flow, may not reflect current spending plans.
    """)

    st.error("""
    **NOT FINANCIAL ADVICE**

    This dashboard is for informational and educational purposes only. It does not constitute investment advice,
    financial advice, trading advice, or any other sort of advice. You should conduct your own due diligence
    and consult with a qualified financial advisor before making any investment decisions.
    """)

    st.markdown("---")

    # Config File Locations
    st.markdown("### Configuration Files")

    st.code("""
    JuniorGoldIntel-Tucker/
    └── config/
        ├── companies.yaml      # Company & project details
        ├── assumptions.yaml    # Gold prices, discount rates
        ├── risk_weights.yaml   # Risk scoring criteria
        └── benchmarks.yaml     # Self-storage benchmark
    """, language="text")

    st.markdown("*Edit these YAML files to update project parameters, add companies, or adjust assumptions.*")

    st.markdown("---")

    # Version Info
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Version:** 1.0.0")

    with col2:
        st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}")

    with col3:
        st.markdown("**Data Provider:** Yahoo Finance")
