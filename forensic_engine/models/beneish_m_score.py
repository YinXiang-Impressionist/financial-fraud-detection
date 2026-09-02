# -*- coding: utf-8 -*-
"""
Beneish M-Score 8-Variable Manipulation Detection Model
贝尼斯 M-Score 8 变量财务操纵预测模型 (Messod Beneish, 1999)

判定标准:
- M-Score > -1.78: 存在极高财报操纵概率 (High Probability of Manipulation)
- M-Score <= -1.78: 处于正常未操纵区间 (Normal)
"""

from typing import Dict, Any, Union
import numpy as np
import pandas as pd


def compute_beneish_components(
    sales_t: float, sales_prev: float,
    cogs_t: float, cogs_prev: float,
    ar_t: float, ar_prev: float,
    assets_t: float, assets_prev: float,
    current_assets_t: float, current_assets_prev: float,
    ppe_net_t: float, ppe_net_prev: float,
    depr_t: float, depr_prev: float,
    sga_t: float, sga_prev: float,
    liabilities_t: float, liabilities_prev: float,
    net_income_t: float, cfo_t: float,
    securities_t: float = 0.0, securities_prev: float = 0.0
) -> Dict[str, float]:
    """
    计算单期 Beneish M-Score 的 8 大子变量及综合评分
    """
    # 1. DSRI (Days Sales in Receivables Index)
    dsr_t = (ar_t / sales_t) if sales_t > 0 else 0.0
    dsr_prev = (ar_prev / sales_prev) if sales_prev > 0 else 0.0
    dsri = (dsr_t / dsr_prev) if dsr_prev > 0 else 1.0

    # 2. GMI (Gross Margin Index)
    gm_t = ((sales_t - cogs_t) / sales_t) if sales_t > 0 else 0.0
    gm_prev = ((sales_prev - cogs_prev) / sales_prev) if sales_prev > 0 else 0.0
    gmi = (gm_prev / gm_t) if gm_t > 0 else 1.0

    # 3. AQI (Asset Quality Index)
    # 非流动资产中除固定资产和证券以外的资产占比 (反映费用资本化或资产水分)
    non_hard_t = 1.0 - ((current_assets_t + ppe_net_t + securities_t) / assets_t) if assets_t > 0 else 0.0
    non_hard_prev = 1.0 - ((current_assets_prev + ppe_net_prev + securities_prev) / assets_prev) if assets_prev > 0 else 0.0
    non_hard_t = max(0.0, non_hard_t)
    non_hard_prev = max(0.0, non_hard_prev)
    aqi = (non_hard_t / non_hard_prev) if non_hard_prev > 0 else 1.0

    # 4. SGI (Sales Growth Index)
    sgi = (sales_t / sales_prev) if sales_prev > 0 else 1.0

    # 5. DEPI (Depreciation Index)
    depr_denom_t = depr_t + ppe_net_t
    depr_denom_prev = depr_prev + ppe_net_prev
    depr_rate_t = (depr_t / depr_denom_t) if depr_denom_t > 0 else 0.0
    depr_rate_prev = (depr_prev / depr_denom_prev) if depr_denom_prev > 0 else 0.0
    depi = (depr_rate_prev / depr_rate_t) if depr_rate_t > 0 else 1.0

    # 6. SGAI (Sales, General and Administrative Expenses Index)
    sga_ratio_t = (sga_t / sales_t) if sales_t > 0 else 0.0
    sga_ratio_prev = (sga_prev / sales_prev) if sales_prev > 0 else 0.0
    sgai = (sga_ratio_t / sga_ratio_prev) if sga_ratio_prev > 0 else 1.0

    # 7. LVGI (Leverage Index)
    lev_t = (liabilities_t / assets_t) if assets_t > 0 else 0.0
    lev_prev = (liabilities_prev / assets_prev) if assets_prev > 0 else 0.0
    lvgi = (lev_t / lev_prev) if lev_prev > 0 else 1.0

    # 8. TATA (Total Accruals to Total Assets)
    tata = ((net_income_t - cfo_t) / assets_t) if assets_t > 0 else 0.0

    # 限制异常极值 (防极端异常值拉爆回归方程)
    dsri_c = float(np.clip(dsri, 0.0, 10.0))
    gmi_c = float(np.clip(gmi, 0.0, 10.0))
    aqi_c = float(np.clip(aqi, 0.0, 10.0))
    sgi_c = float(np.clip(sgi, 0.0, 10.0))
    depi_c = float(np.clip(depi, 0.0, 10.0))
    sgai_c = float(np.clip(sgai, 0.0, 10.0))
    lvgi_c = float(np.clip(lvgi, 0.0, 10.0))
    tata_c = float(np.clip(tata, -2.0, 2.0))

    # Beneish 8-Variable Standard Equation:
    m_score = (
        -4.84
        + 0.920 * dsri_c
        + 0.528 * gmi_c
        + 0.404 * aqi_c
        + 0.892 * sgi_c
        + 0.115 * depi_c
        - 0.172 * sgai_c
        + 4.037 * tata_c
        + 0.0327 * lvgi_c
    )

    is_manipulator = bool(m_score > -1.78)

    return {
        "m_score": round(m_score, 3),
        "is_manipulator": is_manipulator,
        "dsri": round(dsri, 3),
        "gmi": round(gmi, 3),
        "aqi": round(aqi, 3),
        "sgi": round(sgi, 3),
        "depi": round(depi, 3),
        "sgai": round(sgai, 3),
        "lvgi": round(lvgi, 3),
        "tata": round(tata, 4)
    }


