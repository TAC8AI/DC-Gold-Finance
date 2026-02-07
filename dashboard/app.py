"""
Junior Gold Intel Dashboard - Main Streamlit Application
"""
import streamlit as st
import yaml
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.pages.executive_summary import render_executive_summary
from dashboard.pages.company_comparison import render_company_comparison
from dashboard.pages.npv_sensitivity import render_npv_sensitivity
from dashboard.pages.capital_risk import render_capital_risk
from dashboard.pages.signals_feed import render_signals_feed
from dashboard.pages.about import render_about
from data_ingestion.gold_price_fetcher import GoldPriceFetcher


# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Junior Gold Intel | Decision Intelligence",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
def load_custom_css():
    """Load custom CSS styling"""
    css_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "styles",
        "custom.css"
    )
    try:
        with open(css_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Unable to load custom styles: {e}")


def load_config():
    """Load company configuration"""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config',
        'companies.yaml'
    )
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        st.error(f"Error loading config: {e}")
        return {}


def main():
    """Main application entry point"""

    # Load CSS
    load_custom_css()

    # Load configuration
    config = load_config()
    companies = config.get('companies', {})
    tickers = list(companies.keys())

    # Get gold price for header
    gold_fetcher = GoldPriceFetcher()
    gold_data = gold_fetcher.get_current_price()
    gold_price = gold_data.get('price', 2100)
    gold_change = gold_data.get('daily_change_pct', 0)

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-brand-card">
            <div class="sidebar-brand-title">⛏ Junior Gold Intel</div>
            <div class="sidebar-brand-sub">Decision Intelligence Platform</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Gold price display
        gold_change_class = "trend-up" if gold_change >= 0 else "trend-down"
        st.markdown(
            f"""
            <div class="gold-spot-card">
                <div class="gold-spot-label">Gold Spot</div>
                <div class="gold-spot-ticker">GC=F</div>
                <div class="gold-spot-price">${gold_price:,.0f}</div>
                <div class="gold-spot-change {gold_change_class}">{gold_change:+.1f}%</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("---")

        # Navigation
        st.markdown('<div class="sidebar-section-title">Navigation</div>', unsafe_allow_html=True)
        page = st.radio(
            "Select View",
            [
                "Executive Summary",
                "Company Comparison",
                "NPV & Sensitivity",
                "Capital & Risk",
                "Signals Feed",
                "About"
            ],
            index=2,
            label_visibility="collapsed"
        )

        if page != "NPV & Sensitivity":
            st.markdown("---")

            # Companies tracked
            st.markdown('<div class="sidebar-section-title">Companies Tracked</div>', unsafe_allow_html=True)
            for ticker in tickers:
                company = companies.get(ticker, {})
                company_name = company.get('name', ticker)
                st.markdown(
                    f"""
                    <div class="company-chip">
                        <span class="company-chip-ticker">{ticker}</span>
                        <span class="company-chip-name">{company_name}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.markdown("---")

        # Data refresh
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.caption("Data source: Yahoo Finance + model calculations")
        st.caption(f"Gold updated: {gold_data.get('fetch_time', 'N/A')[:16]}")
        st.caption("Junior Gold Intel v1.0")
        st.caption("Not Financial Advice")

    # --- MAIN CONTENT ---
    st.markdown(
        f"""
        <div class="app-banner">
            <div class="app-banner-label">Investor Decision Console</div>
            <div class="app-banner-title">Junior Gold Miner Decision Intelligence</div>
            <div class="app-banner-meta">Live gold: ${gold_price:,.0f} ({gold_change:+.1f}%)</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Render selected page
    if page == "Executive Summary":
        render_executive_summary(tickers)
    elif page == "Company Comparison":
        render_company_comparison(tickers)
    elif page == "NPV & Sensitivity":
        render_npv_sensitivity(tickers)
    elif page == "Capital & Risk":
        render_capital_risk(tickers)
    elif page == "Signals Feed":
        render_signals_feed(tickers)
    elif page == "About":
        render_about()


if __name__ == "__main__":
    main()
