# -*- coding: utf-8 -*-
"""
SEC 美股财务数据分析与法务排雷一键式主平台 (All-in-One US Stock Forensic Platform)
承担全生命周期完整任务 (交互式控制台、智能跳过、在线/离线双模排雷、公司主键Excel架构、量化回测)：

1. 智能交互式控制台 (最推荐：免记任何繁琐参数):
   - python main.py (弹出交互菜单，输入数字编号即可执行所有功能)

2. 在线秒级审计 (命令行静默调用):
   - 单票多维法务体检: python main.py --ticker NVDA
   - 自选股池批量体检: python main.py --batch "AAPL,NVDA,TSLA,BABA"

3. 本地数据生命周期管理 (智能跳过已存在数据):
   - 检查本地湖仓完整性: python main.py --check-data
   - 一键下载缺失数据包: python main.py --download (已下载文件自动跳过，断点续传)
   - 一键构建 DuckDB 湖仓: python main.py --build (已转换 Parquet 自动跳过)

4. 全市场离线排雷与量化研究 (以公司为主键导出三级工作簿):
   - 全美股最新财年扫描: python main.py --scan
   - 2020-2026 历年大排查: python main.py --scan --all-years
   - 6 大法务因子回测:   python main.py --backtest
"""

import os
import sys
import time
import argparse
import pandas as pd

# 保证 Windows 控制台 UTF-8 输出
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from pipelines import EdgarPipeline
from forensic_engine import ForensicEvaluator
from pipelines.lakehouse import (
    SecDeraDownloader,
    SecToDuckDBPipeline,
    SecQueryEngine,
    USStockFraudDetector,
    safe_save_excel
)


def check_lakehouse_ready(db_path: str) -> tuple:
    """
    检查本地 DuckDB 湖仓完整性
    返回: (is_ready: bool, status_message: str, row_count: int)
    """
    if not os.path.exists(db_path):
        return False, "未找到数据库文件", 0
    try:
        import duckdb
        con = duckdb.connect(db_path, read_only=True)
        tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]
        if 'sub' not in tables or 'num' not in tables:
            con.close()
            return False, "数据库表结构不完整 (缺失 sub/num 视图)", 0
        
        # 验证底层视图数据是否可读取 (排查 Parquet 路径断链)
        row = con.execute("SELECT count(*) FROM sub").fetchone()
        con.close()
        if row and row[0] > 0:
            return True, f"数据完整 (挂载 {row[0]:,} 份财报申报记录)", row[0]
        return False, "数据库记录数为空", 0
    except Exception as e:
        return False, f"底层 Parquet 数据缺失或读取异常: {e}", 0


def ensure_lakehouse_ready(
    db_path: str = "./sec_financials.duckdb",
    zips_dir: str = "./sec_zips",
    parquet_dir: str = "./sec_parquet",
    start_year: int = 2020,
    end_year: int = 2026,
    force_download: bool = False
) -> bool:
    """
    全自动保证本地湖仓可用：
    1. 若已有完整数据，智能跳过下载与构建，秒级直接使用；
    2. 若缺失数据，自动启动断点续传下载与 Parquet 湖仓构建。
    """
    ready, msg, _ = check_lakehouse_ready(db_path)
    if ready and not force_download:
        print(f"[+] 湖仓就绪检查通过: {msg}")
        print("[+] 检测到本地已存在完整数据，自动跳过下载与构建，直接执行分析任务！\n")
        return True

    print(f"\n[*] 检查本地数据状态: {msg}")
    print("[*] 正在为您全自动整备全市场历史数据 (已有季度文件自动跳过，无需重复下载)...")

    # 1. 检查并下载 SEC DERA 原始数据包
    downloader = SecDeraDownloader(download_dir=zips_dir, start_year=start_year, end_year=end_year)
    downloader.run()

    # 2. 转换为 ZSTD Parquet 并挂载 DuckDB 视图
    builder = SecToDuckDBPipeline(zips_dir=zips_dir, parquet_dir=parquet_dir, db_path=db_path)
    builder.run()

    # 最终验证
    ready_after, msg_after, _ = check_lakehouse_ready(db_path)
    if ready_after:
        print(f"\n🎉 本地湖仓全自动整备完毕: {msg_after}\n")
        return True
    else:
        print(f"\n[-] 湖仓整备失败: {msg_after}。请检查网络或日志。\n")
        return False


