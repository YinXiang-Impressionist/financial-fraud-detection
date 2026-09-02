# -*- coding: utf-8 -*-
"""
Forensic Audit Evaluator & High-Performance Vectorized Engine
纯数理统计与法务会计量化排雷综合评估引擎 (100% 聚焦纯数据分布、统计背离与计量模型，杜绝新闻与舆情噪音)
"""

from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from .models.beneish_m_score import compute_beneish_components, compute_beneish_dataframe
from .models.altman_z_score import compute_altman_z, compute_altman_z_dataframe
from .models.dechow_f_score import compute_sloan_accrual, compute_dechow_f_score, compute_dechow_f_dataframe
from .models.statistical_anomalies import compute_modified_jones_accrual, compute_statistical_decoupling_metrics
from .rules.balance_sheet_rules import check_balance_sheet_rules, apply_balance_sheet_dataframe
from .rules.income_statement_rules import check_income_statement_rules, apply_income_statement_dataframe
from .rules.cash_flow_rules import check_cash_flow_rules, apply_cash_flow_dataframe
from .tag_mapping import normalize_dataframe_columns, normalize_record_dict


class ForensicEvaluator:
    """
    侦探级数理法务排雷评估器 (Detective Forensic Engine)
    基于修正琼斯模型、贝尼斯 M-Score、奥特曼 Z-Score、Sloan 净应计及跨科目统计背离度
    """

    @staticmethod
    def evaluate_single(record: Dict[str, Any], prev_record: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        单条报表毫秒级数理统计排雷与深度体检
        """
        curr = normalize_record_dict(record)
        prev = normalize_record_dict(prev_record) if prev_record else {}

        all_warnings: List[str] = []
        total_score = 0

        # ----------------------------------------------------
        # 1. 数理统计模型 1: 贝尼斯 M-Score 8 变量操纵预测
        # ----------------------------------------------------
        beneish_res = {}
        if prev:
            beneish_res = compute_beneish_components(
                sales_t=curr.get('sales', 0.0), sales_prev=prev.get('sales', 0.0),
                cogs_t=curr.get('cogs', 0.0), cogs_prev=prev.get('cogs', 0.0),
                ar_t=curr.get('ar', 0.0), ar_prev=prev.get('ar', 0.0),
                assets_t=curr.get('assets', 0.0), assets_prev=prev.get('assets', 0.0),
                current_assets_t=curr.get('current_assets', 0.0), current_assets_prev=prev.get('current_assets', 0.0),
                ppe_net_t=curr.get('ppe_net', 0.0), ppe_net_prev=prev.get('ppe_net', 0.0),
                depr_t=curr.get('depr', 0.0), depr_prev=prev.get('depr', 0.0),
                sga_t=curr.get('sga', 0.0), sga_prev=prev.get('sga', 0.0),
                liabilities_t=curr.get('liabilities', 0.0), liabilities_prev=prev.get('liabilities', 0.0),
                net_income_t=curr.get('net_income', 0.0), cfo_t=curr.get('cfo', 0.0)
            )
            if beneish_res.get('is_manipulator'):
                total_score += 25
                all_warnings.append(f"【Beneish操纵高危】8变量M-Score达 {beneish_res['m_score']} (显著突破 -1.78 统计阈值)，存在极大概率系统性操纵")

        # ----------------------------------------------------
        # 2. 数理统计模型 2: 修正琼斯模型 (Modified Jones) 可操纵应计利润
        # ----------------------------------------------------
        jones_res = {}
        if prev:
            jones_res = compute_modified_jones_accrual(
                net_income=curr.get('net_income', 0.0),
                cfo=curr.get('cfo', 0.0),
                assets_t=curr.get('assets', 0.0),
                assets_prev=prev.get('assets', 0.0),
                sales_t=curr.get('sales', 0.0),
                sales_prev=prev.get('sales', 0.0),
                ar_t=curr.get('ar', 0.0),
                ar_prev=prev.get('ar', 0.0),
                ppe_net_t=curr.get('ppe_net', 0.0)
            )
            if jones_res.get('is_abnormal_discretionary_accrual'):
                total_score += 20
                all_warnings.append(f"【可操纵应计利润异常】修正琼斯模型DA残差达 {jones_res['discretionary_accruals']:.4f} (>0.08警戒线)，存在通过跨期估计人为粉饰利润证据")

        # ----------------------------------------------------
        # 3. 数理统计模型 3: 跨科目统计背离度 (Decoupling Metrics)
        # ----------------------------------------------------
        if prev:
            stat_decoupling = compute_statistical_decoupling_metrics(
                sales_t=curr.get('sales', 0.0), sales_prev=prev.get('sales', 0.0),
                cogs_t=curr.get('cogs', 0.0), cogs_prev=prev.get('cogs', 0.0),
                ar_t=curr.get('ar', 0.0), ar_prev=prev.get('ar', 0.0),
                inv_t=curr.get('inv', 0.0), inv_prev=prev.get('inv', 0.0),
                cfo_t=curr.get('cfo', 0.0), net_income_t=curr.get('net_income', 0.0)
            )
            total_score += stat_decoupling['stat_score']
            all_warnings.extend(stat_decoupling['warnings'])

        # ----------------------------------------------------
        # 4. 数理统计模型 4: 奥特曼 Z-Score 财务危机破产距离
        # ----------------------------------------------------
        altman_res = compute_altman_z(
            assets=curr.get('assets', 0.0),
            current_assets=curr.get('current_assets', 0.0),
            current_liabilities=curr.get('current_liabilities', 0.0),
            retained_earnings=curr.get('retained_earnings', 0.0),
            ebit=curr.get('operating_income', curr.get('net_income', 0.0)),
            equity=curr.get('equity', 0.0),
            liabilities=curr.get('liabilities', 0.0),
            sales=curr.get('sales', 0.0),
            market_cap=curr.get('market_cap', 0.0)
        )
        if altman_res['is_distressed']:
            total_score += 20
            all_warnings.append(f"【Altman破产危机】Z-Score为 {altman_res['z_score']}，落入红色危险破产区，舞弊动机迫切")

        # ----------------------------------------------------
        # 5. 数理统计模型 5: Sloan 净应计异象
        # ----------------------------------------------------
        sloan_res = compute_sloan_accrual(
            net_income=curr.get('net_income', 0.0),
            cfo=curr.get('cfo', 0.0),
            assets=curr.get('assets', 0.0)
        )
        if sloan_res['is_high_accrual']:
            total_score += 15
            all_warnings.append(f"【高应计异象】Sloan净应计为 {sloan_res['sloan_accrual']} (>0.10)，账面富贵缺乏真实真金白银沉淀")

        # ----------------------------------------------------
        # 6. 硬核报表勾稽与资产真实性规则 (存贷双高、商誉悬顶、资不抵债、明股实债)
        # ----------------------------------------------------
        bs_score, bs_warn = check_balance_sheet_rules(curr)
        total_score += bs_score
        all_warnings.extend(bs_warn)

        is_score, is_warn = check_income_statement_rules(curr)
        total_score += is_score
        all_warnings.extend(is_warn)

        cf_score, cf_warn = check_cash_flow_rules(curr)
        total_score += cf_score
        all_warnings.extend(cf_warn)

        # ----------------------------------------------------
        # 7. 官方确凿重大重述 (仅限 1年内承认 Big-R，非新闻人事)
        # ----------------------------------------------------
        if curr.get('has_item_402_restatement'):
            days = curr.get('recent_restatement_days')
            if days is not None and days <= 365:
                total_score += 20
                all_warnings.append(f"【官方确凿重述】近1年内({days}天前)曾发布 8-K Item 4.02 官方承认前期财报存在实质性错报并失效")

        # 分值封顶 100
        final_score = min(100, total_score)
        if final_score >= 50:
            risk_level = "[极危] 红色高危"
        elif final_score >= 30:
            risk_level = "[预警] 橙色关注"
        elif final_score >= 15:
            risk_level = "[提示] 黄色提示"
        else:
            risk_level = "[稳健] 绿色正常"

        return {
            "entity": curr.get('cik') or curr.get('code') or curr.get('symbol') or curr.get('name') or "Unknown",
            "name": curr.get('name', ''),
            "period": curr.get('period', ''),
            "total_risk_score": final_score,
            "risk_level": risk_level,
            "warning_count": len(all_warnings),
            "warnings": all_warnings,
            "altman_z": altman_res.get('z_score'),
            "altman_zone": altman_res.get('zone'),
            "sloan_accrual": sloan_res.get('sloan_accrual'),
            "beneish_m_score": beneish_res.get('m_score'),
            "beneish_is_manipulator": beneish_res.get('is_manipulator', False),
            "discretionary_accruals": jones_res.get('discretionary_accruals')
        }

    @classmethod
    def evaluate_dataframe(cls, df: pd.DataFrame, entity_col: str = 'cik', time_col: str = 'period') -> pd.DataFrame:
        """
        全量向量化批量打分 (100% 基于统计分布与计量模型)
        """
        df_norm = normalize_dataframe_columns(df)

        # 1. 报表勾稽计算
        df_norm = apply_balance_sheet_dataframe(df_norm)
        df_norm = apply_income_statement_dataframe(df_norm)
        df_norm = apply_cash_flow_dataframe(df_norm)

        # 2. 统计模型向量化计算
        df_norm = compute_altman_z_dataframe(df_norm)
        df_norm = compute_dechow_f_dataframe(df_norm, entity_col=entity_col, time_col=time_col)
        df_norm = compute_beneish_dataframe(df_norm, entity_col=entity_col, time_col=time_col)

        # 3. 统计模型惩罚分汇总
        altman_penalty = np.where(df_norm['altman_is_distressed'], 20, 0)
        sloan_penalty = np.where(df_norm['sloan_is_high'], 15, 0)
        beneish_penalty = np.where(df_norm['beneish_is_manipulator'], 25, 0)

        raw_score = (
            df_norm['bs_fraud_score'] +
            df_norm['is_fraud_score'] +
            df_norm['cf_fraud_score'] +
            altman_penalty +
            sloan_penalty +
            beneish_penalty
        )

        total_score = np.clip(raw_score, 0, 100)
        df_norm['total_risk_score'] = total_score

        df_norm['risk_level'] = np.where(
            total_score >= 50,
            "[极危] 红色高危",
            np.where(
                total_score >= 30,
                "[预警] 橙色关注",
                np.where(total_score >= 15, "[提示] 黄色提示", "[稳健] 绿色正常")
            )
        )

        flag_cols = [
            ('flag_negative_equity', '资不抵债'),
            ('flag_cash_debt_anomaly', '存贷双高'),
            ('flag_goodwill_burden', '商誉悬顶'),
            ('flag_ar_anomaly', '应收畸高'),
            ('flag_inv_overhang', '存货积压'),
            ('flag_cip_anomaly', '工程挂账'),
            ('flag_cfo_broken', '净现比断裂'),
            ('flag_op_loss_masked', '主营亏损掩盖'),
            ('altman_is_distressed', 'Altman破产危机'),
            ('sloan_is_high', '高应计无现金'),
            ('beneish_is_manipulator', 'Beneish操纵高危')
        ]

        active_flags = np.zeros(len(df_norm), dtype=int)
        for col_name, _ in flag_cols:
            if col_name in df_norm.columns:
                active_flags += df_norm[col_name].fillna(False).astype(int)
        df_norm['hit_risk_count'] = active_flags

        return df_norm
