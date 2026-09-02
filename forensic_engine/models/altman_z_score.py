# -*- coding: utf-8 -*-
"""
Altman Z-Score Financial Distress & Bankruptcy Prediction Model
奥特曼 Z-Score 财务危机与破产预警模型 (Edward Altman, 1968 / 1983)

判定阈值:
- Z < 1.81: 危机/红色警报区 (Distress Zone) - 企业面临严重破产危机，存在极高财务粉饰与造假动机
- 1.81 <= Z <= 2.99: 灰色观察区 (Grey Zone) - 财务健康状况堪忧
- Z > 2.99: 安全区 (Safe Zone) - 财务结构稳健
"""

from typing import Dict, Any
import numpy as np
import pandas as pd


def compute_altman_z(
    assets: float,
    current_assets: float,
    current_liabilities: float,
    retained_earnings: float,
    ebit: float,
    equity: float,
    liabilities: float,
    sales: float,
    market_cap: float = 0.0
) -> Dict[str, Any]:
    """
    单条记录计算奥特曼 Z-Score (支持有市值与纯财报账面权益两种模式)
    """
    if assets <= 0 or liabilities <= 0:
        return {
            "z_score": 0.0,
            "zone": "未知",
            "is_distressed": False,
            "x1_wc_ta": 0.0,
            "x2_re_ta": 0.0,
            "x3_ebit_ta": 0.0,
            "x4_equity_tl": 0.0,
            "x5_sales_ta": 0.0
        }

    # X1: 营运资金 / 总资产 (流动性)
    working_capital = current_assets - current_liabilities
    x1 = working_capital / assets

    # X2: 留存收益 / 总资产 (积累盈利能力)
    x2 = retained_earnings / assets

    # X3: 息税前利润 (EBIT) / 总资产 (真实资产产出率)
    x3 = ebit / assets

    # X4: 权益总额 / 总负债 (资本结构杠杆，若有市值则用市值，否则使用股东权益账面净资产)
    equity_val = market_cap if market_cap > 0 else equity
    x4 = max(0.0, equity_val) / liabilities

    # X5: 营业收入 / 总资产 (资产周转效率)
    x5 = max(0.0, sales) / assets

    # 标准 Altman Z-Score 公式:
    z_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 0.999 * x5

    if z_score < 1.81:
        zone = "红色危机区(Distress)"
        is_distressed = True
    elif z_score <= 2.99:
        zone = "灰色观察区(Grey)"
        is_distressed = False
    else:
        zone = "绿色安全区(Safe)"
        is_distressed = False

    return {
        "z_score": round(float(z_score), 2),
        "zone": zone,
        "is_distressed": is_distressed,
        "x1_wc_ta": round(float(x1), 3),
        "x2_re_ta": round(float(x2), 3),
        "x3_ebit_ta": round(float(x3), 3),
        "x4_equity_tl": round(float(x4), 3),
        "x5_sales_ta": round(float(x5), 3)
    }


def compute_altman_z_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    向量化批量计算整个 DataFrame 的 Altman Z-Score
    """
    df = df.copy()

    # 必需列兼容性处理
    assets = df['assets'] if 'assets' in df.columns else pd.Series(0.0, index=df.index)
    curr_assets = df['current_assets'] if 'current_assets' in df.columns else df.get('assets', 0.0) * 0.4
    curr_liab = df['current_liabilities'] if 'current_liabilities' in df.columns else df.get('liabilities', 0.0) * 0.5
    retained_earnings = df['retained_earnings'] if 'retained_earnings' in df.columns else df.get('equity', 0.0) * 0.5
    ebit = df['operating_income'] if 'operating_income' in df.columns else df.get('net_income', 0.0)
    equity = df['equity'] if 'equity' in df.columns else pd.Series(0.0, index=df.index)
    liabilities = df['liabilities'] if 'liabilities' in df.columns else pd.Series(0.0, index=df.index)
    sales = df['sales'] if 'sales' in df.columns else pd.Series(0.0, index=df.index)
    market_cap = df['market_cap'] if 'market_cap' in df.columns else pd.Series(0.0, index=df.index)

    # 向量化计算各项比率
    safe_assets = np.where(assets > 0, assets, np.nan)
    safe_liab = np.where(liabilities > 0, liabilities, np.nan)

    x1 = (curr_assets - curr_liab) / safe_assets
    x2 = retained_earnings / safe_assets
    x3 = ebit / safe_assets

    equity_term = np.where(market_cap > 0, market_cap, equity)
    x4 = np.maximum(0.0, equity_term) / safe_liab
    x5 = np.maximum(0.0, sales) / safe_assets

    # 缺失值填充为 0
    x1 = np.nan_to_num(x1, nan=0.0)
    x2 = np.nan_to_num(x2, nan=0.0)
    x3 = np.nan_to_num(x3, nan=0.0)
    x4 = np.nan_to_num(x4, nan=0.0)
    x5 = np.nan_to_num(x5, nan=0.0)

    # Altman 线性模型
    z_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 0.999 * x5
    z_score = np.where(assets > 0, z_score, 0.0)

    # 分区标记
    df['altman_z_score'] = np.round(z_score, 2)
    df['altman_is_distressed'] = df['altman_z_score'] < 1.81
    df['altman_zone'] = np.where(
        df['altman_z_score'] < 1.81,
        "红色危机区",
        np.where(df['altman_z_score'] <= 2.99, "灰色观察区", "绿色安全区")
    )
    df['altman_x1_wc_ta'] = np.round(x1, 3)
    df['altman_x2_re_ta'] = np.round(x2, 3)
    df['altman_x3_ebit_ta'] = np.round(x3, 3)
    df['altman_x4_equity_tl'] = np.round(x4, 3)
    df['altman_x5_sales_ta'] = np.round(x5, 3)

    return df