def audit_single_ticker_online(ticker: str) -> dict:
    """通过 edgar-tools 在线秒级抽取完整多维法务档案并执行确定性纯代码排雷"""
    t_total_start = time.time()
    pipeline = EdgarPipeline()
    print(f"\n[*] 正在通过 SEC 官方通道在线抓取 {ticker} 的完整法务档案...")
    
    t_fetch_start = time.time()
    dossier = pipeline.extract_full_forensic_profile(ticker)
    t_fetch = time.time() - t_fetch_start
    
    t_eval_start = time.time()
    # 传入当期与前期报表以计算修正琼斯与贝尼斯 8 变量模型
    report = ForensicEvaluator.evaluate_single(dossier, prev_record=dossier.get("prev_record"))
    t_eval = time.time() - t_eval_start
    t_total = time.time() - t_total_start

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
    print("-" * 75)
    print("⏱️ 【法务审计运行耗时】:")
    print(f"  ● SEC 官方数据抽取耗时: {t_fetch:.2f} 秒")
    print(f"  ● 纯代码排雷评估耗时  : {t_eval * 1000:.2f} 毫秒 (零 LLM 极速执行)")
    print(f"  ● 单票审计全流程总耗时: {t_total:.2f} 秒")
    print("=" * 75 + "\n")

    return {**dossier, **report}


def audit_batch_tickers(ticker_list: list, output_report: str = "./美股自选股法务排雷榜单.xlsx"):
    """批量在线排雷一组股票并导出 Excel 报告"""
    t_batch_start = time.time()
    print(f"\n[*] 启动股票池批量排雷任务，共 {len(ticker_list)} 只股票: {', '.join(ticker_list)}")
    results = []
    for t in ticker_list:
        try:
            t_item_start = time.time()
            res = audit_single_ticker_online(t.strip())
            t_item = time.time() - t_item_start
            results.append({
                "代码": t.strip().upper(),
                "公司名称": res.get('name'),
                "综合风险评分": res.get('total_risk_score'),
                "风险等级": res.get('risk_level'),
                "命中风险项数": res.get('warning_count'),
                "Beneish_M分值": res.get('beneish_m_score'),
                "琼斯DA可操纵应计": res.get('discretionary_accruals'),
                "Altman_Z分值": res.get('altman_z'),
                "Sloan净应计": res.get('sloan_accrual'),
                "8K重大重述": "是" if res.get('has_item_402_restatement') else "否",
                "科研真值标签_历史造假": res.get('target_is_restated_fraud', False),
                "单票耗时_秒": round(t_item, 2),
                "营业收入_百万美元": round(res.get('sales', 0)/1e6, 2),
                "净利润_百万美元": round(res.get('net_income', 0)/1e6, 2),
                "经营现金流_百万美元": round(res.get('cfo', 0)/1e6, 2),
                "预警明细": " | ".join(res.get('warnings', [])) if res.get('warnings') else "正常"
            })
        except Exception as e:
            print(f"[-] 抓取 {t} 失败: {e}")

    t_batch_total = time.time() - t_batch_start
    avg_time = (t_batch_total / len(results)) if results else 0.0

    if results:
        df_out = pd.DataFrame(results).sort_values(by="综合风险评分", ascending=False)
        actual_path = safe_save_excel(df_out, output_report)
        print("\n" + "=" * 70)
        print(f"🎉 批量法务排雷完成！成功分析 {len(df_out)} 只股票，报告已导出至: {os.path.abspath(actual_path)}")
        print("-" * 70)
        print("⏱️ 【批量审计耗时统计】:")
        print(f"  ● 批量分析总耗时  : {t_batch_total:.2f} 秒")
        print(f"  ● 平均每只分析耗时: {avg_time:.2f} 秒/只")
        print("=" * 70 + "\n")


