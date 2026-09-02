# -*- coding: utf-8 -*-
"""
Balance Sheet Forensic Audit Rules
资产负债表穿透排雷规则集

包含规则:
- 规则 1.1: 存贷双高与受限货币资金 (Cash & Debt Coexistence)
- 规则 1.2: 高额商誉悬顶 (Goodwill Burden)
- 规则 1.3: 应收账款堆积与打白条虚增收入 (AR Surge & DSRI Overhang)
- 规则 1.4: 存货异常积压与跌价计提不足 (Inventory Glut)
- 规则 1.5: 在建工程长期挂账不转固 (Construction In Progress CIP Stalling)
- 规则 1.6: 其他应收款与预付账款畸高 (Suspicious Other Receivables / Prepayments)
- 规则 1.7: 开发支出与研发投入过度资本化 (Capitalized R&D Overhang)
- 规则 1.8: “明股实债”少数股东权益与损益严重倒挂 (Minority Interest Distortion)
- 规则 1.9: 永续债与隐性杠杆出表 (Perpetual Debt)
- 规则 1.10: 资不抵债与净资产穿底赤字 (Negative Equity / Insolvent)
"""

from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd


def check_balance_sheet_rules(row: Dict[str, Any]) -> Tuple[int, List[str]]:
    """
    针对单家公司单期报表执行资产负债表穿透规则检测
    返回: (score, list_of_warning_strings)
    """
    score = 0
    warnings = []

    assets = float(row.get('assets') or 0.0)
    equity = float(row.get('equity') or 0.0)
    cash = float(row.get('cash') or 0.0)
    debt = float(row.get('debt') or 0.0)
    goodwill = float(row.get('goodwill') or 0.0)
    ar = float(row.get('ar') or row.get('accounts_receivable') or 0.0)
    sales = float(row.get('sales') or row.get('revenue') or 0.0)
    inv = float(row.get('inv') or row.get('inventory') or 0.0)
    cogs = float(row.get('cogs') or 0.0)
    cip = float(row.get('cip') or row.get('construction_in_progress') or 0.0)
    ppe_net = float(row.get('ppe_net') or 0.0)
    other_rec = float(row.get('other_receivables') or 0.0)
    prepay = float(row.get('prepayments') or 0.0)
    interest_exp = float(row.get('interest_expense') or 0.0)
    interest_inc = float(row.get('interest_income') or 0.0)
    net_income = float(row.get('net_income') or 0.0)
    minority_equity = float(row.get('minority_equity') or 0.0)
    minority_profit = float(row.get('minority_profit') or 0.0)
    capitalized_rd = float(row.get('capitalized_rd') or 0.0)
    total_rd = float(row.get('total_rd') or 0.0)

    # 规则 1.10: 资不抵债与净资产赤字
    if equity < 0 and assets > 1e6:
        score += 30
        warnings.append(f"【资不抵债】所有者权益为赤字负值 ({equity/1e6:.1f}M)，破产与偿债风险极高")

    # 规则 1.1: 存贷双高与受限资金嫌疑
    if assets > 0:
        cash_ratio = cash / assets
        debt_ratio = debt / assets
        if cash_ratio > 0.20 and debt_ratio > 0.30 and cash > 1e7 and debt > 1e7:
            # 进一步检测利息倒挂
            if interest_exp > net_income and net_income > 0:
                score += 25
                warnings.append(f"【存贷双高恶性】巨额现金(占比{cash_ratio*100:.1f}%)与高额债务(占比{debt_ratio*100:.1f}%)并存，且利息支出吞噬净利润")
            elif interest_inc > 0 and (interest_inc / cash) < 0.01:
                score += 25
                warnings.append(f"【存贷双高异常】账面现金充裕(占比{cash_ratio*100:.1f}%)却背负重债(占比{debt_ratio*100:.1f}%)，资金收益率<{interest_inc/cash*100:.2f}%涉嫌受限或虚构")
            else:
                score += 15
                warnings.append(f"【存贷双高疑似】现金占比{cash_ratio*100:.1f}%与有息负债占比{debt_ratio*100:.1f}%双高，警惕资金受限质押")

    # 规则 1.2: 高额商誉悬顶
    if equity > 0 and goodwill > 0:
        gw_ratio = goodwill / equity
        if gw_ratio > 0.50 and goodwill > 5e7:
            score += 25
            warnings.append(f"【商誉极危悬顶】商誉占净资产比例达 {gw_ratio*100:.1f}% (${goodwill/1e6:.1f}M)，面临业绩变脸大额减值洗澡风险")
        elif gw_ratio > 0.30 and goodwill > 3e7:
            score += 15
            warnings.append(f"【高额商誉预警】商誉占净资产比例达 {gw_ratio*100:.1f}% (${goodwill/1e6:.1f}M)")

    # 规则 1.3: 应收账款激增与过高占比
    if sales > 0 and ar > 0:
        ar_ratio = ar / sales
        if ar_ratio > 0.60 and ar > 3e7:
            score += 15
            warnings.append(f"【应收账款畸高】应收账款占营业收入比重达 {ar_ratio*100:.1f}% (${ar/1e6:.1f}M)，大量赊销或存在提前确认收入")

    # 规则 1.4: 存货异常积压
    if assets > 0 and inv > 0:
        inv_ratio = inv / assets
        if inv_ratio > 0.30 and inv > 3e7:
            score += 15
            warnings.append(f"【存货过度积压】存货占总资产比重达 {inv_ratio*100:.1f}% (${inv/1e6:.1f}M)，存在跌价计提不足或虚拟库存沉淀资金风险")

    # 规则 1.5: 在建工程长期挂账不转固
    if ppe_net > 0 and cip > 0:
        cip_ratio = cip / ppe_net
        if cip_ratio > 0.50 and cip > 5e7:
            score += 15
            warnings.append(f"【在建工程异动】在建工程达固定资产净额的 {cip_ratio*100:.1f}% (${cip/1e6:.1f}M)，警惕延缓折旧或借工程掏空资金")

    # 规则 1.6: 其他应收款与预付款项畸高 (资金体外占用通道)
    if assets > 0:
        other_ratio = (other_rec + prepay) / assets
        if other_ratio > 0.10 and (other_rec + prepay) > 3e7:
            score += 15
            warnings.append(f"【其他应收/预付畸高】其他应收款与预付项合计占总资产 {other_ratio*100:.1f}% (${(other_rec+prepay)/1e6:.1f}M)，警惕非经营性资金占用")

    # 规则 1.7: 研发支出过度资本化
    if total_rd > 0 and capitalized_rd > 0:
        cap_rate = capitalized_rd / total_rd
        if cap_rate > 0.25 and capitalized_rd > 1e7:
            score += 15
            warnings.append(f"【研发过度资本化】研发支出资本化率达 {cap_rate*100:.1f}%，显著偏离费用化惯例以虚增利润")

    # 规则 1.8: “明股实债”——少数股东权益与损益严重倒挂
    if equity > 0 and minority_equity > 0:
        min_eq_ratio = minority_equity / equity
        if min_eq_ratio > 0.40 and net_income > 0:
            min_prof_ratio = minority_profit / net_income
            if min_prof_ratio < 0.05 or minority_profit <= 0:
                score += 20
                warnings.append(f"【明股实债嫌疑】少数股东权益占净资产 {min_eq_ratio*100:.1f}%，但分得损益仅占 {min_prof_ratio*100:.1f}%，呈现显著刚性对赌特征")

    return score, warnings


