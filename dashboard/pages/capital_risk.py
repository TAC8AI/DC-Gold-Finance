"""
Capital & Risk Analysis page: runway, dilution, funding
"""
from datetime import datetime
from typing import Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_ingestion.data_normalizer import DataNormalizer
from financial_models.capital_structure import CapitalStructureAnalyzer
from financial_models.cash_analysis import CashAnalyzer
from financial_models.dilution_scenarios import DilutionScenarioModeler
from risk_engine.risk_scorer import RiskScorer


def _fmt_time(value: str) -> str:
    """Safely format timestamps for compact display."""
    if not value:
        return "N/A"
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(value)[:16]


def _risk_chip_class(level: str) -> str:
    """Map risk level to CSS chip class."""
    mapping = {
        "critical": "risk-critical-chip",
        "high": "risk-high-chip",
        "moderate": "risk-moderate-chip",
        "low": "risk-low-chip",
        "minimal": "risk-minimal-chip",
    }
    return mapping.get((level or "").lower(), "risk-moderate-chip")


def _runway_timeline_chart(runway_months: float, max_runway: float = 36) -> go.Figure:
    """Render a cleaner runway timeline with threshold zones."""
    runway_value = max(0, min(runway_months or 0, max_runway))

    fig = go.Figure()
    zone_defs = [
        (0, 6, "#ffe1e1"),
        (6, 12, "#ffeac9"),
        (12, 18, "#fff6c9"),
        (18, max_runway, "#dcf8e7"),
    ]

    for start, end, color in zone_defs:
        fig.add_shape(
            type="rect",
            x0=start,
            y0=-0.35,
            x1=end,
            y1=0.35,
            line=dict(width=0),
            fillcolor=color,
            layer="below",
        )

    fig.add_trace(go.Bar(
        x=[runway_value],
        y=["Runway"],
        orientation="h",
        marker=dict(color="#1f58c7"),
        text=[f"{runway_months:.1f} mo" if runway_months else "N/A"],
        textposition="inside",
        insidetextanchor="middle",
        hovertemplate="Runway: %{x:.1f} months<extra></extra>",
    ))

    for threshold in [6, 12, 18]:
        fig.add_vline(x=threshold, line_width=1.5, line_color="#7a889b", line_dash="dot")

    fig.update_layout(
        title="Cash Runway Timeline",
        xaxis=dict(
            range=[0, max_runway],
            tickvals=[0, 6, 12, 18, 24, 30, 36],
            title="Months",
            gridcolor="rgba(16,35,60,0.08)",
        ),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        margin=dict(l=10, r=15, t=44, b=30),
        height=260,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _cash_vs_capex_chart(cash: float, capex: float) -> go.Figure:
    """Cash vs required capex grouped bars."""
    fig = go.Figure(data=[
        go.Bar(
            name="Cash on Hand",
            x=["Funding"],
            y=[cash],
            marker_color="#17a562",
            text=[f"${cash:.0f}M"],
            textposition="outside",
        ),
        go.Bar(
            name="Required Capex",
            x=["Funding"],
            y=[capex],
            marker_color="#8ea1bb",
            text=[f"${capex:.0f}M"],
            textposition="outside",
        ),
    ])
    fig.update_layout(
        barmode="group",
        title="Cash vs Required Capex",
        yaxis_title="$ Millions",
        height=260,
        margin=dict(l=10, r=10, t=44, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_yaxes(gridcolor="rgba(16,35,60,0.08)")
    return fig


def _dilution_probability_chart(scenarios: Dict) -> go.Figure:
    """Visualize dilution scenarios by probability and severity."""
    rows = []
    for name, scenario in scenarios.items():
        rows.append({
            "Scenario": scenario.get("name", name),
            "Dilution %": scenario.get("dilution_percentage", 0),
            "Probability %": scenario.get("probability", 0) * 100,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return go.Figure()

    fig = px.bar(
        df,
        x="Scenario",
        y="Dilution %",
        color="Probability %",
        color_continuous_scale=["#d9e9ff", "#8fb8ff", "#2f67d7"],
        text="Dilution %",
        title="Dilution Severity by Scenario",
    )
    fig.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
    fig.update_layout(
        height=330,
        margin=dict(l=10, r=10, t=44, b=20),
        coloraxis_colorbar=dict(title="Prob %"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_yaxes(gridcolor="rgba(16,35,60,0.08)")
    return fig


def render_capital_risk(tickers: List[str], selected_ticker: str = None):
    """Render capital and risk analysis page."""
    cash_analyzer = CashAnalyzer()
    capital_analyzer = CapitalStructureAnalyzer()
    dilution_modeler = DilutionScenarioModeler()
    risk_scorer = RiskScorer()
    normalizer = DataNormalizer()

    st.markdown("""
    <div class="capital-hero">
        <div class="capital-hero-kicker">Investor Readout</div>
        <div class="capital-hero-title">Capital & Risk Analysis</div>
        <div class="capital-hero-sub">Cash runway, dilution scenarios, and funding requirements for financing discussions.</div>
    </div>
    """, unsafe_allow_html=True)

    selector_col, meta_col = st.columns([2.2, 1.1])
    with selector_col:
        selected = st.selectbox(
            "Select Company",
            tickers,
            index=tickers.index(selected_ticker) if selected_ticker in tickers else 0
        )
    with meta_col:
        st.markdown("#### Decision Lens")
        st.caption("Runway health, funding gap, and dilution path")

    company_data = normalizer.get_normalized_company_data(selected)
    cash_data = cash_analyzer.analyze_cash_position(selected)
    capital_data = capital_analyzer.analyze_structure(selected)
    dilution_data = dilution_modeler.model_scenarios(selected)
    risk_data = risk_scorer.calculate_composite_score(selected)

    project = company_data.get("project", {})
    cash = cash_data.get("current_cash_millions", 0)
    capex = project.get("initial_capex_millions", 0)
    funding_gap = max(0, capex - cash)
    capex_coverage = (cash / capex * 100) if capex else 0
    runway = cash_data.get("runway_months", 0)
    risk_level = cash_data.get("runway_risk", {}).get("level", "unknown")
    risk_chip = _risk_chip_class(risk_level)
    composite_score = risk_data.get("composite_score", 0)

    st.markdown(
        f"""
        <div class="source-strip">
            <span><strong>{company_data.get('name', selected)}</strong></span>
            <span>Cash data as of: { _fmt_time(cash_data.get('analysis_time')) }</span>
            <span>Risk model as of: { _fmt_time(risk_data.get('analysis_time')) }</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Cash on Hand", f"${cash:.1f}M")
    with c2:
        st.metric("Quarterly Burn", f"${cash_data.get('quarterly_burn_millions', 0):.1f}M")
    with c3:
        st.metric("Runway", f"{runway:.0f} months" if runway else "N/A")
    with c4:
        st.metric("Funding Gap", f"${funding_gap:.0f}M")
    with c5:
        st.metric("Composite Risk", f"{composite_score:.1f}/5" if composite_score else "N/A")
        st.markdown(
            f"<span class='funding-risk-chip {risk_chip}'>{risk_level.title()} Funding Risk</span>",
            unsafe_allow_html=True
        )

    runway_col, funding_col = st.columns(2)
    with runway_col:
        st.plotly_chart(_runway_timeline_chart(runway), use_container_width=True)
        st.caption("Thresholds: <6 critical, 6-12 high, 12-18 moderate, >18 lower risk.")

    with funding_col:
        st.plotly_chart(_cash_vs_capex_chart(cash, capex), use_container_width=True)
        st.metric("Capex Coverage", f"{capex_coverage:.1f}%")
        st.caption(f"Estimated uncovered capex: ${funding_gap:.0f}M")

    st.markdown("---")

    # --- Recent Capital Events ---
    already_raised = dilution_data.get("total_already_raised_millions", 0)
    remaining_gap = dilution_data.get("remaining_funding_gap_millions")
    known_raises = dilution_data.get("known_raises", [])
    strategic = dilution_data.get("strategic_financing", {})

    if known_raises or strategic:
        st.markdown("### Recent Capital Events & Strategic Financing")

        if known_raises:
            for raise_info in known_raises:
                r_name = raise_info.get("name", "Raise")
                r_date = raise_info.get("date", "N/A")
                r_proceeds = raise_info.get("gross_proceeds_millions", 0)
                r_shares = raise_info.get("shares_issued", 0)
                r_price = raise_info.get("price_per_share", 0)
                r_underwriters = raise_info.get("underwriters", [])
                r_use = raise_info.get("use_of_proceeds", "General corporate purposes")

                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, #f0f7ff 0%, #e8f4fd 100%);
                                border-left: 4px solid #1f58c7; border-radius: 8px;
                                padding: 16px 20px; margin-bottom: 12px;">
                        <div style="font-weight: 700; font-size: 1.05rem; color: #0f172a;">
                            {r_name}
                        </div>
                        <div style="color: #475569; font-size: 0.9rem; margin-top: 6px;">
                            <strong>${r_proceeds:.0f}M</strong> gross proceeds
                            &nbsp;·&nbsp; {r_shares:,} shares @ ${r_price:.2f}
                            &nbsp;·&nbsp; Closed {r_date}
                        </div>
                        <div style="color: #64748b; font-size: 0.85rem; margin-top: 4px;">
                            Underwriters: {', '.join(r_underwriters) if r_underwriters else 'N/A'}
                            &nbsp;·&nbsp; Use: {r_use}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        if strategic:
            for partner_key, partner in strategic.items():
                p_name = partner.get("name", partner_key)
                p_invested = partner.get("invested_millions", 0)
                p_own = partner.get("ownership_pct", 0)
                p_commit = partner.get("construction_commitment_millions", 0)
                p_binding = "Binding" if partner.get("binding") else "Non-binding"
                p_royalty = partner.get("royalty_nsr_pct", 0)
                p_matching = partner.get("matching_rights", False)

                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, #f5f0ff 0%, #ede8fd 100%);
                                border-left: 4px solid #7c3aed; border-radius: 8px;
                                padding: 16px 20px; margin-bottom: 12px;">
                        <div style="font-weight: 700; font-size: 1.05rem; color: #0f172a;">
                            Strategic Partner: {p_name}
                        </div>
                        <div style="color: #475569; font-size: 0.9rem; margin-top: 6px;">
                            <strong>${p_invested:.0f}M</strong> invested ({p_own:.1f}% ownership)
                            &nbsp;·&nbsp; {p_royalty:.1f}% NSR royalty
                        </div>
                        <div style="color: #475569; font-size: 0.9rem; margin-top: 4px;">
                            Construction financing: <strong>${p_commit:.0f}M</strong> ({p_binding})
                            {'&nbsp;·&nbsp; Has matching rights' if p_matching else ''}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        ev1, ev2, ev3 = st.columns(3)
        with ev1:
            st.metric("Already Raised", f"${already_raised:.0f}M")
        with ev2:
            if remaining_gap is not None:
                st.metric("Remaining Funding Gap", f"${remaining_gap:.0f}M",
                          f"-${already_raised:.0f}M from raises")
        with ev3:
            total_commitment = sum(
                p.get("construction_commitment_millions", 0) for p in strategic.values()
            )
            if total_commitment > 0:
                st.metric("Debt Backstop Available", f"${total_commitment:.0f}M")

        st.markdown("---")

    st.markdown("### Dilution Scenarios")
    if "error" not in dilution_data:
        scenarios = dilution_data.get("scenarios", {})

        dcol1, dcol2 = st.columns(2)
        with dcol1:
            st.plotly_chart(_dilution_probability_chart(scenarios), use_container_width=True)
        with dcol2:
            fig = go.Figure(go.Waterfall(
                name="Shares",
                orientation="v",
                x=["Current"] + [s.get("name", "") for s in scenarios.values()],
                y=[dilution_data.get("current_shares_millions", 0)] +
                  [s.get("new_shares_millions", 0) * s.get("probability", 0) for s in scenarios.values()],
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                text=[f"{dilution_data.get('current_shares_millions', 0):.1f}M"] +
                     [f"+{s.get('new_shares_millions', 0):.1f}M" for s in scenarios.values()],
                textposition="outside"
            ))
            fig.update_layout(
                title="Probability-Weighted Share Impact",
                height=330,
                yaxis_title="Shares (Millions)",
                margin=dict(l=10, r=10, t=44, b=20),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

        scenario_rows = []
        for name, scenario in scenarios.items():
            scenario_rows.append({
                "Scenario": scenario.get("name", name),
                "Dilution": f"{scenario.get('dilution_percentage', 0)}%",
                "Probability": f"{scenario.get('probability', 0) * 100:.0f}%",
                "New Shares (M)": f"{scenario.get('new_shares_millions', 0):.1f}",
                "Post Shares (M)": f"{scenario.get('post_shares_millions', 0):.1f}",
                "Ownership After": f"{scenario.get('ownership_post', 0):.1f}%",
            })

        scenario_df = pd.DataFrame(scenario_rows)
        st.dataframe(scenario_df, use_container_width=True, hide_index=True)

        e1, e2, e3 = st.columns(3)
        with e1:
            st.metric("Expected Dilution", f"{dilution_data.get('expected_dilution_percentage', 0):.0f}%")
        with e2:
            current_shares = dilution_data.get("current_shares_millions", 0)
            expected_shares = dilution_data.get("expected_post_shares_millions", 0)
            st.metric("Current Shares", f"{current_shares:.1f}M", f"+{expected_shares - current_shares:.1f}M expected")
        with e3:
            expected_ownership = dilution_data.get("expected_ownership_post", 0)
            st.metric("Expected Ownership", f"{expected_ownership:.1f}%", f"-{100 - expected_ownership:.1f}%")

    st.markdown("---")

    st.markdown("### Capital Structure")
    cs1, cs2, cs3, cs4 = st.columns(4)
    with cs1:
        st.metric("Shares Outstanding", f"{capital_data.get('shares_outstanding_millions', 0):.1f}M")
    with cs2:
        st.metric("Float", f"{capital_data.get('float_percentage', 0):.1f}%")
    with cs3:
        st.metric("Total Debt", f"${capital_data.get('total_debt_millions', 0):.1f}M")
    with cs4:
        st.metric("Enterprise Value", f"${capital_data.get('ev_millions', 0):.0f}M")

    st.markdown("---")

    st.markdown("### Risk Score Breakdown")
    if "error" not in risk_data:
        categories = risk_data.get("categories", {})
        interpretation = risk_data.get("interpretation", {})
        weakest = risk_data.get("weakest_category", "")
        weakest_score = risk_data.get("weakest_score", 0)

        r1, r2 = st.columns([1, 2])
        with r1:
            st.metric("Composite Score", f"{composite_score:.2f}/5" if composite_score else "N/A")
            st.markdown(f"**{interpretation.get('level', 'Unknown')}**")
            st.caption(interpretation.get("description", ""))
            if weakest:
                st.caption(f"Weakest category: {weakest.title()} ({weakest_score:.1f}/5)")

        with r2:
            cat_data = []
            for name, cat in categories.items():
                cat_data.append({
                    "Category": name.title(),
                    "Score": cat.get("score", 0),
                    "Weight": f"{cat.get('weight', 0) * 100:.0f}%",
                    "Level": cat.get("level", "unknown").title(),
                    "Description": cat.get("description", "")
                })

            cat_df = pd.DataFrame(cat_data)
            fig = px.bar(
                cat_df,
                y="Category",
                x="Score",
                color="Score",
                color_continuous_scale=["#ffdfdf", "#ffe9bf", "#fff6bf", "#dff7eb"],
                orientation="h",
                text="Score",
                title="Risk Scores by Category (1 = highest risk, 5 = lowest)",
            )
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig.update_layout(
                height=310,
                xaxis_range=[0, 5.5],
                margin=dict(l=10, r=10, t=44, b=20),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            fig.update_xaxes(gridcolor="rgba(16,35,60,0.08)")
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(cat_df, use_container_width=True, hide_index=True)

        if weakest_score <= 2:
            st.warning(f"Attention: {weakest.title()} risk is elevated ({weakest_score:.1f}/5).")
        elif weakest_score <= 3:
            st.info(f"Monitor: {weakest.title()} is the weakest category ({weakest_score:.1f}/5).")

    st.markdown("---")

    st.markdown("### Cross-Company Risk Comparison")
    comparison_data = []
    for ticker in tickers:
        risk = risk_scorer.calculate_composite_score(ticker)
        if "error" not in risk:
            comparison_data.append({
                "Ticker": ticker,
                "Composite": risk.get("composite_score", 0),
                "Funding": risk.get("funding_score", 0),
                "Execution": risk.get("execution_score", 0),
                "Commodity": risk.get("commodity_score", 0),
                "Control": risk.get("control_score", 0),
                "Timing": risk.get("timing_score", 0),
                "Weakest": risk.get("weakest_category", "").title(),
            })

    if comparison_data:
        comp_df = pd.DataFrame(comparison_data)
        st.dataframe(
            comp_df.style.background_gradient(subset=["Composite"], cmap="RdYlGn"),
            use_container_width=True,
            hide_index=True,
        )
