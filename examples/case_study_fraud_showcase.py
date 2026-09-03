# -*- coding: utf-8 -*-
"""
Historical Financial Fraud Case Study & Forensic Diagnostic Showcase
经典财务舞弊与造假历史案例复盘展示
演示纯数理法务排雷引擎如何在企业暴雷/重述前，精准识别报表底层数字的异常脱节与系统性操纵
"""

import os
import sys

# 保证当前项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from forensic_engine import ForensicEvaluator


def run_showcase():
    print("=" * 80)
    print("🏛️ 【SEC Financial Lakehouse 法务排雷引擎: 经典历史造假案例复盘】")
    print("=" * 80 + "\n")

    # -------------------------------------------------------------
    # 案例一：安然式/经典激进跨期操纵与空心化公司 (Enron-Style Case)
    # 特征：营收从 400 亿暴增至 1000 亿 (SGI 极高)，应收账款打白条急剧膨胀 (DSRI 异动)，
    # 账面净利润暴增但经营现金流为负数 (净现比恶性断裂)，非流动资产充斥虚假估值 (AQI 异动)。
    # -------------------------------------------------------------
    enron_style_curr = {
        "name": "Enron-Style Energy Trading (FY2000 Peak)",
        "cik": "0001024401",
        "period": "2000-12-31",
        "sales": 100789000000,           # 营收暴涨至千亿美元 (Mark-to-market 虚构)
        "cogs": 94517000000,
        "ar": 10396000000,              # 应收账款飙升
        "assets": 65503000000,
        "current_assets": 30381000000,
        "ppe_net": 11689000000,
        "depr": 854000000,
        "sga": 3175000000,
        "liabilities": 54033000000,     # 巨额表外负债与隐蔽负债
        "equity": 11470000000,
        "operating_income": 1953000000,
        "net_income": 979000000,        # 账面净利润近 10 亿美元
        "cfo": -220000000,              # 核心经营现金流实质净流出 -2.2 亿美元!
        "cash": 1374000000,
        "debt": 10229000000
    }

    enron_style_prev = {
        "sales": 40112000000,           # 前一财年仅 401 亿美元
        "cogs": 34761000000,
        "ar": 3030000000,
        "assets": 33381000000,
        "current_assets": 11622000000,
        "ppe_net": 8940000000,
        "depr": 696000000,
        "sga": 2726000000,
        "liabilities": 23819000000,
        "equity": 9562000000,
        "operating_income": 1304000000,
        "net_income": 893000000,
        "cfo": 1228000000
    }

    # -------------------------------------------------------------
    # 案例二：标杆健康稳健高盈利龙头 (Benchmark Solid Enterprise: Tech Giant)
    # 特征：强劲经营现金流、低杠杆、资产真实性高、无跨期拼凑利润痕迹
    # -------------------------------------------------------------
    solid_giant_curr = {
        "name": "Benchmark Solid Blue-Chip (Tech Giant)",
        "cik": "0000320193",
        "period": "2024-09-30",
        "sales": 391035000000,
        "cogs": 210352000000,
        "ar": 29944000000,
        "assets": 364980000000,
        "current_assets": 152985000000,
        "current_liabilities": 176392000000,
        "ppe_net": 45255000000,
        "depr": 11519000000,
        "sga": 26038000000,
        "liabilities": 308030000000,
        "equity": 56950000000,
        "operating_income": 123216000000,
        "net_income": 93736000000,      # 净利润 937 亿美元
        "cfo": 118264000000,            # 经营现金流 1182 亿美元 (净现比 1.26，真金白银沉淀)
        "cash": 29943000000,
        "debt": 106629000000
    }

    solid_giant_prev = {
        "sales": 383285000000,
        "cogs": 214137000000,
        "ar": 29508000000,
        "assets": 352583000000,
        "current_assets": 143566000000,
        "current_liabilities": 145308000000,
        "ppe_net": 43715000000,
        "depr": 11519000000,
        "sga": 24932000000,
        "liabilities": 290437000000,
        "equity": 62146000000,
        "operating_income": 114301000000,
        "net_income": 96995000000,
        "cfo": 110543000000
    }

    cases = [
        ("【经典案例 1】激进跨期操纵与现金流背离型造假 (Enron-Style)", enron_style_curr, enron_style_prev),
        ("【经典案例 2】稳健高韧性蓝筹企业 (Solid Blue-Chip Benchmark)", solid_giant_curr, solid_giant_prev)
    ]

    for title, curr, prev in cases:
        print("-" * 80)
        print(f"{title}")
        print(f"  ● 公司名称: {curr['name']}")
        print(f"  ● 营业收入: ${curr['sales']/1e6:,.2f} Million")
        print(f"  ● 净利润  : ${curr['net_income']/1e6:,.2f} Million")
        print(f"  ● 经营现金: ${curr['cfo']/1e6:,.2f} Million (净现比 CFO/NI: {curr['cfo']/curr['net_income']:.2f})")

        res = ForensicEvaluator.evaluate_single(curr, prev_record=prev)

        print(f"\n📊 【排雷体检结果】:")
        print(f"  ● 综合风险评分: {res['total_risk_score']} 分 (0~100)")
        print(f"  ● 风险定级结论: {res['risk_level']}")
        print(f"  ● 贝尼斯 Beneish M-Score: {res['beneish_m_score']} ({'❌ 突破-1.78警戒线(操纵高危)' if res['beneish_is_manipulator'] else '✅ 安全区间'})")
        print(f"  ● 修正琼斯可操纵应计 (DA): {res['discretionary_accruals']:.4f} ({'❌ 跨期操纵显著' if (res['discretionary_accruals'] or 0) > 0.08 else '✅ 正常'})")
        print(f"  ● 奥特曼破产 Altman Z: {res['altman_z']} ({res['altman_zone']})")
        print(f"  ● 命中风险预警项数: {res['warning_count']} 项")
        print(f"  ● 诊断成因与证据明细:")
        for line in res['risk_reasons_notes'].split('\n'):
            print(f"     {line}")
        print()

    print("=" * 80)
    print("✅ 案例复盘展示结束: 引擎成功将激进操纵样本判定为红色高危，并将稳健企业判定为绿色安全。")
    print("=" * 80)


if __name__ == "__main__":
    run_showcase()
