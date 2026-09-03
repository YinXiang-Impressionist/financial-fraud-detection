# -*- coding: utf-8 -*-
"""
Statistical Forensic Accounting & Mathematical Anomaly Engine
纯统计与数理法务舞弊侦测模型 (拒绝任何新闻与舆情噪音，专注于纯数字分布与统计偏离度)

核心模块:
1. 修正琼斯模型 (Modified Jones Model, Dechow et al. 1995): 
   估计非操纵应计利润，直接提取管理层人为做账的“可操纵应计利润残差 (Discretionary Accruals)”
2. 跨科目时序与截面统计背离度 (Statistical Decoupling Z-Scores):
   - 应收-营收增速严重背离指数 (Z_AR_Sales)
   - 存货-成本结转背离指数 (Z_Inv_COGS)
   - 毛利率飙升与存货周转骤降逆向背离指数 (Z_GM_Turnover)
   - 净现比统计断裂指数 (Z_CFO_Decoupling)
"""

import os
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd


def compute_modified_jones_accrual(
    net_income: float,
    cfo: float,
    assets_t: float,
    assets_prev: float,
    sales_t: float,
    sales_prev: float,
    ar_t: float,
    ar_prev: float,
    ppe_net_t: float
) -> Dict[str, Any]:
    """
    修正琼斯模型 (Modified Jones Model):
    Total Accruals = Net Income - CFO
    Normal Accruals = a1 * (1/Assets_prev) + a2 * (ΔSales - ΔAR)/Assets_prev + a3 * (PPE/Assets_prev)
    Discretionary Accruals (DA) = Total Accruals/Assets_prev - Normal Accruals
    DA 即为管理层通过会计估计调节/伪造的纯数理可操纵利润
    """
    base_assets = assets_prev if assets_prev > 0 else (assets_t if assets_t > 0 else 1.0)
    
    # 总应计利润
    total_accruals = (net_income - cfo) / base_assets
    
    delta_sales = sales_t - sales_prev
    delta_ar = ar_t - ar_prev
    adjusted_delta_rev = (delta_sales - delta_ar) / base_assets
    ppe_ratio = ppe_net_t / base_assets
    
    # 采用经典实证标准参数 (Dechow 1995 cross-sectional benchmarks: a1 ≈ 0, a2 ≈ 0.05, a3 ≈ -0.10)
    expected_accruals = 0.05 * adjusted_delta_rev - 0.10 * ppe_ratio
    
    # 可操纵应计利润残差 DA
    da = total_accruals - expected_accruals
    
    # 统计异常判定: DA > 0.08 即为高操纵水分 (通过激进权责发生制或虚构应收虚增利润)
    is_high_da = bool(da > 0.08)
    
    return {
        "total_accruals_ratio": round(float(total_accruals), 4),
        "discretionary_accruals": round(float(da), 4),
        "is_abnormal_discretionary_accrual": is_high_da
    }


