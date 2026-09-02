# -*- coding: utf-8 -*-
"""
Governance & Multi-Source Forensic Red Flags
公司治理、8-K重大事件、Form 4内部人套现与内控缺陷规则集

包含规则:
- 规则 4.1: 控股股东/实控人高比例股权质押 (High Share Pledge Ratio)
- 规则 4.2: Form 4 董监高与大股东大额抛售套现 (Pump & Dump)
- 规则 4.3: 审计意见非标及 8-K Item 4.01 突发换所 (Auditor Turnover & Opinion Shopping)
- 规则 4.4: Form 8-K Item 4.02 真实重大差错与重述 (时效衰减机制 + 科研真值标签)
- 规则 4.5: Form 8-K Item 5.02 CFO/财务负责人或审计委员会独董突发离职
- 规则 4.6: 10-K Item 9A 内部控制重大实质性缺陷 (Material Weakness)
"""

from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd


def check_governance_rules(row: Dict[str, Any]) -> Tuple[int, List[str]]:
    """
    单条记录多维法务与治理红旗规则检测
    """
    score = 0
    warnings = []

    pledge_ratio = float(row.get('pledge_ratio') or 0.0)
    audit_opinion = str(row.get('audit_opinion') or '').strip().lower()
    auditor_changed = bool(row.get('auditor_changed') or False)

    # 1. 规则 4.1: 高比例股权质押
    if pledge_ratio > 0.70:
        score += 20
        warnings.append(f"【大股东质押极危】控股股东股权质押比例达 {pledge_ratio*100:.1f}%，爆仓强平压力巨大，操纵市值动机极强")
    elif pledge_ratio > 0.50:
        score += 10
        warnings.append(f"【大股东高质押预警】控股股东股权质押比例达 {pledge_ratio*100:.1f}%")

    # 2. 规则 4.3: 审计意见非标
    if audit_opinion and audit_opinion not in ['clean', 'unqualified', '标准无保留', '无保留意见']:
        score += 25
        warnings.append(f"【审计意见非标】审计机构出具非标意见 ({audit_opinion})，报表可信度存疑")

    # 3. 8-K Item 4.01 换所公告
    if bool(row.get('accountant_changed_8k') or auditor_changed):
        score += 20
        warnings.append("【8-K突发换所】官方公告 Item 4.01 解聘/更换会计师事务所，警惕购买审计意见 (Opinion Shopping)")

    # 4. 规则 4.4: 8-K Item 4.02 重大重述 (结合时效衰减机制)
    # 若直接传入计算好的扣分值则优先使用
    if 'restatement_score_penalty' in row:
        penalty = int(row.get('restatement_score_penalty') or 0)
        score += penalty
        if penalty >= 20:
            warnings.append(f"【近期重大重述】近1年内发生 8-K Item 4.02 前期财报失效并重述，警惕后续连环追溯调整与监管调查风险 (+{penalty}分)")
        elif penalty > 0:
            warnings.append(f"【历史观察期重述】历史 1~3 年内曾发生财务重述，内控整改仍在观察期 (+{penalty}分)")
    elif row.get('has_item_402_restatement'):
        # 兼容未传入衰减分值时的天数判定
        days = row.get('recent_restatement_days')
        if days is not None and days <= 365:
            score += 20
            warnings.append(f"【近期重大重述】近1年内({days}天前)发生 8-K Item 4.02 财务重述，处于高度暴雷敏感期")
        elif days is not None and days <= 1095:
            score += 5
            warnings.append(f"【历史观察期重述】历史({days}天前)曾发生财务重述，内控处于整改观察中")

    # 5. 8-K Item 5.02 高管/CFO 异常离职
    if bool(row.get('officer_departure_8k')):
        score += 15
        warnings.append("【8-K高管异动】官方公告 Item 5.02 CFO/财务负责人或独董突发离职，警惕内控人事动荡")

    # 6. Form 4 内部人套现减持 (Pump & Dump)
    if bool(row.get('heavy_insider_selling')):
        net_sell = float(row.get('insider_net_sell_val') or 0.0)
        score += 20
        warnings.append(f"【内部人集中套现】Form 4 监测到高管/大股东大额净抛售套现 (${net_sell/1e6:.1f}M)，大额减持动机高危")

    # 7. 10-K Item 9A 内部控制重大缺陷 (Material Weakness)
    if bool(row.get('has_material_weakness')):
        score += 25
        warnings.append("【内控实质性缺陷】最新 10-K Item 9A 披露存在实质性重大缺陷 (Material Weakness)，内控防线失效")

    return score, warnings


def apply_governance_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    批量向量化评估治理与多维非财务红旗
    """
    df = df.copy()
    pledge_ratio = df['pledge_ratio'] if 'pledge_ratio' in df.columns else pd.Series(0.0, index=df.index)
    auditor_changed = df['auditor_changed'] if 'auditor_changed' in df.columns else pd.Series(False, index=df.index)
    accountant_changed_8k = df['accountant_changed_8k'] if 'accountant_changed_8k' in df.columns else pd.Series(False, index=df.index)
    officer_departure_8k = df['officer_departure_8k'] if 'officer_departure_8k' in df.columns else pd.Series(False, index=df.index)
    heavy_insider_selling = df['heavy_insider_selling'] if 'heavy_insider_selling' in df.columns else pd.Series(False, index=df.index)
    has_material_weakness = df['has_material_weakness'] if 'has_material_weakness' in df.columns else pd.Series(False, index=df.index)
    restatement_score_penalty = df['restatement_score_penalty'] if 'restatement_score_penalty' in df.columns else pd.Series(0, index=df.index)

    cond_pledge_high = pledge_ratio > 0.70
    cond_auditor_changed = (auditor_changed == True) | (accountant_changed_8k == True)
    cond_officer_departure = officer_departure_8k == True
    cond_insider_dump = heavy_insider_selling == True
    cond_material_weakness = has_material_weakness == True

    gov_score = (
        cond_pledge_high.astype(int) * 20 +
        cond_auditor_changed.astype(int) * 20 +
        cond_officer_departure.astype(int) * 15 +
        cond_insider_dump.astype(int) * 20 +
        cond_material_weakness.astype(int) * 25 +
        restatement_score_penalty.astype(int)
    )

    df['gov_fraud_score'] = gov_score
    df['flag_pledge_high'] = cond_pledge_high
    df['flag_auditor_changed'] = cond_auditor_changed
    df['flag_officer_departure'] = cond_officer_departure
    df['flag_insider_dump'] = cond_insider_dump
    df['flag_material_weakness'] = cond_material_weakness

    return df
