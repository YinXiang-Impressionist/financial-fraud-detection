# -*- coding: utf-8 -*-
"""
法务会计排雷研报生成器 (Reader-Friendly Forensic Report Generator)
为决策者与研究员生成结构化、排版优美、直观透彻的 Markdown 总结研报。
"""

import os
from datetime import datetime
import pandas as pd


def _find_col(df: pd.DataFrame, candidates: list) -> str:
    """在 DataFrame 中鲁棒查找匹配的列名"""
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
    生成美股全市场财务排雷大扫描的 Reader-Friendly 总结研报 (Markdown 格式)
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_companies = len(df_full_company)
    
    score_col = _find_col(df_full_company, ['当前综合风险评分', '综合风险评分', 'total_risk_score'])
    cik_col = _find_col(df_full_company, ['CIK', 'cik'])
    name_col = _find_col(df_full_company, ['公司名称', 'name'])
    period_col = _find_col(df_full_company, ['最新申报期', '财报报告期', 'period'])
    diag_col = _find_col(df_full_company, ['排雷诊断结论', 'diagnostic_summary'])
    level_col = _find_col(df_full_company, ['当前风险等级', '风险等级', 'risk_level'])
    notes_col = _find_col(df_full_company, [
        '具体风险成因与排雷证据说明(Notes)',
        '当期具体风险成因与排雷证据说明(Notes)',
        'risk_reasons_notes'
    ])
    beneish_col = _find_col(df_full_company, ['最新Beneish_M', 'Beneish_M分值', 'beneish_m_score'])

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
    lines.append("| 排名 | CIK | 公司名称 | 最新申报期 | 风险分 | 风险等级 | 排雷诊断结论与核心证据说明 |")
    lines.append("| :---: | :---: | :--- | :---: | :---: | :---: | :--- |")

    top20 = df_top_risks.head(20)
    for idx, (_, row) in enumerate(top20.iterrows(), 1):
        cik = row.get(cik_col, '') if cik_col else ''
        name = row.get(name_col, '') if name_col else ''
        period = row.get(period_col, '') if period_col else ''
        score = row.get(score_col, 0) if score_col else 0
        level = row.get(level_col, '') if level_col else ''
        diag = row.get(diag_col, '') if diag_col else ''
        reasons = str(row.get(notes_col, '')) if notes_col else ''
        
        clean_reasons = reasons.replace('\n', '; ').strip('; ')
        if len(clean_reasons) > 120:
            clean_reasons = clean_reasons[:117] + "..."
        desc = f"**{diag}**<br><sub>{clean_reasons}</sub>" if clean_reasons and clean_reasons != 'nan' else f"**{diag}**"

        lines.append(f"| {idx} | `{cik}` | **{name}** | `{period}` | **{score}** | {level} | {desc} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 💣 3. 四大核心舞弊手法集中爆发区 (Forensic Deep Dive)")
    lines.append("")

    # 子分类 3.1: 贝尼斯 M-Score 涉嫌操纵收入/资产
    lines.append("### 3.1 贝尼斯 M-Score 涉嫌操纵收入/资产 (Beneish M > -1.78)")
    lines.append("> **识别逻辑**: 8 变量综合计量模型，捕捉毛利下滑逆势扩张、异常折旧变动与超额应收挂账。")
    lines.append("")
    lines.append("| CIK | 公司名称 | 申报期 | Beneish M-Score | 操纵标记 | 综合风险分 |")
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
                lines.append(f"| `{r.get(cik_col, '')}` | **{r.get(name_col, '')}** | `{r.get(period_col, '')}` | **{m_val}** | ❌ 疑似系统操纵 | {r.get(score_col, '')} 分 |")
            b_found = True
    if not b_found:
        lines.append("| - | - | - | ✅ 市场未见显著操纵突破 -1.78 阈值标的 | - | - |")
    lines.append("")

    # 子分类 3.2: 净现比恶性断裂与造血严重衰竭
    lines.append("### 3.2 净现比恶性断裂与造血严重衰竭 (纸面富贵虚增利润)")
    lines.append("> **识别逻辑**: 账面净利润表现良好但经营现金流为巨额净流出，戳穿纸面富贵与关联虚假销售。")
    lines.append("")
    lines.append("| CIK | 公司名称 | 申报期 | 诊断结论 | 综合风险分 |")
    lines.append("| :---: | :--- | :---: | :--- | :---: |")
    
    cfo_found = False
    if notes_col:
        cfo_df = df_top_risks[df_top_risks[notes_col].astype(str).str.contains('净现比|造血|流出', na=False)].head(5)
        if not cfo_df.empty:
            for _, r in cfo_df.iterrows():
                lines.append(f"| `{r.get(cik_col, '')}` | **{r.get(name_col, '')}** | `{r.get(period_col, '')}` | {r.get(diag_col, '')} | **{r.get(score_col, '')}** 分 |")
            cfo_found = True
    if not cfo_found:
        lines.append("| - | - | - | ✅ 市场未见显著净现比恶化标的 | - |")
    lines.append("")

    # 子分类 3.3: Sloan 高应计异象与应收账款反常扩张
    lines.append("### 3.3 Sloan 高应计异象与应收账款反常挂账 (假销售/提前确认嫌疑)")
    lines.append("> **识别逻辑**: 应计利润占总资产超 10%，或应收账款占营收比例反常飙升，警惕虚构订单或向关联方压货。")
    lines.append("")
    lines.append("| CIK | 公司名称 | 申报期 | 诊断结论 | 综合风险分 |")
    lines.append("| :---: | :--- | :---: | :--- | :---: |")
    
    accrual_found = False
    if notes_col:
        accrual_df = df_top_risks[df_top_risks[notes_col].astype(str).str.contains('应收账款|高应计|Sloan', na=False)].head(5)
        if not accrual_df.empty:
            for _, r in accrual_df.iterrows():
                lines.append(f"| `{r.get(cik_col, '')}` | **{r.get(name_col, '')}** | `{r.get(period_col, '')}` | {r.get(diag_col, '')} | **{r.get(score_col, '')}** 分 |")
            accrual_found = True
    if not accrual_found:
        lines.append("| - | - | - | ✅ 市场未见显著高应计与应收反常标的 | - |")
    lines.append("")

    # 子分类 3.4: 商誉悬顶 / 业绩大变脸洗澡
    lines.append("### 3.4 巨额商誉悬顶与业绩大变脸减值大洗澡")
    lines.append("> **识别逻辑**: 商誉占净资产比重奇高（>50%），前期高溢价并购标的暴雷将引发雪崩式减值亏损。")
    lines.append("")
    lines.append("| CIK | 公司名称 | 申报期 | 诊断结论 | 综合风险分 |")
    lines.append("| :---: | :--- | :---: | :--- | :---: |")
    
    gw_found = False
    if notes_col:
        gw_df = df_top_risks[df_top_risks[notes_col].astype(str).str.contains('商誉|减值|洗澡', na=False)].head(5)
        if not gw_df.empty:
            for _, r in gw_df.iterrows():
                lines.append(f"| `{r.get(cik_col, '')}` | **{r.get(name_col, '')}** | `{r.get(period_col, '')}` | {r.get(diag_col, '')} | **{r.get(score_col, '')}** 分 |")
            gw_found = True
    if not gw_found:
        lines.append("| - | - | - | ✅ 市场未见巨额商誉减值危机企业 | - |")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 💡 4. 投资避坑与法务排雷实操行动纲领")
    lines.append("1. **一票否决制原则**: 对综合评分 >= 50 分的标的，坚决移出投资备选池。造假公司哪怕估值再诱人，本金永久性损失风险极高。")
    lines.append("2. **重点检验真金白银造血**: 密切关注**净现比断裂**（利润为正但现金净流出）与**修正琼斯 DA 异常**，绝不为纸面富贵买单。")
    lines.append("3. **警惕掏空与洗澡动作**: 业绩大幅滑坡期伴随超额分红/股权注资减持，或第四季度单季突发巨额亏损的，多属管理层集中出清旧账，需格外戒备。")
    lines.append("")
    lines.append("---")
    lines.append(f"*报告自动生成于 {now_str}，配套完整明细见同名 Excel 工作簿。*")

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
    生成自选股股票池批量体检的 Reader-Friendly 总结研报 (Markdown 格式)
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sorted_results = sorted(results, key=lambda x: x.get('综合风险评分', 0), reverse=True)

    lines = []
    lines.append("# 📋 自选股组合法务会计排雷体检研报")
    lines.append(f"> **生成时间**: `{now_str}` | **受检股票数**: `{len(sorted_results)}` 只 | **审计引擎**: `纯数理法务排雷引擎`")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🏆 1. 自选股排雷体检总览排行榜 (按风险评分倒序)")
    lines.append("")
    lines.append("| 股票代码 | 公司名称 | 综合风险分 | 风险等级 | Altman Z分 | Sloan 净应计 | Beneish 操纵嫌疑 | 核心排雷诊断结论 |")
    lines.append("| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |")

    for item in sorted_results:
        ticker = item.get('代码') or item.get('股票代码') or item.get('ticker') or ''
        name = item.get('公司名称') or item.get('name') or ''
        score = item.get('综合风险评分') or item.get('total_risk_score', 0)
        level = item.get('风险等级') or item.get('risk_level', '')
        
        z_val = item.get('Altman_Z分值') or item.get('Altman_Z分') or item.get('altman_z')
        z_str = f"{z_val:.2f}" if isinstance(z_val, (int, float)) else (str(z_val) if z_val is not None else 'N/A')
        
        sloan_val = item.get('Sloan净应计') or item.get('sloan_accrual')
        sloan_str = f"{sloan_val:.4f}" if isinstance(sloan_val, (int, float)) else (str(sloan_val) if sloan_val is not None else 'N/A')
        
        m_val = pd.to_numeric(item.get('Beneish_M分值') or item.get('beneish_m_score'), errors='coerce')
        m_flag = "❌ 操纵高危" if (m_val is not None and m_val > -1.78) else "✅ 安全稳健"
        
        diag = item.get('排雷诊断结论') or item.get('diagnostic_summary') or ''
        lines.append(f"| **{ticker}** | {name} | **{score}** | {level} | {z_str} | {sloan_str} | {m_flag} | {diag} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🔍 2. 每只股票法务审计诊断卡片 (Detailed Diagnostic Cards)")
    lines.append("")

    for idx, item in enumerate(sorted_results, 1):
        ticker = item.get('代码') or item.get('股票代码') or item.get('ticker') or ''
        name = item.get('公司名称') or item.get('name') or ''
        score = item.get('综合风险评分') or item.get('total_risk_score', 0)
        level = item.get('风险等级') or item.get('risk_level', '')
        diag = item.get('排雷诊断结论') or item.get('diagnostic_summary') or ''
        notes = str(item.get('具体风险成因与证据说明(Notes)') or item.get('risk_reasons_notes') or item.get('当期具体风险成因与排雷证据说明(Notes)') or '')

        lines.append(f"### 2.{idx} {name} (`{ticker}`)")
        lines.append(f"* **综合评分**: **{score} 分** ({level})")
        lines.append(f"* **诊断结论**: **{diag}**")
        
        lines.append("* **详细排雷证据与成因说明 (Notes)**:")
        if notes and notes != 'nan' and notes.strip():
            items = [p.strip() for p in notes.replace(';', '\n').split('\n') if p.strip()]
            for p_clean in items:
                if p_clean.startswith('✅'):
                    lines.append(f"  - {p_clean}")
                else:
                    lines.append(f"  - ❌ {p_clean}")
        else:
            lines.append("  - ✅ 财务勾稽严密，各项计量模型均处于安全区间，未见明显财务粉饰迹象。")
        lines.append("")

    lines.append("---")
    lines.append(f"*报告自动生成于 {now_str}，配套全量指标明细见同名 Excel 底表。*")

    content = "\n".join(lines)
    os.makedirs(os.path.dirname(os.path.abspath(output_md_path)), exist_ok=True)
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(content)

    return os.path.abspath(output_md_path)