def compute_statistical_decoupling_metrics(
    sales_t: float, sales_prev: float,
    cogs_t: float, cogs_prev: float,
    ar_t: float, ar_prev: float,
    inv_t: float, inv_prev: float,
    cfo_t: float, net_income_t: float
) -> Dict[str, Any]:
    """
    纯数理统计背离度检测:
    1. 应收 vs 营收增速差: (ΔAR/AR_prev) - (ΔSales/Sales_prev)
    2. 存货 vs 成本增速差: (ΔInv/Inv_prev) - (ΔCOGS/COGS_prev)
    3. 毛利 vs 周转背离度: 毛利率提升但存货周转天数大幅拉长
    4. 净现比偏离度
    """
    warnings = []
    stat_score = 0

    zh = os.environ.get("FORENSIC_LANG", "en").lower().startswith("zh")

    # 1. 应收账款增速远超营收增速统计偏离
    ar_growth = ((ar_t - ar_prev) / ar_prev) if ar_prev > 0 else 0.0
    sales_growth = ((sales_t - sales_prev) / sales_prev) if sales_prev > 0 else 0.0
    ar_sales_divergence = ar_growth - sales_growth

    if ar_sales_divergence > 0.25 and (ar_t - ar_prev) > 1e7:
        stat_score += 20
        msg = f"【应收-营收统计背离】应收账款增速({ar_growth*100:.1f}%)超营收增速({sales_growth*100:.1f}%)达 {ar_sales_divergence*100:.1f}%，统计显著异常" if zh else f"[AR vs Revenue Decoupling] Receivables growth ({ar_growth*100:.1f}%) significantly exceeded revenue growth ({sales_growth*100:.1f}%) by {ar_sales_divergence*100:.1f}%, indicating abnormal credit expansion"
        warnings.append(msg)

    # 2. 存货积压增速远超营业成本结转增速
    inv_growth = ((inv_t - inv_prev) / inv_prev) if inv_prev > 0 else 0.0
    cogs_growth = ((cogs_t - cogs_prev) / cogs_prev) if cogs_prev > 0 else 0.0
    inv_cogs_divergence = inv_growth - cogs_growth

    if inv_cogs_divergence > 0.30 and (inv_t - inv_prev) > 1e7:
        stat_score += 20
        msg = f"【存货-成本统计背离】存货增速({inv_growth*100:.1f}%)超营业成本增速({cogs_growth*100:.1f}%)达 {inv_cogs_divergence*100:.1f}%，少结转成本虚增毛利嫌疑" if zh else f"[Inventory vs Cost Decoupling] Inventory growth ({inv_growth*100:.1f}%) exceeded COGS growth ({cogs_growth*100:.1f}%) by {inv_cogs_divergence*100:.1f}%, signaling inventory accumulation or deferred cost recognition"
        warnings.append(msg)

    # 3. 毛利率走高与存货周转放缓反向背离 (Detective Red Flag)
    gm_t = ((sales_t - cogs_t) / sales_t) if sales_t > 0 else 0.0
    gm_prev = ((sales_prev - cogs_prev) / sales_prev) if sales_prev > 0 else 0.0
    inv_turnover_t = (cogs_t / inv_t) if inv_t > 0 else 0.0
    inv_turnover_prev = (cogs_prev / inv_prev) if inv_prev > 0 else 0.0

    if (gm_t - gm_prev) > 0.03 and inv_turnover_prev > 0 and (inv_turnover_t / inv_turnover_prev) < 0.80:
        stat_score += 20
        msg = f"【毛利-周转反向背离】毛利率逆势扩张 {((gm_t-gm_prev)*100):.1f}% 但存货周转效率骤降 {((1 - inv_turnover_t/inv_turnover_prev)*100):.1f}%，典型虚构高毛利表象" if zh else f"[Margin vs Turnover Inversion] Gross margin expanded {((gm_t-gm_prev)*100):.1f}% despite inventory turnover plunging {((1 - inv_turnover_t/inv_turnover_prev)*100):.1f}%, contradicting organic market dynamics"
        warnings.append(msg)

    # 4. 净现比严重背离 (硬核现金流统计断裂)
    if net_income_t > 5e7:
        if cfo_t <= 0:
            stat_score += 25
            msg = f"【净现比恶性断裂】净利润盈利 (${net_income_t/1e6:.1f}M) 但实际经营现金净流出 (${cfo_t/1e6:.1f}M)" if zh else f"[Malignant Cash Decoupling] Positive Net Income (${net_income_t/1e6:.1f}M) accompanied by negative Operating Cash Flow (${cfo_t/1e6:.1f}M)"
            warnings.append(msg)
        elif (cfo_t / net_income_t) < 0.30:
            stat_score += 15
            msg = f"【现金流造血孱弱】净现比仅为 {cfo_t/net_income_t:.2f} (远低于0.5警戒线)" if zh else f"[Weak Cash Generation] CFO to Net Income ratio is {cfo_t/net_income_t:.2f} (critically below 0.50 benchmark)"
            warnings.append(msg)

    return {
        "stat_score": stat_score,
        "warnings": warnings,
        "ar_growth": round(float(ar_growth), 3),
        "sales_growth": round(float(sales_growth), 3),
        "ar_sales_divergence": round(float(ar_sales_divergence), 3),
        "inv_cogs_divergence": round(float(inv_cogs_divergence), 3),
        "gross_margin_current": round(float(gm_t), 3),
        "gross_margin_prev": round(float(gm_prev), 3)
    }
