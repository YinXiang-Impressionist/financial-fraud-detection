# -*- coding: utf-8 -*-
"""
Forensic Financial Fraud Detection Engine Unit Tests & Performance Benchmark
法务会计与财报排雷 Python 引擎测试与性能基准验证
同时兼容 pytest runner、unittest discover 与独立脚本执行
"""

import os
import sys
import time
import unittest

# 保证当前项目根目录在 sys.path 中
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import numpy as np
import pandas as pd

from forensic_engine import (
    ForensicEvaluator,
    compute_beneish_components,
    compute_altman_z,
    compute_sloan_accrual,
    BenfordTest
)


def test_beneish_m_score():
    """测试 Beneish M-Score 模型对稳健企业与造假操纵企业的识别能力"""
    # 模拟一家稳健公司
    healthy_res = compute_beneish_components(
        sales_t=1000, sales_prev=950,
        cogs_t=600, cogs_prev=570,
        ar_t=100, ar_prev=98,
        assets_t=2000, assets_prev=1900,
        current_assets_t=800, current_assets_prev=780,
        ppe_net_t=800, ppe_net_prev=780,
        depr_t=80, depr_prev=75,
        sga_t=150, sga_prev=145,
        liabilities_t=600, liabilities_prev=580,
        net_income_t=120, cfo_t=150
    )
    assert healthy_res['m_score'] <= -1.78, "稳健公司 M-Score 应该处于正常安全区间 (<= -1.78)"
    assert not healthy_res['is_manipulator']

    # 模拟一家严重操纵报表公司 (应收账款暴涨、毛利率虚增、应计项巨大、资产质量恶化)
    manipulator_res = compute_beneish_components(
        sales_t=1500, sales_prev=800,       # SGI 激增
        cogs_t=700, cogs_prev=600,         # 毛利率暴增 GMI 异动
        ar_t=600, ar_prev=100,             # DSRI 暴涨 (打白条赊销)
        assets_t=2500, assets_prev=1200,
        current_assets_t=800, current_assets_prev=600,
        ppe_net_t=500, ppe_net_prev=500,   # 非流动非固定资产激增 (AQI 水分大)
        depr_t=20, depr_prev=50,           # 折旧减速调节利润 DEPI 异动
        sga_t=100, sga_prev=90,
        liabilities_t=1800, liabilities_prev=600, # 杠杆暴增 LVGI 飙升
        net_income_t=300, cfo_t=-100       # 净利润虚高但现金流流出 TATA 巨大
    )
    assert manipulator_res['m_score'] > -1.78, "操纵公司 M-Score 应该判定为高危操纵 (> -1.78)"
    assert manipulator_res['is_manipulator']


def test_altman_z_score():
    """测试 Altman Z-Score 破产与财务危机判定"""
    # 稳健公司
    safe_res = compute_altman_z(
        assets=1000, current_assets=600, current_liabilities=200,
        retained_earnings=400, ebit=150, equity=700, liabilities=300, sales=1200
    )
    assert safe_res['z_score'] > 2.99
    assert "Safe" in safe_res['zone']

    # 破产危机公司
    distress_res = compute_altman_z(
        assets=1000, current_assets=150, current_liabilities=500,
        retained_earnings=-200, ebit=-80, equity=100, liabilities=900, sales=400
    )
    assert distress_res['z_score'] < 1.81
    assert distress_res['is_distressed']


def test_benfords_law():
    """测试 Benford's Law 分录数理分布与卡方检验"""
    np.random.seed(42)
    # 构造符合本福特定律的对数随机数
    u = np.random.uniform(0, 1, 1000)
    benford_numbers = 10 ** (u * 4)  # 跨越多个数量级的对数分布
    res_natural = BenfordTest.test_first_digit(benford_numbers)
    assert res_natural['is_conforming']

    # 构造人为均匀捏造的数据 (首位数字 1~9 等概率分布)
    fake_numbers = []
    for _ in range(1000):
        lead = np.random.randint(1, 10)
        fake_numbers.append(lead * 10000 + np.random.randint(100, 999))
    res_fake = BenfordTest.test_first_digit(fake_numbers)
    assert not res_fake['is_conforming']


def test_single_stock_evaluator():
    """测试单票法务深度审计 Evaluator 综合打分与四级预警"""
    bad_company = {
        "name": "高危造假测试公司",
        "cik": "999999",
        "assets": 1000000000,
        "equity": 300000000,
        "cash": 400000000,
        "debt": 500000000,
        "goodwill": 200000000,
        "revenue": 800000000,
        "net_income": 100000000,
        "cfo": -50000000,
        "liabilities": 700000000
    }
    prev_company = {
        "revenue": 700000000,
        "cogs": 500000000,
        "ar": 100000000,
        "assets": 900000000,
        "current_assets": 500000000,
        "ppe_net": 300000000,
        "depr": 30000000,
        "sga": 50000000,
        "liabilities": 600000000
    }

    report = ForensicEvaluator.evaluate_single(bad_company, prev_record=prev_company)
    assert report['total_risk_score'] >= 50, "多重暴雷公司评分应 >= 50"
    assert report['risk_level'] in ["[极危] 红色高危", "[Critical] Red Distress"]
    assert report['warning_count'] >= 5


