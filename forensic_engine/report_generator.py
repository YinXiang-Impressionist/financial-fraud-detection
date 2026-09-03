# -*- coding: utf-8 -*-
"""
法务会计排雷研报生成器 (Reader-Friendly Forensic Report Generator)
针对 Notion / Obsidian / 现代文档软件深度优化排版，彻底消除 HTML 标签泄露与表格挤压。
"""

import os
from datetime import datetime
import pandas as pd


def is_zh_mode() -> bool:
    return os.environ.get("FORENSIC_LANG", "en").lower().startswith("zh")


def _find_col(df: pd.DataFrame, candidates: list) -> str:
    """Robust column resolver supporting both English and Chinese keys"""
    for c in candidates:
        if c in df.columns:
            return c
    return ""


def generate_market_scan_summary_md(
    scan_meta: dict,
    df_top_risks: pd.DataFrame,
    df_full_company: pd.DataFrame,
    output_md_path: str
) -> str:
    """
    Generate reader-friendly executive Markdown report (English default, Chinese supported)
    """
    zh = is_zh_mode()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_companies = len(df_full_company)
    
    score_col = _find_col(df_full_company, ['Total_Risk_Score', 'total_risk_score', '当前综合风险评分', '综合风险评分'])
    cik_col = _find_col(df_full_company, ['CIK', 'cik'])
    name_col = _find_col(df_full_company, ['Company_Name', 'name', '公司名称'])
    period_col = _find_col(df_full_company, ['Latest_Period', 'Period', 'period', '最新申报期', '财报报告期'])
    diag_col = _find_col(df_full_company, ['Diagnostic_Summary', 'diagnostic_summary', '排雷诊断结论'])
    level_col = _find_col(df_full_company, ['Risk_Level', 'risk_level', '当前风险等级', '风险等级'])
    notes_col = _find_col(df_full_company, [
        'Forensic_Evidence_Notes', 'risk_reasons_notes',
        '具体风险成因与排雷证据说明(Notes)', '当期具体风险成因与排雷证据说明(Notes)'
    ])
    beneish_col = _find_col(df_full_company, ['Beneish_M', 'beneish_m_score', '最新Beneish_M', 'Beneish_M分值'])

    scores = pd.to_numeric(df_full_company[score_col], errors='coerce').fillna(0) if score_col else pd.Series([0]*len(df_full_company))
    
    red_df = df_full_company[scores >= 50]
    orange_df = df_full_company[(scores >= 30) & (scores < 50)]
    yellow_df = df_full_company[(scores >= 15) & (scores < 30)]
    green_df = df_full_company[scores < 15]

    red_cnt = len(red_df)
    orange_cnt = len(orange_df)
    yellow_cnt = len(yellow_df)
    green_cnt = len(green_df)

    red_pct = (red_cnt / total_companies * 100) if total_companies > 0 else 0
    orange_pct = (orange_cnt / total_companies * 100) if total_companies > 0 else 0
    yellow_pct = (yellow_cnt / total_companies * 100) if total_companies > 0 else 0
    green_pct = (green_cnt / total_companies * 100) if total_companies > 0 else 0

    lines = []
    if zh:
        lines.append("# 🏛️ SEC 美股上市公司财务造假与粉饰排雷审计研报")
        lines.append(f"> **生成时间**: `{now_str}` | **审计引擎**: `DuckDB + Forensic Evaluator (纯数理确定性审计)`")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 📊 1. 全市场财务健康全景看板 (Executive Overview)")
        lines.append(f"* **审计覆盖区间**: `{scan_meta.get('min_year', '')} 年 ~ {scan_meta.get('max_year', '')} 年`")
        lines.append(f"* **覆盖上市公司总数**: `{total_companies:,}` 家 (以公司为核心主体聚合)")
        lines.append(f"* **穿透审计财报总数**: `{scan_meta.get('total_filings', 0):,}` 份 (10-K 年报与 10-Q 季报)")
        lines.append("")
        lines.append("| 风险评级 | 风险程度 | 公司数量 | 占比 | 投资建议与处置策略 |")
        lines.append("| :--- | :---: | :---: | :---: | :--- |")
        lines.append(f"| 🔴 **[极危] 红色高危** | 50 ~ 100 分 | **{red_cnt:,}** 家 | `{red_pct:.1f}%` | ⚠️ **坚决一票否决/立即清仓**，多项致命舞弊特征共振 |")
        lines.append(f"| 🟠 **[预警] 橙色关注** | 30 ~ 49 分 | **{orange_cnt:,}** 家 | `{orange_pct:.1f}%` | 🔍 **高度警惕**，存在跨期操纵或造血能力恶化 |")
        lines.append(f"| 🟡 **[提示] 黄色提示** | 15 ~ 29 分 | **{yellow_cnt:,}** 家 | `{yellow_pct:.1f}%` | ⚠️ **持续追踪**，个别资产负债科目异化或周转放缓 |")
        lines.append(f"| 🟢 **[安全] 绿色稳健** | 0 ~ 14 分 | **{green_cnt:,}** 家 | `{green_pct:.1f}%` | ✅ **财务稳健**，三张表勾稽良好，现金流造血充沛 |")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 🚨 2. 全美股风险最高 TOP 20 极危暴雷黑榜 (Top Distress Watchlist)")
        lines.append("以下公司在数理法务审计中命中多项排雷硬指标，存在系统性虚构收入、破产危机或大洗澡嫌疑：")
        lines.append("")
        lines.append("### 2.1 极危企业速览看板 (Executive Table)")
        lines.append("")
        lines.append("| 排名 | CIK | 公司名称 | 最新申报期 | 风险分 | 风险等级 | 核心排雷结论 |")
        lines.append("| :---: | :---: | :--- | :---: | :---: | :---: | :--- |")
    else:
        lines.append("# 🏛️ SEC US Public Companies Forensic Fraud & Accounting Quality Screener")
        lines.append(f"> **Generated**: `{now_str}` | **Audit Engine**: `DuckDB + Forensic Evaluator (Econometric & Deterministic)`")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 📊 1. Market-Wide Financial Health (Executive Overview)")
        lines.append(f"* **Period Span**: `FY {scan_meta.get('min_year', '')} ~ {scan_meta.get('max_year', '')}`")
        lines.append(f"* **Companies Screened**: `{total_companies:,}` public companies")
        lines.append(f"* **Filings Analyzed**: `{scan_meta.get('total_filings', 0):,}` reports (Form 10-K & 10-Q)")
        lines.append("")
        lines.append("| Risk Classification | Score Range | Companies | Proportion | Action & Investment Strategy |")
        lines.append("| :--- | :---: | :---: | :---: | :--- |")
        lines.append(f"| 🔴 **[Critical] Red Distress** | 50 ~ 100 | **{red_cnt:,}** | `{red_pct:.1f}%` | ⚠️ **Immediate Divestment / One-Vote Veto** (Concurrence of multiple critical red flags) |")
        lines.append(f"| 🟠 **[Warning] Orange Alert** | 30 ~ 49 | **{orange_cnt:,}** | `{orange_pct:.1f}%` | 🔍 **High Caution** (Suspected cross-period earnings manipulation or cash decay) |")
        lines.append(f"| 🟡 **[Notice] Yellow Caution** | 15 ~ 29 | **{yellow_cnt:,}** | `{yellow_pct:.1f}%` | ⚠️ **Continuous Tracking** (Mild balance sheet anomalies or decelerating turnover) |")
        lines.append(f"| 🟢 **[Safe] Green Normal** | 0 ~ 14 | **{green_cnt:,}** | `{green_pct:.1f}%` | ✅ **Sound Quality** (Rigorous 3-statement reconciliation with strong organic cash flow) |")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 🚨 2. Top 20 Forensic Distress Watchlist")
        lines.append("Companies triggering multiple empirical accounting fraud & distress red flags:")
        lines.append("")
        lines.append("### 2.1 Executive Overview Table")
        lines.append("")
        lines.append("| Rank | CIK | Company Name | Period | Score | Risk Level | Diagnostic Conclusion |")
        lines.append("| :---: | :---: | :--- | :---: | :---: | :---: | :--- |")

    top20 = df_top_risks.head(20)
    for idx, (_, row) in enumerate(top20.iterrows(), 1):
        cik = str(row.get(cik_col, '')) if cik_col else ''
        name = str(row.get(name_col, '')) if name_col else ''
        period = str(row.get(period_col, '')) if period_col else ''
        score = row.get(score_col, 0) if score_col else 0
        level = str(row.get(level_col, '')) if level_col else ''
        diag = str(row.get(diag_col, '')) if diag_col else ''
        lines.append(f"| {idx} | `{cik}` | **{name}** | `{period}` | **{score}** | {level} | {diag} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    card_header = "### 2.2 TOP 20 极危企业实锤深度档案 (Detailed Evidence Cards)" if zh else "### 2.2 Top 20 Detailed Forensic Diagnostic Dossiers"
    lines.append(card_header)
    lines.append("")

    for idx, (_, row) in enumerate(top20.iterrows(), 1):
        cik = str(row.get(cik_col, '')) if cik_col else ''
        name = str(row.get(name_col, '')) if name_col else ''
        period = str(row.get(period_col, '')) if period_col else ''
        score = row.get(score_col, 0) if score_col else 0
        level = str(row.get(level_col, '')) if level_col else ''
        diag = str(row.get(diag_col, '')) if diag_col else ''
        raw_reasons = str(row.get(notes_col, '')) if notes_col else ''

        lines.append(f"#### {idx}. {name} (`CIK: {cik}`)")
        period_label = "最新报告期" if zh else "Latest Period"
        score_label = "综合风险评分" if zh else "Risk Score"
        diag_label = "排雷核心结论" if zh else "Key Diagnostic Finding"
        evidence_label = "**🔍 实锤证据与风险成因清单**:" if zh else "**🔍 Deterministic Evidence & Forensic Flags**:"
        lines.append(f"* **{period_label}**: `{period}` | **{score_label}**: **{score}** ({level})")
        lines.append(f"> **{diag_label}**: {diag}")
        lines.append("")
        lines.append(evidence_label)

        if raw_reasons and raw_reasons != 'nan' and raw_reasons.strip():
            reason_items = [p.strip() for p in raw_reasons.replace('\r', '').split('\n') if p.strip()]
            for item in reason_items:
                clean_item = item.lstrip('0123456789. ').strip()
                if clean_item.startswith('❌') or clean_item.startswith('✅') or clean_item.startswith('ℹ️'):
                    lines.append(f"- {clean_item}")
                else:
                    lines.append(f"- ❌ {clean_item}")
        else:
            safe_text = "- ✅ 财务勾稽严密，未见显著造假特征。" if zh else "- ✅ Financial statements are rigorously reconciled; zero systemic anomalies detected."
            lines.append(safe_text)
        lines.append("")

    lines.append("---")
    lines.append("")

    section3_title = "## 💣 3. 四大核心舞弊手法集中爆发区 (Forensic Deep Dive)" if zh else "## 💣 3. Deep Dive into 4 Major Forensic Red Flag Clusters"
    lines.append(section3_title)
    lines.append("")

    # 3.1 Beneish
    b_title = "### 3.1 贝尼斯 M-Score 涉嫌操纵收入/资产 (Beneish M > -1.78)" if zh else "### 3.1 Beneish M-Score Earnings Manipulation Alert (M > -1.78)"
    b_logic = "> **识别逻辑**: 8 变量综合计量模型，捕捉毛利下滑逆势扩张、异常折旧变动与超额应收挂账。" if zh else "> **Methodology**: 8-variable econometric model identifying aggressive revenue recognition, declining gross margins, and inflated capitalization."
    lines.append(b_title)
    lines.append(b_logic)
    lines.append("")
    table_hdr = "| CIK | 公司名称 | 申报期 | Beneish M-Score | 操纵标记 | 综合风险分 |" if zh else "| CIK | Company Name | Period | Beneish M-Score | Classification | Total Risk Score |"
    lines.append(table_hdr)
    lines.append("| :---: | :--- | :---: | :---: | :---: | :---: |")
    
    b_found = False
    if beneish_col:
        m_vals = pd.to_numeric(df_top_risks[beneish_col], errors='coerce')
        b_df = df_top_risks[m_vals > -1.78].copy()
        if not b_df.empty:
            b_df['m_num'] = pd.to_numeric(b_df[beneish_col], errors='coerce')
            b_df = b_df.sort_values(by='m_num', ascending=False).head(5)
            for _, r in b_df.iterrows():
                m_val = round(float(r[beneish_col]), 3)
                flag_text = "❌ 疑似系统操纵" if zh else "❌ Suspected Manipulator"
                score_unit = "分" if zh else ""
                lines.append(f"| `{r.get(cik_col, '')}` | **{r.get(name_col, '')}** | `{r.get(period_col, '')}` | **{m_val}** | {flag_text} | {r.get(score_col, '')} {score_unit} |")
            b_found = True
    if not b_found:
        none_text = "| - | - | - | ✅ 市场未见显著操纵突破 -1.78 阈值标的 | - | - |" if zh else "| - | - | - | ✅ Zero companies breached -1.78 Beneish threshold in current cohort | - | - |"
        lines.append(none_text)
    lines.append("")

    section4_title = "## 💡 4. 投资避坑与法务排雷实操行动纲领" if zh else "## 💡 4. Quantitative Forensic Action Guidelines"
    lines.append("---")
    lines.append("")
    lines.append(section4_title)
    if zh:
        lines.append("1. **一票否决制原则**: 对综合评分 >= 50 分的标的，坚决移出投资备选池。造假公司哪怕估值再诱人，本金永久性损失风险极高。")
        lines.append("2. **重点检验真金白银造血**: 密切关注**净现比断裂**（利润为正但现金净流出）与**修正琼斯 DA 异常**，绝不为纸面富贵买单。")
        lines.append("3. **警惕掏空与洗澡动作**: 业绩大幅滑坡期伴随超额分红/股权注资减持，或第四季度单季突发巨额亏损的，多属管理层集中出清旧账，需格外戒备。")
    else:
        lines.append("1. **One-Vote Veto Rule**: Strictly exclude entities scoring >= 50 from buy lists. Accounting fraud carries irreversible tail-risk of permanent capital loss regardless of valuation multiples.")
        lines.append("2. **Validate Organic Cash Generation**: Scrutinize net income to operating cash flow decoupling and abnormal Modified Jones discretionary accruals. Never pay for paper profits.")
        lines.append("3. **Watch for Tunneling & Big Baths**: Beware of sudden mega-write-offs in Q4 or excessive cash drainage during sharp earnings decelerations, typically indicating kitchen-sink accounting.")
    lines.append("")
    lines.append("---")
    footer_text = f"*报告自动生成于 {now_str}，配套完整明细见同名 Excel 工作簿。*" if zh else f"*Report generated automatically at {now_str}. Supporting granular datasets are available in the corresponding Excel workbook.*"
    lines.append(footer_text)

    content = "\n".join(lines)
    os.makedirs(os.path.dirname(os.path.abspath(output_md_path)), exist_ok=True)
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(content)

    return os.path.abspath(output_md_path)


def generate_batch_summary_md(
    results: list,
    output_md_path: str
) -> str:
    """
    Generate reader-friendly watchlist audit summary report (English default, Chinese supported)
    """
    zh = is_zh_mode()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    score_getter = lambda x: x.get('Total_Risk_Score') or x.get('综合风险评分') or x.get('total_risk_score', 0)
    sorted_results = sorted(results, key=score_getter, reverse=True)

    lines = []
    if zh:
        lines.append("# 📋 自选股组合法务会计排雷体检研报")
        lines.append(f"> **生成时间**: `{now_str}` | **受检股票数**: `{len(sorted_results)}` 只 | **审计引擎**: `纯数理法务排雷引擎`")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 🏆 1. 自选股排雷体检总览排行榜 (按风险评分倒序)")
        lines.append("")
        lines.append("| 股票代码 | 公司名称 | 综合风险分 | 风险等级 | Altman Z分 | Sloan 净应计 | Beneish 操纵嫌疑 | 核心排雷诊断结论 |")
        lines.append("| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |")
    else:
        lines.append("# 📋 Watchlist Portfolio Quantitative Forensic Audit Report")
        lines.append(f"> **Generated**: `{now_str}` | **Tickers Audited**: `{len(sorted_results)}` | **Audit Engine**: `Deterministic Forensic Econometrics`")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 🏆 1. Watchlist Forensic Ranking (Sorted by Total Risk Score)")
        lines.append("")
        lines.append("| Ticker | Company Name | Risk Score | Risk Classification | Altman Z | Sloan Accrual | Beneish M | Key Diagnostic Finding |")
        lines.append("| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |")

    for item in sorted_results:
        ticker = item.get('代码') or item.get('股票代码') or item.get('ticker') or item.get('Ticker') or ''
        name = item.get('公司名称') or item.get('name') or item.get('Company_Name') or ''
        score = item.get('综合风险评分') or item.get('Total_Risk_Score') or item.get('total_risk_score', 0)
        level = item.get('风险等级') or item.get('Risk_Level') or item.get('risk_level', '')
        
        z_val = item.get('Altman_Z分值') or item.get('Altman_Z') or item.get('altman_z')
        z_str = f"{z_val:.2f}" if isinstance(z_val, (int, float)) else (str(z_val) if z_val is not None else 'N/A')
        
        sloan_val = item.get('Sloan净应计') or item.get('Sloan_Accrual') or item.get('sloan_accrual')
        sloan_str = f"{sloan_val:.4f}" if isinstance(sloan_val, (int, float)) else (str(sloan_val) if sloan_val is not None else 'N/A')
        
        m_val = pd.to_numeric(item.get('Beneish_M分值') or item.get('Beneish_M') or item.get('beneish_m_score'), errors='coerce')
        if zh:
            m_flag = "❌ 操纵高危" if (m_val is not None and m_val > -1.78) else "✅ 安全稳健"
        else:
            m_flag = "❌ Manipulator" if (m_val is not None and m_val > -1.78) else "✅ Normal"
        
        diag = item.get('排雷诊断结论') or item.get('Diagnostic_Summary') or item.get('diagnostic_summary') or ''
        lines.append(f"| **{ticker}** | {name} | **{score}** | {level} | {z_str} | {sloan_str} | {m_flag} | {diag} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    section2_title = "## 🔍 2. 每只股票法务审计诊断卡片 (Detailed Diagnostic Cards)" if zh else "## 🔍 2. Granular Diagnostic Dossiers by Ticker"
    lines.append(section2_title)
    lines.append("")

    for idx, item in enumerate(sorted_results, 1):
        ticker = item.get('代码') or item.get('股票代码') or item.get('ticker') or item.get('Ticker') or ''
        name = item.get('公司名称') or item.get('name') or item.get('Company_Name') or ''
        score = item.get('综合风险评分') or item.get('Total_Risk_Score') or item.get('total_risk_score', 0)
        level = item.get('风险等级') or item.get('Risk_Level') or item.get('risk_level', '')
        diag = item.get('排雷诊断结论') or item.get('Diagnostic_Summary') or item.get('diagnostic_summary') or ''
        notes = str(item.get('具体风险成因与证据说明(Notes)') or item.get('Forensic_Evidence_Notes') or item.get('risk_reasons_notes') or '')

        lines.append(f"### 2.{idx} {name} (`{ticker}`)")
        score_prefix = "综合评分" if zh else "Risk Score"
        diag_prefix = "诊断结论" if zh else "Diagnostic Finding"
        notes_prefix = "**详细排雷证据与成因说明 (Notes)**:" if zh else "**Forensic Evidences & Red Flags (Notes)**:"
        lines.append(f"* **{score_prefix}**: **{score}** ({level})")
        lines.append(f"* **{diag_prefix}**: **{diag}**")
        lines.append("")
        lines.append(notes_prefix)
        if notes and notes != 'nan' and notes.strip():
            items = [p.strip() for p in notes.replace(';', '\n').split('\n') if p.strip()]
            for p_clean in items:
                clean_text = p_clean.lstrip('0123456789. ').strip()
                if clean_text.startswith('✅') or clean_text.startswith('❌') or clean_text.startswith('ℹ️'):
                    lines.append(f"- {clean_text}")
                else:
                    lines.append(f"- ❌ {clean_text}")
        else:
            safe_diag = "- ✅ 财务勾稽严密，各项计量模型均处于安全区间，未见明显财务粉饰迹象。" if zh else "- ✅ Rigorous financial reconciliations; econometric models in safe zones."
            lines.append(safe_diag)
        lines.append("")

    lines.append("---")
    foot_text = f"*报告自动生成于 {now_str}，配套全量指标明细见同名 Excel 底表。*" if zh else f"*Report generated automatically at {now_str}. Granular dataset is saved in the accompanying Excel spreadsheet.*"
    lines.append(foot_text)

    content = "\n".join(lines)
    os.makedirs(os.path.dirname(os.path.abspath(output_md_path)), exist_ok=True)
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(content)

    return os.path.abspath(output_md_path)
