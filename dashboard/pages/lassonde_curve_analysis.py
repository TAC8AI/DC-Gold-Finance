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
        {"name": "Exploration", "start": 0, "end": 16, "desc": "Early drilling and mapping define geologic potential."},
        {"name": "Discovery Peak", "start": 16, "end": 30, "desc": "Speculation spikes as headline intercepts attract momentum buyers."},
        {"name": "Orphan Period", "start": 30, "end": 56, "desc": "Excitement fades while technical studies and de-risking grind forward."},
        {"name": "Feasibility", "start": 56, "end": 72, "desc": "Economic studies tighten confidence around capex, opex, and mine plan."},
        {"name": "Construction", "start": 72, "end": 86, "desc": "Permits and financing convert the project from idea to build."},
        {"name": "Production Re-rate", "start": 86, "end": 100, "desc": "Commissioning and cash flow trigger valuation multiple expansion."},
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
            y=1.30 if idx % 2 == 0 else 1.23,
            text=f"<b>{stage['name']}</b><br><span style='font-size:11px'>{stage['desc']}</span>",
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
        fig.add_trace(
            go.Scatter(
                x=[company["x"]],
                y=[y_value],
                mode="markers+text",
                marker=dict(size=14, color=company["color"], line=dict(color="#ffffff", width=2)),
                text=[company["label"]],
                textposition="top center",
                name=company["ticker"],
                hovertemplate=f"{company['label']}<extra></extra>",
            )
        )

    fig.update_layout(
        title="The Lassonde Curve",
        height=520,
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
            range=[0, 1.36],
            gridcolor="rgba(16, 35, 60, 0.08)",
            zeroline=False,
            showticklabels=False,
        ),
    )
    return fig


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_ppta_two_year_data() -> pd.DataFrame:
    """Fetch PPTA two-year daily close data from Yahoo Finance."""
    history = yf.Ticker("PPTA").history(period="2y", auto_adjust=False)
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


def _build_ppta_case_study_chart(history: pd.DataFrame) -> go.Figure:
    """Build PPTA stock chart with key lifecycle events."""
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

    feb_window = history[
        (history["Date"] >= pd.Timestamp("2024-02-01")) &
        (history["Date"] < pd.Timestamp("2024-03-01"))
    ]
    if not feb_window.empty:
        feb_low_date = feb_window.loc[feb_window["Close"].idxmin(), "Date"]
    else:
        feb_low_date = pd.Timestamp("2024-02-15")

    permit_date = pd.Timestamp("2025-01-03")
    construction_date = pd.Timestamp("2025-10-21")
    current_date = history["Date"].iloc[-1]

    events = [
        {
            "date": feb_low_date,
            "price": 7.81,
            "label": "Feb 2024: $7.81 low (orphan period)",
            "color": BAD_RED,
        },
        {
            "date": permit_date,
            "price": _close_on_or_before(history, permit_date),
            "label": "Jan 3, 2025: Permit issued<br><b>INFLECTION POINT</b>",
            "color": BRAND_LIGHT,
        },
        {
            "date": construction_date,
            "price": _close_on_or_before(history, construction_date),
            "label": "Oct 21, 2025: Construction started",
            "color": GOOD_GREEN,
        },
        {
            "date": current_date,
            "price": float(history["Close"].iloc[-1]),
            "label": "Current: ~$27",
            "color": WARN_ORANGE,
        },
    ]

    for event in events:
        fig.add_trace(
            go.Scatter(
                x=[event["date"]],
                y=[event["price"]],
                mode="markers+text",
                marker=dict(size=11, color=event["color"], line=dict(color="#ffffff", width=1.5)),
                text=[event["label"]],
                textposition="top center",
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

    fig.update_layout(
        title="PPTA Case Study: Orphan Period to Construction Re-rate",
        height=470,
        margin=dict(l=20, r=20, t=60, b=20),
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Date", gridcolor="rgba(16, 35, 60, 0.08)"),
        yaxis=dict(title="Share Price (USD)", gridcolor="rgba(16, 35, 60, 0.08)"),
    )
    return fig


def render_lassonde_curve_analysis():
    """Render Lassonde Curve Analysis page."""
    st.markdown("## Lassonde Curve Analysis")
    st.markdown("A stage-by-stage framework for why PPTA re-rated and how DC could follow a similar path.")

    st.markdown("---")
    st.markdown("### Section 1: The Lassonde Curve")
    st.plotly_chart(_build_lassonde_curve_chart(), use_container_width=True)

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

    st.markdown("---")
    st.markdown("### Section 2: PPTA Case Study")
    ppta_history = _fetch_ppta_two_year_data()
    if ppta_history.empty:
        st.warning("Unable to load PPTA price history from Yahoo Finance right now.")
    else:
        st.plotly_chart(_build_ppta_case_study_chart(ppta_history), use_container_width=True)

    st.info("PPTA went 3.5x after getting permitted and starting construction.")

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
    st.plotly_chart(fig, use_container_width=True)
