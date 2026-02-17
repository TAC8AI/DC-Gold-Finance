"""
Lassonde Curve Analysis page: lifecycle framing for developer-stage miners.
"""
from datetime import datetime
from typing import Dict, List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


BRAND_BLUE = "#1846a3"
BRAND_LIGHT = "#2f67d7"
GOOD_GREEN = "#119c5b"
WARN_ORANGE = "#c48512"
BAD_RED = "#d64242"
PLOTLY_VIDEO_CONFIG = {"displayModeBar": False, "responsive": True}

PPTA_AMENDED_PFS_DATE = pd.Timestamp("2019-03-28")
PPTA_FS_ISSUED_DATE = pd.Timestamp("2021-01-27")
PPTA_FS_EFFECTIVE_DATE = pd.Timestamp("2020-12-22")
PPTA_PERMIT_DATE = pd.Timestamp("2025-01-03")
PPTA_CONSTRUCTION_DATE = pd.Timestamp("2025-10-21")


def _interpolate_y(x_value: float, points: List[Dict[str, float]]) -> float:
    """Linear interpolation helper for marker placement on the curve."""
    for idx in range(len(points) - 1):
        x1 = points[idx]["x"]
        x2 = points[idx + 1]["x"]
        if x1 <= x_value <= x2:
            y1 = points[idx]["y"]
            y2 = points[idx + 1]["y"]
            if x2 == x1:
                return y1
            return y1 + ((x_value - x1) / (x2 - x1)) * (y2 - y1)
    return points[-1]["y"]


def _build_lassonde_curve_chart() -> go.Figure:
    """Create the stylized Lassonde curve with lifecycle annotations."""
    curve_points = [
        {"x": 0, "y": 0.24},
        {"x": 16, "y": 0.62},
        {"x": 26, "y": 1.00},
        {"x": 40, "y": 0.36},
        {"x": 56, "y": 0.30},
        {"x": 70, "y": 0.56},
        {"x": 84, "y": 0.83},
        {"x": 100, "y": 1.12},
    ]
    curve_x = [point["x"] for point in curve_points]
    curve_y = [point["y"] for point in curve_points]

    stages = [
        {"name": "Exploration", "start": 0, "end": 16},
        {"name": "Discovery Peak", "start": 16, "end": 30},
        {"name": "Orphan Period", "start": 30, "end": 56},
        {"name": "Feasibility", "start": 56, "end": 72},
        {"name": "Construction", "start": 72, "end": 86},
        {"name": "Production Re-rate", "start": 86, "end": 100},
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=curve_x,
            y=curve_y,
            mode="lines",
            line=dict(color=BRAND_BLUE, width=5, shape="spline", smoothing=1.15),
            fill="tozeroy",
            fillcolor="rgba(24, 70, 163, 0.10)",
            hovertemplate="Curve Position: %{x:.0f}<br>Sentiment Level: %{y:.2f}<extra></extra>",
            name="Lassonde Curve",
        )
    )

    for idx, stage in enumerate(stages):
        fill = "rgba(24, 70, 163, 0.04)" if idx % 2 == 0 else "rgba(47, 103, 215, 0.02)"
        fig.add_vrect(
            x0=stage["start"],
            x1=stage["end"],
            fillcolor=fill,
            opacity=1,
            line_width=0,
            layer="below",
        )
        fig.add_annotation(
            x=(stage["start"] + stage["end"]) / 2,
            y=1.26,
            text=f"<b>{stage['name']}</b>",
            showarrow=False,
            align="center",
            font=dict(color="#1f2e45"),
        )

    fig.add_annotation(
        x=26,
        y=1.02,
        text="<b>Retail buys here</b>",
        showarrow=True,
        arrowhead=2,
        ax=70,
        ay=-40,
        font=dict(color=BAD_RED),
        arrowcolor=BAD_RED,
    )
    fig.add_annotation(
        x=48,
        y=0.30,
        text="<b>Smart money accumulates here</b>",
        showarrow=True,
        arrowhead=2,
        ax=120,
        ay=15,
        font=dict(color=GOOD_GREEN),
        arrowcolor=GOOD_GREEN,
    )

    company_positions = [
        {"ticker": "DC", "x": 58, "label": "DC (late orphan / early feasibility)", "color": WARN_ORANGE},
        {"ticker": "PPTA", "x": 82, "label": "PPTA (construction / pre-production)", "color": GOOD_GREEN},
    ]
    for company in company_positions:
        y_value = _interpolate_y(company["x"], curve_points)
        text_position = "bottom center" if company["ticker"] == "DC" else "top center"
        fig.add_trace(
            go.Scatter(
                x=[company["x"]],
                y=[y_value],
                mode="markers+text",
                marker=dict(size=14, color=company["color"], line=dict(color="#ffffff", width=2)),
                text=[company["label"]],
                textposition=text_position,
                name=company["ticker"],
                hovertemplate=f"{company['label']}<extra></extra>",
            )
        )

    fig.update_layout(
        title="The Lassonde Curve",
        height=500,
        margin=dict(l=20, r=20, t=110, b=20),
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title="Project Development Progress",
            range=[0, 100],
            tickmode="array",
            tickvals=[8, 23, 43, 64, 79, 93],
            ticktext=["Exploration", "Discovery", "Orphan", "Feasibility", "Construction", "Production"],
            gridcolor="rgba(16, 35, 60, 0.08)",
        ),
        yaxis=dict(
            title="Relative Sentiment / Valuation",
            range=[0, 1.32],
            gridcolor="rgba(16, 35, 60, 0.08)",
            zeroline=False,
            showticklabels=False,
        ),
    )
    return fig


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_ppta_history(period: str = "10y") -> pd.DataFrame:
    """Fetch PPTA daily close data from Yahoo Finance."""
    history = yf.Ticker("PPTA").history(period=period, auto_adjust=False)
    if history.empty:
        return pd.DataFrame(columns=["Date", "Close"])

    history = history.reset_index()
    history["Date"] = pd.to_datetime(history["Date"]).dt.tz_localize(None)
    history = history[["Date", "Close"]].dropna().sort_values("Date")
    return history


