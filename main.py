# -*- coding: utf-8 -*-
"""
SEC 美股财务数据分析与量化排雷一键式主程序 (All-in-One US Stock Platform)
一键支持：
1. 搜索美股公司 / 查询单票历史财务三张表
2. 单票法务审计与排雷诊断卡片
3. 全美股 10,000+ 家上市公司全量秒级造假风险扫描
4. 法务会计量化 Alpha 因子全市场回测
"""

import os
import sys
import argparse

# 保证 Windows 控制台 UTF-8 输出
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from query_sec import SecQueryEngine
from us_fraud_detector import USStockFraudDetector
from quant_fraud_backtest import ForensicFactorEngine, FactorBacktester


def main():
    parser = argparse.ArgumentParser(description="SEC 美股财务数据分析与量化排雷一键式主程序")
    parser.add_argument("--db", type=str, default="./sec_financials.duckdb", help="DuckDB 数据库路径")
    parser.add_argument("--company", "--ticker", dest="company", type=str, default="", help="查询/审计指定美股公司，如: --company 'APPLE' 或 'NVIDIA'")
    parser.add_argument("--search", type=str, default="", help="搜索美股公司名称或 CIK，如: --search 'Tesla'")
    parser.add_argument("--scan", action="store_true", help="全量扫描美股上万家公司的造假与粉饰风险")
    parser.add_argument("--all-years", action="store_true", help="全量扫描 2020-2026 历年全部 18 万份历史申报记录")
    parser.add_argument("--backtest", action="store_true", help="运行 6 大法务会计量化因子全市场回测")
    parser.add_argument("--fy", type=str, default="", help="指定目标财年过滤，如: 2025")
    parser.add_argument("--output", type=str, default="./美股上市公司财报造假风险扫描榜单.xlsx", help="导出报告路径")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"[-] 未找到数据库文件: {args.db}！请先运行:\n    python sec_downloader.py\n    python sec_to_duckdb.py")
        return

    query_engine = SecQueryEngine(db_path=args.db)
    detector = USStockFraudDetector(db_path=args.db, output_report=args.output)

    if args.search:
        print(f"\n[*] 正在搜索美股公司: '{args.search}'...")
        df_res = query_engine.search_company(args.search)
        print("=" * 75)
        print(df_res.to_string(index=False))
        print("=" * 75)

    elif args.company:
        print(f"\n[*] 正在查询并审计美股公司: '{args.company}'...")
        detector.analyze_single_stock(cik_or_name=args.company, fy=args.fy)

    elif args.backtest:
        print("\n[*] 启动法务会计量化因子全市场回测引擎...")
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

    elif args.scan or args.all_years:
        detector.scan_all_stocks(fy=args.fy, all_years=args.all_years, output_report=args.output)

    else:
        print("\n" + "=" * 70)
        print("🌟 【SEC 美股财务数据分析与量化排雷系统】")
        print("=" * 70)
        print("常用命令指南:")
        print("  1. 搜索公司代码:     python main.py --search 'Tesla'")
        print("  2. 单票排雷审计:     python main.py --company 'NVIDIA'")
        print("  3. 全美股最新扫描:   python main.py --scan")
        print("  4. 2020-2026全量大排查: python main.py --scan --all-years")
        print("  5. 量化因子回测:     python main.py --backtest")
        print("=" * 70)
        # 默认执行单票演示
        detector.analyze_single_stock(cik_or_name="NVIDIA")


if __name__ == "__main__":
    main()
