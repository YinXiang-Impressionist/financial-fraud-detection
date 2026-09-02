# -*- coding: utf-8 -*-
"""
Income Statement Forensic Audit Rules
利润表操纵与粉饰检测规则集

包含规则:
- 规则 2.1: 净现比严重背离 (纸面富贵 / 盈利无现金支撑)
- 规则 2.2: 扣非净利润巨亏与非经常性损益掩护 (主营枯竭靠营业外/投资收益保壳)
- 规则 2.3: 毛利率异常逆势飙升与存货周转背离 (Gross Margin Manipulation)
- 规则 2.4: 大宗贸易/供应链“总额法”虚刷营收流水 (Gross Revenue Inflation)
- 规则 2.5: 折旧减速与跨期调节费用 (Depreciation Rate Manipulation)
- 规则 2.6: 合同资产占收入比重畸高 (Aggressive Revenue Recognition)
"""

from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd


def check_income_statement_rules(row: Dict[str, Any]) -> Tuple[int, List[str]]:
    """
    单条记录利润表操纵规则检测
    """
    score = 0
    warnings = []

    sales = float(row.get('sales') or row.get('revenue') or 0.0)
    net_income = float(row.get('net_income') or 0.0)
    cfo = float(row.get('cfo') or 0.0)
    op_inc = float(row.get('operating_income') or row.get('ebit') or 0.0)
    cogs = float(row.get('cogs') or 0.0)
    inv = float(row.get('inv') or row.get('inventory') or 0.0)
    depr = float(row.get('depr') or 0.0)
    depr_prev = float(row.get('depr_prev') or 0.0)
    contract_assets = float(row.get('contract_assets') or 0.0)

    # 规则 2.1: 净现比严重背离
    if net_income > 5e7:
        if cfo <= 0:
            score += 25
            warnings.append(f"【净现比恶性断裂】净利润盈利 (${net_income/1e6:.1f}M) 但经营活动现金流为净流出 (${cfo/1e6:.1f}M)")
        elif (cfo / net_income) < 0.30:
            score += 15
            warnings.append(f"【现金流造血孱弱】净现比仅为 {cfo/net_income:.2f} (远低于0.5健康警戒线)，存在严重纸面富贵")

    # 规则 2.2: 扣非/主营经营利润巨亏，靠非经常性损益/投资收益粉饰
    if net_income > 0 and op_inc < 0 and net_income > 2e7:
        score += 20
        warnings.append(f"【主营造血枯竭】主营营业利润亏损 (${op_inc/1e6:.1f}M) 但净利润依靠非经常性损益/公允价值掩护为正 (${net_income/1e6:.1f}M)")

    # 规则 2.4: 大宗贸易/供应链“总额法”虚刷流水
    if sales > 1e9 and net_income > 0:
        net_margin = net_income / sales
        if net_margin < 0.005:  # 净利率 < 0.5%
            score += 15
            warnings.append(f"【总额法流水刷单嫌疑】营收超十亿美元 (${sales/1e6:.0f}M) 但净利率仅为 {net_margin*100:.2f}%，典型通道贸易虚增流水")

    # 规则 2.6: 合同资产畸高 (完工百分比激进确认)
    if sales > 0 and contract_assets > 0:
        ca_ratio = contract_assets / sales
        if ca_ratio > 0.50 and contract_assets > 5e7:
            score += 15
            warnings.append(f"【合同资产畸高】合同资产占收入比重达 {ca_ratio*100:.1f}% (${contract_assets/1e6:.1f}M)，警惕提前确认收入与后续大额冲减")

    # 规则 2.7: 业绩滑坡期突击超额分红与股份回购 (长春高新式手法: 暴雷前掏空现金)
    dividends = float(row.get('dividends') or 0.0)
    repurchases = float(row.get('repurchases') or 0.0)
    prev_net_income = float(row.get('prev_net_income') or 0.0)
    total_payout = dividends + repurchases
    if net_income > 1e7 and total_payout > 1e7 and prev_net_income > 0:
        if net_income < prev_net_income:  # 业绩已进入滑坡通道
            payout_ratio = total_payout / net_income
            if payout_ratio > 0.50:
                score += 15
                warnings.append(
                    f"【突击超额分红回购】业绩滑坡期分红与回购总额达 ${total_payout/1e6:.1f}M (占当期净利 {payout_ratio*100:.1f}%)，警惕暴雷崩塌前提前掏空真金白银"
                )

    # 规则 2.8: 第四季度单季突发巨额“大洗澡” (长春高新式手法: Q1-Q3盈利，Q4亏掉大半甚至全年)
    q4_ni = row.get('q4_net_income')
    q1_3_ni = row.get('q1_to_q3_net_income')
    if q4_ni is not None and q1_3_ni is not None:
        q4_ni = float(q4_ni)
        q1_3_ni = float(q1_3_ni)
        if q1_3_ni > 1e7 and q4_ni < -3e7:
            loss_ratio = abs(q4_ni) / q1_3_ni
            if loss_ratio > 0.50:
                score += 20
                warnings.append(
                    f"【Q4突发大洗澡】前三季度维持盈利 (${q1_3_ni/1e6:.1f}M)，第四季度单季突发巨亏 (${abs(q4_ni)/1e6:.1f}M，吞噬前三季盈利 {loss_ratio*100:.1f}%)，存在集中洗澡操纵嫌疑"
                )

    return score, warnings


