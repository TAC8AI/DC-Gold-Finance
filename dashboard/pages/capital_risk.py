"""
Capital & Risk Analysis page: Runway, dilution, funding
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import List

from financial_models.cash_analysis import CashAnalyzer
from financial_models.capital_structure import CapitalStructureAnalyzer
from financial_models.dilution_scenarios import DilutionScenarioModeler
from risk_engine.risk_scorer import RiskScorer
from data_ingestion.data_normalizer import DataNormalizer


def render_capital_risk(tickers: List[str], selected_ticker: str = None):
    """Render capital and risk analysis page"""

    st.markdown("## Capital & Risk Analysis")
    st.markdown("Cash runway, dilution scenarios, and funding requirements")

    # Initialize
    cash_analyzer = CashAnalyzer()
    capital_analyzer = CapitalStructureAnalyzer()
    dilution_modeler = DilutionScenarioModeler()
    risk_scorer = RiskScorer()
    normalizer = DataNormalizer()

    # Company selector
    selected = st.selectbox(
        "Select Company",
        tickers,
        index=tickers.index(selected_ticker) if selected_ticker in tickers else 0
    )

    # Get all data
    company_data = normalizer.get_normalized_company_data(selected)
    cash_data = cash_analyzer.analyze_cash_position(selected)
    capital_data = capital_analyzer.analyze_structure(selected)
    dilution_data = dilution_modeler.model_scenarios(selected)
    risk_data = risk_scorer.calculate_composite_score(selected)

    st.markdown(f"### {company_data.get('name', selected)}")

    st.markdown("---")

    # Cash Runway Section
    st.markdown("### Cash Position & Runway")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Cash on Hand",
            f"${cash_data.get('current_cash_millions', 0):.1f}M"
        )

    with col2:
        st.metric(
            "Quarterly Burn",
            f"${cash_data.get('quarterly_burn_millions', 0):.1f}M"
        )

    with col3:
        runway = cash_data.get('runway_months', 0)
        delta_color = "normal" if runway >= 18 else "inverse" if runway < 12 else "off"
        st.metric(
            "Runway",
            f"{runway:.0f} months" if runway else "N/A",
            delta_color=delta_color
        )

    with col4:
        risk_level = cash_data.get('runway_risk', {}).get('level', 'unknown')
        st.metric("Funding Risk", risk_level.title())

    # Runway gauge
    col1, col2 = st.columns([1, 1])

    with col1:
        runway_months = cash_data.get('runway_months', 0)
        max_runway = 36

        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=runway_months,
            number={'suffix': " months"},
            delta={'reference': 18, 'position': "bottom"},
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Cash Runway"},
            gauge={
                'axis': {'range': [0, max_runway], 'tickwidth': 1},
                'bar': {'color': "#3b82f6"},
                'bgcolor': "white",
                'borderwidth': 2,
                'steps': [
                    {'range': [0, 6], 'color': '#fecaca'},
                    {'range': [6, 12], 'color': '#fed7aa'},
                    {'range': [12, 18], 'color': '#fef08a'},
                    {'range': [18, max_runway], 'color': '#bbf7d0'}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 12
                }
            }
        ))
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Cash vs Capex comparison
        project = company_data.get('project', {})
        capex = project.get('initial_capex_millions', 0)
        cash = cash_data.get('current_cash_millions', 0)
        funding_gap = max(0, capex - cash)

        fig = go.Figure(data=[
            go.Bar(name='Cash on Hand', x=['Funding'], y=[cash], marker_color='#22c55e'),
            go.Bar(name='Required Capex', x=['Funding'], y=[capex], marker_color='#94a3b8'),
        ])
        fig.update_layout(
            barmode='group',
            title="Cash vs Required Capex",
            height=300,
            yaxis_title="$ Millions"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.metric("Funding Gap", f"${funding_gap:.0f}M")

    st.markdown("---")

    # Dilution Scenarios
    st.markdown("### Dilution Scenarios")

    if 'error' not in dilution_data:
        scenarios = dilution_data.get('scenarios', {})

        # Create scenario comparison table
        scenario_rows = []
        for name, scenario in scenarios.items():
            scenario_rows.append({
                'Scenario': scenario.get('name', name),
                'Dilution': f"{scenario.get('dilution_percentage', 0)}%",
                'Probability': f"{scenario.get('probability', 0) * 100:.0f}%",
                'New Shares (M)': f"{scenario.get('new_shares_millions', 0):.1f}",
                'Post Shares (M)': f"{scenario.get('post_shares_millions', 0):.1f}",
                'Ownership After': f"{scenario.get('ownership_post', 0):.1f}%"
            })

        scenario_df = pd.DataFrame(scenario_rows)
        st.dataframe(scenario_df, use_container_width=True, hide_index=True)

        # Expected dilution
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Expected Dilution",
                f"{dilution_data.get('expected_dilution_percentage', 0):.0f}%"
            )

        with col2:
            current_shares = dilution_data.get('current_shares_millions', 0)
            expected_shares = dilution_data.get('expected_post_shares_millions', 0)
            st.metric(
                "Current Shares",
                f"{current_shares:.1f}M",
                f"+{expected_shares - current_shares:.1f}M expected"
            )

        with col3:
            st.metric(
                "Expected Ownership",
                f"{dilution_data.get('expected_ownership_post', 0):.1f}%",
                f"-{100 - dilution_data.get('expected_ownership_post', 100):.1f}%"
            )

        # Dilution waterfall chart
        fig = go.Figure(go.Waterfall(
            name="Shares",
            orientation="v",
            x=["Current"] + [s.get('name', '') for s in scenarios.values()],
            y=[dilution_data.get('current_shares_millions', 0)] +
              [s.get('new_shares_millions', 0) * s.get('probability', 0) for s in scenarios.values()],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            text=[f"{dilution_data.get('current_shares_millions', 0):.1f}M"] +
                 [f"+{s.get('new_shares_millions', 0):.1f}M" for s in scenarios.values()],
            textposition="outside"
        ))
        fig.update_layout(
            title="Share Count Waterfall (Probability Weighted)",
            height=350,
            yaxis_title="Shares (Millions)"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Capital Structure
    st.markdown("### Capital Structure")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Shares Outstanding",
            f"{capital_data.get('shares_outstanding_millions', 0):.1f}M"
        )

    with col2:
        st.metric(
            "Float",
            f"{capital_data.get('float_percentage', 0):.1f}%"
        )

    with col3:
        st.metric(
            "Total Debt",
            f"${capital_data.get('total_debt_millions', 0):.1f}M"
        )

    with col4:
        st.metric(
            "Enterprise Value",
            f"${capital_data.get('ev_millions', 0):.0f}M"
        )

    st.markdown("---")

    # Risk Score Breakdown
    st.markdown("### Risk Score Breakdown")

    if 'error' not in risk_data:
        categories = risk_data.get('categories', {})

        col1, col2 = st.columns([1, 2])

        with col1:
            # Overall score gauge
            composite = risk_data.get('composite_score', 0)

            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=composite,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Composite Risk Score"},
                gauge={
                    'axis': {'range': [1, 5]},
                    'bar': {'color': "#3b82f6"},
                    'steps': [
                        {'range': [1, 2], 'color': '#fecaca'},
                        {'range': [2, 3], 'color': '#fed7aa'},
                        {'range': [3, 4], 'color': '#fef08a'},
                        {'range': [4, 5], 'color': '#bbf7d0'}
                    ]
                }
            ))
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig, use_container_width=True)

            interpretation = risk_data.get('interpretation', {})
            st.markdown(f"**{interpretation.get('level', 'Unknown')}**")
            st.caption(interpretation.get('description', ''))

        with col2:
            # Category breakdown
            cat_data = []
            for name, cat in categories.items():
                cat_data.append({
                    'Category': name.title(),
                    'Score': cat.get('score', 0),
                    'Weight': f"{cat.get('weight', 0) * 100:.0f}%",
                    'Level': cat.get('level', 'unknown').title(),
                    'Description': cat.get('description', '')
                })

            cat_df = pd.DataFrame(cat_data)

            # Horizontal bar chart
            fig = px.bar(
                cat_df,
                y='Category',
                x='Score',
                color='Score',
                color_continuous_scale='RdYlGn',
                orientation='h',
                text='Score',
                title="Risk Scores by Category (1=Highest Risk, 5=Lowest)"
            )
            fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            fig.update_layout(height=300, xaxis_range=[0, 5.5])
            st.plotly_chart(fig, use_container_width=True)

        # Detailed breakdown table
        st.dataframe(cat_df, use_container_width=True, hide_index=True)

        # Weakest category callout
        weakest = risk_data.get('weakest_category', '')
        weakest_score = risk_data.get('weakest_score', 0)

        if weakest_score <= 2:
            st.warning(f"**Attention:** {weakest.title()} risk is elevated (score: {weakest_score}/5)")
        elif weakest_score <= 3:
            st.info(f"**Monitor:** {weakest.title()} is the weakest category (score: {weakest_score}/5)")

    st.markdown("---")

    # All Companies Comparison
    st.markdown("### Cross-Company Risk Comparison")

    comparison_data = []
    for ticker in tickers:
        risk = risk_scorer.calculate_composite_score(ticker)
        if 'error' not in risk:
            comparison_data.append({
                'Ticker': ticker,
                'Composite': risk.get('composite_score', 0),
                'Funding': risk.get('funding_score', 0),
                'Execution': risk.get('execution_score', 0),
                'Commodity': risk.get('commodity_score', 0),
                'Control': risk.get('control_score', 0),
                'Timing': risk.get('timing_score', 0),
                'Weakest': risk.get('weakest_category', '').title()
            })

    if comparison_data:
        comp_df = pd.DataFrame(comparison_data)
        st.dataframe(
            comp_df.style.background_gradient(subset=['Composite'], cmap='RdYlGn'),
            use_container_width=True,
            hide_index=True
        )
