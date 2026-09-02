# -*- coding: utf-8 -*-
"""
Dechow F-Score & Sloan Accrual Quality Model
德乔 F-Score 财务重述概率与 Sloan 净应计异象模型 (Dechow et al., 2011; Sloan, 1996)

判定阈值:
- F-Score > 1.0: 舞弊与重大财务重述(Restatement)概率高于市场基准平均线
- F-Score > 2.45: 极高造假与重述风险 (High Fraud/Restatement Risk)
- Sloan Accruals > 0.10: 高应计利润、纸面富贵、盈利缺乏现金支持
"""

from typing import Dict, Any
import numpy as np
import pandas as pd


def compute_sloan_accrual(net_income: float, cfo: float, assets: float) -> Dict[str, Any]:
    """
    计算 Sloan 经典净应计利润异象指标
    Accrual = (Net Income - CFO) / Total Assets
    """
    if assets <= 0:
        return {"sloan_accrual": 0.0, "is_high_accrual": False}
    accrual = (net_income - cfo) / assets
    return {
        "sloan_accrual": round(float(accrual), 4),
        "is_high_accrual": bool(accrual > 0.10)
    }


def compute_dechow_f_score(
    assets_t: float, assets_prev: float,
    net_income_t: float, cfo_t: float,
    ar_t: float, ar_prev: float,
    inv_t: float, inv_prev: float,
    sales_t: float, sales_prev: float,
    cash_t: float, ppe_net_t: float
) -> Dict[str, Any]:
    """
    单条记录计算德乔 F-Score (Dechow 2011 Model 1 / Model 2 特征简化版)
    """
    avg_assets = (assets_t + assets_prev) / 2.0 if (assets_t + assets_prev) > 0 else max(assets_t, 1.0)
    
    # 1. RSST / 总应计项对平均资产比
    total_accruals = (net_income_t - cfo_t) / avg_assets

    # 2. 应收账款变动 / 平均总资产
    chg_rec = (ar_t - ar_prev) / avg_assets

    # 3. 存货变动 / 平均总资产
    chg_inv = (inv_t - inv_prev) / avg_assets

    # 4. 软资产占比 Soft Assets Ratio = (Total Assets - PP&E - Cash) / Total Assets
    soft_assets = max(0.0, assets_t - ppe_net_t - cash_t) / assets_t if assets_t > 0 else 0.0

    # 5. 现金销售增长异常 = (Sales_t - ΔAR_t) / (Sales_prev - ΔAR_prev)
    cash_sales_t = sales_t - (ar_t - ar_prev)
    cash_sales_prev = sales_prev
    chg_cash_sales = (cash_sales_t - cash_sales_prev) / cash_sales_prev if cash_sales_prev > 0 else 0.0

    # 综合 F-Score 预测值 (无偏比率，以 1.0 为基准线)
    # 逻辑回归基线截距与主要权重系数拟合
    predicted_val = (
        -7.893
        + 0.790 * total_accruals
        + 2.518 * chg_rec
        + 1.191 * chg_inv
        + 1.979 * soft_assets
        + 0.171 * chg_cash_sales
    )
    
    # 转换为概率或比值 (对数胜算比变换 F-Score = Prob / Unconditional Prob)
    # 平均无条件舞弊重述概率约为 0.0037 (0.37%)
    unconditional_prob = 0.0037
    prob = 1.0 / (1.0 + np.exp(-predicted_val))
    f_score = prob / unconditional_prob

    return {
        "f_score": round(float(f_score), 2),
        "is_high_f_score": bool(f_score > 1.0),
        "is_extreme_f_score": bool(f_score > 2.45),
        "total_accruals": round(float(total_accruals), 4),
        "soft_assets_ratio": round(float(soft_assets), 3),
        "chg_rec": round(float(chg_rec), 4),
        "chg_inv": round(float(chg_inv), 4)
    }


def compute_dechow_f_dataframe(df: pd.DataFrame, entity_col: str = 'cik', time_col: str = 'period') -> pd.DataFrame:
    """
    向量化计算 DataFrame 的 Sloan 净应计与 Dechow F-Score
    """
    df = df.copy()
    if entity_col in df.columns and time_col in df.columns:
        df = df.sort_values(by=[entity_col, time_col]).reset_index(drop=True)
        grp = df.groupby(entity_col)
        for col in ['assets', 'ar', 'inv', 'sales']:
            if col in df.columns and f'{col}_prev' not in df.columns:
                df[f'{col}_prev'] = grp[col].shift(1)

    assets = df.get('assets', 0.0)
    assets_prev = df.get('assets_prev', assets)
    avg_assets = np.where((assets + assets_prev) > 0, (assets + assets_prev) / 2.0, np.maximum(assets, 1.0))
    
    net_income = df.get('net_income', 0.0)
    cfo = df.get('cfo', 0.0)
    ar = df.get('ar', 0.0)
    ar_prev = df.get('ar_prev', 0.0)
    inv = df.get('inv', 0.0)
    inv_prev = df.get('inv_prev', 0.0)
    ppe_net = df.get('ppe_net', 0.0)
    cash = df.get('cash', 0.0)
    sales = df.get('sales', 0.0)
    sales_prev = df.get('sales_prev', 0.0)

    # 1. Sloan 经典净应计
    sloan = np.where(assets > 0, (net_income - cfo) / assets, 0.0)
    df['sloan_accrual'] = np.round(sloan, 4)
    df['sloan_is_high'] = df['sloan_accrual'] > 0.10

    # 2. Dechow 指标项
    chg_rec = (ar - ar_prev) / avg_assets
    chg_inv = (inv - inv_prev) / avg_assets
    soft_assets = np.where(assets > 0, np.maximum(0.0, assets - ppe_net - cash) / assets, 0.0)
    
    cash_sales = sales - (ar - ar_prev)
    chg_cash_sales = np.where(sales_prev > 0, (cash_sales - sales_prev) / sales_prev, 0.0)

    predicted_val = (
        -7.893
        + 0.790 * sloan
        + 2.518 * np.clip(chg_rec, -1.0, 1.0)
        + 1.191 * np.clip(chg_inv, -1.0, 1.0)
        + 1.979 * np.clip(soft_assets, 0.0, 1.0)
        + 0.171 * np.clip(chg_cash_sales, -2.0, 2.0)
    )

    unconditional_prob = 0.0037
    prob = 1.0 / (1.0 + np.exp(-predicted_val))
    f_score = prob / unconditional_prob

    df['dechow_f_score'] = np.round(f_score, 2)
    df['dechow_is_high_risk'] = df['dechow_f_score'] > 1.0
    df['dechow_soft_assets'] = np.round(soft_assets, 3)

    return df
