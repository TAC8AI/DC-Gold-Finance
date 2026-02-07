"""
Executive Summary page: What changed? What matters? What worries us?
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Any, List

from financial_models.metrics_calculator import MetricsCalculator
from risk_engine.risk_scorer import RiskScorer
from data_ingestion.gold_price_fetcher import GoldPriceFetcher
from benchmarks.adjusted_return import AdjustedReturnCalculator


def render_executive_summary(tickers: List[str]):
    """Render the executive summary page"""

    st.markdown("## Executive Summary")
    st.markdown("Quick overview of portfolio health and key developments")

    # Initialize calculators
    metrics_calc = MetricsCalculator()
    risk_scorer = RiskScorer()
    gold_fetcher = GoldPriceFetcher()
    return_calc = AdjustedReturnCalculator()

    # Get gold price
    gold_data = gold_fetcher.get_current_price()
    gold_price = gold_data.get('price', 2100)
    gold_change = gold_data.get('daily_change_pct', 0)

    # Header metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Gold Price",
            f"${gold_price:,.0f}/oz",
            f"{gold_change:+.1f}%"
        )

    # Get summary for all companies
    all_metrics = {}
    all_risks = {}

    for ticker in tickers:
        all_metrics[ticker] = metrics_calc.get_summary_metrics(ticker)
        all_risks[ticker] = risk_scorer.calculate_composite_score(ticker)

    # Calculate portfolio totals
    total_market_cap = sum(m.get('market_cap_millions', 0) for m in all_metrics.values())
    avg_risk = sum(r.get('composite_score', 3) for r in all_risks.values() if 'error' not in r) / len(tickers)

    with col2:
        st.metric("Portfolio Mkt Cap", f"${total_market_cap:.0f}M")

    with col3:
        st.metric("Avg Risk Score", f"{avg_risk:.1f}/5.0")

    with col4:
        st.metric("Companies Tracked", str(len(tickers)))

    st.markdown("---")

    # Three-column layout for key insights
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### What Changed?")
        st.markdown("*Material developments in the last 24-48 hours*")

        for ticker in tickers:
            metrics = all_metrics[ticker]
            price = metrics.get('price', 0)

            # Check for significant price moves
            # In a real system, would compare to historical data
            st.markdown(f"""
            **{ticker}** - ${price:.2f}
            - Gold at ${gold_price:,.0f} ({gold_change:+.1f}% today)
            - Cash runway: {metrics.get('runway_months', 0):.0f} months
            """)

    with col2:
        st.markdown("### What Matters?")
        st.markdown("*Key metrics driving investment thesis*")

        for ticker in tickers:
            metrics = all_metrics[ticker]
            risk = all_risks[ticker]

            margin = metrics.get('margin', 0)
            runway = metrics.get('runway_months', 0)
            stage = metrics.get('stage', 'unknown')

            st.markdown(f"""
            **{ticker}** ({stage.title()})
            - Margin: ${margin:.0f}/oz at current gold
            - Runway: {runway:.0f} months
            - Risk Score: {risk.get('composite_score', 0):.1f}/5.0
            """)

    with col3:
        st.markdown("### What Worries Us?")
        st.markdown("*Risk factors requiring attention*")

        for ticker in tickers:
            risk = all_risks[ticker]
            metrics = all_metrics[ticker]

            if 'error' in risk:
                st.warning(f"{ticker}: Unable to assess risk")
                continue

            weakest = risk.get('weakest_category', 'unknown')
            weakest_score = risk.get('weakest_score', 0)

            concerns = []

            # Check funding
            if metrics.get('runway_months', 0) < 12:
                concerns.append(f"Short runway ({metrics.get('runway_months', 0):.0f} mo)")

            # Check dilution
            if metrics.get('expected_dilution', 0) > 40:
                concerns.append(f"High dilution ({metrics.get('expected_dilution', 0):.0f}%)")

            # Check AISC
            if metrics.get('aisc', 0) > 1400:
                concerns.append(f"High costs (${metrics.get('aisc', 0):,.0f} AISC)")

            # Check timing
            if metrics.get('start_year', 2030) > 2028:
                concerns.append(f"Long timeline ({metrics.get('start_year', 2030)})")

            if concerns:
                st.markdown(f"**{ticker}** - *{weakest.title()}* is weakest ({weakest_score}/5)")
                for c in concerns:
                    st.markdown(f"  - {c}")
            else:
                st.markdown(f"**{ticker}** - No major concerns")

    st.markdown("---")

    # Company ranking table
    st.markdown("### Company Ranking")

    ranking_data = []
    for ticker in tickers:
        metrics = all_metrics[ticker]
        risk = all_risks[ticker]

        # Get adjusted return
        adj_return = return_calc.calculate_adjusted_return(ticker)
        adj_ret_pct = adj_return.get('adjusted_return_pct', 0) if 'error' not in adj_return else 0

        ranking_data.append({
            'Ticker': ticker,
            'Price': f"${metrics.get('price', 0):.2f}",
            'Mkt Cap': f"${metrics.get('market_cap_millions', 0):.0f}M",
            'Risk Score': f"{risk.get('composite_score', 0):.1f}",
            'Adjusted Return': f"{adj_ret_pct:.1f}%",
            'Runway': f"{metrics.get('runway_months', 0):.0f} mo" if metrics.get('runway_months') else 'N/A',
            'Stage': metrics.get('stage', 'unknown').title()
        })

    st.dataframe(ranking_data, use_container_width=True, hide_index=True)

    # Key takeaways
    st.markdown("---")
    st.markdown("### Key Takeaways")

    # Find best and worst
    best_risk = min(all_risks.items(), key=lambda x: x[1].get('composite_score', 0) if 'error' not in x[1] else 10)
    worst_risk = max(all_risks.items(), key=lambda x: x[1].get('composite_score', 0) if 'error' not in x[1] else 0)

    col1, col2 = st.columns(2)

    with col1:
        st.success(f"""
        **Lowest Risk:** {best_risk[0]}
        - Score: {best_risk[1].get('composite_score', 0):.1f}/5.0
        - Best positioned for current market conditions
        """)

    with col2:
        if worst_risk[1].get('composite_score', 5) < 3:
            st.warning(f"""
            **Highest Risk:** {worst_risk[0]}
            - Score: {worst_risk[1].get('composite_score', 0):.1f}/5.0
            - Requires close monitoring
            """)
        else:
            st.info(f"""
            **All Companies:** Moderate to Low Risk
            - Portfolio is well-positioned
            """)
