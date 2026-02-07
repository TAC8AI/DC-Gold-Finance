"""
HTML Report Generator - Creates a shareable investment memo from live dashboard data
"""
from datetime import datetime
from typing import Dict, Any, List

from financial_models.metrics_calculator import MetricsCalculator
from risk_engine.risk_scorer import RiskScorer
from data_ingestion.gold_price_fetcher import GoldPriceFetcher
from scenario_engine.npv_calculator import NPVCalculator
from benchmarks.adjusted_return import AdjustedReturnCalculator


def generate_report(tickers: List[str]) -> str:
    """
    Generate a polished HTML investment memo for all tracked companies.

    Args:
        tickers: List of company ticker symbols

    Returns:
        Complete HTML string ready for download
    """
    # Gather all data
    metrics_calc = MetricsCalculator()
    risk_scorer = RiskScorer()
    gold_fetcher = GoldPriceFetcher()
    npv_calc = NPVCalculator()
    return_calc = AdjustedReturnCalculator()

    gold_data = gold_fetcher.get_current_price()
    gold_price = gold_data.get('price', 2100)
    gold_change = gold_data.get('daily_change_pct', 0)

    all_metrics = {}
    all_risks = {}
    all_npv = {}

    for ticker in tickers:
        all_metrics[ticker] = metrics_calc.get_all_metrics(ticker)
        all_risks[ticker] = risk_scorer.calculate_composite_score(ticker)

        # Calculate NPV at current gold price
        proj = all_metrics[ticker]['project']
        if proj['production_oz'] > 0 and proj['capex_millions'] > 0:
            npv_result = npv_calc.calculate_project_metrics(
                gold_price=gold_price,
                annual_production_oz=proj['production_oz'],
                aisc_per_oz=proj['aisc'],
                discount_rate=0.08,
                initial_capex=proj['capex_millions'] * 1_000_000,
                start_year=proj['start_year'],
                mine_life_years=proj['mine_life_years']
            )
            all_npv[ticker] = npv_result

    date_str = datetime.now().strftime("%B %d, %Y")
    time_str = datetime.now().strftime("%I:%M %p")

    # Build portfolio summary stats
    total_mkt_cap = sum(m['market']['market_cap_millions'] for m in all_metrics.values())
    avg_risk = sum(
        r.get('composite_score', 3) for r in all_risks.values() if 'error' not in r
    ) / max(len(tickers), 1)

    # --- BUILD HTML ---
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Junior Gold Intel | Portfolio Report - {date_str}</title>
    <style>
        :root {{
            --primary: #0f172a;
            --secondary: #334155;
            --accent: #1e40af;
            --green: #059669;
            --red: #dc2626;
            --amber: #d97706;
            --bg: #f8fafc;
            --white: #ffffff;
            --border: #e2e8f0;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1e293b;
            background: var(--bg);
        }}

        .header {{
            background: var(--white);
            border-bottom: 4px solid var(--primary);
            padding: 40px 8%;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}

        .header h1 {{
            font-size: 2rem;
            color: var(--primary);
            letter-spacing: -0.5px;
        }}

        .header .subtitle {{
            color: #64748b;
            margin-top: 4px;
        }}

        .header .meta {{
            text-align: right;
            font-size: 0.85rem;
            color: var(--secondary);
        }}

        .container {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 40px 20px;
        }}

        .section {{
            background: var(--white);
            padding: 30px;
            margin-bottom: 24px;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            border: 1px solid var(--border);
        }}

        h2 {{
            border-bottom: 2px solid var(--border);
            padding-bottom: 10px;
            margin-bottom: 20px;
            color: var(--primary);
            font-size: 1.15rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        h3 {{
            color: var(--accent);
            font-size: 1rem;
            margin-bottom: 12px;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 16px;
        }}

        .metric-card {{
            background: #f1f5f9;
            padding: 18px;
            border-left: 4px solid var(--secondary);
        }}

        .metric-card.accent {{
            border-left-color: var(--accent);
            background: #eff6ff;
        }}

        .metric-card.green {{
            border-left-color: var(--green);
            background: #ecfdf5;
        }}

        .metric-card.red {{
            border-left-color: var(--red);
            background: #fef2f2;
        }}

        .metric-label {{
            display: block;
            font-size: 0.7rem;
            text-transform: uppercase;
            color: var(--secondary);
            font-weight: 600;
            margin-bottom: 4px;
            letter-spacing: 0.5px;
        }}

        .metric-value {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary);
        }}

        .metric-sub {{
            font-size: 0.8rem;
            color: #64748b;
            margin-top: 2px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            font-size: 0.85rem;
        }}

        th {{
            background: var(--primary);
            color: var(--white);
            padding: 10px 12px;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
        }}

        tr:nth-child(even) {{
            background: #f8fafc;
        }}

        .company-section {{
            border-top: 3px solid var(--accent);
            margin-top: 8px;
        }}

        .risk-badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        .risk-low {{ background: #dcfce7; color: #166534; }}
        .risk-moderate {{ background: #fef9c3; color: #854d0e; }}
        .risk-high {{ background: #fecaca; color: #991b1b; }}

        .three-col {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 24px;
        }}

        .three-col > div {{
            padding: 16px;
            background: #f8fafc;
            border-radius: 4px;
            border: 1px solid var(--border);
        }}

        .three-col h3 {{
            margin-bottom: 8px;
        }}

        .three-col ul {{
            padding-left: 18px;
            font-size: 0.85rem;
        }}

        .three-col li {{
            margin-bottom: 6px;
        }}

        .footer {{
            text-align: center;
            font-size: 0.75rem;
            color: #94a3b8;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
        }}

        @media print {{
            body {{ background: white; }}
            .section {{ box-shadow: none; break-inside: avoid; }}
            .header {{ padding: 20px 5%; }}
        }}

        @media (max-width: 768px) {{
            .three-col {{ grid-template-columns: 1fr; }}
            .header {{ flex-direction: column; align-items: flex-start; gap: 12px; }}
            .header .meta {{ text-align: left; }}
        }}
    </style>
</head>
<body>

    <header class="header">
        <div>
            <h1>Junior Gold Miner Decision Intelligence</h1>
            <p class="subtitle">{date_str} | Portfolio Report</p>
        </div>
        <div class="meta">
            <strong>Generated:</strong> {time_str}<br>
            <strong>Gold Spot:</strong> ${gold_price:,.0f}/oz ({gold_change:+.1f}%)<br>
            <strong>Companies:</strong> {len(tickers)}
        </div>
    </header>

    <div class="container">

        <!-- PORTFOLIO OVERVIEW -->
        <div class="section">
            <h2>Portfolio Overview</h2>
            <div class="metrics-grid">
                <div class="metric-card accent">
                    <span class="metric-label">Gold Price</span>
                    <span class="metric-value">${gold_price:,.0f}</span>
                    <span class="metric-sub">{gold_change:+.1f}% today</span>
                </div>
                <div class="metric-card">
                    <span class="metric-label">Portfolio Market Cap</span>
                    <span class="metric-value">${total_mkt_cap:,.0f}M</span>
                    <span class="metric-sub">{len(tickers)} companies</span>
                </div>
                <div class="metric-card">
                    <span class="metric-label">Avg Risk Score</span>
                    <span class="metric-value">{avg_risk:.1f}/5.0</span>
                    <span class="metric-sub">{'Low' if avg_risk >= 3.5 else 'Moderate' if avg_risk >= 2.5 else 'High'} risk</span>
                </div>
            </div>
        </div>

        <!-- COMPARISON TABLE -->
        <div class="section">
            <h2>Company Comparison</h2>
            <table>
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Price</th>
                        <th>Mkt Cap</th>
                        <th>AISC</th>
                        <th>Margin/oz</th>
                        <th>Runway</th>
                        <th>Risk</th>
                        <th>NPV (8%)</th>
                        <th>Stage</th>
                    </tr>
                </thead>
                <tbody>
"""

    for ticker in tickers:
        m = all_metrics[ticker]
        r = all_risks[ticker]
        npv_data = all_npv.get(ticker, {})

        risk_score = r.get('composite_score', 0)
        risk_class = 'risk-low' if risk_score >= 3.5 else 'risk-moderate' if risk_score >= 2.5 else 'risk-high'

        npv_str = f"${npv_data.get('npv_billions', 0):.2f}B" if npv_data else 'N/A'
        runway = m['cash']['runway_months']
        runway_str = f"{runway:.0f} mo" if runway > 0 else 'N/A'

        html += f"""                    <tr>
                        <td><strong>{ticker}</strong></td>
                        <td>${m['market']['current_price']:.2f}</td>
                        <td>${m['market']['market_cap_millions']:,.0f}M</td>
                        <td>${m['project']['aisc']:,.0f}</td>
                        <td>${m['project']['margin_per_oz']:,.0f}</td>
                        <td>{runway_str}</td>
                        <td><span class="risk-badge {risk_class}">{risk_score:.1f}</span></td>
                        <td>{npv_str}</td>
                        <td>{m['project']['stage'].title()}</td>
                    </tr>
"""

    html += """                </tbody>
            </table>
        </div>

        <!-- WHAT CHANGED / MATTERS / WORRIES -->
        <div class="section">
            <h2>Executive Intelligence</h2>
            <div class="three-col">
                <div>
                    <h3 style="color: var(--accent);">What Changed?</h3>
                    <ul>
"""

    for ticker in tickers:
        m = all_metrics[ticker]
        runway = m['cash']['runway_months']
        html += f"                        <li><strong>{ticker}</strong> - ${m['market']['current_price']:.2f} | Gold at ${gold_price:,.0f} | Runway: {runway:.0f} mo</li>\n"

    html += """                    </ul>
                </div>
                <div>
                    <h3 style="color: var(--green);">What Matters?</h3>
                    <ul>
"""

    for ticker in tickers:
        m = all_metrics[ticker]
        r = all_risks[ticker]
        html += f"                        <li><strong>{ticker}</strong> ({m['project']['stage'].title()}) - Margin: ${m['project']['margin_per_oz']:,.0f}/oz, Risk: {r.get('composite_score', 0):.1f}/5</li>\n"

    html += """                    </ul>
                </div>
                <div>
                    <h3 style="color: var(--red);">What Worries Us?</h3>
                    <ul>
"""

    for ticker in tickers:
        m = all_metrics[ticker]
        r = all_risks[ticker]
        concerns = []

        if m['cash']['runway_months'] < 12 and m['cash']['runway_months'] > 0:
            concerns.append(f"Short runway ({m['cash']['runway_months']:.0f} mo)")
        if m['dilution']['expected_dilution_pct'] > 40:
            concerns.append(f"High dilution ({m['dilution']['expected_dilution_pct']:.0f}%)")
        if m['project']['aisc'] > 1400:
            concerns.append(f"High AISC (${m['project']['aisc']:,.0f})")
        if m['project']['start_year'] > 2028:
            concerns.append(f"Long timeline ({m['project']['start_year']})")

        weakest = r.get('weakest_category', 'unknown')
        if concerns:
            html += f"                        <li><strong>{ticker}</strong> - {weakest.title()} weakest: {'; '.join(concerns)}</li>\n"
        else:
            html += f"                        <li><strong>{ticker}</strong> - No major concerns</li>\n"

    html += """                    </ul>
                </div>
            </div>
        </div>
"""

    # Individual company sections
    for ticker in tickers:
        m = all_metrics[ticker]
        r = all_risks[ticker]
        npv_data = all_npv.get(ticker, {})
        proj = m['project']

        risk_score = r.get('composite_score', 0)
        risk_class = 'risk-low' if risk_score >= 3.5 else 'risk-moderate' if risk_score >= 2.5 else 'risk-high'

        html += f"""
        <!-- {ticker} DETAIL -->
        <div class="section company-section">
            <h2>{ticker} - {m['company_name']}</h2>

            <div class="metrics-grid">
                <div class="metric-card">
                    <span class="metric-label">Share Price</span>
                    <span class="metric-value">${m['market']['current_price']:.2f}</span>
                    <span class="metric-sub">Mkt Cap: ${m['market']['market_cap_millions']:,.0f}M</span>
                </div>
                <div class="metric-card {'green' if risk_score >= 3 else 'red'}">
                    <span class="metric-label">Risk Score</span>
                    <span class="metric-value">{risk_score:.1f}/5.0</span>
                    <span class="metric-sub"><span class="risk-badge {risk_class}">{'Low' if risk_score >= 3.5 else 'Moderate' if risk_score >= 2.5 else 'High'}</span></span>
                </div>
"""

        if npv_data:
            html += f"""                <div class="metric-card accent">
                    <span class="metric-label">Project NPV (8%)</span>
                    <span class="metric-value">${npv_data['npv_billions']:.2f}B</span>
                    <span class="metric-sub">Breakeven: ${npv_data.get('breakeven_gold_price', 0):,.0f}/oz</span>
                </div>
"""

        html += f"""                <div class="metric-card">
                    <span class="metric-label">Cash Position</span>
                    <span class="metric-value">${m['cash']['total_cash_millions']:.1f}M</span>
                    <span class="metric-sub">Runway: {m['cash']['runway_months']:.0f} months</span>
                </div>
            </div>

            <table>
                <tr><td><strong>Project</strong></td><td>{proj['name']}</td><td><strong>Stage</strong></td><td>{proj['stage'].title()}</td></tr>
                <tr><td><strong>Annual Production</strong></td><td>{proj['production_oz']:,.0f} oz</td><td><strong>Mine Life</strong></td><td>{proj['mine_life_years']} years</td></tr>
                <tr><td><strong>AISC</strong></td><td>${proj['aisc']:,.0f}/oz</td><td><strong>Margin at Current Gold</strong></td><td>${proj['margin_per_oz']:,.0f}/oz</td></tr>
                <tr><td><strong>Initial Capex</strong></td><td>${proj['capex_millions']:,.0f}M</td><td><strong>Production Start</strong></td><td>{proj['start_year']}</td></tr>
                <tr><td><strong>Funding Gap</strong></td><td>${m['funding']['funding_gap_millions']:,.0f}M</td><td><strong>Expected Dilution</strong></td><td>{m['dilution']['expected_dilution_pct']:.0f}%</td></tr>
            </table>
"""

        # Risk breakdown
        categories = r.get('categories', {})
        if categories:
            html += """            <h3>Risk Breakdown</h3>
            <table>
                <thead><tr><th>Category</th><th>Score</th><th>Level</th><th>Weight</th></tr></thead>
                <tbody>
"""
            for cat_name, cat_data in categories.items():
                cat_score = cat_data.get('score', 0)
                cat_class = 'risk-low' if cat_score >= 4 else 'risk-moderate' if cat_score >= 3 else 'risk-high'
                html += f"""                    <tr>
                        <td>{cat_name.title()}</td>
                        <td><span class="risk-badge {cat_class}">{cat_score}/5</span></td>
                        <td>{cat_data.get('level', 'N/A')}</td>
                        <td>{cat_data.get('weight', 0)*100:.0f}%</td>
                    </tr>
"""
            html += """                </tbody>
            </table>
"""

        html += "        </div>\n"

    # Footer
    html += f"""
        <!-- DISCLAIMER -->
        <div class="section" style="background: #f8fafc;">
            <h2>Disclaimer</h2>
            <p style="font-size: 0.85rem; color: #64748b;">
                This report is generated from the Junior Gold Intel Decision Intelligence platform for informational purposes only.
                It does not constitute financial advice, investment recommendations, or an offer to buy or sell securities.
                All data is sourced from Yahoo Finance (live market data) and company disclosures (project parameters).
                Users should conduct independent due diligence and consult a qualified financial advisor before making investment decisions.
                Past performance does not guarantee future results. Mining investments carry significant risk including total loss of capital.
            </p>
        </div>

    </div>

    <div class="footer">
        <p>Junior Gold Intel | Generated {date_str} at {time_str}<br>
        Data sources: Yahoo Finance (market data), Company filings (project parameters)</p>
    </div>

</body>
</html>"""

    return html