def run_interactive_menu():
    """交互式询问菜单模式：免记繁琐参数，输入数字与提示即刻完成排雷"""
    while True:
        print("\n" + "=" * 72)
        print("🌟 【SEC 美股财务数据分析与法务排雷平台 (交互式控制台)】")
        print("=" * 72)
        print("请选择您要执行的任务 (输入数字编号):")
        print("  [1] 🎯 单票在线排雷审计 (输入股票代码，如 NVDA / TSLA / AAPL)")
        print("  [2] 📋 自选股批量排雷体检 (输入多只股票，自动导出 Excel 诊断榜单)")
        print("  [3] ⚡ 全美股最新财年大扫描 (秒级扫描数千家公司，自动调度湖仓)")
        print("  [4] 📚 2020-2026 历年历史大排查 (全量 18 万份财报回溯)")
        print("  [5] 📈 6 大法务会计量化因子全市场回测")
        print("  [6] 🔍 检查本地 DuckDB 湖仓完整性与数据状态")
        print("  [7] 📥 批量下载/补齐 SEC 官方历史数据 (已有文件自动跳过)")
        print("  [8] ⚙️ 构建/刷新 DuckDB 湖仓 Parquet 视图")
        print("  [0] 🚪 退出系统")
        print("=" * 72)

        try:
            choice = input("👉 请输入选项编号 [0-8]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 感谢使用，已安全退出系统。\n")
            break

        if choice in ['0', 'q', 'exit', 'quit']:
            print("\n👋 感谢使用，已安全退出系统。\n")
            break

        t_op_start = time.time()

        if choice == '1':
            ticker = input("\n📝 请输入美股股票代码 (如 NVDA, AAPL, TSLA): ").strip()
            if ticker:
                audit_single_ticker_online(ticker)
            else:
                print("[-] 股票代码不能为空！")

        elif choice == '2':
            raw = input("\n📝 请输入逗号分隔的股票列表 (如 AAPL,NVDA,TSLA,MSFT): ").strip()
            if raw:
                tickers = [t.strip() for t in raw.replace('，', ',').split(',') if t.strip()]
                audit_batch_tickers(tickers)
            else:
                print("[-] 股票列表不能为空！")

        elif choice == '3':
            if ensure_lakehouse_ready():
                detector = USStockFraudDetector()
                detector.scan_all_stocks()

        elif choice == '4':
            if ensure_lakehouse_ready():
                detector = USStockFraudDetector()
                detector.scan_all_stocks(all_years=True)

        elif choice == '5':
            if ensure_lakehouse_ready():
                from backtest import ForensicFactorEngine, FactorBacktester
                factor_engine = ForensicFactorEngine()
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

        elif choice == '6':
            ready, msg, count = check_lakehouse_ready("./sec_financials.duckdb")
            print("\n" + "=" * 65)
            print("🔍 【本地 SEC 数据湖仓完整性检查报告】")
            print("=" * 65)
            print(f"● 湖仓就绪状态: {'✅ 完整可用' if ready else '❌ 尚未就绪'}")
            print(f"● 详细状态说明: {msg}")
            if ready:
                print(f"● 总财报申报数: {count:,} 份")
            print("=" * 65 + "\n")

        elif choice == '7':
            start_y = input("📅 起始年份 [默认 2020]: ").strip() or "2020"
            end_y = input("📅 结束年份 [默认 2026]: ").strip() or "2026"
            downloader = SecDeraDownloader(start_year=int(start_y), end_year=int(end_y))
            downloader.run()

        elif choice == '8':
            builder = SecToDuckDBPipeline()
            builder.run()

        else:
            print("[-] 无效选项，请输入 0 到 8 之间的数字！")

        print(f"⏱️ 【当前操作耗时】: {time.time() - t_op_start:.2f} 秒")
        try:
            input("\n⏎ 按 Enter 键返回主菜单...")
        except (KeyboardInterrupt, EOFError):
            print("\n👋 感谢使用，已安全退出系统。\n")
            break


