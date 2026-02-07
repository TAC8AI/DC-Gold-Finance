"""
NPV & Sensitivity Analysis page
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any

from scenario_engine.npv_calculator import NPVCalculator
from scenario_engine.sensitivity_matrix import SensitivityMatrix
from scenario_engine.probability_weighting import ProbabilityWeightedAnalysis
from data_ingestion.data_normalizer import DataNormalizer
from data_ingestion.gold_price_fetcher import GoldPriceFetcher


def render_npv_sensitivity(tickers: List[str], selected_ticker: str = None):
    """Render NPV and sensitivity analysis page"""

    st.markdown("## NPV & Sensitivity Analysis")
    st.markdown("DCF valuation and scenario modeling")

    # Initialize
    calculator = NPVCalculator()
    sensitivity = SensitivityMatrix()
    probability = ProbabilityWeightedAnalysis()
    normalizer = DataNormalizer()
    gold_fetcher = GoldPriceFetcher()

    gold_data = gold_fetcher.get_current_price()
    current_gold = gold_data.get('price', 2100)

    # Company selector
    selected = st.selectbox(
        "Select Company",
        tickers,
        index=tickers.index(selected_ticker) if selected_ticker in tickers else 0
    )

    # Get company data
    company_data = normalizer.get_normalized_company_data(selected)
    project = company_data.get('project', {})
    market = company_data.get('market', {})

    st.markdown(f"### {company_data.get('name', selected)} - {project.get('name', 'Project')}")

    # Sidebar inputs
    with st.sidebar:
        st.markdown("### Valuation Assumptions")

        gold_price = st.slider(
            "Gold Price ($/oz)",
            min_value=1500,
            max_value=3500,
            value=int(current_gold),
            step=50
        )

        discount_rate = st.slider(
            "Discount Rate (%)",
            min_value=3,
            max_value=15,
            value=8
        ) / 100

        st.markdown("---")
        st.markdown("### Project Parameters")

        production = st.number_input(
            "Annual Production (oz)",
            value=project.get('annual_production_oz', 150000),
            step=10000
        )

        aisc = st.number_input(
            "AISC ($/oz)",
            value=project.get('aisc_per_oz', 1100),
            step=50
        )

        capex = st.number_input(
            "Capex ($M)",
            value=project.get('initial_capex_millions', 400),
            step=25
        )

        start_year = st.selectbox(
            "Production Start",
            [2025, 2026, 2027, 2028, 2029, 2030, 2031],
            index=max(0, project.get('production_start_year', 2029) - 2025)
        )

        mine_life = st.slider(
            "Mine Life (Years)",
            min_value=5,
            max_value=30,
            value=project.get('mine_life_years', 17)
        )

    # Calculate NPV
    metrics = calculator.calculate_project_metrics(
        gold_price=gold_price,
        annual_production_oz=production,
        aisc_per_oz=aisc,
        discount_rate=discount_rate,
        initial_capex=capex * 1_000_000,
        start_year=start_year,
        mine_life_years=mine_life
    )

    # Expected NPV with probability weighting
    expected = probability.calculate_expected_npv(
        annual_production_oz=production,
        aisc_per_oz=aisc,
        discount_rate=discount_rate,
        initial_capex=capex * 1_000_000,
        start_year=start_year,
        mine_life_years=mine_life
    )

    # Main NPV display
    npv = metrics['npv']
    npv_billions = npv / 1_000_000_000
    market_cap = market.get('market_cap', 0)
    shares = market.get('shares_outstanding', 0)

    implied_price = npv / shares if shares > 0 else 0
    upside_pct = ((npv - market_cap) / market_cap * 100) if market_cap > 0 else 0

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #ffffff 0%, #f0f4f8 100%); padding: 40px; border-radius: 20px; border: 4px solid #3b82f6; box-shadow: 0 20px 60px rgba(59, 130, 246, 0.2); text-align: center; margin: 20px 0;">
        <h3 style="color: #475569; margin: 0 0 10px 0; font-size: 1rem; text-transform: uppercase; letter-spacing: 2px;">
            Project NPV at ${gold_price:,}/oz Gold, {discount_rate*100:.0f}% Discount
        </h3>
        <h1 style="color: #1e40af; margin: 0; font-size: 4rem; font-weight: 800;">
            ${npv_billions:.2f}B
        </h1>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-top: 20px; padding-top: 20px; border-top: 2px solid #e2e8f0;">
            <div>
                <p style="color: #64748b; margin: 0; font-size: 0.8rem; text-transform: uppercase;">Implied Share Price</p>
                <p style="color: #0f172a; margin: 0; font-size: 1.8rem; font-weight: 700;">${implied_price:.2f}</p>
            </div>
            <div>
                <p style="color: #64748b; margin: 0; font-size: 0.8rem; text-transform: uppercase;">Current Price</p>
                <p style="color: #0f172a; margin: 0; font-size: 1.8rem; font-weight: 700;">${market.get('current_price', 0):.2f}</p>
            </div>
            <div>
                <p style="color: #64748b; margin: 0; font-size: 0.8rem; text-transform: uppercase;">NPV vs Market</p>
                <p style="color: {'#22c55e' if upside_pct > 0 else '#dc2626'}; margin: 0; font-size: 1.8rem; font-weight: 700;">{upside_pct:+.0f}%</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Tabs for different analyses
    tab1, tab2, tab3, tab4 = st.tabs(["Sensitivity Matrix", "Scenario Analysis", "Cash Flows", "Breakeven"])

    with tab1:
        st.markdown("### NPV Sensitivity: Gold Price vs Discount Rate")

        # Generate sensitivity matrix
        gold_prices = [1600, 1800, 2000, 2200, 2400, 2600, 2800, 3000]
        discount_rates = [0.05, 0.08, 0.10, 0.12]

        matrix_df, matrix_meta = sensitivity.generate_gold_discount_matrix(
            annual_production_oz=production,
            aisc_per_oz=aisc,
            initial_capex=capex * 1_000_000,
            start_year=start_year,
            mine_life_years=mine_life,
            gold_prices=gold_prices,
            discount_rates=discount_rates
        )

        # Heatmap
        fig = px.imshow(
            matrix_df.values,
            labels=dict(x="Gold Price", y="Discount Rate", color="NPV ($M)"),
            x=[f"${g:,}" for g in gold_prices],
            y=[f"{r*100:.0f}%" for r in discount_rates],
            color_continuous_scale="RdYlGn",
            aspect="auto"
        )

        # Add annotations
        for i, rate in enumerate(discount_rates):
            for j, gold in enumerate(gold_prices):
                value = matrix_df.iloc[i, j]
                fig.add_annotation(
                    x=j, y=i,
                    text=f"${value:,.0f}M",
                    showarrow=False,
                    font=dict(size=10, color="white" if abs(value) > 500 else "black")
                )

        fig.update_layout(height=400, title="NPV Sensitivity Matrix ($M)")
        st.plotly_chart(fig, use_container_width=True)

        # Table view
        st.dataframe(
            matrix_df.style.background_gradient(cmap='RdYlGn', axis=None).format("${:,.0f}M"),
            use_container_width=True
        )

        st.caption(f"Breakeven gold prices by discount rate: " +
                  ", ".join([f"{k}: ${v:,.0f}" for k, v in matrix_meta['breakeven_by_discount'].items()]))

    with tab2:
        st.markdown("### Probability-Weighted Scenarios")

        col1, col2 = st.columns([2, 1])

        with col1:
            # Scenario comparison chart
            scenarios = expected.get('scenarios', {})

            scenario_df = pd.DataFrame([
                {
                    'Scenario': s['label'],
                    'Gold Price': s['gold_price'],
                    'Probability': s['probability'] * 100,
                    'NPV ($B)': s['npv_billions']
                }
                for s in scenarios.values()
            ])

            fig = px.bar(
                scenario_df,
                x='Scenario',
                y='NPV ($B)',
                color='NPV ($B)',
                color_continuous_scale='RdYlGn',
                text='NPV ($B)',
                title="NPV by Scenario"
            )
            fig.update_traces(texttemplate='$%{text:.2f}B', textposition='outside')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Expected Values**")
            st.metric("Expected NPV", f"${expected['expected_npv_billions']:.2f}B")
            st.metric("Expected IRR", f"{expected['expected_irr_percentage']:.1f}%")
            st.metric("NPV Std Dev", f"${expected['npv_std_dev_millions']:.0f}M")

            st.markdown("---")
            st.markdown("**Scenario Probabilities**")
            for name, scenario in scenarios.items():
                st.write(f"{scenario['label']}: {scenario['probability']*100:.0f}%")

    with tab3:
        st.markdown("### Projected Cash Flows")

        cf_df = metrics['cash_flow_df']

        fig = px.bar(
            cf_df,
            x='year',
            y='free_cash_flow',
            color='free_cash_flow',
            color_continuous_scale=['#dc2626', '#22c55e'],
            title="Annual Free Cash Flow"
        )
        fig.update_layout(
            height=400,
            xaxis_title="Year",
            yaxis_title="Free Cash Flow ($)"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Cumulative cash flow
        cf_df['cumulative'] = cf_df['free_cash_flow'].cumsum()

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=cf_df['year'],
            y=cf_df['cumulative'],
            mode='lines+markers',
            name='Cumulative CF',
            line=dict(color='#3b82f6', width=3)
        ))
        fig2.add_hline(y=0, line_dash="dash", line_color="gray")
        fig2.update_layout(
            height=350,
            title="Cumulative Cash Flow",
            xaxis_title="Year",
            yaxis_title="Cumulative Cash Flow ($)"
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Key metrics
        st.markdown("### Project Economics")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("IRR", f"{metrics['irr_percentage']:.1f}%")
        with col2:
            st.metric("Payback", f"{metrics['payback_years']:.1f} years")
        with col3:
            st.metric("Annual FCF", f"${metrics['annual_fcf_millions']:.0f}M")
        with col4:
            st.metric("NPV/oz", f"${metrics['npv_per_oz']:.0f}")

    with tab4:
        st.markdown("### Breakeven Analysis")

        breakeven = metrics['breakeven_gold_price']

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Breakeven Gold Price",
                f"${breakeven:,.0f}/oz",
                f"${current_gold - breakeven:,.0f} margin"
            )

            # Visual representation
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=current_gold,
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={
                    'axis': {'range': [1200, 3000]},
                    'bar': {'color': "#22c55e"},
                    'steps': [
                        {'range': [1200, breakeven], 'color': "#fecaca"},
                        {'range': [breakeven, 3000], 'color': "#bbf7d0"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': breakeven
                    }
                },
                title={'text': "Current Gold vs Breakeven"}
            ))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Margin Analysis**")

            margin = gold_price - aisc
            st.metric("Operating Margin", f"${margin:,.0f}/oz")

            margin_pct = (margin / gold_price) * 100
            st.metric("Margin %", f"{margin_pct:.1f}%")

            # Sensitivity to gold price changes
            st.markdown("---")
            st.markdown("**NPV Sensitivity to Gold**")

            for delta in [-200, -100, 0, 100, 200]:
                test_gold = gold_price + delta
                test_npv, _ = calculator.calculate_project_npv(
                    gold_price=test_gold,
                    annual_production_oz=production,
                    aisc_per_oz=aisc,
                    discount_rate=discount_rate,
                    initial_capex=capex * 1_000_000,
                    start_year=start_year,
                    mine_life_years=mine_life
                )
                npv_change = ((test_npv - npv) / npv * 100) if npv != 0 else 0
                color = "green" if delta >= 0 else "red"
                st.write(f"${test_gold:,}: ${test_npv/1e9:.2f}B ({npv_change:+.0f}%)")