def _get_series(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    if col in df.columns:
        return df[col].fillna(default)
    return pd.Series(default, index=df.index)


def apply_balance_sheet_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    批量向量化评估整个 DataFrame 的资产负债表排雷规则
    """
    df = df.copy()
    assets = _get_series(df, 'assets')
    equity = _get_series(df, 'equity')
    cash = _get_series(df, 'cash')
    debt = _get_series(df, 'debt')
    goodwill = _get_series(df, 'goodwill')
    sales = _get_series(df, 'sales')
    ar = _get_series(df, 'ar')
    inv = _get_series(df, 'inv')
    cip = _get_series(df, 'cip')
    ppe_net = _get_series(df, 'ppe_net')
    other_rec = _get_series(df, 'other_receivables')
    prepay = _get_series(df, 'prepayments')

    # 1. 资不抵债
    cond_negative_equity = (equity < 0) & (assets > 1e6)
    
    # 2. 存贷双高
    cash_ratio = np.where(assets > 0, cash / assets, 0.0)
    debt_ratio = np.where(assets > 0, debt / assets, 0.0)
    cond_cash_debt = (cash_ratio > 0.20) & (debt_ratio > 0.30) & (cash > 1e7) & (debt > 1e7)

    # 3. 商誉悬顶
    gw_ratio = np.where(equity > 0, goodwill / equity, 0.0)
    cond_gw_extreme = (gw_ratio > 0.50) & (goodwill > 5e7)
    cond_gw_warn = (gw_ratio > 0.30) & (goodwill > 3e7) & (~cond_gw_extreme)

    # 4. 应收账款畸高
    ar_ratio = np.where(sales > 0, ar / sales, 0.0)
    cond_ar_high = (ar_ratio > 0.60) & (ar > 3e7)

    # 5. 存货积压
    inv_ratio = np.where(assets > 0, inv / assets, 0.0)
    cond_inv_high = (inv_ratio > 0.30) & (inv > 3e7)

    # 6. 在建工程长期挂账
    cip_ratio = np.where(ppe_net > 0, cip / ppe_net, 0.0)
    cond_cip_high = (cip_ratio > 0.50) & (cip > 5e7)

    # 7. 其他应收/预付畸高
    other_ratio = np.where(assets > 0, (other_rec + prepay) / assets, 0.0)
    cond_other_high = (other_ratio > 0.10) & ((other_rec + prepay) > 3e7)

    # 向量化累加评分
    bs_score = (
        cond_negative_equity.astype(int) * 30 +
        cond_cash_debt.astype(int) * 20 +
        cond_gw_extreme.astype(int) * 25 +
        cond_gw_warn.astype(int) * 15 +
        cond_ar_high.astype(int) * 15 +
        cond_inv_high.astype(int) * 15 +
        cond_cip_high.astype(int) * 15 +
        cond_other_high.astype(int) * 15
    )

    df['bs_fraud_score'] = bs_score
    df['flag_negative_equity'] = cond_negative_equity
    df['flag_cash_debt_anomaly'] = cond_cash_debt
    df['flag_goodwill_burden'] = cond_gw_extreme | cond_gw_warn
    df['flag_ar_anomaly'] = cond_ar_high
    df['flag_inv_overhang'] = cond_inv_high
    df['flag_cip_anomaly'] = cond_cip_high
    df['flag_other_rec_anomaly'] = cond_other_high

    return df
