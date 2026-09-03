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

4. 全市场离线排雷大扫描 (以公司为主键导出三级工作簿):
   - 全美股最新财年扫描: python main.py --scan
   - 历年大排查 (跨10年完整数据): python main.py --scan --all-years
"""

import os
import sys
import time
import re
import argparse
from datetime import datetime
import pandas as pd

# 保证 Windows 控制台 UTF-8 输出
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 项目绝对根目录锚定 (消除外部目录执行时的相对路径漂移)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "sec_financials.duckdb")
DEFAULT_ZIPS_DIR = os.path.join(PROJECT_ROOT, "sec_zips")
DEFAULT_PARQUET_DIR = os.path.join(PROJECT_ROOT, "sec_parquet")

# 动态自然时间推导 (终结年份硬编码)
_NOW = datetime.now()
CURRENT_YEAR = _NOW.year
DEFAULT_START_YEAR = CURRENT_YEAR - 10
TEN_YEARS_SPAN_DESC = f"{DEFAULT_START_YEAR}-{CURRENT_YEAR}"

# 运行时国际化支持 (默认英文，支持 --lang zh / --zh / FORENSIC_LANG=zh)
CURRENT_LANG = os.environ.get("FORENSIC_LANG", "en").lower()

def set_language(lang: str):
    global CURRENT_LANG
    CURRENT_LANG = "zh" if lang and lang.lower().startswith("zh") else "en"

def is_zh() -> bool:
    return CURRENT_LANG == "zh"

from pipelines import EdgarPipeline
from forensic_engine import ForensicEvaluator, generate_batch_summary_md
from pipelines.lakehouse import (
    SecDeraDownloader,
    SecToDuckDBPipeline,
    SecQueryEngine,
    USStockFraudDetector,
    safe_save_excel
)


def check_lakehouse_ready(db_path: str = "", require_all_years: bool = False) -> tuple:
    """
    检查本地 DuckDB 湖仓完整性与时间覆盖范围
    返回: (is_ready: bool, status_message: str, row_count: int, min_year: int, max_year: int, year_count: int)
    """
    target_db = db_path if db_path else DEFAULT_DB_PATH
    if not os.path.exists(target_db):
        return False, f"未找到数据库文件 ({os.path.basename(target_db)})", 0, 0, 0, 0
    try:
        import duckdb
        con = duckdb.connect(target_db, read_only=True)
        tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]
        if 'sub' not in tables or 'num' not in tables:
            con.close()
            return False, "数据库表结构不完整 (缺失 sub/num 视图)", 0, 0, 0, 0
        
        # 验证底层视图数据是否可读取并统计实际财报年份跨度 (过滤申报量极少的个别历史迟交补报噪点)
        row = con.execute("""
            WITH yr_stats AS (
                SELECT try_cast(substr(cast(period as varchar), 1, 4) as int) as yr, count(*) as cnt
                FROM sub
                WHERE period IS NOT NULL
                GROUP BY yr
                HAVING cnt >= 1000
            )
            SELECT 
                (SELECT count(*) FROM sub),
                min(yr),
                max(yr),
                count(*)
            FROM yr_stats
        """).fetchone()
        con.close()
        if row and row[0] > 0:
            total_count = row[0]
            min_y = max(row[1] or DEFAULT_START_YEAR, DEFAULT_START_YEAR)
            max_y = row[2] or CURRENT_YEAR
            y_cnt = row[3] or 1

            if require_all_years and (min_y > DEFAULT_START_YEAR + 1 or y_cnt < 8):
                return False, f"本地仅包含 {min_y} 年数据 (共 {y_cnt} 个年份，缺失 {TEN_YEARS_SPAN_DESC} 跨10年历史年度数据包)", total_count, min_y, max_y, y_cnt

            return True, f"数据完整 (覆盖 {min_y}-{max_y} 跨10年完整数据，共 {total_count:,} 份财报申报记录)", total_count, min_y, max_y, y_cnt
        return False, "数据库记录数为空", 0, 0, 0, 0
    except Exception as e:
        return False, f"底层 Parquet 数据缺失或读取异常: {e}", 0, 0, 0, 0


def ensure_lakehouse_ready(
    db_path: str = "",
    zips_dir: str = "",
    parquet_dir: str = "",
    start_year: int = DEFAULT_START_YEAR,
    end_year: int = CURRENT_YEAR,
    force_download: bool = False,
    require_all_years: bool = False
) -> bool:
    """
    全自动保证本地湖仓可用：
    1. 若已有完整数据，智能跳过下载与构建，秒级直接使用；
    2. 若缺失数据或缺少历史年度，向用户给出透明容量提示并自动启动断点续传下载与 Parquet 湖仓构建。
    """
    target_db = db_path if db_path else DEFAULT_DB_PATH
    target_zips = zips_dir if zips_dir else DEFAULT_ZIPS_DIR
    target_parquet = parquet_dir if parquet_dir else DEFAULT_PARQUET_DIR

    ready, msg, _, min_y, max_y, _ = check_lakehouse_ready(target_db, require_all_years=require_all_years)
    if ready and not force_download:
        print(f"[+] 湖仓就绪检查通过: {msg}")
        print("[+] 检测到本地已存在所需数据，自动跳过下载与构建，直接执行分析任务！\n")
        return True

    # 新用户首次开箱冷启动提示
    if not os.path.exists(target_db) and not os.path.exists(target_zips):
        print("\n" + "=" * 70)
        print("💡 【首次运行 SEC 本地湖仓初始化提示】")
        print(f"● 检测到当前环境为首次运行，本地尚未构建离线 SEC 财务湖仓。")
        print(f"● 全美股全量历史大排查约需从 SEC 官方下载 {start_year}-{end_year} 历史数据包 (约 1.4GB 压缩包)。")
        print(f"● 系统支持全自动断点续传与极速 Parquet 分区转换，单次构建后永久秒级本地复用。")
        print("=" * 70)

    print(f"\n[*] 检查本地数据状态: {msg}")
    print(f"[*] 正在为您全自动整备 {start_year}-{end_year} 历史数据 (已有季度文件自动跳过，无需重复下载)...")

    # 1. 检查并下载 SEC DERA 原始数据包
    downloader = SecDeraDownloader(download_dir=target_zips, start_year=start_year, end_year=end_year)
    downloader.run()

    # 2. 转换为 ZSTD Parquet 并挂载 DuckDB 视图
    builder = SecToDuckDBPipeline(zips_dir=target_zips, parquet_dir=target_parquet, db_path=target_db)
    builder.run()

    # 最终验证
    ready_after, msg_after, _, _, _, _ = check_lakehouse_ready(target_db, require_all_years=require_all_years)
    if ready_after:
        print(f"\n🎉 本地湖仓全自动整备完毕: {msg_after}\n")
        return True
    else:
        print(f"\n[-] 湖仓整备状态: {msg_after}\n")
        return False


def audit_single_ticker_online(ticker: str) -> dict:
    """在线秒级抽取完整多维法务档案并执行确定性纯代码排雷 (支持中英双语)"""
    t_total_start = time.time()
    pipeline = EdgarPipeline()
    zh = is_zh()
    fetch_msg = f"\n[*] 正在通过 SEC 官方通道在线抓取 {ticker} 的完整法务档案..." if zh else f"\n[*] Extracting forensic profile for {ticker} from SEC EDGAR official filings..."
    print(fetch_msg)
    
    t_fetch_start = time.time()
    dossier = pipeline.extract_full_forensic_profile(ticker)
    t_fetch = time.time() - t_fetch_start
    
    t_eval_start = time.time()
    report = ForensicEvaluator.evaluate_single(dossier, prev_record=dossier.get("prev_record"))
    t_eval = time.time() - t_eval_start
    t_total = time.time() - t_total_start

    r_info = dossier.get("restatement_info", {})

    print("\n" + "=" * 75)
    title_str = f"🏛️ 【SEC 美股数理统计法务排雷报告】: {dossier['name']} ({ticker.upper()})" if zh else f"🏛️ [SEC Quantitative Forensic Fraud Audit Report]: {dossier['name']} ({ticker.upper()})"
    print(title_str)
    print("=" * 75)
    if zh:
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
        print(f"● 排雷诊断结论 : {report.get('diagnostic_summary', '')}")
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
        print("【排雷诊断与具体成因证据说明 (Notes)】:")
        if report.get('risk_reasons_notes'):
            for line in report['risk_reasons_notes'].split('\n'):
                print(f"  {line}")
        else:
            print("  ✅ 财务三张表勾稽严密，各项数理与统计指标均处于正常安全区间。")
        print("-" * 75)
        print("⏱️ 【法务审计运行耗时】:")
        print(f"  ● SEC 官方数据抽取耗时: {t_fetch:.2f} 秒")
        print(f"  ● 纯代码排雷评估耗时  : {t_eval * 1000:.2f} 毫秒 (零 LLM 极速执行)")
        print(f"  ● 单票审计全流程总耗时: {t_total:.2f} 秒")
    else:
        print(f"● Entity CIK       : {dossier['cik']} | Industry: {dossier.get('industry', 'N/A')}")
        print(f"● Revenue (Sales)  : ${dossier['sales']/1e6:,.2f} Million")
        print(f"● Net Income       : ${dossier['net_income']/1e6:,.2f} Million")
        print(f"● Operating Cash   : ${dossier['cfo']/1e6:,.2f} Million")
        print(f"● Free Cash Flow   : ${dossier['fcf']/1e6:,.2f} Million")
        print(f"● Total Equity     : ${dossier['equity']/1e6:,.2f} Million")
        print(f"● Goodwill         : ${dossier['goodwill']/1e6:,.2f} Million")
        print("-" * 75)
        print(f"● Total Risk Score : {report['total_risk_score']} / 100 (Higher indicates greater forensic risk)")
        print(f"● Risk Level       : {report['risk_level']}")
        print(f"● Diagnostic Sum   : {report.get('diagnostic_summary', '')}")
        print(f"● Warnings Triggered: {report['warning_count']}")
        print("-" * 75)
        print("[Deterministic Econometric & Statistical Detective Findings]:")
        if report.get('beneish_m_score') is not None:
            m_flag = "❌ Breached -1.78 threshold (Manipulator)" if report.get('beneish_is_manipulator') else "✅ Safe (< -1.78)"
            print(f"  ● Beneish M-Score       : {report.get('beneish_m_score')} ({m_flag})")
        if report.get('discretionary_accruals') is not None:
            da = report.get('discretionary_accruals', 0.0)
            da_flag = "❌ Abnormal discretionary accruals (>0.08)" if da > 0.08 else "✅ Normal accruals"
            print(f"  ● Modified Jones DA     : {da:.4f} ({da_flag})")
        print(f"  ● Altman Z-Score        : {report.get('altman_z')} ({report.get('altman_zone')})")
        sloan_val = report.get('sloan_accrual') or 0.0
        sloan_flag = "❌ High accrual anomaly (>0.10)" if sloan_val > 0.10 else "✅ Solid cash flow support"
        print(f"  ● Sloan Net Accrual     : {sloan_val} ({sloan_flag})")
        print(f"  ● Ground Truth Restated : target_is_restated_fraud = {r_info.get('target_is_restated_fraud', False)}")
        print("-" * 75)
        print("[Forensic Diagnostic Evidences & Notes]:")
        if report.get('risk_reasons_notes'):
            for line in report['risk_reasons_notes'].split('\n'):
                print(f"  {line}")
        else:
            print("  ✅ All econometric indicators and cross-statement reconciliations are solid and safe.")
        print("-" * 75)
        print("⏱️ [Audit Elapsed Time]:")
        print(f"  ● SEC Filing Extraction : {t_fetch:.2f} s")
        print(f"  ● Pure Vectorized Audit : {t_eval * 1000:.2f} ms (Zero-LLM instant execution)")
        print(f"  ● Full Pipeline Latency : {t_total:.2f} s")
    print("=" * 75 + "\n")

    return {**dossier, **report}


def audit_batch_tickers(ticker_list: list, output_report: str = ""):
    """批量在线排雷一组股票并导出清晰易读的 Excel 诊断报告 (支持中英双语)"""
    t_batch_start = time.time()
    now_str = datetime.now().strftime("%Y%m%d_%H%M")
    tickers_label = "_".join(ticker_list[:3]) + (f"_etc{len(ticker_list)}" if len(ticker_list) > 3 else "")
    zh = is_zh()
    default_prefix = "美股自选股排雷报告" if zh else "US_Stock_Forensic_Report"
    actual_out_name = output_report or f"./{default_prefix}_{tickers_label}_{now_str}.xlsx"

    start_msg = f"\n[*] 启动股票池批量排雷任务，共 {len(ticker_list)} 只股票: {', '.join(ticker_list)}" if zh else f"\n[*] Starting batch forensic audit for {len(ticker_list)} tickers: {', '.join(ticker_list)}"
    print(start_msg)
    results = []
    for t in ticker_list:
        try:
            t_item_start = time.time()
            res = audit_single_ticker_online(t.strip())
            t_item = time.time() - t_item_start
            if zh:
                results.append({
                    "代码": t.strip().upper(),
                    "公司名称": res.get('name'),
                    "综合风险评分": res.get('total_risk_score'),
                    "风险等级": res.get('risk_level'),
                    "排雷诊断结论": res.get('diagnostic_summary'),
                    "具体风险成因与证据说明(Notes)": res.get('risk_reasons_notes'),
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
                    "经营现金流_百万美元": round(res.get('cfo', 0)/1e6, 2)
                })
            else:
                results.append({
                    "Ticker": t.strip().upper(),
                    "Company": res.get('name'),
                    "Total_Risk_Score": res.get('total_risk_score'),
                    "Risk_Level": res.get('risk_level'),
                    "Diagnostic_Summary": res.get('diagnostic_summary'),
                    "Risk_Reasons_Notes": res.get('risk_reasons_notes'),
                    "Warning_Count": res.get('warning_count'),
                    "Beneish_M_Score": res.get('beneish_m_score'),
                    "Jones_DA": res.get('discretionary_accruals'),
                    "Altman_Z_Score": res.get('altman_z'),
                    "Sloan_Accrual": res.get('sloan_accrual'),
                    "Restatement_8K": "Yes" if res.get('has_item_402_restatement') else "No",
                    "Target_Ground_Truth": res.get('target_is_restated_fraud', False),
                    "Elapsed_Sec": round(t_item, 2),
                    "Revenue_M": round(res.get('sales', 0)/1e6, 2),
                    "Net_Income_M": round(res.get('net_income', 0)/1e6, 2),
                    "Operating_Cash_M": round(res.get('cfo', 0)/1e6, 2)
                })
        except Exception as e:
            fail_msg = f"[-] 抓取 {t} 失败: {e}" if zh else f"[-] Failed extracting {t}: {e}"
            print(fail_msg)

    t_batch_total = time.time() - t_batch_start
    avg_time = (t_batch_total / len(results)) if results else 0.0

    if results:
        sort_col = "综合风险评分" if zh else "Total_Risk_Score"
        df_out = pd.DataFrame(results).sort_values(by=sort_col, ascending=False)
        actual_path = safe_save_excel(df_out, actual_out_name)

        md_suffix = '_体检简报.md' if zh else '_summary.md'
        md_file = actual_path.replace('.xlsx', md_suffix)
        actual_md = generate_batch_summary_md(results, md_file)

        print("\n" + "=" * 70)
        done_title = f"🎉 批量法务排雷完成！成功分析 {len(df_out)} 只股票" if zh else f"🎉 Batch forensic audit finished! Successfully screened {len(df_out)} tickers."
        print(done_title)
        if zh:
            print(f"● 🌟 决策简报: {os.path.abspath(actual_md)} (推荐优先阅读，直观排版优美)")
            print(f"● 📊 原始底表: {os.path.abspath(actual_path)} (Excel 格式全量勾稽明细)")
            print("-" * 70)
            print(f"  ● 批量分析总耗时  : {t_batch_total:.2f} 秒")
            print(f"  ● 平均每只分析耗时: {avg_time:.2f} 秒/只")
        else:
            print(f"● 🌟 Executive Summary: {os.path.abspath(actual_md)} (Recommended for quick reading)")
            print(f"● 📊 Full Excel Report : {os.path.abspath(actual_path)} (Comprehensive cross-statement dataset)")
            print("-" * 70)
            print(f"  ● Total Batch Latency : {t_batch_total:.2f} s")
            print(f"  ● Average Time/Ticker : {avg_time:.2f} s/ticker")
        print("⏱️ 【批量审计耗时统计】:")
        print(f"  ● 批量分析总耗时  : {t_batch_total:.2f} 秒")
        print(f"  ● 平均每只分析耗时: {avg_time:.2f} 秒/只")
        print("=" * 70 + "\n")


def run_interactive_menu():
    """交互式询问菜单模式：免记繁琐参数，默认英文，按 L 随时切换为中文"""
    while True:
        zh = is_zh()
        print("\n" + "=" * 74)
        if zh:
            print("🌟 【SEC 美股财务数据分析与法务排雷平台 (交互式控制台)】")
            print("=" * 74)
            print("当前语言: 中文 (按 [L] 切换为 English)")
            print("请选择您要执行的任务 (输入选项编号):")
            print("  [1] 🎯 单票在线排雷审计 (输入股票代码，如 NVDA / TSLA / AAPL)")
            print("  [2] 📋 自选股批量排雷体检 (输入多只股票，自动导出 Excel 诊断榜单)")
            print("  [3] ⚡ 全美股最新财年大扫描 (秒级扫描数千家公司，自动调度湖仓)")
            print(f"  [4] 📚 {TEN_YEARS_SPAN_DESC} 历年历史大排查 (跨 10 年完整数据全量回溯)")
            print("  [5] 🔍 检查本地 DuckDB 湖仓完整性与数据状态")
            print("  [6] 📥 批量下载/补齐 SEC 官方历史数据 (已有文件自动跳过)")
            print("  [7] ⚙️ 构建/刷新 DuckDB 湖仓 Parquet 视图")
            print("  [L] 🌐 切换语言 (Switch to English)")
            print("  [0] 🚪 退出系统")
        else:
            print("🌟 [SEC US Stock Financial Lakehouse & Forensic Audit Platform]")
            print("=" * 74)
            print("Language: English (Press [L] to switch to 中文)")
            print("Please select an action (Enter number):")
            print("  [1] 🎯 Single-Ticker Online Forensic Audit (e.g. NVDA, AAPL, TSLA)")
            print("  [2] 📋 Batch Watchlist Audit & Diagnostic Report (Generates Excel & Summary)")
            print("  [3] ⚡ Full-Market Latest Fiscal Year Scan (Columnar vectorized audit)")
            print(f"  [4] 📚 Historical Full-Market Decade Backtest ({TEN_YEARS_SPAN_DESC})")
            print("  [5] 🔍 Check Local DuckDB Lakehouse Integrity & Record Count")
            print("  [6] 📥 Download / Resume SEC DERA Historical Datasets")
            print("  [7] ⚙️ Build / Refresh DuckDB Lakehouse Parquet Views")
            print("  [L] 🌐 Switch Language (切换为中文)")
            print("  [0] 🚪 Exit System")
        print("=" * 74)

        try:
            choice = input("👉 Select option / 请输入编号 [0-7, L]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Goodbye / 已退出系统。\n")
            break

        if choice in ['0', 'q', 'exit', 'quit']:
            print("\n👋 Goodbye / 已退出系统。\n")
            break

        if choice == 'l':
            set_language("en" if zh else "zh")
            print(f"\n[+] Language switched to: {'中文' if is_zh() else 'English'}")
            continue

        t_op_start = time.time()

        if choice == '1':
            prompt = "\n📝 Please enter US stock ticker (e.g. NVDA, AAPL, TSLA): " if not zh else "\n📝 请输入美股股票代码 (如 NVDA, AAPL, TSLA): "
            ticker = input(prompt).strip()
            if ticker:
                audit_single_ticker_online(ticker)
            else:
                print("[-] Ticker cannot be empty! / 股票代码不能为空！")

        elif choice == '2':
            prompt = "\n📝 Enter comma-separated tickers (e.g. AAPL,NVDA,TSLA,MSFT): " if not zh else "\n📝 请输入逗号分隔的股票列表 (如 AAPL,NVDA,TSLA,MSFT): "
            raw = input(prompt).strip()
            if raw:
                tickers = [t.strip() for t in raw.replace('，', ',').split(',') if t.strip()]
                audit_batch_tickers(tickers)
            else:
                print("[-] Ticker list cannot be empty! / 股票列表不能为空！")

        elif choice == '3':
            if ensure_lakehouse_ready():
                detector = USStockFraudDetector(db_path=DEFAULT_DB_PATH)
                detector.scan_all_stocks()

        elif choice == '4':
            ready, msg, count, min_y, max_y, y_cnt = check_lakehouse_ready(DEFAULT_DB_PATH, require_all_years=True)
            if not ready and min_y > DEFAULT_START_YEAR + 1:
                print("\n" + "=" * 70)
                warn_title = "⚠️ 【历史年度数据完整性提醒】" if zh else "⚠️ [Historical Dataset Coverage Notice]"
                print(warn_title)
                print("=" * 70)
                print(f"● Status: {msg}")
                if zh:
                    print(f"● 提示: 您选择了 [{TEN_YEARS_SPAN_DESC} 历年历史大排查]，但本地仅包含 {min_y} 年起的申报。")
                else:
                    print(f"● Note: Decade backtest requires SEC data from {DEFAULT_START_YEAR}, but local DB starts at {min_y}.")
                print("=" * 70)
                confirm_prompt = f"👉 Download missing historical packets now? [y/N]: " if not zh else f"👉 是否立即下载补齐历史数据包？[y/N]: "
                ans = input(confirm_prompt).strip().lower()
                if ans in ['y', 'yes']:
                    if not ensure_lakehouse_ready(start_year=DEFAULT_START_YEAR, end_year=CURRENT_YEAR, force_download=True, require_all_years=True):
                        continue
                else:
                    continue_msg = f"[*] Proceeding with available local data ({min_y}+)..." if not zh else f"[*] 继续基于本地现有数据 ({min_y}年) 执行排查...\n"
                    print(continue_msg)
            elif not ready:
                if not ensure_lakehouse_ready(start_year=DEFAULT_START_YEAR, end_year=CURRENT_YEAR, require_all_years=True):
                    continue

            detector = USStockFraudDetector(db_path=DEFAULT_DB_PATH)
            detector.scan_all_stocks(all_years=True)

        elif choice == '5':
            ready, msg, count, min_y, max_y, y_cnt = check_lakehouse_ready(DEFAULT_DB_PATH)
            print("\n" + "=" * 65)
            report_title = "🔍 【本地 SEC 数据湖仓完整性检查报告】" if zh else "🔍 [Local SEC DuckDB Lakehouse Integrity Report]"
            print(report_title)
            print("=" * 65)
            print(f"● Status     : {'✅ Ready' if ready else '❌ Incomplete'} ({msg})")
            if ready:
                print(f"● Time Span  : FY {min_y} ~ {max_y} ({y_cnt} fiscal years)")
                print(f"● Total Rows : {count:,} filings")
            print("=" * 65 + "\n")

        elif choice == '6':
            start_prompt = f"📅 Start Year [Default {DEFAULT_START_YEAR}]: " if not zh else f"📅 起始年份 [默认 {DEFAULT_START_YEAR}]: "
            end_prompt = f"📅 End Year [Default {CURRENT_YEAR}]: " if not zh else f"📅 结束年份 [默认 {CURRENT_YEAR}]: "
            start_y = input(start_prompt).strip() or str(DEFAULT_START_YEAR)
            end_y = input(end_prompt).strip() or str(CURRENT_YEAR)
            downloader = SecDeraDownloader(download_dir=DEFAULT_ZIPS_DIR, start_year=int(start_y), end_year=int(end_y))
            downloader.run()

        elif choice == '7':
            builder = SecToDuckDBPipeline(zips_dir=DEFAULT_ZIPS_DIR, parquet_dir=DEFAULT_PARQUET_DIR, db_path=DEFAULT_DB_PATH)
            builder.run()

        else:
            invalid_msg = "[-] Invalid option! / 无效选项，请输入有效编号！"
            print(invalid_msg)

        elapsed_msg = f"⏱️ [Elapsed Time]: {time.time() - t_op_start:.2f} s" if not zh else f"⏱️ 【当前操作耗时】: {time.time() - t_op_start:.2f} 秒"
        print(elapsed_msg)
        try:
            return_prompt = "\n⏎ Press Enter to return to main menu..." if not zh else "\n⏎ 按 Enter 键返回主菜单..."
            input(return_prompt)
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Goodbye / 已退出系统。\n")
            break


def main():
    session_start = time.time()

    parser = argparse.ArgumentParser(description="SEC US Stock Financial Forensic Engine & Lakehouse Console")
    
    # 语言支持 (默认英文)
    parser.add_argument("--lang", type=str, default="en", choices=["en", "zh"], help="Output language: 'en' (default) or 'zh' (Chinese)")
    parser.add_argument("--zh", action="store_true", help="Shortcut to run in Chinese mode (相当于 --lang zh)")

    # 在线实时审计参数
    parser.add_argument("--ticker", "--company", dest="ticker", type=str, default="", help="Single-ticker online forensic audit (e.g. --ticker NVDA)")
    parser.add_argument("--batch", type=str, default="", help="Batch audit for comma-separated tickers (e.g. --batch 'AAPL,NVDA,TSLA')")
    
    # 湖仓数据管理与生命周期参数
    parser.add_argument("--check-data", action="store_true", help="Check local DuckDB Lakehouse integrity and count")
    parser.add_argument("--download", action="store_true", help="Download / resume bulk SEC DERA dataset packages")
    parser.add_argument("--build", action="store_true", help="Convert zip files to Parquet and mount DuckDB views")
    parser.add_argument("--zips-dir", type=str, default=DEFAULT_ZIPS_DIR, help="Directory for raw SEC zip files")
    parser.add_argument("--parquet-dir", type=str, default=DEFAULT_PARQUET_DIR, help="Directory for converted Parquet lakehouse")
    parser.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR, help=f"Start year (default {DEFAULT_START_YEAR})")
    parser.add_argument("--end-year", type=int, default=CURRENT_YEAR, help=f"End year (default {CURRENT_YEAR})")
    
    # 离线批量扫描参数
    parser.add_argument("--db", type=str, default=DEFAULT_DB_PATH, help="DuckDB database file path")
    parser.add_argument("--scan", action="store_true", help="Run full-market forensic screener on latest filings")
    parser.add_argument("--all-years", action="store_true", help=f"Run full historical scan across {TEN_YEARS_SPAN_DESC}")
    parser.add_argument("--fy", type=str, default="", help="Filter by target fiscal year (e.g. 2025)")
    parser.add_argument("--output", type=str, default="", help="Custom output report path")
    
    args = parser.parse_args()

    # 设定全局语言状态
    if args.zh or (args.lang and args.lang.lower().startswith("zh")):
        set_language("zh")
    else:
        set_language(args.lang)

    # 若无任务参数传入，直接进入智能交互式菜单模式
    has_action = any([
        args.ticker, args.batch, args.check_data, args.download,
        args.build, args.scan, args.all_years
    ])
    if not has_action:
        run_interactive_menu()
        return

    try:
        # 1. 在线单票多维审计 (秒级直连 SEC)
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
            ready, msg, count, min_y, max_y, y_cnt = check_lakehouse_ready(args.db)
            zh = is_zh()
            print("\n" + "=" * 65)
            print("🔍 [Local SEC DuckDB Lakehouse Integrity Report]" if not zh else "🔍 【本地 SEC 数据湖仓完整性检查报告】")
            print("=" * 65)
            print(f"● Database Path: {os.path.abspath(args.db)}")
            print(f"● Status       : {'✅ Ready' if ready else '❌ Incomplete'} ({msg})")
            if ready:
                print(f"● Time Span    : FY {min_y} ~ {max_y} ({y_cnt} fiscal years)")
                print(f"● Total Rows   : {count:,} filings")
            print("=" * 65 + "\n")
            return

        # 4. 显式单步下载任务 (已有文件自动跳过)
        if args.download:
            downloader = SecDeraDownloader(download_dir=args.zips_dir, start_year=args.start_year, end_year=args.end_year)
            downloader.run()
            return

        # 5. 显式单步构建湖仓任务
        if args.build:
            builder = SecToDuckDBPipeline(zips_dir=args.zips_dir, parquet_dir=args.parquet_dir, db_path=args.db)
            builder.run()
            return

        # 6. 本地全市场大扫描
        if args.scan or args.all_years:
            if not ensure_lakehouse_ready(
                db_path=args.db,
                zips_dir=args.zips_dir,
                parquet_dir=args.parquet_dir,
                start_year=args.start_year,
                end_year=args.end_year,
                require_all_years=args.all_years
            ):
                return

            detector = USStockFraudDetector(db_path=args.db, output_report=args.output)
            detector.scan_all_stocks(fy=args.fy, all_years=args.all_years, output_report=args.output)
            return

    finally:
        total_session = time.time() - session_start
        latency_str = f"⏱️ [Total Session Latency]: {total_session:.2f} s\n" if not is_zh() else f"⏱️ 【命令行会话总耗时】: {total_session:.2f} 秒\n"
        print(latency_str)


if __name__ == "__main__":
    main()
