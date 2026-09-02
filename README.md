# SEC Financial Lakehouse & Forensic Accounting Alpha Engine 🚀
### 全美股财务数据湖仓、数理法务排雷审计与量化 Alpha 回测系统

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![edgar-tools](https://img.shields.io/badge/edgar--tools-5.55%2B-orange.svg)](https://github.com/edgarminers/edgatools)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.0%2B-yellow.svg)](https://duckdb.org/)
[![Apache Parquet](https://img.shields.io/badge/Parquet-ZSTD-brightgreen.svg)](https://parquet.apache.org/)
[![Performance](https://img.shields.io/badge/Speed-280%2C000%20filings%2Fsec-red.svg)](#)
[![Zero-LLM](https://img.shields.io/badge/Logic-100%25%20Deterministic%20Pure%20Math-purple.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An ultra-fast, local financial data lakehouse and quantitative forensic accounting engine built on **SEC official filings** across **10,000+ US public companies**.

基于美国证券交易委员会（SEC EDGAR & DERA）官方全量财务数据，依托 **edgar-tools + DuckDB + ZSTD Parquet** 现代技术栈，实现：
1. **在线秒级穿透**：输入任意美股代码（如 `NVDA`），秒级直连 SEC 抽取财报三张表、8-K 重大重述（带时效衰减与科研真值）、10-K 内控缺陷；
2. **纯数理计量排雷**：彻底摒弃新闻与人事舆情噪音，基于修正琼斯模型（Modified Jones DA）、贝尼斯 Beneish M-Score、奥特曼 Altman Z-Score、Sloan 净应计异象与跨科目统计背离度，提供确定性的“侦探级（Detective）”财务造假排雷评分（0~100 分）；
3. **极速离线湖仓**：以 **280,000+ 份报表/秒** 的向量化吞吐量，在数秒内完成全美股 18 万份历史申报大排查；
4. **全自动生命周期管理**：`main.py` 内置智能检测，**已有数据 100% 自动跳过，免重复下载与重复构建**，缺失数据全自动断点补齐。

---

## 🌟 核心特性 (Key Features)

### 1. 纯数理统计与计量造假侦测 (Detective Statistical Forensic)
* **拒绝新闻舆情假阳性**：彻底剔除 CFO 离职、常规换所等软性公关新闻，专注于报表底层数字的数学反常；
* **修正琼斯模型 (Modified Jones Model)**：计量回归剥离正常应计，直接捕捉管理层人为跨期粉饰的可操纵应计残差 $DA$（$DA > 0.08$ 触发预警）；
* **贝尼斯 8 变量操纵指数 (Beneish M-Score)**：严密追踪 $DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA$，突破 $-1.78$ 阈值判定系统性操纵；
* **奥特曼破产距离 (Altman Z-Score)**：连续度量企业财务危机与违约破产距离（$Z < 1.81$ 红色危机区）；
* **跨科目统计背离度 (Statistical Decoupling)**：捕捉应收-营收增速严重脱节（$>25\%$）、存货-成本结转背离（$>30\%$）、毛利率逆势走高与存货周转骤降反常背离、净现比恶性断裂。

### 2. 双轨制 8-K 重述 (Item 4.02) 机制
* **实盘排雷（时效衰减）**：1 年内刚重述扣 **+20分**（连环暴雷敏感期）；1~3 年扣 **+5分**（整改观察期）；超过 3 年历史问题已出清，**0 分（不扣分、不误杀）**；
* **学术科研（黄金真值）**：无论何时重述，均永久标记 `target_is_restated_fraud = True`，专供多空回测与机器学习模型作为 100% 确凿的 Ground Truth 训练样本。

### 3. 全自动化数据生命周期管理 (`main.py`)
* `main.py` 统管单票、批量、全市场扫描、回测与下载构建全流程；
* **智能跳过（Smart Skip）**：若本地已存在完整 DuckDB 湖仓，秒级直接使用，**不产生任何多余网络开销与下载**；
* **断点续传（Breakpoint Resume）**：每个季度 zip 文件独立校验，已下载完好的季度自动秒级跳过（3000+ 季度/秒），仅下载缺失部分。

### 4. 量化法务会计 Alpha 因子实证回测
* 提供现金流造血质量、Sloan 应计异象、商誉安全排雷等 WorldQuant BRAIN 风格因子；
* 全美股回测实证：**净现比造血因子 Rank IC 高达 +0.3840 (IC IR = 9.94)**，Q1 造假高危组次年资产回报率平均暴跌 **-18.42%**。

---

## 📁 项目工程架构 (Project Structure)

```text
sec_financial_lakehouse/
│
├── main.py                            # 🚀 一键全能控制台 (在线单票排雷 / 股票池批量体检 / 离线全市场大扫描)
├── requirements.txt                   # 📦 Python 依赖环境清单 (含 edgartools, duckdb 等)
├── README.md                          # 📖 项目介绍与快速上手指南
├── FORENSIC_SCORING_METHODOLOGY.md   # 🏛️ 法务排雷评分与数理统计模型白皮书
├── LICENSE                            # 📄 MIT 开源许可证
├── .gitignore                         # 🙈 Git 忽略配置 (自动排除大型数据集与临时 Excel)
│
├── forensic_engine/                   # 🧠 [核心] 纯代码法务排雷算法与计量模型
│   ├── evaluator.py                   # 综合评分与四级风险等级判定总控
│   ├── tag_mapping.py                 # 统一会计科目映射 (US-GAAP / IFRS / A股)
│   ├── models/                        # 纯数理统计模型 (Beneish, Modified Jones, Altman, Benford, Decoupling)
│   └── rules/                         # 三张表穿透规则 (资产负债表, 利润表, 现金流量表, 8-K重述)
│
├── pipelines/                         # 🌐 [数据通道] 统一数据获取引擎
│   ├── edgar_pipeline.py              # 基于 edgar-tools 的 SEC 在线秒级多维穿透抽取
│   └── lakehouse/                     # [可选] 离线 DuckDB 大数据湖仓构建模块
│       ├── sec_downloader.py          # DERA 批量数据包下载器 (带完整性校验与断点跳过)
│       ├── sec_to_duckdb.py           # DuckDB 湖仓建表与 Parquet 转换
│       ├── query_sec.py               # 湖仓本地 SQL 检索
│       └── us_fraud_detector.py       # 湖仓批量向量化排雷
│
├── backtest/                          # 📈 [量化研究] Alpha 因子回测引擎
│   └── quant_fraud_backtest.py        # 6 大法务会计因子多空绩效回测
│
├── tests/                             # 🧪 [测试套件] 自动化测试与性能基准压测
│   ├── test_forensic_engine.py        # 核心算法与 10,000 条报表向量化性能压测 (28万份/秒)
│   └── test_edgar_pipeline.py         # 真实美股在线穿透测试 (NVDA, AAPL)
│
└── sample_reports/                    # 📊 导出的全美股排雷榜单与自选股诊断 Excel 样例
```

---

## 🛠️ 快速开始 (Quick Start)

### 1. 安装依赖环境
```bash
git clone <your-repo-url>
cd sec_financial_lakehouse
pip install -r requirements.txt
```

### 2. 交互式控制台模式 (最推荐：无需记忆任何繁琐参数)
直接在终端运行 `python main.py`，系统将自动弹出交互式菜单，输入数字编号并按提示输入代码即可：
```bash
python main.py
```

### 3. 在线单票多维深度排雷 (命令行直连模式)
秒级直连 SEC 官方，抓取最新连续两期财报、8-K 重大重述与内控审查，并运行纯数理模型打分：
```bash
python main.py --ticker NVDA
# 或
python main.py --ticker TSLA
```

### 3. 自选股股票池批量在线排雷并导出 Excel
一键排查一组自选股，自动评估打分并生成结构化 Excel 排雷榜单：
```bash
python main.py --batch "AAPL,NVDA,TSLA,MSFT,BABA" --output "./我的自选股法务排雷榜单.xlsx"
```

### 4. 本地数据湖仓管理 (全自动检测，已有数据智能跳过)
```bash
# 检查本地湖仓完整性与数据行数
python main.py --check-data

# 批量下载/补齐 SEC 官方历史报表数据 (已存在的文件秒级自动跳过)
python main.py --download

# 将已下载 zip 转换为 Parquet 并挂载 DuckDB 视图
python main.py --build
```

### 5. 全美股全市场排雷大扫描 (以公司为核心主键)
系统自动检查本地数据，**若已有完整数据直接使用，无需重复下载**；若未就绪将全自动触发整备。
导出的 Excel 具备直白透彻的**诊断说明与分条排雷 Notes**，并根据扫描对象与时间**智能动态命名**（如 `美股上市公司排雷榜单_2023-2026历年全景_20260903_0336.xlsx`）：
* **直白成因 Notes**：不仅输出量化评分，更分条列出 `排雷诊断结论` 与 `具体风险成因与证据说明(Notes)`（例如：Beneish 模型超标涉嫌虚构收入、修正琼斯 DA 跨期估计粉饰、净现比断裂、Altman 破产危机、存货滞销积压等）；
* **自适应工作表架构**：
  * **历年全量大排查模式 (`--all-years`)**：
    * **Sheet 1: `公司历年穿透明细(2016-2026)`** —— 同一家公司的跨年度历史 10-K/10-Q 紧挨连续排列，时间倒序完整展现跨期 10 年演变；
    * **Sheet 2: `美股上市公司排雷总榜`** —— 每家公司独立一行，展示最新风险分、历史最高风险与最新财务；
    * **Sheet 3: `高危操纵关注名单`** —— 提取综合风险 $\ge 50$ 分的极危重点排查企业；
  * **最新财年扫描模式**：Sheet 1 为公司排雷总榜，Sheet 2 为穿透明细，Sheet 3 为高危关注名单。

```bash
# 全美股所有公司最新一期报表秒级大扫描 (输出 Top 风险排行并保存 Excel)
python main.py --scan

# 2016-2026 历年跨 10 年完整历史申报记录全量大排查 (自动检测并提示补齐历史数据包)
python main.py --scan --all-years
```

### 6. 法务会计量化 Alpha 因子全市场回测
```bash
python main.py --backtest
```

### 7. 运行自动化测试套件
```bash
# 验证核心算法精度与 10,000 份报表向量化基准压测
python tests/test_forensic_engine.py

# 验证 SEC 官方接口与真实股票在线抓取
python tests/test_edgar_pipeline.py AAPL
```

---

## 🏛️ 详细评分逻辑与技术白皮书

完整的数学公式推导、变量定义、扣分细则与实证依据，请参阅技术白皮书：
👉 [**`FORENSIC_SCORING_METHODOLOGY.md`**](FORENSIC_SCORING_METHODOLOGY.md)

---

## 📄 许可协议 (License)

本项目采用 [MIT 许可证](LICENSE) 开源。
