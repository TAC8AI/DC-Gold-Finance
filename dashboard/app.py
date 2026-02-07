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
    css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        * {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            color: #1a202c;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%);
            border-right: 1px solid #e2e8f0;
        }

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] label {
            color: #2d3748 !important;
        }

        h1 {
            color: #1e40af !important;
            font-weight: 700 !important;
            font-size: 2.5rem !important;
            margin-bottom: 0.5rem !important;
        }

        h2, h3 {
            color: #1e3a8a !important;
            font-weight: 600 !important;
        }

        div[data-testid="metric-container"] {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #cbd5e1;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }

        div[data-testid="metric-container"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            border-color: #60a5fa;
        }

        div[data-testid="metric-container"] label {
            color: #64748b !important;
            font-weight: 600 !important;
            font-size: 0.875rem !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        div[data-testid="metric-container"] [data-testid="stMetricValue"] {
            color: #0f172a !important;
            font-weight: 700 !important;
            font-size: 2rem !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 4px;
            gap: 4px;
        }

        .stTabs [data-baseweb="tab"] {
            color: #475569;
            border-radius: 6px;
            font-weight: 600;
        }

        .stTabs [aria-selected="true"] {
            background-color: #3b82f6 !important;
            color: white !important;
        }

        .stButton button {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            font-weight: 600;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            transition: all 0.3s;
            box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3);
        }

        .stButton button:hover {
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            transform: translateY(-1px);
        }

        .streamlit-expanderHeader {
            background-color: #ffffff;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            color: #1e293b !important;
            font-weight: 600;
        }

        .npv-box {
            background: linear-gradient(135deg, #ffffff 0%, #f0f4f8 100%) !important;
            padding: 40px !important;
            border-radius: 20px !important;
            border: 4px solid #3b82f6 !important;
            box-shadow: 0 20px 60px rgba(59, 130, 246, 0.2) !important;
            text-align: center !important;
            margin: 30px 0 !important;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


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
        st.markdown("# ⛏️ Junior Gold Intel")
        st.markdown("*Decision Intelligence Platform*")

        st.markdown("---")

        # Gold price display
        st.markdown("### Gold Spot")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("GC=F", f"${gold_price:,.0f}", f"{gold_change:+.1f}%")

        st.markdown("---")

        # Navigation
        st.markdown("### Navigation")
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
            label_visibility="collapsed"
        )

        st.markdown("---")

        # Companies tracked
        st.markdown("### Companies Tracked")
        for ticker in tickers:
            company = companies.get(ticker, {})
            st.markdown(f"**{ticker}** - {company.get('name', ticker)[:20]}")

        st.markdown("---")

        # Data refresh
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.caption("Junior Gold Intel v1.0")
        st.caption("Not Financial Advice")

    # --- MAIN CONTENT ---
    st.title("⛏️ Junior Gold Miner Decision Intelligence")

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
