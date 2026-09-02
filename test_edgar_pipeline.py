# -*- coding: utf-8 -*-
"""
EDGAR Pipeline & Multi-Source Forensic Audit Test Script
测试基于 edgar-tools 的新一代数据抽取与立体排雷审计全流程 (AAPL / NVDA 实战测试)
"""

import sys
import time

# 保证 Windows 控制台 UTF-8 输出
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from edgar_pipeline import EdgarPipeline
from forensic_engine import ForensicEvaluator


def test_edgar_pipeline(ticker: str = "AAPL"):
    print("=" * 70)
    print(f"🚀 【启动 EDGAR 立体法务审计全流程测试】: 目标股票 {ticker}")
    print("=" * 70 + "\n")

    pipeline = EdgarPipeline()
    t0 = time.time()

    print(f"[*] 正在从 SEC 官方在线抽取 {ticker} 的完整法务档案 (三张表 + 8-K + Form 4 + 10-K内控)...")
    dossier = pipeline.extract_full_forensic_profile(ticker)
    fetch_time = time.time() - t0
    print(f"[+] 数据抽取成功！耗时 {fetch_time:.2f} 秒。\n")

    # 打印基础概览
    print("【1. 财务三张表审计事实】:")
    print(f"  ● 公司全称: {dossier['name']} (CIK: {dossier['cik']})")
    print(f"  ● 所属行业: {dossier.get('industry')} (SIC: {dossier.get('sic')})")
    print(f"  ● 营业收入: ${dossier['sales']/1e6:,.2f} Million")
    print(f"  ● 净利润  : ${dossier['net_income']/1e6:,.2f} Million")
    print(f"  ● 经营现金: ${dossier['cfo']/1e6:,.2f} Million")
    print(f"  ● 自由现金: ${dossier['fcf']/1e6:,.2f} Million")
    print(f"  ● 股东权益: ${dossier['equity']/1e6:,.2f} Million")
    print(f"  ● 账面商誉: ${dossier['goodwill']/1e6:,.2f} Million")

    print("\n【2. Form 8-K 重大舞弊与治理异动】:")
    r_info = dossier.get("restatement_info", {})
    print(f"  ● 重大差错重述 (Item 4.02): {'❌ 曾发生重述' if r_info.get('has_item_402_restatement') else '✅ 无重大重述记录'}")
    print(f"  ● 重述时效评定: {r_info.get('restatement_time_tier')} (衰减罚分: +{r_info.get('restatement_score_penalty')}分)")
    print(f"  ● 科研真值标签 (Ground Truth): target_is_restated_fraud = {r_info.get('target_is_restated_fraud')}")
    print(f"  ● 突发更换审计所 (Item 4.01): {'⚠️ 有换所记录' if r_info.get('has_item_401_auditor_change') else '✅ 未见突发解聘'}")
    print(f"  ● 高管/CFO 突发离职 (Item 5.02): {'⚠️ 有高管离职公告' if r_info.get('has_item_502_officer_departure') else '✅ 高管团队稳定'}")

    print("\n【3. Form 4 董监高内部人套现减持 (近20份交易)】:")
    i_info = dossier.get("insider_info", {})
    print(f"  ● 内部人交易监控: {'已捕获' if i_info.get('has_insider_trading') else '近期无公开申报'}")
    print(f"  ● 净套现减持金额: ${i_info.get('net_sell_value', 0)/1e6:,.2f} Million")
    print(f"  ● 高危大额减持: {'⚠️ 存在巨额净套现' if i_info.get('heavy_insider_selling') else '✅ 正常持股变动区间'}")

    print("\n【4. 10-K Item 9A 内部控制与审计所】:")
    c_info = dossier.get("control_info", {})
    print(f"  ● 独立审计师: {c_info.get('auditor_name')}")
    print(f"  ● 内控健康状态: {c_info.get('internal_control_status')}")
    print(f"  ● 实质性缺陷: {'❌ 存在重大内控缺陷' if c_info.get('has_material_weakness') else '✅ 未披露实质性内控缺陷'}")

    # 执行法务排雷算法综合打分
    t_eval = time.time()
    report = ForensicEvaluator.evaluate_single(dossier)
    eval_time = time.time() - t_eval

    print("\n" + "=" * 70)
    print("🏛️ 【法务排雷综合体检报告】:")
    print("=" * 70)
    print(f"● 综合风险评分: {report['total_risk_score']} 分 (0~100)")
    print(f"● 综合风险等级: {report['risk_level']}")
    print(f"● 命中风险项数: {report['warning_count']} 项")
    print(f"● Altman Z分值: {report.get('altman_z')} ({report.get('altman_zone')})")
    print(f"● Sloan净应计 : {report.get('sloan_accrual')}")
    print("-" * 70)
    print("【排雷预警明细】:")
    if report['warnings']:
        for w in report['warnings']:
            print(f"  ❌ {w}")
    else:
        print("  ✅ 全项指标稳健，无触发高危造假与治理异常预警。")
    print("=" * 70)
    print(f"[+] 纯 Python 引擎全流程耗时: 数据抽取 {fetch_time:.2f}s + 向量化排雷 {eval_time*1000:.1f}ms (零 LLM 依赖)！\n")


if __name__ == "__main__":
    ticker_to_test = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    test_edgar_pipeline(ticker_to_test)
