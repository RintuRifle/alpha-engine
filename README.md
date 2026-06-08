# Quant Research Platform

A production-ready quantitative research and backtesting platform built with Python, SQLAlchemy, and Streamlit.

## Setup Instructions

1. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

4. **Run the Dashboard**:
   ```bash
   make run
   # OR
   streamlit run app/streamlit_app.py
   ```

## Architecture
- `src/`: Core logic (data fetching, strategies, backtesting engine, analytics)
- `tests/`: Unit tests for the core logic
- `app/`: Streamlit interactive dashboard
- `notebooks/`: Jupyter notebooks for exploratory data analysis
