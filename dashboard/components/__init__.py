"""
Reusable dashboard components
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, Any, List, Optional


def render_metric_card(label: str, value: str, delta: Optional[str] = None, delta_color: str = "normal"):
    """Render a styled metric card"""
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)


def render_company_header(company_data: Dict[str, Any]):
    """Render company header with key info"""
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown(f"### {company_data.get('name', 'Unknown')} ({company_data.get('ticker', '')})")
        st.caption(company_data.get('description', ''))

    with col2:
        price = company_data.get('market', {}).get('current_price', 0)
        change = company_data.get('market', {}).get('daily_change_pct', 0)
        st.metric("Price", f"${price:.2f}", f"{change:+.1f}%")

    with col3:
        mcap = company_data.get('market', {}).get('market_cap_millions', 0)
        st.metric("Market Cap", f"${mcap:.0f}M")


def render_risk_gauge(score: float, label: str = "Risk Score"):
    """Render a gauge chart for risk score (1-5 scale)"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': label, 'font': {'size': 16}},
        gauge={
            'axis': {'range': [1, 5], 'tickwidth': 1},
            'bar': {'color': "#3b82f6"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#e2e8f0",
            'steps': [
                {'range': [1, 2], 'color': '#fecaca'},
                {'range': [2, 3], 'color': '#fed7aa'},
                {'range': [3, 4], 'color': '#fef08a'},
                {'range': [4, 5], 'color': '#bbf7d0'}
            ],
            'threshold': {
                'line': {'color': "#1e40af", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))

    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': "#1e293b"}
    )

    return fig


def render_runway_gauge(months: float, max_months: float = 36):
    """Render a gauge for cash runway"""
    # Determine color based on months
    if months < 6:
        color = "#dc2626"
    elif months < 12:
        color = "#f97316"
    elif months < 18:
        color = "#eab308"
    else:
        color = "#22c55e"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=months,
        number={'suffix': " mo"},
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Cash Runway", 'font': {'size': 16}},
        delta={'reference': 12, 'position': "bottom"},
        gauge={
            'axis': {'range': [0, max_months], 'tickwidth': 1},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#e2e8f0",
            'steps': [
                {'range': [0, 6], 'color': '#fecaca'},
                {'range': [6, 12], 'color': '#fed7aa'},
                {'range': [12, 18], 'color': '#fef08a'},
                {'range': [18, max_months], 'color': '#bbf7d0'}
            ]
        }
    ))

    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)'
    )

    return fig


def render_npv_box(npv: float, discount_rate: float, implied_price: float, upside_pct: float):
    """Render the prominent NPV display box"""
    st.markdown(f"""
    <div class="npv-box">
        <h1 style="color: #0f172a !important; margin: 0 0 10px 0; font-size: 1.2rem; text-transform: uppercase; letter-spacing: 2px; font-weight: 700;">
            Expected Project NPV ({discount_rate*100:.0f}% Discount Rate)
        </h1>
        <h1 style="color: #1e40af !important; margin: 0; font-size: 4.5rem; font-weight: 800; letter-spacing: -2px;">
            ${npv:.2f}B
        </h1>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 30px; padding-top: 30px; border-top: 3px solid #3b82f6;">
            <div>
                <p style="color: #475569 !important; margin: 0 0 8px 0; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;">
                    Implied Share Price
                </p>
                <h2 style="color: #0f172a !important; margin: 0; font-size: 2.5rem; font-weight: 800;">
                    ${implied_price:.2f}
                </h2>
            </div>
            <div>
                <p style="color: #475569 !important; margin: 0 0 8px 0; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;">
                    NPV vs Market Cap
                </p>
                <h2 style="color: {'#059669' if upside_pct > 0 else '#dc2626'} !important; margin: 0; font-size: 2.5rem; font-weight: 800;">
                    {upside_pct:+.1f}%
                </h2>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_sensitivity_heatmap(df: pd.DataFrame, title: str = "NPV Sensitivity"):
    """Render a heatmap for sensitivity analysis"""
    fig = px.imshow(
        df.values,
        labels=dict(x="Gold Price", y="Discount Rate", color="NPV ($M)"),
        x=df.columns.tolist(),
        y=df.index.tolist(),
        color_continuous_scale="RdYlGn",
        aspect="auto"
    )

    fig.update_layout(
        title=title,
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)'
    )

    # Add value annotations
    for i, row in enumerate(df.index):
        for j, col in enumerate(df.columns):
            fig.add_annotation(
                x=col,
                y=row,
                text=f"${df.loc[row, col]:.0f}M",
                showarrow=False,
                font=dict(size=10, color="white" if abs(df.loc[row, col]) > df.values.max() * 0.5 else "black")
            )

    return fig


def render_cash_flow_chart(df: pd.DataFrame):
    """Render cash flow bar chart"""
    fig = px.bar(
        df,
        x='year',
        y='free_cash_flow',
        title="Projected Free Cash Flows",
        color='free_cash_flow',
        color_continuous_scale=['#dc2626', '#22c55e']
    )

    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis_title="Year",
        yaxis_title="Free Cash Flow ($)"
    )

    return fig


def render_comparison_table(data: List[Dict], highlight_best: bool = True):
    """Render a styled comparison table"""
    df = pd.DataFrame(data)
    st.dataframe(
        df.style.background_gradient(subset=['Margin'], cmap='RdYlGn'),
        use_container_width=True,
        hide_index=True
    )


def render_signal_card(signal: Dict[str, Any]):
    """Render a signal/alert card"""
    signal_type = signal.get('type', 'info')
    color_class = {
        'positive': 'signal-card positive',
        'negative': 'signal-card negative',
        'warning': 'signal-card warning',
        'info': 'signal-card'
    }.get(signal_type, 'signal-card')

    st.markdown(f"""
    <div class="{color_class}">
        <strong>{signal.get('title', 'Signal')}</strong><br>
        <span style="color: #64748b; font-size: 0.9rem;">{signal.get('description', '')}</span><br>
        <span style="color: #94a3b8; font-size: 0.8rem;">{signal.get('timestamp', '')}</span>
    </div>
    """, unsafe_allow_html=True)