def _close_on_or_before(data: pd.DataFrame, event_date: datetime) -> float:
    """Get the latest close on or before a target date."""
    eligible = data[data["Date"] <= event_date]
    if eligible.empty:
        return float(data["Close"].iloc[0]) if not data.empty else 0.0
    return float(eligible["Close"].iloc[-1])


def _build_ppta_historical_chart(history: pd.DataFrame) -> go.Figure:
    """Build PPTA long-horizon chart (2018-present) with study/permit milestones."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=history["Date"],
            y=history["Close"],
            mode="lines",
            name="PPTA Close",
            line=dict(color=BRAND_BLUE, width=3),
            hovertemplate="%{x|%Y-%m-%d}<br>$%{y:.2f}<extra></extra>",
        )
    )

    current_date = history["Date"].iloc[-1]

    events = [
        {
            "date": PPTA_AMENDED_PFS_DATE,
            "price": _close_on_or_before(history, PPTA_AMENDED_PFS_DATE),
            "short_label": "Amended PFS",
            "color": BRAND_LIGHT,
            "ax": 20,
            "ay": -45,
            "xshift": 0,
        },
        {
            "date": PPTA_FS_ISSUED_DATE,
            "price": _close_on_or_before(history, PPTA_FS_ISSUED_DATE),
            "short_label": "FS Issued",
            "color": WARN_ORANGE,
            "ax": -20,
            "ay": 55,
            "xshift": 0,
        },
        {
            "date": PPTA_PERMIT_DATE,
            "price": _close_on_or_before(history, PPTA_PERMIT_DATE),
            "short_label": "Permit Issued",
            "color": GOOD_GREEN,
            "ax": 20,
            "ay": -55,
            "xshift": 0,
        },
        {
            "date": PPTA_CONSTRUCTION_DATE,
            "price": _close_on_or_before(history, PPTA_CONSTRUCTION_DATE),
            "short_label": "Construction Started",
            "color": GOOD_GREEN,
            "ax": 20,
            "ay": -55,
            "xshift": 0,
        },
        {
            "date": current_date,
            "price": float(history["Close"].iloc[-1]),
            "label": f"Current: ${float(history['Close'].iloc[-1]):.2f}",
            "short_label": f"Current ${float(history['Close'].iloc[-1]):.2f}",
            "color": WARN_ORANGE,
            "ax": -40,
            "ay": -45,
            "xshift": 0,
        },
    ]

    for event in events:
        fig.add_trace(
            go.Scatter(
                x=[event["date"]],
                y=[event["price"]],
                mode="markers",
                marker=dict(size=11, color=event["color"], line=dict(color="#ffffff", width=1.5)),
                showlegend=False,
                hovertemplate=f"{event['date']:%Y-%m-%d}<br>${event['price']:.2f}<extra></extra>",
            )
        )
        fig.add_vline(
            x=event["date"],
            line_dash="dot",
            line_color=event["color"],
            opacity=0.45,
        )
        fig.add_annotation(
            x=event["date"],
            y=event["price"],
            text=f"<b>{event['short_label']}</b>",
            showarrow=True,
            arrowhead=2,
            arrowwidth=1.5,
            ax=event["ax"],
            ay=event["ay"],
            xshift=event["xshift"],
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor=event["color"],
            borderwidth=1,
            font=dict(color="#1f2e45", size=11),
        )

    y_min = float(history["Close"].min())
    y_max = float(history["Close"].max())

    fig.update_layout(
        title="PPTA Long-Horizon Milestones (2018-Present)",
        height=470,
        margin=dict(l=20, r=20, t=70, b=20),
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Date", gridcolor="rgba(16, 35, 60, 0.08)"),
        yaxis=dict(
            title="Share Price (USD)",
            gridcolor="rgba(16, 35, 60, 0.08)",
            range=[y_min * 0.85, y_max * 1.18],
        ),
    )
    return fig


def _build_ppta_historical_table(history: pd.DataFrame) -> pd.DataFrame:
    """Historical milestone summary for PPTA."""
    rows = [
        ("Amended PFS", PPTA_AMENDED_PFS_DATE),
        ("FS Issued", PPTA_FS_ISSUED_DATE),
        ("Permit Issued", PPTA_PERMIT_DATE),
        ("Construction Started", PPTA_CONSTRUCTION_DATE),
    ]
    data = []
    for milestone, event_date in rows:
        px = _close_on_or_before(history, event_date)
        data.append(
            {
                "Milestone": milestone,
                "Date": event_date.strftime("%Y-%m-%d"),
                "Price Near Date (USD)": f"${px:.2f}",
            }
        )
    return pd.DataFrame(data)


def _build_ppta_recent_chart(full_history: pd.DataFrame, recent_history: pd.DataFrame) -> go.Figure:
    """Build recent 1Y PPTA chart for near-term execution view."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=recent_history["Date"],
            y=recent_history["Close"],
            mode="lines",
            name="PPTA Close",
            line=dict(color=BRAND_BLUE, width=3),
            hovertemplate="%{x|%Y-%m-%d}<br>$%{y:.2f}<extra></extra>",
        )
    )

    recent_start = recent_history["Date"].iloc[0]
    current_date = recent_history["Date"].iloc[-1]
    start_price = float(recent_history["Close"].iloc[0])
    current_price = float(recent_history["Close"].iloc[-1])

    events = [
        {
            "date": recent_start,
            "price": start_price,
            "short_label": "1Y Start",
            "color": BRAND_LIGHT,
            "ax": 20,
            "ay": -45,
            "xshift": 0,
        },
        {
            "date": PPTA_CONSTRUCTION_DATE,
            "price": _close_on_or_before(full_history, PPTA_CONSTRUCTION_DATE),
            "short_label": "Construction Started",
            "color": GOOD_GREEN,
            "ax": 20,
            "ay": -55,
            "xshift": 0,
        },
        {
            "date": current_date,
            "price": current_price,
            "short_label": f"Current ${current_price:.2f}",
            "color": WARN_ORANGE,
            "ax": -40,
            "ay": -45,
            "xshift": 0,
        },
    ]

    for event in events:
        if not (recent_start <= event["date"] <= current_date):
            continue
        fig.add_trace(
            go.Scatter(
                x=[event["date"]],
                y=[event["price"]],
                mode="markers",
                marker=dict(size=11, color=event["color"], line=dict(color="#ffffff", width=1.5)),
                showlegend=False,
                hovertemplate=f"{event['date']:%Y-%m-%d}<br>${event['price']:.2f}<extra></extra>",
            )
        )
        fig.add_vline(
            x=event["date"],
            line_dash="dot",
            line_color=event["color"],
            opacity=0.45,
        )
        fig.add_annotation(
            x=event["date"],
            y=event["price"],
            text=f"<b>{event['short_label']}</b>",
            showarrow=True,
            arrowhead=2,
            arrowwidth=1.5,
            ax=event["ax"],
            ay=event["ay"],
            xshift=event["xshift"],
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor=event["color"],
            borderwidth=1,
            font=dict(color="#1f2e45", size=11),
        )

    y_min = float(recent_history["Close"].min())
    y_max = float(recent_history["Close"].max())

    fig.update_layout(
        title="PPTA Recent Execution Window (1Y)",
        height=470,
        margin=dict(l=20, r=20, t=70, b=20),
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Date", gridcolor="rgba(16, 35, 60, 0.08)"),
        yaxis=dict(
            title="Share Price (USD)",
            gridcolor="rgba(16, 35, 60, 0.08)",
            range=[y_min * 0.9, y_max * 1.15],
        ),
    )
    return fig


