"""
Company Comparison page: Side-by-side analysis
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import List

from financial_models.metrics_calculator import MetricsCalculator
from risk_engine.risk_scorer import RiskScorer
from data_ingestion.gold_price_fetcher import GoldPriceFetcher
from data_ingestion.data_normalizer import DataNormalizer


def render_company_comparison(tickers: List[str]):
    """Render the company comparison page"""

    st.markdown("## Company Comparison")
    st.markdown("Side-by-side analysis of key metrics across all tracked companies")

    # Initialize
    metrics_calc = MetricsCalculator()
    risk_scorer = RiskScorer()
    gold_fetcher = GoldPriceFetcher()
    normalizer = DataNormalizer()

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
        margins = df['Margin ($/oz)'].tolist()
        colors = ['#22c55e' if m > 1000 else '#f97316' if m > 500 else '#dc2626' for m in margins]

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
