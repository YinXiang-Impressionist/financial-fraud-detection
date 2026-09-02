# -*- coding: utf-8 -*-
"""
Forensic Financial Fraud Detection Engine
法务会计与财务报表造假排雷核心 Python 代码引擎 (0 LLM 依赖、毫秒级执行、全市场向量化)
"""

from .evaluator import ForensicEvaluator
from .models.beneish_m_score import compute_beneish_components, compute_beneish_dataframe
from .models.altman_z_score import compute_altman_z, compute_altman_z_dataframe
from .models.dechow_f_score import compute_sloan_accrual, compute_dechow_f_score, compute_dechow_f_dataframe
from .models.statistical_anomalies import compute_modified_jones_accrual, compute_statistical_decoupling_metrics
from .models.benfords_law import BenfordTest
from .tag_mapping import normalize_dataframe_columns, normalize_record_dict

__all__ = [
    "ForensicEvaluator",
    "compute_beneish_components",
    "compute_beneish_dataframe",
    "compute_altman_z",
    "compute_altman_z_dataframe",
    "compute_sloan_accrual",
    "compute_dechow_f_score",
    "compute_dechow_f_dataframe",
    "compute_modified_jones_accrual",
    "compute_statistical_decoupling_metrics",
    "BenfordTest",
    "normalize_dataframe_columns",
    "normalize_record_dict"
]