def test_abnormal_payout_and_q4_bath():
    """测试业绩滑坡超额分红掏空 + Q4单季突发大洗澡规则"""
    test_case = {
        "name": "滑坡掏空测试样本",
        "sales": 10000000000,
        "net_income": 500000000,
        "cfo": 2000000000,
        "dividends": 1000000000,
        "repurchases": 500000000,
        "prev_net_income": 4000000000,
        "q1_to_q3_net_income": 1500000000,
        "q4_net_income": -1000000000
    }

    report = ForensicEvaluator.evaluate_single(test_case)
    warning_texts = " ".join(report['warnings'])
    assert "突击超额分红回购" in warning_texts or "Surge Payout" in warning_texts
    assert "Q4突发大洗澡" in warning_texts or "Big-Bath" in warning_texts


def test_vectorized_benchmark():
    """测试全量向量化打分性能基准 (10,000 份报表面板数据)"""
    np.random.seed(42)
    N = 10000
    data = {
        'cik': [f"CIK_{i:06d}" for i in range(N)],
        'period': ['2025-12-31'] * N,
        'assets': np.random.uniform(5e7, 1e10, N),
        'equity': np.random.uniform(1e7, 5e9, N),
        'sales': np.random.uniform(3e7, 8e9, N),
        'cogs': np.random.uniform(2e7, 6e9, N),
        'net_income': np.random.uniform(-5e7, 5e8, N),
        'cfo': np.random.uniform(-1e8, 6e8, N),
        'cash': np.random.uniform(5e6, 2e9, N),
        'debt': np.random.uniform(1e7, 3e9, N),
        'goodwill': np.random.uniform(0, 1e9, N),
        'ar': np.random.uniform(5e6, 2e9, N),
        'inv': np.random.uniform(5e6, 1e9, N),
        'cip': np.random.uniform(0, 5e8, N),
        'ppe_net': np.random.uniform(1e7, 3e9, N),
        'liabilities': np.random.uniform(2e7, 6e9, N)
    }
    df_large = pd.DataFrame(data)

    t0 = time.time()
    df_result = ForensicEvaluator.evaluate_dataframe(df_large)
    elapsed = time.time() - t0

    assert len(df_result) == N
    assert elapsed < 3.0, f"10,000 条数据向量化计算耗时过长: {elapsed:.2f}s"


class TestForensicEngine(unittest.TestCase):
    """Python 标准 unittest 测试类封装，支持 unittest runner 自动发现"""

    def test_beneish(self):
        test_beneish_m_score()

    def test_altman(self):
        test_altman_z_score()

    def test_benford(self):
        test_benfords_law()

    def test_evaluator(self):
        test_single_stock_evaluator()

    def test_payout_bath(self):
        test_abnormal_payout_and_q4_bath()

    def test_vectorized(self):
        test_vectorized_benchmark()


def main():
    print("=" * 65)
    print("🚀 【Forensic Fraud Engine 核心算法与规则库测试】")
    print("=" * 65 + "\n")
    print("[*] 正在测试 Beneish M-Score 模型...")
    test_beneish_m_score()
    print("  ✅ Beneish M-Score 模型测试通过！\n")

    print("[*] 正在测试 Altman Z-Score 财务危机模型...")
    test_altman_z_score()
    print("  ✅ Altman Z-Score 财务危机模型测试通过！\n")

    print("[*] 正在测试 Benford's Law 分录数理分布与卡方检验...")
    test_benfords_law()
    print("  ✅ Benford's Law 卡方与 MAD 检验测试通过！\n")

    print("[*] 正在测试单票法务深度审计 Evaluator...")
    test_single_stock_evaluator()
    print("  ✅ 单票法务深度审计 Evaluator 测试通过！\n")

    print("[*] 正在测试长春高新式专项排雷: 业绩滑坡超额分红掏空 + Q4单季突发大洗澡...")
    test_abnormal_payout_and_q4_bath()
    print("  ✅ 业绩滑坡超额分红与Q4单季突发大洗澡专项测试通过！\n")

    print("[*] 正在执行全量向量化性能基准测试 (10,000 家公司规模)...")
    test_vectorized_benchmark()
    print("  ✅ 全量向量化性能基准测试通过！\n")

    print("=" * 65)
    print("🎉 【全部测试 100% 顺利通过！】")
    print("=" * 65)


if __name__ == "__main__":
    main()
