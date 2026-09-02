# -*- coding: utf-8 -*-
"""
SEC 美股财务数据分析与法务排雷一键式主程序 (All-in-One US Stock Platform)
全面升级支持基于 edgar-tools 的在线秒级多维法务穿透审计与全市场 DuckDB 湖仓秒级扫描：
1. 单票全景审计：输入股票代码 (如 NVDA)，秒级直连 SEC 抽取财报三张表 + 8-K重述换所 + Form 4大股东抛售 + 10-K内控缺陷
2. 批量股票池审计：一键批量排查自选股 (如 --batch "AAPL,NVDA,TSLA,BABA") 并导出 Excel 诊断榜单
3. 全市场全量扫雷：基于 DuckDB 湖仓秒级向量化扫描数万家上市公司历史申报记录
4. 量化因子回测：6 大法务会计量化因子全市场多空收益回测
"""

import os
import sys
import argparse
import pandas as pd

# 保证 Windows 控制台 UTF-8 输出
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from edgar_pipeline import EdgarPipeline
from forensic_engine import ForensicEvaluator
from us_fraud_detector import USStockFraudDetector, safe_save_excel


def audit_single_ticker_online(ticker: str) -> dict:
    """通过 edgar-tools 在线秒级抽取完整多维法务档案并执行确定性纯代码排雷"""
    pipeline = EdgarPipeline()
    print(f"\n[*] 正在通过 SEC 官方通道在线抓取 {ticker} 的完整法务档案...")
    dossier = pipeline.extract_full_forensic_profile(ticker)
    
    # 传入当期与前期报表以计算修正琼斯与贝尼斯 8 变量模型
    report = ForensicEvaluator.evaluate_single(dossier, prev_record=dossier.get("prev_record"))
    r_info = dossier.get("restatement_info", {})
    c_info = dossier.get("control_info", {})

    print("\n" + "=" * 75)
    print(f"🏛️ 【SEC 美股数理统计法务排雷报告】: {dossier['name']} ({ticker.upper()})")
    print("=" * 75)
    print(f"● 申报企业 CIK : {dossier['cik']} | 所属行业: {dossier.get('industry', 'N/A')}")
    print(f"● 最新营业收入 : ${dossier['sales']/1e6:,.2f} Million")
    print(f"● 最新净利润   : ${dossier['net_income']/1e6:,.2f} Million")
    print(f"● 经营现金流量 : ${dossier['cfo']/1e6:,.2f} Million")
    print(f"● 自由现金流量 : ${dossier['fcf']/1e6:,.2f} Million")
    print(f"● 股东总权益   : ${dossier['equity']/1e6:,.2f} Million")
    print(f"● 账面商誉规模 : ${dossier['goodwill']/1e6:,.2f} Million")
    print("-" * 75)
    print(f"● 综合风险评分 : {report['total_risk_score']} 分 (0~100, 越高风险越致命)")
    print(f"● 综合风险等级 : {report['risk_level']}")
    print(f"● 命中风险项数 : {report['warning_count']} 项")
    print("-" * 75)
    print("【纯数理统计与计量模型侦测结果 (Statistical Detective)】:")
    if report.get('beneish_m_score') is not None:
        print(f"  ● 贝尼斯 Beneish M-Score : {report.get('beneish_m_score')} ({'❌ 突破-1.78阈值，高危操纵' if report.get('beneish_is_manipulator') else '✅ 未见系统性操纵'})")
    if report.get('discretionary_accruals') is not None:
        da = report.get('discretionary_accruals', 0.0)
        print(f"  ● 修正琼斯可操纵应计 (DA) : {da:.4f} ({'❌ 跨期操纵显著(>0.08)' if da > 0.08 else '✅ 应计利润正常'})")
    print(f"  ● 奥特曼 Altman Z-Score  : {report.get('altman_z')} ({report.get('altman_zone')})")
    print(f"  ● Sloan 经典净应计异象   : {report.get('sloan_accrual')} ({'❌ 高应计虚增' if (report.get('sloan_accrual') or 0) > 0.10 else '✅ 现金流支撑强'})")
    print(f"  ● 科研真值标签 (Ground Truth) : target_is_restated_fraud = {r_info.get('target_is_restated_fraud', False)}")
    print("-" * 75)
    print("【排雷诊断与纯数理反常预警】:")
    if report['warnings']:
        for item in report['warnings']:
            print(f"  ❌ {item}")
    else:
        print("  ✅ 财务三张表勾稽严密，各项数理与统计指标均处于正常安全区间。")
    print("=" * 75 + "\n")

    return {**dossier, **report}