def compute_beneish_dataframe(df: pd.DataFrame, entity_col: str = 'cik', time_col: str = 'period') -> pd.DataFrame:
    """
    向量化批量计算整个 DataFrame 的 Beneish M-Score
    输入 DataFrame 需包含当前期和前期的财务科目，或者包含历史跨期序列自动按 entity_col 进行 shift(1)
    """
    df = df.copy()
    if entity_col in df.columns and time_col in df.columns:
        df = df.sort_values(by=[entity_col, time_col]).reset_index(drop=True)
        grp = df.groupby(entity_col)
        
        # 自动生成上期值 (若未预先提供)
        for col in ['sales', 'cogs', 'ar', 'assets', 'current_assets', 'ppe_net', 'depr', 'sga', 'liabilities']:
            if col in df.columns and f'{col}_prev' not in df.columns:
                df[f'{col}_prev'] = grp[col].shift(1)

    # 填充缺失为 0
    cols_to_fill = [
        'sales', 'sales_prev', 'cogs', 'cogs_prev', 'ar', 'ar_prev',
        'assets', 'assets_prev', 'current_assets', 'current_assets_prev',
        'ppe_net', 'ppe_net_prev', 'depr', 'depr_prev', 'sga', 'sga_prev',
        'liabilities', 'liabilities_prev', 'net_income', 'cfo'
    ]
    for c in cols_to_fill:
        if c not in df.columns:
            df[c] = 0.0
        else:
            df[c] = df[c].fillna(0.0)

    with np.errstate(divide='ignore', invalid='ignore'):
        # 1. DSRI
        dsr_t = np.where(df['sales'] > 0, df['ar'] / df['sales'], 0.0)
        dsr_prev = np.where(df['sales_prev'] > 0, df['ar_prev'] / df['sales_prev'], 0.0)
        dsri = np.where(dsr_prev > 0, dsr_t / dsr_prev, 1.0)

        # 2. GMI
        gm_t = np.where(df['sales'] > 0, (df['sales'] - df['cogs']) / df['sales'], 0.0)
        gm_prev = np.where(df['sales_prev'] > 0, (df['sales_prev'] - df['cogs_prev']) / df['sales_prev'], 0.0)
        gmi = np.where(gm_t > 0, gm_prev / gm_t, 1.0)

        # 3. AQI
        non_hard_t = np.where(df['assets'] > 0, 1.0 - (df['current_assets'] + df['ppe_net']) / df['assets'], 0.0)
        non_hard_prev = np.where(df['assets_prev'] > 0, 1.0 - (df['current_assets_prev'] + df['ppe_net_prev']) / df['assets_prev'], 0.0)
        non_hard_t = np.clip(non_hard_t, 0.0, None)
        non_hard_prev = np.clip(non_hard_prev, 0.0, None)
        aqi = np.where(non_hard_prev > 0, non_hard_t / non_hard_prev, 1.0)

        # 4. SGI
        sgi = np.where(df['sales_prev'] > 0, df['sales'] / df['sales_prev'], 1.0)

        # 5. DEPI
        depr_denom_t = df['depr'] + df['ppe_net']
        depr_denom_prev = df['depr_prev'] + df['ppe_net_prev']
        depr_rate_t = np.where(depr_denom_t > 0, df['depr'] / depr_denom_t, 0.0)
        depr_rate_prev = np.where(depr_denom_prev > 0, df['depr_prev'] / depr_denom_prev, 0.0)
        depi = np.where(depr_rate_t > 0, depr_rate_prev / depr_rate_t, 1.0)

        # 6. SGAI
        sga_r_t = np.where(df['sales'] > 0, df['sga'] / df['sales'], 0.0)
        sga_r_prev = np.where(df['sales_prev'] > 0, df['sga_prev'] / df['sales_prev'], 0.0)
        sgai = np.where(sga_r_prev > 0, sga_r_t / sga_r_prev, 1.0)

        # 7. LVGI
        lev_t = np.where(df['assets'] > 0, df['liabilities'] / df['assets'], 0.0)
        lev_prev = np.where(df['assets_prev'] > 0, df['liabilities_prev'] / df['assets_prev'], 0.0)
        lvgi = np.where(lev_prev > 0, lev_t / lev_prev, 1.0)

        # 8. TATA
        tata = np.where(df['assets'] > 0, (df['net_income'] - df['cfo']) / df['assets'], 0.0)

        # 补全 NaN/Inf 为默认值
        dsri = np.nan_to_num(dsri, nan=1.0, posinf=5.0, neginf=1.0)
        gmi = np.nan_to_num(gmi, nan=1.0, posinf=5.0, neginf=1.0)
        aqi = np.nan_to_num(aqi, nan=1.0, posinf=5.0, neginf=1.0)
        sgi = np.nan_to_num(sgi, nan=1.0, posinf=5.0, neginf=1.0)
        depi = np.nan_to_num(depi, nan=1.0, posinf=5.0, neginf=1.0)
        sgai = np.nan_to_num(sgai, nan=1.0, posinf=5.0, neginf=1.0)
        lvgi = np.nan_to_num(lvgi, nan=1.0, posinf=5.0, neginf=1.0)
        tata = np.nan_to_num(tata, nan=0.0, posinf=1.0, neginf=-1.0)

    # Clip values to prevent arithmetic overflow in extreme outlier cases
    dsri = np.clip(dsri, 0.0, 10.0)
    gmi = np.clip(gmi, 0.0, 10.0)
    aqi = np.clip(aqi, 0.0, 10.0)
    sgi = np.clip(sgi, 0.0, 10.0)
    depi = np.clip(depi, 0.0, 10.0)
    sgai = np.clip(sgai, 0.0, 10.0)
    lvgi = np.clip(lvgi, 0.0, 10.0)
    tata = np.clip(tata, -2.0, 2.0)

    m_score = (
        -4.84
        + 0.920 * dsri
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.037 * tata
        + 0.0327 * lvgi
    )

    df['beneish_m_score'] = np.round(m_score, 3)
    df['beneish_is_manipulator'] = df['beneish_m_score'] > -1.78
    df['beneish_dsri'] = np.round(dsri, 3)
    df['beneish_gmi'] = np.round(gmi, 3)
    df['beneish_aqi'] = np.round(aqi, 3)
    df['beneish_sgi'] = np.round(sgi, 3)
    df['beneish_depi'] = np.round(depi, 3)
    df['beneish_sgai'] = np.round(sgai, 3)
    df['beneish_lvgi'] = np.round(lvgi, 3)
    df['beneish_tata'] = np.round(tata, 4)

    return df
