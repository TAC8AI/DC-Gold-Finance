"""
Signals Feed page: Material changes and alerts
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

from financial_models.metrics_calculator import MetricsCalculator
from data_ingestion.yfinance_fetcher import YFinanceFetcher
from data_ingestion.gold_price_fetcher import GoldPriceFetcher
from risk_engine.risk_scorer import RiskScorer


def generate_signals(tickers: List[str]) -> List[Dict[str, Any]]:
    """Generate signals based on current data"""

    signals = []
    metrics_calc = MetricsCalculator()
    yf_fetcher = YFinanceFetcher()
    gold_fetcher = GoldPriceFetcher()
    risk_scorer = RiskScorer()

    # Gold price signal
    gold_data = gold_fetcher.get_current_price()
    gold_change = gold_data.get('daily_change_pct', 0)

    if abs(gold_change) > 1.5:
        signal_type = 'positive' if gold_change > 0 else 'negative'
        signals.append({
            'type': signal_type,
            'category': 'Gold Price',
            'title': f"Gold {'Up' if gold_change > 0 else 'Down'} {abs(gold_change):.1f}%",
            'description': f"Gold trading at ${gold_data.get('price', 0):,.0f}/oz, significant move from previous close",
            'impact': 'high',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'ticker': 'GC=F'
        })

    # Company-specific signals
    for ticker in tickers:
        try:
            metrics = metrics_calc.get_all_metrics(ticker)
            risk = risk_scorer.calculate_composite_score(ticker)

            # Price movement signals
            daily_change = metrics.get('market', {}).get('daily_change_pct', 0)
            if abs(daily_change) > 5:
                signal_type = 'positive' if daily_change > 0 else 'negative'
                signals.append({
                    'type': signal_type,
                    'category': 'Price Movement',
                    'title': f"{ticker} {'Up' if daily_change > 0 else 'Down'} {abs(daily_change):.1f}%",
                    'description': f"Significant daily price movement. Current: ${metrics.get('market', {}).get('current_price', 0):.2f}",
                    'impact': 'high',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'ticker': ticker
                })

            # Runway alerts
            runway = metrics.get('cash', {}).get('runway_months', 0)
            if runway and runway < 6:
                signals.append({
                    'type': 'negative',
                    'category': 'Funding Alert',
                    'title': f"{ticker} Critical Runway Alert",
                    'description': f"Cash runway of only {runway:.0f} months. Immediate funding action likely required.",
                    'impact': 'critical',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'ticker': ticker
                })
            elif runway and runway < 12:
                signals.append({
                    'type': 'warning',
                    'category': 'Funding Watch',
                    'title': f"{ticker} Short Runway",
                    'description': f"Cash runway of {runway:.0f} months. Funding discussions likely in progress.",
                    'impact': 'medium',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'ticker': ticker
                })

            # Risk score alerts
            if 'error' not in risk:
                composite = risk.get('composite_score', 3)
                if composite < 2:
                    signals.append({
                        'type': 'warning',
                        'category': 'Risk Alert',
                        'title': f"{ticker} Elevated Risk Profile",
                        'description': f"Composite risk score of {composite:.1f}/5.0. Weakest: {risk.get('weakest_category', 'unknown').title()}",
                        'impact': 'high',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        'ticker': ticker
                    })

            # AISC margin alert
            project = metrics.get('project', {})
            margin = project.get('margin_per_oz', 0)
            if margin < 500:
                signals.append({
                    'type': 'warning',
                    'category': 'Margin Alert',
                    'title': f"{ticker} Thin Operating Margin",
                    'description': f"Operating margin of ${margin:.0f}/oz at current gold prices. Sensitive to gold decline.",
                    'impact': 'medium',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'ticker': ticker
                })

            # 52-week high/low proximity
            from_high = metrics.get('market', {}).get('from_52w_high_pct', 0)
            if from_high > -5:  # Within 5% of 52-week high
                signals.append({
                    'type': 'positive',
                    'category': 'Technical',
                    'title': f"{ticker} Near 52-Week High",
                    'description': f"Trading within {abs(from_high):.1f}% of 52-week high. Momentum positive.",
                    'impact': 'low',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'ticker': ticker
                })
            elif from_high < -40:  # More than 40% below high
                signals.append({
                    'type': 'warning',
                    'category': 'Technical',
                    'title': f"{ticker} Significant Drawdown",
                    'description': f"Trading {abs(from_high):.1f}% below 52-week high.",
                    'impact': 'medium',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'ticker': ticker
                })

        except Exception as e:
            signals.append({
                'type': 'warning',
                'category': 'System',
                'title': f"Error analyzing {ticker}",
                'description': str(e),
                'impact': 'low',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'ticker': ticker
            })

    # Sort by impact and timestamp
    impact_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    signals.sort(key=lambda x: (impact_order.get(x.get('impact', 'low'), 4), x.get('timestamp', '')))

    return signals


def render_signals_feed(tickers: List[str]):
    """Render the signals feed page"""

    st.markdown("## Signals Feed")
    st.markdown("Material changes and alerts requiring attention")

    # Generate signals
    with st.spinner("Scanning for signals..."):
        signals = generate_signals(tickers)

    # Summary stats
    col1, col2, col3, col4 = st.columns(4)

    critical_count = len([s for s in signals if s.get('impact') == 'critical'])
    high_count = len([s for s in signals if s.get('impact') == 'high'])
    warning_count = len([s for s in signals if s.get('type') == 'warning'])
    positive_count = len([s for s in signals if s.get('type') == 'positive'])

    with col1:
        st.metric("Critical", critical_count)
    with col2:
        st.metric("High Priority", high_count)
    with col3:
        st.metric("Warnings", warning_count)
    with col4:
        st.metric("Positive", positive_count)

    st.markdown("---")

    # Filter controls
    col1, col2, col3 = st.columns(3)

    with col1:
        filter_type = st.selectbox(
            "Signal Type",
            ["All", "Critical/High Only", "Warnings", "Positive"]
        )

    with col2:
        filter_ticker = st.selectbox(
            "Company",
            ["All"] + tickers
        )

    with col3:
        filter_category = st.selectbox(
            "Category",
            ["All"] + list(set(s.get('category', '') for s in signals))
        )

    # Apply filters
    filtered_signals = signals

    if filter_type == "Critical/High Only":
        filtered_signals = [s for s in filtered_signals if s.get('impact') in ['critical', 'high']]
    elif filter_type == "Warnings":
        filtered_signals = [s for s in filtered_signals if s.get('type') == 'warning']
    elif filter_type == "Positive":
        filtered_signals = [s for s in filtered_signals if s.get('type') == 'positive']

    if filter_ticker != "All":
        filtered_signals = [s for s in filtered_signals if s.get('ticker') == filter_ticker]

    if filter_category != "All":
        filtered_signals = [s for s in filtered_signals if s.get('category') == filter_category]

    st.markdown("---")

    # Display signals
    if not filtered_signals:
        st.info("No signals matching current filters")
    else:
        for signal in filtered_signals:
            signal_type = signal.get('type', 'info')
            impact = signal.get('impact', 'low')

            # Color coding
            if signal_type == 'positive':
                border_color = '#22c55e'
                bg_color = '#f0fdf4'
            elif signal_type == 'negative' or impact == 'critical':
                border_color = '#dc2626'
                bg_color = '#fef2f2'
            elif signal_type == 'warning':
                border_color = '#f97316'
                bg_color = '#fff7ed'
            else:
                border_color = '#3b82f6'
                bg_color = '#eff6ff'

            # Impact badge
            impact_badge = {
                'critical': '🔴 CRITICAL',
                'high': '🟠 HIGH',
                'medium': '🟡 MEDIUM',
                'low': '🟢 LOW'
            }.get(impact, '⚪ INFO')

            st.markdown(f"""
            <div style="background: {bg_color}; border-left: 4px solid {border_color}; border-radius: 8px; padding: 16px; margin: 8px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase;">
                        {signal.get('category', 'Signal')} | {signal.get('ticker', '')}
                    </span>
                    <span style="font-size: 0.75rem; font-weight: 600;">
                        {impact_badge}
                    </span>
                </div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #0f172a; margin-bottom: 4px;">
                    {signal.get('title', 'Signal')}
                </div>
                <div style="font-size: 0.9rem; color: #475569;">
                    {signal.get('description', '')}
                </div>
                <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 8px;">
                    {signal.get('timestamp', '')}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Signal statistics
    st.markdown("### Signal Summary")

    # By category
    category_counts = {}
    for signal in signals:
        cat = signal.get('category', 'Other')
        category_counts[cat] = category_counts.get(cat, 0) + 1

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**By Category**")
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            st.write(f"- {cat}: {count}")

    with col2:
        st.markdown("**By Company**")
        ticker_counts = {}
        for signal in signals:
            ticker = signal.get('ticker', 'Other')
            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1

        for ticker, count in sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True):
            st.write(f"- {ticker}: {count}")

    # Refresh button
    st.markdown("---")
    if st.button("Refresh Signals"):
        st.rerun()
