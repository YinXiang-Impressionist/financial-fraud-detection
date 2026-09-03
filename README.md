# SEC Financial Lakehouse & Quantitative Forensic Fraud Detection Engine 🚀
### Ultra-Fast US Stock Financial Lakehouse & Deterministic Forensic Audit Engine

[English](README.md) | [简体中文](README_CN.md)

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![edgar-tools](https://img.shields.io/badge/edgar--tools-5.55%2B-orange.svg)](https://github.com/edgarminers/edgatools)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.0%2B-yellow.svg)](https://duckdb.org/)
[![Apache Parquet](https://img.shields.io/badge/Parquet-ZSTD-brightgreen.svg)](https://parquet.apache.org/)
[![Performance](https://img.shields.io/badge/Speed-280%2C000%20filings%2Fsec-red.svg)](#)
[![Zero-LLM](https://img.shields.io/badge/Logic-100%25%20Deterministic%20Pure%20Math-purple.svg)](#)
[![CI Matrix](https://github.com/your-repo/sec_financial_lakehouse/actions/workflows/ci.yml/badge.svg)](https://github.com/your-repo/sec_financial_lakehouse/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An ultra-fast, local financial data lakehouse and quantitative forensic accounting engine built directly on **official SEC EDGAR & DERA filings** covering **10,000+ US public companies**.

Powered by **edgar-tools + DuckDB + ZSTD Parquet**, this project delivers:
1. **Sub-second Online Extraction**: Inspect any ticker (e.g. `NVDA`, `AAPL`) in seconds by directly extracting financial statements, 8-K restatements (with exponential time-decay penalties and research ground truth), and 10-K internal control weaknesses.
2. **Pure Mathematical Forensic Audit**: Free of NLP/news sentiment noise. Driven by Modified Jones Model ($DA$), Beneish 8-variable $M$-Score, Altman $Z$-Score, Sloan Net Accrual anomaly, and cross-statement decoupling metrics (0–100 risk score).
3. **High-Throughput Offline Lakehouse**: Scan over 180,000 historical SEC quarterly filings in seconds at **280,000+ filings/sec** via vectorized columnar execution.
4. **Automated Lifecycle & Smart Caching**: `main.py` skips already downloaded/built data in 0 ms, with seamless breakpoint resuming.

---

## 🌟 Key Features

### 1. Detective Statistical Forensic Models (Zero Sentiment Noise)
* **Modified Jones Model**: Separates nondiscretionary accruals from discretionary accruals ($DA$) to catch managerial cross-period earnings manipulation ($DA > 0.08$ triggers warning).
* **Beneish 8-Variable M-Score**: Tracks $DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA$. Identifies systematic manipulation when $M > -1.78$.
* **Altman Z-Score**: Evaluates continuous distance-to-default and financial distress ($Z < 1.81$ red alert).
* **Cross-Statement Statistical Decoupling**: Catches extreme gaps between revenue growth and accounts receivable ($>25\%$), inventory growth vs. cost of goods sold ($>30\%$), diverging gross margins vs. plunging inventory turnover, and negative operating cash flows despite positive net income.
* **Financial Sector Awareness**: Automatically recognizes banking, insurance, and brokerage institutions (SIC 6000–6999), providing industry-specific forensic notices.

### 2. Dual-Track Form 8-K Restatement (Item 4.02) Architecture
* **Live Trading Track (Time Decay Penalty)**: Big-R restatements filed within 1 year add **+20 points**; restatements 1–3 years ago add **+5 points**; cleared historical restatements (>3 years) incur **0 penalty** (no false positives for healthy turnarounds).
* **Academic/Quant Research Track (Ground Truth)**: Irrespective of timing, permanently flags `target_is_restated_fraud = True` as verified ground-truth labels for supervised machine learning and long/short factor backtesting.

---

## 📁 Architecture

```text
sec_financial_lakehouse/
│
├── main.py                            # 🚀 All-in-one console (Interactive CLI, Online audit, Batch, Offline scan)
├── pyproject.toml                     # 📦 Modern Python packaging (PEP 517/621, pip installable)
├── requirements.txt                   # 📦 Runtime dependencies
├── README.md                          # 📖 Primary English documentation
├── README_CN.md                       # 📖 Complete Chinese documentation
├── FORENSIC_SCORING_METHODOLOGY.md   # 🏛️ Full mathematical scoring methodology
├── LICENSE                            # 📄 MIT License
├── .gitignore                         # 🙈 Git ignore rules
│
├── forensic_engine/                   # 🧠 Core deterministic forensic engine & models
│   ├── evaluator.py                   # Central evaluator (Single-ticker & Vectorized dataframe)
│   ├── tag_mapping.py                 # US-GAAP / IFRS accounting taxonomy normalizer
│   ├── models/                        # Mathematical models (Beneish, Jones DA, Altman, Benford)
│   └── rules/                         # Forensic rules (Balance sheet, Income, Cash flow, 8-K)
│
├── pipelines/                         # 🌐 Data channels & Lakehouse
│   ├── edgar_pipeline.py              # Real-time SEC EDGAR extractor via edgar-tools
│   └── lakehouse/                     # Offline SEC DERA DuckDB Lakehouse
│       ├── sec_downloader.py          # Bulk dataset downloader with checksums
│       ├── sec_to_duckdb.py           # Parquet converter and DuckDB table loader
│       ├── query_sec.py               # Fast local SQL query engine
│       └── us_fraud_detector.py       # Full-market vectorized forensic screener
│
├── examples/                          # 💡 Case studies & historical showcases
│   └── case_study_fraud_showcase.py   # Historical fraud case study (Enron vs. Tech giant)
│
├── tests/                             # 🧪 Test suite (unittest & pytest compatible)
│   ├── test_forensic_engine.py        # Core model tests & 10,000-filing benchmark
│   └── test_edgar_pipeline.py         # Live SEC connection & integration test
│
└── sample_reports/                    # 📊 Sample diagnostic Excel outputs & backtest reports
```

---

## 🛠️ Quick Start

### 1. Installation

```bash
git clone https://github.com/your-repo/sec_financial_lakehouse.git
cd sec_financial_lakehouse

# Install runtime dependencies
pip install -r requirements.txt

# Or install in editable mode with dev dependencies
pip install -e ".[dev]"
```

> [!TIP]
> **SEC EDGAR Compliance**: The SEC requires a custom User-Agent format: `Name AdminContact@domain.com`.
> Set your identity via environment variables:
> ```bash
> # Linux / macOS
> export EDGAR_IDENTITY="YourName your_email@domain.com"
> # Windows PowerShell
> $env:EDGAR_IDENTITY="YourName your_email@domain.com"
> ```

### 2. Instant Single-Ticker Audit (Zero local download needed ⚡)

```bash
python main.py --ticker NVDA
# Or test another ticker
python main.py --ticker TSLA
```

### 3. Interactive Menu Mode (Recommended for newcomers)

```bash
python main.py
```
A visual menu will guide you through all features without requiring command-line flags.

### 4. Batch Screener for Watchlists (Dual output: Excel + Markdown)

```bash
python main.py --batch "AAPL,NVDA,TSLA,MSFT,BABA" --output "./my_watchlist_audit.xlsx"
# Automatically generates ./my_watchlist_audit_summary.md as well!
```

### 5. Historical Fraud Case Study Benchmark

```bash
python examples/case_study_fraud_showcase.py
```

### 6. Run Test Suite

```bash
# Using native unittest runner
python -m unittest discover tests

# Using pytest
pytest tests/
```

---

## 🏛️ Mathematical Methodology

For complete mathematical derivations, variable definitions, and econometric justifications, please refer to:
👉 [**`FORENSIC_SCORING_METHODOLOGY.md`**](FORENSIC_SCORING_METHODOLOGY.md)

---

## ⚖️ Disclaimer

* **Not Financial Advice**: This software is built for educational, academic, and quantitative forensic research purposes only. None of the risk scores, classifications, or findings constitute investment advice or buy/sell recommendations.
* **SEC Fair Access Compliance**: Users must comply with the SEC Fair Access Policy, maintaining request frequencies below 10 requests per second and providing a valid User-Agent identifier.

---

## 📄 License

This project is open-sourced under the [MIT License](LICENSE).
