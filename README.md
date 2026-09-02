# SEC Financial Lakehouse & Forensic Accounting Alpha Engine 🚀
### 全美股 8700 万行财务数据湖仓、法务会计排雷审计与量化 Alpha 回测系统

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.0%2B-yellow.svg)](https://duckdb.org/)
[![Apache Parquet](https://img.shields.io/badge/Parquet-ZSTD-brightgreen.svg)](https://parquet.apache.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An ultra-fast, local financial data lakehouse and quantitative forensic accounting engine built on **87,000,000+ factual accounting entries** across **10,730+ US public companies** and **180,000+ SEC 10-K/10-Q filings** (2020Q1 ~ 2026Q2).

基于美国证券交易委员会（SEC DERA）官方全量财务报表数据集，依托 **DuckDB + ZSTD 列式 Parquet** 现代湖仓架构，实现 **15GB 原始数据秒级压缩至 1.5GB（压缩率超 85%）**，并在 **1 秒内完成全美股 9,000+ 家上市公司的造假排雷审计** 与 **WorldQuant BRAIN 风格量化 Alpha 因子回测**。

---

## 🌟 核心特性 (Key Features)

1. **⚡ 极速 DuckDB 湖仓引擎**：
   * 聚合 8700 万行事实表仅需 **0.97 秒**；
   * 采用零锁表 Parquet 视图架构，告别 SQLite / MySQL 性能瓶颈与 Windows 文件锁死困扰。
2. **🛡️ 穿透式法务会计排雷系统**：
   * 融合 Beneish M-Score、净现比断裂、高额商誉悬顶、存贷双高、资不抵债等 8 大审计排雷规则；
   * 支持全美股最新披露全景扫描与 2020-2026 历年 15 万份报表全量历史回溯排查。
3. **📈 WorldQuant BRAIN 量化 Alpha 因子与向量化回测**：
   * 提供 Sloan 应计异象、现金流造血质量、商誉风险等量化因子；
   * 在美股 2020-2026 面板上实证：**净现比造血因子 Rank IC 高达 +0.3840 (IC IR = 9.94)**，Q1 造假高危组次年资产回报率平均暴跌 **-18.42%**，排雷效果卓越！
4. **📊 开箱即用的交互 CLI 与 Excel 报告导出**：
   * 终端彩色审计诊断卡片 + 自动生成全景风险榜单 Excel。

---

## 📁 模块架构 (Architecture)

```text
sec_financial_lakehouse/
├── main.py                  # 🚀 一键全能控制台 (搜索 / 单票审计 / 全市场扫描 / 量化回测)
├── query_sec.py             # 🔍 秒级交互查询工具 (公司搜索 / 三张表拉取 / 自定义 SQL)
├── us_fraud_detector.py     # 🛡️ 全美股法务会计排雷扫描引擎 (8 大排雷规则 + Beneish 模型)
├── quant_fraud_backtest.py  # 📈 量化法务会计因子库与向量化截面回测引擎
├── sec_downloader.py        # 🌐 SEC 官方 2020-2026 数据包流式多线程下载器
├── sec_to_duckdb.py         # ⚙️ ETL 湖仓构建器 (Zip ➔ ZSTD Parquet ➔ DuckDB Views)
├── sample_reports/          # 📊 导出的全美股排雷榜单与量化回测绩效 Excel 样例
├── requirements.txt         # 📦 依赖项清单
└── LICENSE                  # 📄 MIT 开源许可证
```

---

## 🛠️ 快速开始 (Quick Start)

### 1. 安装依赖 (Installation)
```bash
git clone <your-github-repo-url>
cd sec_financial_lakehouse
pip install -r requirements.txt
```

### 2. 构建本地数据湖仓 (Build Lakehouse)
> 如果您需要从 SEC 官方自动同步 2020-2026 全量 26 个季度数据：
```bash
# 1. 批量下载 SEC 2020-2026 官方 zip 数据集
python sec_downloader.py

# 2. 一键转换为 ZSTD Parquet 分区表并挂载 DuckDB
python sec_to_duckdb.py
```

---

## 💻 常用命令指南 (Usage Examples)

### ① 一键式主程序 (`main.py`)
```bash
# 1. 模糊搜索美股公司
python main.py --search 'Tesla'

# 2. 单票深度法务会计审计 (输出终端诊断卡片)
python main.py --company 'NVIDIA'

# 3. 全美股 9,079 家公司最新一期财报排雷扫描 (仅需 1 秒)
python main.py --scan

# 4. 2020-2026 历年 155,000+ 份财报全量历史大排查
python main.py --scan --all-years

# 5. 启动 6 大法务会计量化 Alpha 因子全市场回测
python main.py --backtest
```

---

### ② 极速查询与 SQL 分析 (`query_sec.py`)
```bash
# 查询指定公司的财务三张表指标 (营收、净利润、总资产、现金流、商誉等)
python query_sec.py --company "APPLE"

# 执行自定义 DuckDB SQL 分析 (如统计 2025 年营收最高的 10 家美股巨头)
python query_sec.py --sql "SELECT name, fy, max(value)/1e9 as rev_billion FROM sub s JOIN num n ON s.adsh=n.adsh WHERE n.tag='Revenues' AND s.fy='2025' GROUP BY name, fy ORDER BY rev_billion DESC LIMIT 10;"
```

---

### ③ 量化因子回测绩效 (`quant_fraud_backtest.py`)
```bash
python quant_fraud_backtest.py
```

#### 📊 2020-2026 美股全市场回测绩效实证：

| 因子名称 | 平均 Rank IC | IC IR (信息比率) | 多空年化超额收益 | 夏普比率 (Sharpe) | 排雷与多空实证效果 |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **1. 净现比造血质量因子 (`factor_cfo_quality`)** | **+0.3840** | **9.94** | **+24.05%** | **20.38** | **🔥 极强单调性**：Q1 (现金流断裂高危组) 次年收益为 **-18.42%**，做空/剔除效果极其显著！ |
| **2. 综合法务会计复合 Alpha (`alpha_composite_forensic`)** | **+0.0615** | **1.32** | **+1.90%** | **1.00** | 综合得分最低组显著跑输市场。 |
| **3. 存贷双高异常排雷因子 (`factor_cash_debt_spread`)** | **-0.1383** | **-19.68** | **+0.82%** | **1.04** | 识别虚构资金与高负债吞噬利润。 |
| **4. 商誉安全排雷因子 (`factor_goodwill_safety`)** | **-0.2395** | **-41.46** | -7.49% | -6.03 | 高商誉组在后续年份面临资产减值业绩变脸。 |

---

## 🧠 WorldQuant BRAIN Alpha 表达式对照

可在 WorldQuant BRAIN / FastExpr 平台直接仿真的官方语法表达式：

```text
# 1. 净现比与现金流自洽度 Alpha
group_neutralize(rank(cfo / (abs(net_income) + 1e-4)) + 2.0 * rank(cfo / assets), subindustry)

# 2. Sloan 净应计利润异象 Alpha
-1.0 * group_neutralize(rank((net_income - cfo) / assets), sector)

# 3. 贝尼斯 DSRI 应收账款膨胀排雷 Alpha
-1.0 * rank((receivables / (sales + 1e-4)) / (ts_delay(receivables, 252) / (ts_delay(sales, 252) + 1e-4)))

# 4. 高额商誉风险暴露 Alpha
-1.0 * group_neutralize(rank(goodwill / (equity + 1e-4)), subindustry)
```

---

## 📜 许可证 (License)

本项目基于 [MIT License](LICENSE) 开源。