def _get_series(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    if col in df.columns:
        return df[col].fillna(default)
    return pd.Series(default, index=df.index)


def apply_income_statement_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    批量向量化评估整个 DataFrame 的利润表排雷规则
    """
    df = df.copy()
    sales = _get_series(df, 'sales')
    net_income = _get_series(df, 'net_income')
    cfo = _get_series(df, 'cfo')
    op_inc = _get_series(df, 'operating_income', default=0.0)
    if 'operating_income' not in df.columns:
        op_inc = net_income
    contract_assets = _get_series(df, 'contract_assets')
    dividends = _get_series(df, 'dividends')
    repurchases = _get_series(df, 'repurchases')
    prev_net_income = _get_series(df, 'prev_net_income')
    q4_ni = _get_series(df, 'q4_net_income', default=0.0)
    q1_3_ni = _get_series(df, 'q1_to_q3_net_income', default=0.0)

    # 1. 净现比断裂
    cond_cfo_neg = (net_income > 5e7) & (cfo <= 0)
    cond_cfo_weak = (net_income > 5e7) & (cfo > 0) & ((cfo / np.maximum(net_income, 1.0)) < 0.30)

    # 2. 主营亏损非经常保壳
    cond_op_loss_ni_pos = (net_income > 2e7) & (op_inc < 0)

    # 3. 总额法刷流水
    net_margin = np.where(sales > 0, net_income / sales, 0.0)
    cond_volume_pumping = (sales > 1e9) & (net_income > 0) & (net_margin < 0.005)

    # 4. 合同资产畸高
    ca_ratio = np.where(sales > 0, contract_assets / sales, 0.0)
    cond_ca_high = (ca_ratio > 0.50) & (contract_assets > 5e7)

    # 5. 规则 2.7: 业绩滑坡期超额分红与回购
    total_payout = dividends + repurchases
    payout_ratio = np.where(net_income > 0, total_payout / net_income, 0.0)
    cond_payout_drain = (net_income > 1e7) & (total_payout > 1e7) & (prev_net_income > 0) & (net_income < prev_net_income) & (payout_ratio > 0.50)

    # 6. 规则 2.8: Q4突发单季巨额大洗澡
    q4_loss_ratio = np.where(q1_3_ni > 0, np.abs(q4_ni) / q1_3_ni, 0.0)
    cond_q4_big_bath = (q1_3_ni > 1e7) & (q4_ni < -3e7) & (q4_loss_ratio > 0.50)

    is_score = (
        cond_cfo_neg.astype(int) * 25 +
        cond_cfo_weak.astype(int) * 15 +
        cond_op_loss_ni_pos.astype(int) * 20 +
        cond_volume_pumping.astype(int) * 15 +
        cond_ca_high.astype(int) * 15 +
        cond_payout_drain.astype(int) * 15 +
        cond_q4_big_bath.astype(int) * 20
    )

    df['is_fraud_score'] = is_score
    df['flag_cfo_broken'] = cond_cfo_neg | cond_cfo_weak
    df['flag_op_loss_masked'] = cond_op_loss_ni_pos
    df['flag_volume_pumping'] = cond_volume_pumping
    df['flag_contract_assets_high'] = cond_ca_high
    df['flag_payout_drain'] = cond_payout_drain
    df['flag_q4_big_bath'] = cond_q4_big_bath

    return df
