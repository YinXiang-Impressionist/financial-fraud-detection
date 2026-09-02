# -*- coding: utf-8 -*-
"""
Forensic Financial Fraud Detection Engine Unit Tests & Performance Benchmark
法务会计与财报排雷 Python 引擎测试与性能基准验证
"""

import os
import sys
import time

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
    print("[*] 正在测试 Beneish M-Score 模型...")
    # 模拟一家健康稳健公司
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
    print(f"  ● 稳健公司 M-Score: {healthy_res['m_score']} (操纵标记: {healthy_res['is_manipulator']})")
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
    print(f"  ● 操纵公司 M-Score: {manipulator_res['m_score']} (操纵标记: {manipulator_res['is_manipulator']})")
    assert manipulator_res['m_score'] > -1.78, "操纵公司 M-Score 应该判定为高危操纵 (> -1.78)"
    assert manipulator_res['is_manipulator']
    print("  ✅ Beneish M-Score 模型测试通过！\n")


def test_altman_z_score():
    print("[*] 正在测试 Altman Z-Score 财务危机模型...")
    # 稳健公司
    safe_res = compute_altman_z(
        assets=1000, current_assets=600, current_liabilities=200,
        retained_earnings=400, ebit=150, equity=700, liabilities=300, sales=1200
    )
    print(f"  ● 稳健公司 Z-Score: {safe_res['z_score']} ({safe_res['zone']})")
    assert safe_res['z_score'] > 2.99
    assert safe_res['zone'] == "绿色安全区(Safe)"

    # 破产危机公司
    distress_res = compute_altman_z(
        assets=1000, current_assets=150, current_liabilities=500,
        retained_earnings=-200, ebit=-80, equity=100, liabilities=900, sales=400
    )
    print(f"  ● 危机公司 Z-Score: {distress_res['z_score']} ({distress_res['zone']})")
    assert distress_res['z_score'] < 1.81
    assert distress_res['is_distressed']
    print("  ✅ Altman Z-Score 财务危机模型测试通过！\n")


def test_benfords_law():
    print("[*] 正在测试 Benford's Law 分录数理分布与卡方检验...")
    np.random.seed(42)
    # 构造符合本福特定律的对数随机数
    u = np.random.uniform(0, 1, 1000)
    benford_numbers = 10 ** (u * 4)  # 跨越多个数量级的对数分布
    res_natural = BenfordTest.test_first_digit(benford_numbers)
    print(f"  ● 自然发生对数数据 MAD: {res_natural['mad']}, p-value: {res_natural['p_value']}, 结论: {res_natural['conformity_eval']}")
    assert res_natural['is_conforming']

    # 构造人为均匀捏造的数据 (首位数字 1~9 等概率分布)
    fake_numbers = []
    for _ in range(1000):
        lead = np.random.randint(1, 10)
        fake_numbers.append(lead * 10000 + np.random.randint(100, 999))
    res_fake = BenfordTest.test_first_digit(fake_numbers)
    print(f"  ● 人为伪造数据 MAD: {res_fake['mad']}, p-value: {res_fake['p_value']}, 结论: {res_fake['conformity_eval']}")
    assert not res_fake['is_conforming']
    print("  ✅ Benford's Law 卡方与 MAD 检验测试通过！\n")


def test_single_stock_evaluator():
    print("[*] 正在测试单票法务深度审计 Evaluator...")
    # 模拟一家触发多重地雷的公司: 存贷双高 + 高商誉 + 净现比断裂
    bad_company = {
        "name": "高危造假测试公司",
        "cik": "999999",
        "assets": 1000000000,        # 10亿总资产
        "equity": 300000000,          # 3亿净资产
        "cash": 400000000,            # 4亿现金 (占比 40%)
        "debt": 500000000,            # 5亿有息负债 (占比 50%) -> 存贷双高!
        "goodwill": 200000000,        # 2亿商誉 (占净资产 66.7%) -> 商誉悬顶!
        "revenue": 800000000,         # 8亿营收
        "net_income": 100000000,      # 1亿净利润
        "cfo": -50000000,             # 经营现金流负5000万 -> 净现比断裂!
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
    print(f"  ● 评估公司: {report['name']}")
    print(f"  ● 综合风险评分: {report['total_risk_score']} 分 ({report['risk_level']})")
    print(f"  ● 命中风险项数: {report['warning_count']} 项")
    print("  ● 预警明细:")
    for w in report['warnings']:
        print(f"     ❌ {w}")
    assert report['total_risk_score'] >= 50, "多重暴雷公司评分应 >= 50"
    assert report['risk_level'] == "[极危] 红色高危"
    print("  ✅ 单票法务深度审计 Evaluator 测试通过！\n")


def test_vectorized_benchmark():
    print("[*] 正在执行全量向量化性能基准测试 (10,000 家公司规模)...")
    np.random.seed(42)
    N = 10000
    # 生成 10,000 条仿真财务三张表面板数据
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

    print(f"  ● 评估记录总数: {len(df_result):,} 份报表")
    print(f"  ● 总计算耗时  : {elapsed:.3f} 秒")
    print(f"  ● 每秒扫描速度: {len(df_result) / elapsed:,.0f} 份/秒 (零 LLM 依赖极速执行)")
    print(f"  ● 红色高危检出: {len(df_result[df_result['total_risk_score'] >= 50]):,} 家")
    print(f"  ● 绿色安全企业: {len(df_result[df_result['total_risk_score'] < 15]):,} 家")
    
    assert elapsed < 3.0, "10,000 条数据必须在 3 秒内完成向量化打分"
    print("  ✅ 全量向量化性能基准测试通过！\n")


def test_abnormal_payout_and_q4_bath():
    print("[*] 正在测试长春高新式专项排雷: 业绩滑坡超额分红掏空 + Q4单季突发大洗澡...")
    # 模拟长春高新式案例:
    # 1. 前期净利 40亿，当期净利下滑至 5亿 (业绩崩塌滑坡)
    # 2. 分红 10亿 + 回购 5亿 = 15亿 (占净利 100% > 50%) -> 触发超额分红掏空!
    # 3. 前三季度盈利 15亿，Q4单季度亏损 10亿 (单季亏损达前三季 66.7% > 50%) -> 触发Q4突发大洗澡!
    test_case = {
        "name": "长春高新式测试样本",
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
    print(f"  ● 命中预警项: {report['warning_count']} 项")
    for w in report['warnings']:
        print(f"     👉 {w}")
    
    assert "【突击超额分红回购】" in warning_texts, "应成功命中超额分红掏空规则"
    assert "【Q4突发大洗澡】" in warning_texts, "应成功命中Q4突发大洗澡规则"
    print("  ✅ 业绩滑坡超额分红与Q4单季突发大洗澡专项测试通过！\n")


def main():
    print("=" * 65)
    print("🚀 【Forensic Fraud Engine 核心算法与规则库测试】")
    print("=" * 65 + "\n")
    test_beneish_m_score()
    test_altman_z_score()
    test_benfords_law()
    test_single_stock_evaluator()
    test_abnormal_payout_and_q4_bath()
    test_vectorized_benchmark()
    print("=" * 65)
    print("🎉 【全部测试 100% 顺利通过！】")
    print("=" * 65)


if __name__ == "__main__":
    main()