def main():
    session_start = time.time()

    # 若无参数传入，直接进入智能询问/菜单模式
    if len(sys.argv) == 1:
        run_interactive_menu()
        return

    parser = argparse.ArgumentParser(description="SEC 美股财务数据分析与法务排雷一键式全功能主程序")
    
    # 在线实时审计参数
    parser.add_argument("--ticker", "--company", dest="ticker", type=str, default="", help="在线单票多维深度排雷，如: --ticker NVDA 或 AAPL")
    parser.add_argument("--batch", type=str, default="", help="批量排查逗号分隔的股票列表，如: --batch 'AAPL,NVDA,TSLA,BABA'")
    
    # 湖仓数据管理与生命周期参数 (支持已有数据自动跳过)
    parser.add_argument("--check-data", action="store_true", help="检查本地 DuckDB 湖仓的数据完整性与状态")
    parser.add_argument("--download", action="store_true", help="批量下载/补齐 SEC DERA 历史报表数据 (已存在的文件自动跳过)")
    parser.add_argument("--build", action="store_true", help="将已下载的 zip 转换为 Parquet 并构建 DuckDB 湖仓视图")
    parser.add_argument("--zips-dir", type=str, default="./sec_zips", help="原始 zip 数据集存放目录")
    parser.add_argument("--parquet-dir", type=str, default="./sec_parquet", help="Parquet 湖仓存储目录")
    parser.add_argument("--start-year", type=int, default=2020, help="下载与构建的起始年份 (默认 2020)")
    parser.add_argument("--end-year", type=int, default=2026, help="下载与构建的结束年份 (默认 2026)")
    
    # 离线批量扫描与量化因子回测参数
    parser.add_argument("--db", type=str, default="./sec_financials.duckdb", help="DuckDB 数据库路径")
    parser.add_argument("--scan", action="store_true", help="全量扫描美股数万家上市公司的造假风险 (自动检测本地数据)")
    parser.add_argument("--all-years", action="store_true", help="全量扫描 2020-2026 历年全部 18 万份历史申报记录")
    parser.add_argument("--backtest", action="store_true", help="运行 6 大法务会计量化因子全市场回测 (自动检测本地数据)")
    parser.add_argument("--fy", type=str, default="", help="指定目标财年过滤，如: 2025")
    parser.add_argument("--output", type=str, default="./美股上市公司财报造假风险扫描榜单.xlsx", help="导出报告路径")
    
    args = parser.parse_args()

    try:
        # 1. 在线单票多维审计 (秒级直连 SEC，无需本地海量历史数据)
        if args.ticker:
            audit_single_ticker_online(args.ticker)
            return

        # 2. 批量股票池在线审计
        if args.batch:
            tickers = [t.strip() for t in args.batch.split(",") if t.strip()]
            audit_batch_tickers(tickers, output_report=args.output)
            return

        # 3. 显式检查本地数据完整性
        if args.check_data:
            ready, msg, count = check_lakehouse_ready(args.db)
            print("\n" + "=" * 65)
            print("🔍 【本地 SEC 数据湖仓完整性检查报告】")
            print("=" * 65)
            print(f"● 数据库文件路径: {os.path.abspath(args.db)}")
            print(f"● 湖仓就绪状态  : {'✅ 完整可用' if ready else '❌ 尚未就绪'}")
            print(f"● 状态详细说明  : {msg}")
            if ready:
                print(f"● 总财报申报数  : {count:,} 份")
            print("=" * 65 + "\n")
            return

        # 4. 显式单步下载任务 (已有文件自动跳过，断点续传)
        if args.download:
            downloader = SecDeraDownloader(download_dir=args.zips_dir, start_year=args.start_year, end_year=args.end_year)
            downloader.run()
            return

        # 5. 显式单步构建湖仓任务
        if args.build:
            builder = SecToDuckDBPipeline(zips_dir=args.zips_dir, parquet_dir=args.parquet_dir, db_path=args.db)
            builder.run()
            return

        # 6. 本地全市场大扫描或因子回测 (全自动保证数据可用，已有数据免下载)
        if args.scan or args.all_years or args.backtest:
            if not ensure_lakehouse_ready(
                db_path=args.db,
                zips_dir=args.zips_dir,
                parquet_dir=args.parquet_dir,
                start_year=args.start_year,
                end_year=args.end_year
            ):
                return

            if args.scan or args.all_years:
                detector = USStockFraudDetector(db_path=args.db, output_report=args.output)
                detector.scan_all_stocks(fy=args.fy, all_years=args.all_years, output_report=args.output)
            elif args.backtest:
                from backtest import ForensicFactorEngine, FactorBacktester
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

    finally:
        total_session = time.time() - session_start
        print(f"⏱️ 【命令行会话总耗时】: {total_session:.2f} 秒\n")


if __name__ == "__main__":
    main()