def _build_ppta_recent_table(full_history: pd.DataFrame, recent_history: pd.DataFrame) -> pd.DataFrame:
    """Recent 1Y milestone summary for PPTA."""
    rows = [
        ("1Y Start", recent_history["Date"].iloc[0]),
        ("Construction Started", PPTA_CONSTRUCTION_DATE),
        ("Current", recent_history["Date"].iloc[-1]),
    ]
    data = []
    for milestone, event_date in rows:
        px = _close_on_or_before(full_history, event_date)
        data.append(
            {
                "Milestone": milestone,
                "Date": event_date.strftime("%Y-%m-%d"),
                "Price Near Date (USD)": f"${px:.2f}",
            }
        )
    return pd.DataFrame(data)


def render_lassonde_curve_analysis():
    """Render Lassonde Curve Analysis page."""
    st.markdown("## Lassonde Curve Analysis")
    st.markdown("A stage-by-stage framework for why PPTA re-rated and how DC could follow a similar path.")
    st.caption("Focus: compare DC milestone timing against the PPTA de-risking path.")

    st.markdown("---")
    st.markdown("### Section 1: The Lassonde Curve")
    st.plotly_chart(
        _build_lassonde_curve_chart(),
        use_container_width=True,
        config=PLOTLY_VIDEO_CONFIG,
    )

    stage_table = pd.DataFrame(
        [
            {"Stage": "Exploration", "One-Sentence Explanation": "Early drilling identifies targets, but uncertainty keeps valuation anchored."},
            {"Stage": "Discovery Peak", "One-Sentence Explanation": "Breakthrough intercepts create narrative momentum and a speculative valuation spike."},
            {"Stage": "Orphan Dip", "One-Sentence Explanation": "The market loses patience while technical studies, permits, and financing work proceeds."},
            {"Stage": "Feasibility", "One-Sentence Explanation": "Engineering and economics become more concrete, reducing execution uncertainty."},
            {"Stage": "Construction", "One-Sentence Explanation": "Permits and capital commitments convert optionality into tangible project buildout."},
            {"Stage": "Production Re-rate", "One-Sentence Explanation": "First production and cash flow usually unlock a higher-quality valuation multiple."},
        ]
    )
    st.dataframe(stage_table, use_container_width=True, hide_index=True)
    st.caption("Framework source: Lassonde lifecycle concept adapted for junior gold developers.")

    st.markdown("---")
    st.markdown("### Section 2: PPTA Case Study")
    ppta_history = _fetch_ppta_history(period="10y")
    if ppta_history.empty:
        st.warning("Unable to load PPTA price history from Yahoo Finance right now.")
    else:
        latest_date = ppta_history["Date"].iloc[-1]
        one_year_start = latest_date - pd.Timedelta(days=365)
        recent_history = ppta_history[ppta_history["Date"] >= one_year_start].copy()
        historical_history = ppta_history[ppta_history["Date"] >= pd.Timestamp("2018-01-01")].copy()

        tab_hist, tab_recent = st.tabs(["Historical Context (2018-Present)", "Recent Execution (1Y)"])

        with tab_hist:
            st.plotly_chart(
                _build_ppta_historical_chart(historical_history),
                use_container_width=True,
                config=PLOTLY_VIDEO_CONFIG,
            )
            st.dataframe(_build_ppta_historical_table(historical_history), use_container_width=True, hide_index=True)
            st.caption(
                "Context dates: Amended PFS (2019-03-28), FS issued (2021-01-27; effective 2020-12-22), "
                "permit issued (2025-01-03), construction start (2025-10-21)."
            )
            st.caption(
                f"Data as of {latest_date:%Y-%m-%d}. Source: Yahoo Finance via yfinance."
            )

        with tab_recent:
            if recent_history.empty:
                st.info("Recent 1Y window unavailable right now.")
            else:
                st.plotly_chart(
                    _build_ppta_recent_chart(ppta_history, recent_history),
                    use_container_width=True,
                    config=PLOTLY_VIDEO_CONFIG,
                )
                st.dataframe(_build_ppta_recent_table(ppta_history, recent_history), use_container_width=True, hide_index=True)
                st.caption(
                    f"1Y window: {recent_history['Date'].iloc[0]:%Y-%m-%d} to {latest_date:%Y-%m-%d}."
                )

        st.info(
            "A strict 5-year window from 2026 starts in 2021 and misses the 2019 Amended PFS, "
            "so historical view is set to 2018-present."
        )

    st.info("PPTA shows a step-up in valuation as major de-risking milestones are cleared.")

    st.markdown("---")
    st.markdown("### Section 3: Dakota Gold vs PPTA")

    milestone_df = pd.DataFrame(
        [
            {"Milestone": "PFS", "PPTA": "✅ Done", "DC": "🔲 H2 2026"},
            {"Milestone": "Feasibility", "PPTA": "✅ Done", "DC": "🔲 2027"},
            {"Milestone": "Permit", "PPTA": "✅ Jan 2025", "DC": "🔲 TBD"},
            {"Milestone": "Construction", "PPTA": "✅ Oct 2025", "DC": "🔲 2027-28"},
            {"Milestone": "Production", "PPTA": "🔲 2028", "DC": "🔲 2029"},
        ]
    )
    st.table(milestone_df)
    st.info("DC is 1-2 years behind PPTA on the curve.")

    st.markdown("---")
    st.markdown("### Section 4: DC Scenario Model")

    scenario_df = pd.DataFrame(
        [
            {"Stage": "Current", "Implied Price": 5.47, "Return": "-"},
            {"Stage": "PFS Complete", "Implied Price": 7.34, "Return": "+34%"},
            {"Stage": "Permitted", "Implied Price": 13.45, "Return": "+146%"},
            {"Stage": "Construction", "Implied Price": 17.11, "Return": "+213%"},
            {"Stage": "Production", "Implied Price": 24.45, "Return": "+347%"},
        ]
    )

    display_df = scenario_df.copy()
    display_df["Implied Price"] = display_df["Implied Price"].map(lambda value: f"${value:.2f}")
    st.table(display_df)

    bar_colors = [BRAND_BLUE, BRAND_LIGHT, "#3d79df", "#4f8ae5", GOOD_GREEN]
    fig = go.Figure(
        data=[
            go.Bar(
                x=scenario_df["Stage"],
                y=scenario_df["Implied Price"],
                marker_color=bar_colors,
                text=scenario_df["Return"],
                textposition="outside",
                hovertemplate="%{x}<br>Implied Price: $%{y:.2f}<br>Return: %{text}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title="DC Implied Valuation Progression Along the Lassonde Curve",
        height=420,
        margin=dict(l=20, r=20, t=60, b=20),
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Development Stage",
        yaxis_title="Implied Share Price (USD)",
        yaxis=dict(gridcolor="rgba(16, 35, 60, 0.08)"),
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_VIDEO_CONFIG)
    st.caption(
        "Modeled scenario outputs from internal assumptions; not a prediction or investment advice."
    )
