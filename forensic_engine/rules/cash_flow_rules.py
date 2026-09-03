# -*- coding: utf-8 -*-
"""
Cash Flow Forensic Audit Rules
现金流量表勾稽断裂规则集

包含规则:
- 规则 3.1: “假现金流”自循环与投资-经营镜像对冲 (Circular Flow Washing)
- 规则 3.2: 自由现金流持续失血与筹资借新还旧 (FCF Chronic Bleeding)
- 规则 3.3: 销售收现比断裂 (Cash Collection Decoupling)
"""

import os
from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd


def check_cash_flow_rules(row: Dict[str, Any]) -> Tuple[int, List[str]]:
    """
    单条记录现金流勾稽规则检测
    """
    score = 0
    warnings = []
    zh = os.environ.get("FORENSIC_LANG", "en").lower().startswith("zh")

    cfo = float(row.get('cfo') or 0.0)
    cfi = float(row.get('cfi') or 0.0)
    cff = float(row.get('cff') or 0.0)
    capex = float(row.get('capex') or 0.0)
    sales = float(row.get('sales') or row.get('revenue') or 0.0)
    cash_from_sales = float(row.get('cash_from_sales') or 0.0)

    # 自由现金流 FCF = CFO - Capex
    if capex > 0:
        fcf = cfo - capex
        if fcf < -5e7 and cff > 5e7:
            score += 15
            msg = f"【造血失血借新还旧】自由现金流严重失血 (${fcf/1e6:.1f}M) 且完全依赖外部大额借款筹资支撑周转" if zh else f"[Chronic FCF Bleeding] Severe negative Free Cash Flow (${fcf/1e6:.1f}M) financed via continuous debt issuance"
            warnings.append(msg)

    # 销售收现比检查
    if sales > 5e7 and cash_from_sales > 0:
        cash_ratio = cash_from_sales / sales
        if cash_ratio < 0.75:
            score += 15
            msg = f"【销售收现率断裂】销售收现比仅为 {cash_ratio*100:.1f}%，与营业收入严重脱节，涉嫌虚构销售回款" if zh else f"[Cash Collection Breakdown] Cash collection ratio is {cash_ratio*100:.1f}%, decoupled from revenue, signaling fictitious sales"
            warnings.append(msg)

    # 投资现金流流出与经营现金流入镜像自循环嫌疑
    if cfo > 5e7 and cfi < -5e7:
        # 若投资流出与经营流入高度接近 (如比例在 0.85 ~ 1.15 之间)
        ratio = abs(cfi) / cfo
        if 0.85 <= ratio <= 1.15:
            score += 20
            msg = f"【疑似体外循环洗钱】投资流出 (${abs(cfi)/1e6:.1f}M) 与经营流入 (${cfo/1e6:.1f}M) 呈现高度镜像对冲形态" if zh else f"[Suspected Cash Recycling] Investing outflow (${abs(cfi)/1e6:.1f}M) and operating inflow (${cfo/1e6:.1f}M) display mirror hedging patterns"
            warnings.append(msg)

    return score, warnings


def _get_series(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    if col in df.columns:
        return df[col].fillna(default)
    return pd.Series(default, index=df.index)


def apply_cash_flow_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    批量向量化评估整个 DataFrame 的现金流勾稽规则
    """
    df = df.copy()
    cfo = _get_series(df, 'cfo')
    cfi = _get_series(df, 'cfi')
    cff = _get_series(df, 'cff')
    capex = _get_series(df, 'capex')
    sales = _get_series(df, 'sales')
    cash_from_sales = _get_series(df, 'cash_from_sales')

    fcf = cfo - capex
    cond_fcf_bleeding = (capex > 0) & (fcf < -5e7) & (cff > 5e7)

    cash_ratio = np.where(sales > 0, cash_from_sales / sales, 1.0)
    cond_collection_low = (sales > 5e7) & (cash_from_sales > 0) & (cash_ratio < 0.75)

    mirror_ratio = np.where(cfo > 0, np.abs(cfi) / cfo, 0.0)
    cond_mirror_flow = (cfo > 5e7) & (cfi < -5e7) & (mirror_ratio >= 0.85) & (mirror_ratio <= 1.15)

    cf_score = (
        cond_fcf_bleeding.astype(int) * 15 +
        cond_collection_low.astype(int) * 15 +
        cond_mirror_flow.astype(int) * 20
    )

    df['cf_fraud_score'] = cf_score
    df['flag_fcf_bleeding'] = cond_fcf_bleeding
    df['flag_collection_low'] = cond_collection_low
    df['flag_mirror_flow'] = cond_mirror_flow

    return df