def audit_batch_tickers(ticker_list: list, output_report: str = "./美股自选股法务排雷榜单.xlsx"):
    """批量在线排雷一组股票并导出 Excel 报告"""
    print(f"\n[*] 启动股票池批量排雷任务，共 {len(ticker_list)} 只股票: {', '.join(ticker_list)}")
    results = []
    for t in ticker_list:
        try:
            res = audit_single_ticker_online(t.strip())
            results.append({
                "代码": t.strip().upper(),
                "公司名称": res.get('name'),
                "综合风险评分": res.get('total_risk_score'),
                "风险等级": res.get('risk_level'),
                "命中风险项数": res.get('warning_count'),
                "Altman_Z分值": res.get('altman_z'),
                "Sloan净应计": res.get('sloan_accrual'),
                "8K重大重述": "是" if res.get('has_item_402_restatement') else "否",
                "重述时效等级": res.get('restatement_info', {}).get('restatement_time_tier', '无'),
                "科研真值标签_历史造假": res.get('target_is_restated_fraud', False),
                "8K突发换所": "是" if res.get('accountant_changed_8k') else "否",
                "8K高管辞职": "是" if res.get('officer_departure_8k') else "否",
                "内部人净套现_百万美元": round(res.get('insider_net_sell_val', 0)/1e6, 2),
                "内控缺陷Status": res.get('control_info', {}).get('internal_control_status', '正常'),
                "营业收入_百万美元": round(res.get('sales', 0)/1e6, 2),
                "净利润_百万美元": round(res.get('net_income', 0)/1e6, 2),
                "经营现金流_百万美元": round(res.get('cfo', 0)/1e6, 2),
                "预警明细": " | ".join(res.get('warnings', [])) if res.get('warnings') else "正常"
            })
        except Exception as e:
            print(f"[-] 抓取 {t} 失败: {e}")

    if results:
        df_out = pd.DataFrame(results).sort_values(by="综合风险评分", ascending=False)
        actual_path = safe_save_excel(df_out, output_report)
        print("\n" + "=" * 70)
        print(f"🎉 批量法务排雷完成！成功分析 {len(df_out)} 只股票，报告已导出至: {os.path.abspath(actual_path)}")
        print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="SEC 美股财务数据分析与法务排雷一键式主程序")
    parser.add_argument("--ticker", "--company", dest="ticker", type=str, default="", help="在线单票多维深度排雷，如: --ticker NVDA 或 AAPL")
    parser.add_argument("--batch", type=str, default="", help="批量排查逗号分隔的股票列表，如: --batch 'AAPL,NVDA,TSLA,BABA'")
    parser.add_argument("--db", type=str, default="./sec_financials.duckdb", help="DuckDB 数据库路径")
    parser.add_argument("--scan", action="store_true", help="全量扫描美股上万家公司的造假与粉饰风险 (需要本地 DuckDB 湖仓)")
    parser.add_argument("--all-years", action="store_true", help="全量扫描 2020-2026 历年全部 18 万份历史申报记录")
    parser.add_argument("--backtest", action="store_true", help="运行 6 大法务会计量化因子全市场回测")
    parser.add_argument("--fy", type=str, default="", help="指定目标财年过滤，如: 2025")
    parser.add_argument("--output", type=str, default="./美股上市公司财报造假风险扫描榜单.xlsx", help="导出报告路径")
    args = parser.parse_args()

    # 1. 在线单票多维审计 (秒级直连 SEC，无需本地巨大数据库)
    if args.ticker:
        audit_single_ticker_online(args.ticker)
        return

    # 2. 批量股票池在线审计
    if args.batch:
        tickers = [t.strip() for t in args.batch.split(",") if t.strip()]
        audit_batch_tickers(tickers, output_report=args.output)
        return

    # 3. 本地 DuckDB 湖仓回测与全市场扫描模式
    if args.scan or args.all_years or args.backtest:
        if not os.path.exists(args.db):
            print(f"[-] 未找到本地数据库文件: {args.db}！\n    若需全市场离线扫描，请先运行 sec_downloader.py 与 sec_to_duckdb.py。\n    若需审计单票，请直接运行: python main.py --ticker NVDA")
            return
        
        detector = USStockFraudDetector(db_path=args.db, output_report=args.output)
        if args.scan or args.all_years:
            detector.scan_all_stocks(fy=args.fy, all_years=args.all_years, output_report=args.output)
        elif args.backtest:
            from quant_fraud_backtest import ForensicFactorEngine, FactorBacktester
            factor_engine = ForensicFactorEngine(db_path=args.db)
            panel = factor_engine.build_factor_panel()
            backtester = FactorBacktester(panel)
            for f_col, f_name in [
                ("factor_cfo_quality", "1. 净现比与造血质量因子 (CFO/NetIncome)"),
                ("alpha_composite_forensic", "2. 综合法务会计复合质量 Alpha 因子"),
                ("factor_sloan_accrual", "3. Sloan 净应计利润异象因子"),
                ("factor_goodwill_safety", "4. 商誉安全排雷因子"),
                ("factor_cash_debt_spread", "5. 存贷双高异常排雷因子")
            ]:
                backtester.run_backtest(factor_col=f_col, factor_name=f_name)
        return

    # 默认模式：展示帮助并对英伟达执行一次完整在线排雷演示
    print("\n" + "=" * 70)
    print("🌟 【SEC 美股立体法务会计与财报排雷系统 (0 LLM 纯代码极速引擎)】")
    print("=" * 70)
    print("常用命令指南:")
    print("  1. 在线单票多维审计:  python main.py --ticker NVDA")
    print("  2. 在线批量股票池体检: python main.py --batch 'AAPL,NVDA,TSLA,BABA'")
    print("  3. 本地湖仓全市场大扫描: python main.py --scan")
    print("  4. 历年全量大排查:     python main.py --scan --all-years")
    print("=" * 70)
    print("[*] 正在执行默认演示 (NVDA 在线多维立体法务排雷)...")
    audit_single_ticker_online("NVDA")


if __name__ == "__main__":
    main()
