# -*- coding: utf-8 -*-
"""
Benford's Law Forensic Testing Engine
本福特定律分录数理分布与反舞弊卡方检验引擎 (Frank Benford, 1938; Mark Nigrini, 2012)

用于对日记账分录 (Journal Entries)、发票明细、采购订单、报销单据或全套财报数字的真实性检测：
1. 首位数字测试 (First-Digit Test) 与卡方拟合优度检验 (Chi-square Test)
2. 平均绝对偏差 (Mean Absolute Deviation - MAD) 评估合规度
3. 异常整数与阈值规避峰值检测 (Round Numbers & Number Duplication)
"""

from typing import List, Dict, Any, Union
import numpy as np
import pandas as pd


class BenfordTest:
    # 本福特定律首位数字 1~9 理论概率分布
    THEORETICAL_FIRST_DIGIT = {
        d: np.log10(1.0 + 1.0 / d) for d in range(1, 10)
    }

    @staticmethod
    def extract_first_digit(numbers: Union[List[float], pd.Series, np.ndarray]) -> np.ndarray:
        """从数值序列中提取首位有效非零数字 (1~9)"""
        s = pd.Series(numbers).dropna().abs()
        s = s[s > 0]
        # 转换为字符串提取首位数字
        digits = []
        for val in s:
            val_str = f"{val:.10f}".replace(".", "").lstrip("0")
            if val_str and val_str[0] in "123456789":
                digits.append(int(val_str[0]))
        return np.array(digits)

    @classmethod
    def test_first_digit(cls, numbers: Union[List[float], pd.Series, np.ndarray]) -> Dict[str, Any]:
        """
        对一组连续财务金额执行首位数字卡方检验与 MAD 检验
        """
        digits = cls.extract_first_digit(numbers)
        n = len(digits)
        if n < 50:
            return {
                "sample_size": n,
                "is_conforming": True,
                "message": "样本量不足 (少于 50 个非零有效数字)，统计效力不足",
                "chi_square": 0.0,
                "p_value": 1.0,
                "mad": 0.0,
                "distribution": {}
            }

        counts = {d: 0 for d in range(1, 10)}
        for d in digits:
            counts[d] += 1

        observed_props = {d: counts[d] / n for d in range(1, 10)}
        expected_props = cls.THEORETICAL_FIRST_DIGIT

        # 卡方检验 (Chi-square Test, df = 8)
        observed_counts = np.array([counts[d] for d in range(1, 10)])
        expected_counts = np.array([expected_props[d] * n for d in range(1, 10)])
        
        chi2_stat = float(np.sum((observed_counts - expected_counts) ** 2 / expected_counts))
        try:
            from scipy import stats
            p_val = float(stats.chi2.sf(chi2_stat, df=8))
        except Exception:
            # 查表近似 (df=8, 0.05临界值为15.507)
            p_val = 0.01 if chi2_stat > 15.507 else 0.50

        # MAD (Mean Absolute Deviation)
        mad = float(np.mean([abs(observed_props[d] - expected_props[d]) for d in range(1, 10)]))

        # Nigrini MAD 审计判定标准:
        # MAD <= 0.006: 高度吻合 (Close conformity)
        # 0.006 < MAD <= 0.012: 可接受吻合 (Acceptable conformity)
        # 0.012 < MAD <= 0.015: 临界可疑 (Marginally acceptable)
        # MAD > 0.015: 不符合/涉嫌人为捏造 (Nonconformity)
        if mad <= 0.006:
            conformity = "高度自然吻合 (Close Conformity)"
            is_conforming = True
        elif mad <= 0.012:
            conformity = "基本吻合 (Acceptable)"
            is_conforming = True
        elif mad <= 0.015:
            conformity = "临界可疑 (Marginally Acceptable)"
            is_conforming = True
        else:
            conformity = "显著异常/涉嫌人为捏造编造 (Nonconformity)"
            is_conforming = False

        return {
            "sample_size": n,
            "chi_square": round(float(chi2_stat), 3),
            "p_value": round(float(p_val), 5),
            "mad": round(mad, 5),
            "conformity_eval": conformity,
            "is_conforming": is_conforming,
            "observed_proportions": {d: round(observed_props[d], 3) for d in range(1, 10)},
            "expected_proportions": {d: round(expected_props[d], 3) for d in range(1, 10)}
        }

    @staticmethod
    def detect_round_numbers(numbers: Union[List[float], pd.Series, np.ndarray]) -> Dict[str, Any]:
        """
        检测分录金额中异常整数 (如以 000, 0000 结尾) 的聚集度
        """
        s = pd.Series(numbers).dropna().abs()
        s = s[s > 100]
        n = len(s)
        if n == 0:
            return {"round_number_ratio": 0.0, "is_suspicious": False}

        # 统计整千整万的比例
        round_1000 = (s % 1000 == 0).sum()
        ratio = round_1000 / n

        return {
            "sample_size": n,
            "round_1000_count": int(round_1000),
            "round_number_ratio": round(float(ratio), 4),
            "is_suspicious": bool(ratio > 0.20)  # 超过 20% 为规整整数分录即存在手工调整可疑
        }
