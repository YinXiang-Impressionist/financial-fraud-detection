# Quantitative Forensic Accounting & Statistical Fraud Detection Whitepaper
### Deterministic Financial Statement Forensic Architecture for US Equities

<p align="left">
  <a href="FORENSIC_SCORING_METHODOLOGY.md"><img src="https://img.shields.io/badge/Language-English-blue?style=for-the-badge" alt="English"></a>
  <a href="FORENSIC_SCORING_METHODOLOGY_CN.md"><img src="https://img.shields.io/badge/语言-简体中文-red?style=for-the-badge" alt="简体中文"></a>
</p>

---

## Table of Contents
1. [Core Design Philosophy & Architectural Principles](#1-core-design-philosophy--architectural-principles)
2. [Composite Risk Scoring & Four-Tier Risk Spectrum](#2-composite-risk-scoring--four-tier-risk-spectrum)
3. [Four Core Mathematical & Econometric Models](#3-four-core-mathematical--econometric-models)
   - [3.1 Beneish 8-Variable M-Score Earnings Manipulation Index](#31-beneish-8-variable-m-score-earnings-manipulation-index)
   - [3.2 Modified Jones Model (Discretionary Accruals Residual)](#32-modified-jones-model-discretionary-accruals-residual)
   - [3.3 Altman Z-Score Distance-to-Default & Financial Distress](#33-altman-z-score-distance-to-default--financial-distress)
   - [3.4 Sloan Net Accrual Anomaly](#34-sloan-net-accrual-anomaly)
4. [Cross-Statement Statistical Decoupling Diagnostics](#4-cross-statement-statistical-decoupling-diagnostics)
5. [Deterministic Tri-Statement Forensic Auditing Rules](#5-deterministic-tri-statement-forensic-auditing-rules)
   - [5.1 Balance Sheet Forensics](#51-balance-sheet-forensics)
   - [5.2 Income Statement Manipulation Diagnostics](#52-income-statement-manipulation-diagnostics)
   - [5.3 Cash Flow Decoupling & Recycling Diagnostics](#53-cash-flow-decoupling--recycling-diagnostics)
6. [Official SEC Form 8-K Item 4.02 Restatement Architecture](#6-official-sec-form-8-k-item-402-restatement-architecture)
   - [6.1 Live Trading Track (Exponential Time-Decay Penalty)](#61-live-trading-track-exponential-time-decay-penalty)
   - [6.2 Quantitative & Academic Research Track (Permanent Ground Truth)](#62-quantitative--academic-research-track-permanent-ground-truth)
7. [Scoring Aggregation & Closed-Form Formulations](#7-scoring-aggregation--closed-form-formulations)

---

## 1. Core Design Philosophy & Architectural Principles

This forensic system is engineered specifically for **corporate financial statement fraud detection and quantitative forensic accounting**, grounded firmly on three immutable technical principles:

1. **Zero Noise & Zero Media/Headline Sentiment (100% Noise-Free)**:
   Soft business news such as "CFO resignation", "routine auditor rotation", or "press rumors" are strictly excluded. Executive transitions routinely occur for benign reasons (retirement, term expirations, career development); conflating managerial mobility with financial crime triggers severe false-positive penalties.
2. **Deterministic Mathematical & Econometric Verification**:
   The engine trusts only line-item accounting entries, cross-period difference vectors, statistical distribution laws, and econometric residuals. Every alert is mathematically explainable and auditable.
3. **Zero LLM / Zero Hallucination Dependency**:
   All algorithms run natively via vectorized linear algebra in NumPy, Pandas, and DuckDB columnar kernels. Single-ticker audit latency is under **0.1 ms**, and full-market scans across 10,000+ public companies complete in seconds with deterministic precision and zero token costs.

---

## 2. Composite Risk Scoring & Four-Tier Risk Spectrum

The engine synthesizes all detected anomalies into an integrated **0 to 100** Risk Score (`total_risk_score`):

| Score Range | Risk Tier | Indicator | Economic Significance & Forensic Audit Recommendation |
| :---: | :---: | :---: | :--- |
| **50 – 100** | **Red Critical** | `[Critical]` | Multiple severe anomalies breached simultaneously (e.g., Beneish manipulation + Jones abnormal accruals + cash/debt paradox or cash flow decoupling). Systemic earnings fraud or impending distress detected. **Immediate liquidation or mandatory short hedge.** |
| **30 – 49** | **Orange Warning** | `[Warning]` | Breaches primary econometric thresholds (e.g., aggressive revenue recognition, runaway receivables, or abnormal accruals). Indicates significant earnings management or aggressive accounting policies. Detailed footnote inspection required. |
| **15 – 29** | **Yellow Caution** | `[Caution]` | Isolated metrics drift beyond historical deciles (e.g., minor margin-turnover divergence or borderline liquidity buffer). Core fundamentals remain viable. Regular monitoring advised. |
| **0 – 14** | **Green Sound** | `[Sound]` | Clean tri-statement cross-articulation, robust operational cash flow backing, healthy accruals, and all econometric models remain comfortably within safe benchmark corridors. |

---

## 3. Four Core Mathematical & Econometric Models

### 3.1 Beneish 8-Variable M-Score Earnings Manipulation Index
The most widely cited earnings manipulation predictive model among forensic auditors, short sellers (e.g., Muddy Waters, Hindenburg Research), and academic finance:

#### Mathematical Formulation:
$$\begin{aligned}
M\text{-Score} = &-4.84 + 0.920 \times \text{DSRI} + 0.528 \times \text{GMI} + 0.404 \times \text{AQI} \\
&+ 0.892 \times \text{SGI} + 0.115 \times \text{DEPI} - 0.172 \times \text{SGAI} \\
&+ 4.037 \times \text{TATA} + 0.0327 \times \text{LVGI}
\end{aligned}$$

| Variable | Metric Name | Definition / Formula | Forensic Anomaly Implication |
| :--- | :--- | :--- | :--- |
| **DSRI** | Days Sales in Receivables Index | $\frac{\text{AR}_t / \text{Sales}_t}{\text{AR}_{t-1} / \text{Sales}_{t-1}}$ | $> 1$ indicates receivables growing faster than revenue (premature recognition or fictitious channel stuffing). |
| **GMI** | Gross Margin Index | $\frac{\text{GrossMargin}_{t-1}}{\text{GrossMargin}_t}$ | Deteriorating or erratic margins intensify incentives to manipulate earnings. |
| **AQI** | Asset Quality Index | $\frac{1 - (\text{CA}_t + \text{PPE}_t)/\text{TA}_t}{1 - (\text{CA}_{t-1} + \text{PPE}_{t-1})/\text{TA}_{t-1}}$ | $> 1$ indicates an increasing proportion of capitalized intangible assets, goodwill, or deferred charges. |
| **SGI** | Sales Growth Index | $\frac{\text{Sales}_t}{\text{Sales}_{t-1}}$ | Rapid revenue deceleration or aggressive growth surges create immense pressure to sustain valuation multiples. |
| **DEPI** | Depreciation Index | $\frac{\text{DeprRate}_{t-1}}{\text{DeprRate}_t}$ | $> 1$ indicates decelerating depreciation rates, extending asset lifespans to artificially inflate net income. |
| **SGAI** | Sales, General & Admin Index | $\frac{\text{SGA}_t / \text{Sales}_t}{\text{SGA}_{t-1} / \text{Sales}_{t-1}}$ | Disproportionate operating cost spikes or sudden declines signaling margin compression. |
| **LVGI** | Leverage Index | $\frac{\text{Liab}_t / \text{TA}_t}{\text{Liab}_{t-1} / \text{TA}_{t-1}}$ | Escalating financial leverage increases risk of covenant breach and window-dressing. |
| **TATA** | Total Accruals to Total Assets | $\frac{\text{NetIncome}_t - \text{CFO}_t}{\text{TA}_t}$ | Primary earnings quality gauge: net income devoid of operational cash backing. |

* **Decision Criterion**: If $M\text{-Score} > -1.78$, the firm is classified as a likely manipulator, incurring a **+25 points** penalty.

---

### 3.2 Modified Jones Model (Discretionary Accruals Residual)
The standard econometric methodology to decompose total accruals into non-discretionary (business-driven) accruals and discretionary accruals ($DA$):

#### Estimation Equation:
$$\frac{\text{Total Accruals}_t}{\text{Assets}_{t-1}} = \alpha_1 \left(\frac{1}{\text{Assets}_{t-1}}\right) + \alpha_2 \left(\frac{\Delta \text{Sales}_t - \Delta \text{AR}_t}{\text{Assets}_{t-1}}\right) + \alpha_3 \left(\frac{\text{PPE}_t}{\text{Assets}_{t-1}}\right) + \epsilon_t$$

* Where $\text{Total Accruals}_t = \text{Net Income}_t - \text{CFO}_t$;
* The regression residual $\epsilon_t \equiv DA$ captures **managerial discretionary earnings intervention achieved through accounting choices and accrual assumptions**.
* **Decision Criterion**: When $DA > 0.08$ (abnormal discretionary accruals exceed 8% of lagged total assets), a **+20 points** penalty is assigned.

---

### 3.3 Altman Z-Score Distance-to-Default & Financial Distress
Assesses systemic insolvency and bankruptcy probability:
$$Z = 1.2 X_1 + 1.4 X_2 + 3.3 X_3 + 0.6 X_4 + 0.999 X_5$$
* $X_1 = \text{Working Capital} / \text{Total Assets}$ (Short-term operational liquidity)
* $X_2 = \text{Retained Earnings} / \text{Total Assets}$ (Cumulative profitability)
* $X_3 = \text{EBIT} / \text{Total Assets}$ (Operating productivity of capital)
* $X_4 = \text{Market Value of Equity (or Book Equity)} / \text{Total Liabilities}$ (Financial leverage protection)
* $X_5 = \text{Sales} / \text{Total Assets}$ (Asset turnover velocity)
* **Decision Criterion**: When $Z < 1.81$ (Distress Zone), a **+20 points** penalty is assigned.

---

### 3.4 Sloan Net Accrual Anomaly
$$Sloan = \frac{\text{Net Income} - \text{CFO}}{\text{Total Assets}}$$
* **Decision Criterion**: When $Sloan > 0.10$ (accruals without cash realization exceed 10% of total assets), earnings persistence is statistically compromised, incurring a **+15 points** penalty.

---

## 4. Cross-Statement Statistical Decoupling Diagnostics

While fraudsters can falsify individual accounting line items, maintaining organic co-movement across related statement items is mathematically prohibitive:

1. **Revenue vs. Accounts Receivable Growth Scissors**:
   $$\Delta \text{AR}\% - \Delta \text{Sales}\% > 25\% \quad \text{and} \quad \Delta \text{AR} > \$10\text{M}$$
   * Triggers **+20 points** (aggressive credit terms, premature revenue recognition, or channel stuffing).
2. **Inventory Growth vs. COGS Expansion Decoupling**:
   $$\Delta \text{Inv}\% - \Delta \text{COGS}\% > 30\% \quad \text{and} \quad \Delta \text{Inv} > \$10\text{M}$$
   * Triggers **+20 points** (deferred cost recognition to inflate gross margin, or fictitious phantom inventory).
3. **Gross Margin Surge Counter to Collapsing Inventory Turnover**:
   $$(\text{GM}_t - \text{GM}_{t-1}) > 3\% \quad \text{and} \quad \frac{\text{Turnover}_t}{\text{Turnover}_{t-1}} < 0.80$$
   * Triggers **+20 points** (violates economic logic: declining inventory velocity accompanied by surging gross margins signals inventory overvaluation).
4. **Malignant Cash Flow Decoupling (Paper Wealth Syndrome)**:
   $$\text{Net Income} > 0 \quad \text{and} \quad \text{CFO} \le 0$$
   * Triggers **+25 points** (positive net profit accompanied by negative operating cash flow).
   * If $\text{CFO} / \text{Net Income} < 0.30$, triggers **+15 points**.

---

## 5. Deterministic Tri-Statement Forensic Auditing Rules

### 5.1 Balance Sheet Forensics
* **Simultaneous High Cash & High Debt (Restricted Cash Anomaly)**:
  * `Cash / Total Assets > 20%` and `Interest-Bearing Debt / Total Assets > 30%`;
  * Compounded by interest expenses eroding net income or cash yields $< 1\%$;
  * Triggers **+20 – 25 points** (fictitious reported cash or pledged unencumbered deposits).
* **Excessive Goodwill Overhang**:
  * `Goodwill / Equity > 50%` triggers **+25 points** (impending massive write-down risk);
  * `Goodwill / Equity > 30%` triggers **+15 points** (high impairment vulnerability).
* **Balance Sheet Insolvency (Negative Equity)**:
  * `Total Stockholders' Equity < 0` triggers **+30 points** (balance sheet insolvency).
* **Stalled Construction in Progress (CIP)**:
  * `CIP / Net PPE > 50%` triggers **+15 points** (delayed depreciation to prop up earnings or capital tunneling).
* **Other Receivables / Advances Tunneling Channels**:
  * `(Other Receivables + Advances) / Total Assets > 10%` triggers **+15 points** (related-party cash extraction).
* **Excessive R&D Capitalization**:
  * `R&D Capitalization Ratio > 25%` triggers **+15 points** (cost deferral).
* **Shadow Debt (Minority Interest Disconnect)**:
  * `Minority Interest / Total Equity > 40%`, yet `Minority Profit / Net Income < 5%` triggers **+20 points**.

### 5.2 Income Statement Manipulation Diagnostics
* **Gross Invoicing Pass-Through Scheme**:
  * High revenue ($> \$1\text{B}$) with negligible net margins ($< 0.5\%$);
  * Triggers **+15 points** (commodity trading pass-through inflation without actual economic control).
* **Core Operating Losses Masked by Non-Operating Windfalls**:
  * Operating income is negative, while net income appears positive via non-operating gains;
  * Triggers **+20 points** (loss of core profitability masked by non-recurring transactions).
* **Pre-Crash Capital Tunneling via Surge Dividends**:
  * Net income declines ($\Delta\text{NetIncome} < 0$), yet total dividends and share buybacks exceed $50\%$ of net income;
  * Triggers **+15 points** (insiders draining corporate liquidity prior to operational deterioration).
* **Fourth-Quarter Big-Bath Bathing**:
  * First three quarters report cumulative profitability, but Q4 reports an abrupt, massive loss ($< -\$30\text{M}$) wiping out $> 80\%$ of annual gains;
  * Triggers **+20 points** (concentrating write-downs to clear executive balance sheets).

### 5.3 Cash Flow Decoupling & Recycling Diagnostics
* **Mirror Hedging / Cash Recycling Loop**:
  * Massive investing cash outflows closely mirror operating cash inflows (ratio within $0.85 – 1.15$);
  * Triggers **+20 points** (funds cycled out through acquisitions/capex and laundered back as sales receipts).
* **Chronic Free Cash Flow Drain with Debt Rollover**:
  * Free Cash Flow (FCF) bleeding ($< -\$50\text{M}$) completely financed by external debt issuance;
  * Triggers **+15 points** (Ponzi liquidity structure).

---

## 6. Official SEC Form 8-K Item 4.02 Restatement Architecture

For official Big-R restatements reported under SEC Form 8-K Item 4.02 ("Non-Reliance on Previously Issued Financial Statements"), the engine provides dual-track processing:

### 6.1 Live Trading Track (Exponential Time-Decay Penalty)
* **Recent Restatements ($\le 365$ days)**:
  * Sensitive high-risk period with recurring class-action litigation and subsequent restatement waves; penalizes **+20 points**.
* **Historical Restatements (1 – 3 years ago)**:
  * Remediation observation period; penalizes **+5 points**.
* **Cleared Historical Restatements (> 3 years ago)**:
  * Remediated clean records; penalizes **0 points** (eliminating false-positive penalties on successfully turned-around companies).

### 6.2 Quantitative & Academic Research Track (Permanent Ground Truth)
* Irrespective of elapsed time, any company with confirmed restatements is permanently tagged:
  * `target_is_restated_fraud = True / False`
* **Serves as the golden ground-truth label for quantitative alpha factor backtests, academic empirical papers, and supervised machine learning classifiers**.

---

## 7. Scoring Aggregation & Closed-Form Formulations

The integrated risk score is evaluated via deterministic aggregation:

$$\text{Raw Score} = \sum \text{Models Penalty} + \sum \text{Decoupling Penalty} + \sum \text{Statements Penalty} + \text{Restatement Penalty}$$

$$\text{Total Risk Score} = \min(100, \text{Raw Score})$$

* **Columnar Vectorized Execution**: All scoring logic is compiled into high-throughput NumPy and Pandas vector operations.
* **Extreme Throughput**: 10,000 corporate filings are evaluated in **0.033 seconds**, producing transparent, interpretable, and auditable diagnostic reports.
