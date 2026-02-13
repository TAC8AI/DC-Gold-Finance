"""
Executive summary page: decision-first view for investors and management.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from benchmarks.adjusted_return import AdjustedReturnCalculator
from dashboard.report_generator import generate_report
from financial_models.metrics_calculator import MetricsCalculator
from financial_models.nav_model import CorporateNAVModel
from risk_engine.risk_scorer import RiskScorer
from data_ingestion.gold_price_fetcher import GoldPriceFetcher


def _fmt_time(value: str) -> str:
    """Safely format timestamps for compact readouts."""
    if not value:
        return "N/A"
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(value)[:16]


def _funding_window(runway_months: float) -> str:
    """Estimate when financing pressure likely emerges."""
    if runway_months is None or runway_months <= 0:
        return "Unknown"
    funding_date = datetime.now() + timedelta(days=runway_months * 30)
    return funding_date.strftime("%b %Y")


def _risk_tier_class(score: float) -> str:
    """Map numeric score to CSS class used in company cards."""
    if score < 2.5:
        return "risk-tier-high"
    if score < 3.5:
        return "risk-tier-moderate"
    return "risk-tier-low"


def _fmt_oz(value: Any) -> str:
    """Format ounce values for compact dashboard display."""
    if value is None:
        return "N/A"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if numeric <= 0:
        return "N/A"
    return f"{numeric:,.0f}"


def _fmt_moz(value: Any) -> str:
    """Format million-ounce figures."""
    if value is None:
        return "N/A"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if numeric <= 0:
        return "N/A"
    return f"{numeric:.2f} Moz"


def _primary_concern(metrics: Dict[str, Any], risk: Dict[str, Any]) -> str:
    """Return top concern text for quick monitoring."""
    concerns = []
    runway = metrics.get("runway_months", 0)

    if runway and runway < 12:
        concerns.append(f"Runway {runway:.0f} mo")

    if metrics.get("expected_dilution", 0) > 40:
        concerns.append(f"Dilution {metrics.get('expected_dilution', 0):.0f}%")

    if metrics.get("aisc", 0) > 1400:
        concerns.append(f"AISC ${metrics.get('aisc', 0):,.0f}")

    if metrics.get("start_year", 2030) > datetime.now().year + 3:
        concerns.append(f"Start year {metrics.get('start_year', 2030)}")

    if not concerns:
        return "No major flags"

    weakest = risk.get("weakest_category", "risk")
    return f"{weakest.title()}: {', '.join(concerns)}"


def render_executive_summary(tickers: List[str]):
    """Render executive summary with value, risk, and action framing."""
    if not tickers:
        st.warning("No companies configured. Add tickers in config/companies.yaml.")
        return

    metrics_calc = MetricsCalculator()
    risk_scorer = RiskScorer()
    gold_fetcher = GoldPriceFetcher()
    return_calc = AdjustedReturnCalculator()
    nav_model = CorporateNAVModel()

    gold_data = gold_fetcher.get_current_price()
    gold_price = gold_data.get("price", 2100)
    gold_change = gold_data.get("daily_change_pct", 0)

    all_metrics: Dict[str, Dict[str, Any]] = {}
    all_risks: Dict[str, Dict[str, Any]] = {}
    all_returns: Dict[str, Dict[str, Any]] = {}

    for ticker in tickers:
        all_metrics[ticker] = metrics_calc.get_summary_metrics(ticker)
        all_risks[ticker] = risk_scorer.calculate_composite_score(ticker)
        all_returns[ticker] = return_calc.calculate_adjusted_return(ticker)

    nav_analysis = nav_model.compare_companies(
        tickers=tickers,
        gold_price=float(gold_price),
        discount_rate_primary=0.08,
        discount_rate_secondary=0.05,
        use_stage_risking=True,
    )
    nav_summary_df = nav_analysis.get("summary_df", pd.DataFrame())
    nav_peer_stats = nav_analysis.get("peer_stats", {})
    nav_primary_col = nav_peer_stats.get("primary_pnav_col", "P/NAV @8% (x)")
    nav_lookup = {
        row["Ticker"]: row for _, row in nav_summary_df.iterrows()
    } if not nav_summary_df.empty else {}

    focus_ticker = "DC" if "DC" in tickers else tickers[0]
    focus_metrics = all_metrics.get(focus_ticker, {})
    focus_risk = all_risks.get(focus_ticker, {})
    focus_return = all_returns.get(focus_ticker, {})
    focus_nav = nav_lookup.get(focus_ticker)

    focus_runway = focus_metrics.get("runway_months", 0)
    focus_market_cap_m = focus_metrics.get("market_cap_millions", 0)
    focus_market_cap_b = focus_market_cap_m / 1000 if focus_market_cap_m else 0
    focus_npv_b = focus_return.get("expected_npv_billions", 0)
    npv_multiple = (focus_npv_b / focus_market_cap_b) if focus_market_cap_b > 0 else 0
    focus_p_nav = focus_nav.get(nav_primary_col) if focus_nav is not None else None
    focus_nav_percentile = focus_nav.get("P/NAV Percentile (Lower Better)") if focus_nav is not None else None
    peer_median_p_nav = nav_peer_stats.get("median_p_nav")

    st.markdown("## Executive Summary")
    st.markdown("Decision-first view for investor review and management conversations.")

    st.markdown(
        f"""
        <div class="source-strip">
            <span><strong>Primary focus:</strong> {focus_ticker}</span>
            <span>Market data as of: {_fmt_time(gold_data.get('fetch_time'))}</span>
            <span>Risk model as of: {_fmt_time(focus_risk.get('analysis_time'))}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        st.metric("Gold Price", f"${gold_price:,.0f}/oz", f"{gold_change:+.1f}%")
    with k2:
        st.metric(f"{focus_ticker} Price", f"${focus_metrics.get('price', 0):.2f}")
    with k3:
        st.metric(f"{focus_ticker} Mkt Cap", f"${focus_market_cap_m:.0f}M")
    with k4:
        st.metric(f"{focus_ticker} Exp NPV", f"${focus_npv_b:.2f}B")
    with k5:
        if isinstance(focus_p_nav, (int, float)):
            pnav_delta = (
                f"{focus_p_nav - peer_median_p_nav:+.2f}x vs peer med"
                if isinstance(peer_median_p_nav, (int, float))
                else "Peer median unavailable"
            )
            st.metric("P/NAV (Risked 8%)", f"{focus_p_nav:.2f}x", pnav_delta)
        else:
            st.metric("NPV / Mkt Cap", f"{npv_multiple:.1f}x", f"{focus_return.get('implied_upside_pct', 0):+.0f}% implied")
    with k6:
        st.metric(f"{focus_ticker} Runway", f"{focus_runway:.0f} mo" if focus_runway else "N/A", f"Need by {_funding_window(focus_runway)}")

    if isinstance(focus_p_nav, (int, float)):
        nav_caption = f"{focus_ticker} P/NAV {focus_p_nav:.2f}x"
        if isinstance(focus_nav_percentile, (int, float)):
            nav_caption += f" | Valuation percentile {focus_nav_percentile:.0f}% (lower is cheaper)"
        if isinstance(peer_median_p_nav, (int, float)):
            nav_caption += f" | Peer median {peer_median_p_nav:.2f}x"
        st.caption(nav_caption)

    st.markdown("---")
    st.markdown("### Production Snapshot (Gold & Silver)")
    st.caption("Annual production assumptions and published resource context for meeting prep.")

    production_rows = []
    for ticker in tickers:
        metrics = all_metrics.get(ticker, {})
        production_rows.append({
            "Ticker": ticker,
            "Stage": metrics.get("stage", "unknown").title(),
            "Annual Gold (oz/yr)": _fmt_oz(metrics.get("annual_gold_production_oz")),
            "Annual Silver (oz/yr)": _fmt_oz(metrics.get("annual_silver_production_oz")),
            "LOM Gold (oz)": _fmt_oz(metrics.get("life_of_mine_gold_oz")),
            "M&I Gold": _fmt_moz(metrics.get("mi_and_i_gold_moz")),
            "M&I Silver": _fmt_moz(metrics.get("mi_and_i_silver_moz")),
            "Basis": metrics.get("production_basis", "Model assumption"),
            "Source": metrics.get("production_source", "Internal model configuration"),
            "Source Date": metrics.get("production_source_date", "N/A"),
        })

    st.dataframe(pd.DataFrame(production_rows), use_container_width=True, hide_index=True)
    st.caption("Resource figures are not equivalent to annual production guidance.")

    st.markdown("---")
    st.markdown("### Coverage Universe")

    universe_cols = st.columns(len(tickers))
    for col, ticker in zip(universe_cols, tickers):
        metrics = all_metrics.get(ticker, {})
        risk = all_risks.get(ticker, {})
        return_data = all_returns.get(ticker, {})
        score = risk.get("composite_score", 0)
        risk_level = risk.get("interpretation", {}).get("level", "Unknown")
        risk_class = _risk_tier_class(score)

        with col:
            st.markdown(
                f"""
                <div class="coverage-card">
                    <div class="coverage-header">
                        <span class="coverage-ticker">{ticker}</span>
                        <span class="coverage-risk {risk_class}">{risk_level}</span>
                    </div>
                    <div class="coverage-name">{metrics.get('company_name', ticker)}</div>
                    <div class="coverage-line">Price: ${metrics.get('price', 0):.2f} | Mkt Cap: ${metrics.get('market_cap_millions', 0):.0f}M</div>
                    <div class="coverage-line">Runway: {metrics.get('runway_months', 0):.0f} mo | Gap: ${metrics.get('funding_gap', 0):.0f}M</div>
                    <div class="coverage-line">Production: {_fmt_oz(metrics.get('annual_gold_production_oz'))} oz Au | {_fmt_oz(metrics.get('annual_silver_production_oz'))} oz Ag</div>
                    <div class="coverage-line">Exp NPV: ${return_data.get('expected_npv_billions', 0):.2f}B</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("---")
    st.markdown("### Value vs Price")

    valuation_rows = []
    for ticker in tickers:
        metrics = all_metrics.get(ticker, {})
        risk = all_risks.get(ticker, {})
        returns = all_returns.get(ticker, {})
        mcap_b = metrics.get("market_cap_millions", 0) / 1000 if metrics.get("market_cap_millions", 0) else 0
        exp_npv_b = returns.get("expected_npv_billions", 0)

        valuation_rows.append({
            "Ticker": ticker,
            "Price": f"${metrics.get('price', 0):.2f}",
            "Mkt Cap": f"${metrics.get('market_cap_millions', 0):.0f}M",
            "Expected NPV": f"${exp_npv_b:.2f}B",
            "NPV/MktCap": f"{(exp_npv_b / mcap_b):.1f}x" if mcap_b > 0 else "N/A",
            "P/NAV (Risked 8%)": (
                f"{nav_lookup.get(ticker, {}).get(nav_primary_col):.2f}x"
                if isinstance(nav_lookup.get(ticker, {}).get(nav_primary_col), (int, float))
                else "N/A"
            ),
            "NAV Upside (8%)": (
                f"{nav_lookup.get(ticker, {}).get('Implied Upside @8%'):+.0f}%"
                if isinstance(nav_lookup.get(ticker, {}).get("Implied Upside @8%"), (int, float))
                else "N/A"
            ),
            "Implied Upside": f"{returns.get('implied_upside_pct', 0):+.0f}%",
            "Adj Return": f"{returns.get('adjusted_return_pct', 0):.1f}%",
            "Risk": f"{risk.get('composite_score', 0):.1f}/5",
            "Runway": f"{metrics.get('runway_months', 0):.0f} mo" if metrics.get("runway_months") else "N/A",
        })

    valuation_df = pd.DataFrame(valuation_rows)
    st.dataframe(valuation_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### Funding & Risk Monitor")

    monitor_rows = []
    for ticker in tickers:
        metrics = all_metrics.get(ticker, {})
        risk = all_risks.get(ticker, {})
        runway = metrics.get("runway_months", 0)

        monitor_rows.append({
            "Ticker": ticker,
            "Runway": f"{runway:.0f} mo" if runway else "N/A",
            "Funding Need By": _funding_window(runway),
            "Funding Gap": f"${metrics.get('funding_gap', 0):.0f}M",
            "Expected Dilution": f"{metrics.get('expected_dilution', 0):.0f}%",
            "Weakest Category": risk.get("weakest_category", "N/A").title(),
            "Composite": f"{risk.get('composite_score', 0):.1f}/5",
            "Primary Concern": _primary_concern(metrics, risk),
            "runway_months_sort": runway if runway and runway > 0 else 999,
        })

    monitor_df = pd.DataFrame(monitor_rows).sort_values("runway_months_sort")
    st.dataframe(
        monitor_df.drop(columns=["runway_months_sort"]),
        use_container_width=True,
        hide_index=True,
    )

    urgent = [r for r in monitor_rows if 0 < r["runway_months_sort"] < 12]
    if urgent:
        urgent_txt = ", ".join([f"{r['Ticker']} ({r['Runway']})" for r in urgent])
        st.warning(f"Near-term financing watchlist: {urgent_txt}")

    st.markdown("---")
    st.markdown(f"### Management Questions ({focus_ticker})")

    focus_questions = []
    if focus_runway and focus_runway < 18:
        focus_questions.append(
            f"What is the financing plan and sequencing to cover an estimated ${focus_metrics.get('funding_gap', 0):.0f}M gap before {_funding_window(focus_runway)}?"
        )
    focus_questions.append(
        f"What milestones de-risk the targeted {focus_metrics.get('start_year', 'N/A')} production start, and what could shift that timeline?"
    )
    focus_questions.append(
        f"How should investors think about dilution risk ({focus_metrics.get('expected_dilution', 0):.0f}% modeled) under base vs stressed scenarios?"
    )
    focus_questions.append(
        f"What are the largest drivers of cost variance versus current AISC assumption (${focus_metrics.get('aisc', 0):,.0f}/oz)?"
    )
    weakest = focus_risk.get("weakest_category", "risk")
    focus_questions.append(
        f"What concrete actions are underway to improve the weakest risk bucket ({weakest.title()}) over the next two quarters?"
    )

    for idx, question in enumerate(focus_questions, start=1):
        st.markdown(f"{idx}. {question}")

    st.markdown("---")
    st.markdown("### Catalyst Timeline")

    timeline_rows = []
    for ticker in tickers:
        metrics = all_metrics.get(ticker, {})
        risk = all_risks.get(ticker, {})
        runway = metrics.get("runway_months", 0)
        timeline_rows.append({
            "Ticker": ticker,
            "Funding Checkpoint": _funding_window(runway),
            "Target Production Start": metrics.get("start_year", "N/A"),
            "Years to Production": max(0, int(metrics.get("start_year", datetime.now().year) - datetime.now().year)),
            "Stage": metrics.get("stage", "Unknown").title(),
            "Key Dependency": risk.get("weakest_category", "N/A").title(),
        })

    timeline_df = pd.DataFrame(timeline_rows).sort_values("Target Production Start")
    st.dataframe(timeline_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### Export Report")
    report_html = generate_report(tickers)
    date_tag = datetime.now().strftime("%Y-%m-%d")
    st.download_button(
        label="Download Portfolio Report (HTML)",
        data=report_html,
        file_name=f"JuniorGoldIntel_Report_{date_tag}.html",
        mime="text/html",
    )
