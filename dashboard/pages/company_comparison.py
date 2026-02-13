"""
Company Comparison page: Side-by-side analysis
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import List

from financial_models.metrics_calculator import MetricsCalculator
from financial_models.nav_model import CorporateNAVModel
from risk_engine.risk_scorer import RiskScorer
from data_ingestion.gold_price_fetcher import GoldPriceFetcher


def render_company_comparison(tickers: List[str]):
    """Render the company comparison page"""

    st.markdown("## Company Comparison")
    st.markdown("Side-by-side analysis of key metrics across all tracked companies")

    # Initialize
    metrics_calc = MetricsCalculator()
    nav_model = CorporateNAVModel()
    risk_scorer = RiskScorer()
    gold_fetcher = GoldPriceFetcher()

    gold_price = gold_fetcher.get_current_price().get('price', 2100)

    # Get data for all companies
    all_data = {}
    for ticker in tickers:
        all_data[ticker] = metrics_calc.get_all_metrics(ticker)

    st.markdown("---")

    # Key Metrics Comparison Table
    st.markdown("### Key Metrics")

    comparison_data = []
    for ticker in tickers:
        data = all_data[ticker]
        market = data.get('market', {})
        cash = data.get('cash', {})
        project = data.get('project', {})
        dilution = data.get('dilution', {})

        comparison_data.append({
            'Ticker': ticker,
            'Company': data.get('company_name', ticker),
            'Price': market.get('current_price', 0),
            'Market Cap ($M)': market.get('market_cap_millions', 0),
            'Cash ($M)': cash.get('total_cash_millions', 0),
            'Runway (Mo)': cash.get('runway_months', 0),
            'AISC ($/oz)': project.get('aisc', 0),
            'Margin ($/oz)': project.get('margin_per_oz', 0),
            'Production (oz/yr)': project.get('production_oz', 0),
            'Start Year': project.get('start_year', 0),
            'Expected Dilution (%)': dilution.get('expected_dilution_pct', 0)
        })

    df = pd.DataFrame(comparison_data)

    # Format and display
    st.dataframe(
        df.style.format({
            'Price': '${:.2f}',
            'Market Cap ($M)': '${:,.0f}',
            'Cash ($M)': '${:,.1f}',
            'Runway (Mo)': '{:.0f}',
            'AISC ($/oz)': '${:,.0f}',
            'Margin ($/oz)': '${:,.0f}',
            'Production (oz/yr)': '{:,.0f}',
            'Start Year': '{:.0f}',
            'Expected Dilution (%)': '{:.0f}%'
        }).background_gradient(subset=['Margin ($/oz)'], cmap='RdYlGn'),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # NAV Comparison
    st.markdown("### NAV Comparison (Apples-to-Apples)")
    st.caption(
        "Corporate NAV = risk-adjusted project NAV + cash - debt + configured corporate adjustments. "
        "Use this to compare relative valuation across peers."
    )

    nav_controls_col1, nav_controls_col2, nav_controls_col3, nav_controls_col4 = st.columns(4)
    with nav_controls_col1:
        nav_gold_price = st.number_input(
            "NAV Gold Price ($/oz)",
            min_value=1400,
            max_value=5000,
            step=25,
            value=int(round(gold_price)),
            key="nav_gold_price_company_comparison",
        )
    with nav_controls_col2:
        nav_primary_discount = st.slider(
            "Primary Discount Rate (%)",
            min_value=3.0,
            max_value=15.0,
            step=0.25,
            value=8.0,
            key="nav_primary_discount_company_comparison",
        )
    with nav_controls_col3:
        nav_secondary_discount = st.slider(
            "Secondary Discount Rate (%)",
            min_value=3.0,
            max_value=15.0,
            step=0.25,
            value=5.0,
            key="nav_secondary_discount_company_comparison",
        )
    with nav_controls_col4:
        use_stage_risking = st.toggle(
            "Stage-Risk NAV",
            value=True,
            key="nav_stage_risking_company_comparison",
            help="Applies stage probabilities to project NAV for expected-value comparison.",
        )

    nav_analysis = nav_model.compare_companies(
        tickers=tickers,
        gold_price=float(nav_gold_price),
        discount_rate_primary=nav_primary_discount / 100,
        discount_rate_secondary=nav_secondary_discount / 100,
        use_stage_risking=use_stage_risking,
    )
    nav_df = nav_analysis.get("summary_df", pd.DataFrame())
    project_nav_df = nav_analysis.get("project_df", pd.DataFrame())
    primary_rate = nav_analysis.get("assumptions", {}).get("discount_rate_primary", 0.08)
    secondary_rate = nav_analysis.get("assumptions", {}).get("discount_rate_secondary", 0.05)
    primary_pnav_col = nav_analysis.get("peer_stats", {}).get("primary_pnav_col", f"P/NAV @{int(primary_rate * 100)}% (x)")

    if not nav_df.empty:
        peer_stats = nav_analysis.get("peer_stats", {})
        median_p_nav = peer_stats.get("median_p_nav")
        mean_p_nav = peer_stats.get("mean_p_nav")
        positive_count = peer_stats.get("count_positive_nav", 0)

        if median_p_nav is not None:
            st.info(
                f"Peer median {primary_pnav_col}: {median_p_nav:.2f}x "
                f"(mean {mean_p_nav:.2f}x, n={positive_count}). Lower is cheaper versus NAV."
            )

        nav_sort_col = primary_pnav_col if primary_pnav_col in nav_df.columns else "Ticker"
        nav_df = nav_df.sort_values(by=nav_sort_col, ascending=True, na_position="last")

        nav_format_map = {
            "Price": "${:.2f}",
            "Shares (M)": "{:,.1f}",
            "Market Cap ($M)": "${:,.0f}",
            f"Project NAV @{int(primary_rate * 100)}% ($M)": "${:,.0f}",
            f"Corporate NAV @{int(primary_rate * 100)}% ($M)": "${:,.0f}",
            f"NAV/Share @{int(primary_rate * 100)}%": "${:.2f}",
            primary_pnav_col: "{:.2f}x",
            f"EV/NAV @{int(primary_rate * 100)}% (x)": "{:.2f}x",
            f"Corporate NAV @{int(secondary_rate * 100)}% ($M)": "${:,.0f}",
            f"NAV/Share @{int(secondary_rate * 100)}%": "${:.2f}",
            f"P/NAV @{int(secondary_rate * 100)}% (x)": "{:.2f}x",
            f"Implied Upside @{int(primary_rate * 100)}%": "{:+.0f}%",
            "Cash ($M)": "${:,.0f}",
            "Debt ($M)": "${:,.0f}",
            "Corporate Adj ($M)": "${:,.0f}",
            "P/NAV Percentile (Lower Better)": "{:.0f}%",
        }
        nav_format_map = {k: v for k, v in nav_format_map.items() if k in nav_df.columns}
        nav_style = nav_df.style.format(nav_format_map)
        if primary_pnav_col in nav_df.columns:
            nav_style = nav_style.background_gradient(subset=[primary_pnav_col], cmap="RdYlGn_r")
        st.dataframe(nav_style, use_container_width=True, hide_index=True)

        nav_col1, nav_col2 = st.columns(2)

        with nav_col1:
            if primary_pnav_col in nav_df.columns:
                pnav_chart_df = nav_df[["Ticker", primary_pnav_col]].dropna()
                if not pnav_chart_df.empty:
                    fig = px.bar(
                        pnav_chart_df.sort_values(primary_pnav_col),
                        x="Ticker",
                        y=primary_pnav_col,
                        color=primary_pnav_col,
                        color_continuous_scale="RdYlGn_r",
                        title=f"{primary_pnav_col} Ranking",
                    )
                    if median_p_nav is not None:
                        fig.add_hline(
                            y=median_p_nav,
                            line_dash="dash",
                            line_color="orange",
                            annotation_text=f"Peer median {median_p_nav:.2f}x",
                        )
                    fig.update_layout(showlegend=False, height=340)
                    st.plotly_chart(fig, use_container_width=True)

        with nav_col2:
            corp_nav_col = f"Corporate NAV @{int(primary_rate * 100)}% ($M)"
            if corp_nav_col in nav_df.columns:
                scatter_df = nav_df[[corp_nav_col, "Market Cap ($M)", "Ticker"]].dropna()
                if not scatter_df.empty:
                    fig = px.scatter(
                        scatter_df,
                        x=corp_nav_col,
                        y="Market Cap ($M)",
                        text="Ticker",
                        color="Ticker",
                        title=f"Market Cap vs Corporate NAV @{int(primary_rate * 100)}%",
                    )
                    max_axis = max(scatter_df[corp_nav_col].max(), scatter_df["Market Cap ($M)"].max()) * 1.1
                    fig.add_trace(
                        go.Scatter(
                            x=[0, max_axis],
                            y=[0, max_axis],
                            mode="lines",
                            name="Parity (1.0x)",
                            line=dict(color="gray", dash="dash"),
                        )
                    )
                    fig.update_traces(textposition="top center")
                    fig.update_layout(height=340)
                    st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### NAV Bridge Drilldown")
        nav_focus_ticker = st.selectbox(
            "Select ticker for corporate NAV bridge",
            nav_df["Ticker"].tolist(),
            key="nav_bridge_ticker_company_comparison",
        )
        nav_focus = nav_analysis.get("primary_results", {}).get(nav_focus_ticker, {})

        if nav_focus:
            bridge_labels = [
                "Project NAV",
                "Cash",
                "Debt",
                "Corp Adj",
                "Corporate NAV",
            ]
            bridge_values = [
                nav_focus.get("project_nav_selected", 0) / 1_000_000,
                nav_focus.get("cash", 0) / 1_000_000,
                -(nav_focus.get("debt", 0) / 1_000_000),
                nav_focus.get("corporate_adjustment", 0) / 1_000_000,
                nav_focus.get("corporate_nav", 0) / 1_000_000,
            ]
            bridge_measures = ["relative", "relative", "relative", "relative", "total"]

            fig = go.Figure(
                go.Waterfall(
                    measure=bridge_measures,
                    x=bridge_labels,
                    y=bridge_values,
                    connector={"line": {"color": "rgba(63, 63, 63, 0.4)"}},
                    increasing={"marker": {"color": "#22c55e"}},
                    decreasing={"marker": {"color": "#dc2626"}},
                    totals={"marker": {"color": "#2563eb"}},
                )
            )
            fig.update_layout(
                title=f"{nav_focus_ticker} Corporate NAV Bridge @{int(primary_rate * 100)}%",
                yaxis_title="Value ($M)",
                height=320,
            )
            st.plotly_chart(fig, use_container_width=True)

            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
            with metric_col1:
                st.metric("NAV/Share", f"${nav_focus.get('nav_per_share', 0):.2f}")
            with metric_col2:
                pnav_value = nav_focus.get("p_nav")
                st.metric("P/NAV", f"{pnav_value:.2f}x" if pnav_value is not None else "N/A")
            with metric_col3:
                ev_nav_value = nav_focus.get("ev_nav")
                st.metric("EV/NAV", f"{ev_nav_value:.2f}x" if ev_nav_value is not None else "N/A")
            with metric_col4:
                st.metric(
                    "Implied Upside",
                    f"{nav_focus.get('implied_upside_pct', 0):+.0f}%",
                )

        if not project_nav_df.empty:
            st.markdown("#### Project-Level NAV Stack")
            risked_col = f"Risked NAV @{int(primary_rate * 100)}% ($M)"
            project_format_map = {
                "Ownership (%)": "{:.0f}%",
                "Annual Gold (oz/yr)": "{:,.0f}",
                "AISC ($/oz)": "${:,.0f}",
                "Capex Used ($M)": "${:,.0f}",
                "Stage Probability": "{:.0%}",
                f"Unrisked NAV @{int(primary_rate * 100)}% ($M)": "${:,.0f}",
                risked_col: "${:,.0f}",
            }
            project_format_map = {k: v for k, v in project_format_map.items() if k in project_nav_df.columns}
            project_style = project_nav_df.style.format(project_format_map)
            if risked_col in project_nav_df.columns:
                project_style = project_style.background_gradient(subset=[risked_col], cmap="RdYlGn")
            st.dataframe(project_style, use_container_width=True, hide_index=True)
    else:
        st.warning("NAV comparison unavailable due to missing market or project inputs.")

    st.markdown("---")

    # Visual Comparisons
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Market Cap Comparison")
        fig = px.bar(
            df,
            x='Ticker',
            y='Market Cap ($M)',
            color='Ticker',
            title="Market Capitalization ($M)"
        )
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### AISC Comparison")
        fig = px.bar(
            df,
            x='Ticker',
            y='AISC ($/oz)',
            color='AISC ($/oz)',
            color_continuous_scale='RdYlGn_r',
            title="All-In Sustaining Cost ($/oz)"
        )
        fig.add_hline(y=gold_price, line_dash="dash", line_color="gold",
                     annotation_text=f"Gold: ${gold_price:,.0f}")
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Cash Runway")
        fig = go.Figure()

        for i, row in df.iterrows():
            color = '#22c55e' if row['Runway (Mo)'] >= 18 else '#f97316' if row['Runway (Mo)'] >= 12 else '#dc2626'
            fig.add_trace(go.Bar(
                name=row['Ticker'],
                x=[row['Ticker']],
                y=[row['Runway (Mo)']],
                marker_color=color
            ))

        fig.add_hline(y=12, line_dash="dash", line_color="orange", annotation_text="12 month warning")
        fig.add_hline(y=18, line_dash="dash", line_color="green", annotation_text="18 month target")
        fig.update_layout(title="Cash Runway (Months)", showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Margin at Current Gold")
        fig = px.bar(
            df,
            x='Ticker',
            y='Margin ($/oz)',
            color='Margin ($/oz)',
            color_continuous_scale='RdYlGn',
            title=f"Operating Margin at ${gold_price:,.0f}/oz Gold"
        )
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Risk Score Comparison
    st.markdown("### Risk Score Comparison")

    risk_data = []
    for ticker in tickers:
        risk = risk_scorer.calculate_composite_score(ticker)
        if 'error' not in risk:
            risk_data.append({
                'Ticker': ticker,
                'Composite': risk.get('composite_score', 0),
                'Funding': risk.get('funding_score', 0),
                'Execution': risk.get('execution_score', 0),
                'Commodity': risk.get('commodity_score', 0),
                'Control': risk.get('control_score', 0),
                'Timing': risk.get('timing_score', 0)
            })

    if risk_data:
        risk_df = pd.DataFrame(risk_data)

        # Radar chart for risk comparison
        categories = ['Funding', 'Execution', 'Commodity', 'Control', 'Timing']

        fig = go.Figure()

        for _, row in risk_df.iterrows():
            values = [row[cat] for cat in categories]
            values.append(values[0])  # Close the polygon

            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                fill='toself',
                name=row['Ticker'],
                opacity=0.7
            ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 5])
            ),
            showlegend=True,
            title="Risk Profile Comparison (Higher = Lower Risk)",
            height=450
        )
        st.plotly_chart(fig, use_container_width=True)

        # Risk score table
        st.dataframe(
            risk_df.style.background_gradient(subset=['Composite'], cmap='RdYlGn'),
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")

    # Project Timeline Comparison
    st.markdown("### Production Timeline")

    timeline_data = []
    for ticker in tickers:
        data = all_data[ticker]
        project = data.get('project', {})
        timeline_data.append({
            'Ticker': ticker,
            'Project': project.get('name', 'Unknown'),
            'Stage': project.get('stage', 'unknown').title(),
            'Start Year': project.get('start_year', 2030),
            'Mine Life': project.get('mine_life_years', 0),
            'End Year': project.get('start_year', 2030) + project.get('mine_life_years', 0)
        })

    timeline_df = pd.DataFrame(timeline_data)

    # Gantt-style chart
    fig = px.timeline(
        timeline_df,
        x_start=timeline_df['Start Year'].apply(lambda x: f"{x}-01-01"),
        x_end=timeline_df['End Year'].apply(lambda x: f"{x}-01-01"),
        y='Ticker',
        color='Stage',
        title="Project Timelines"
    )
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(timeline_df, use_container_width=True, hide_index=True)
