from setuptools import setup, find_packages

setup(
    name="quant_research_platform",
    version="1.0.0",
    description="A modular, production-ready quant research and backtesting platform.",
    author="Akshit Kumar Tiwari",
    url="https://github.com/RintuRifle/alpha-engine",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "pandas",
        "numpy",
        "yfinance",
        "streamlit",
        "quantstats",
        "sqlalchemy",
        "pyyaml",
        "python-dotenv",
        "tenacity",
        "plotly",
    ],
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Topic :: Office/Business :: Financial :: Investment",
        "Intended Audience :: Financial and Insurance Industry",
    ],
)
