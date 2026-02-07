#!/usr/bin/env python3
"""
Junior Gold Intel Dashboard - Entry Point

Run with: streamlit run run_dashboard.py
"""
import os
import sys

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import and run the main app
from dashboard.app import main

if __name__ == "__main__":
    main()
