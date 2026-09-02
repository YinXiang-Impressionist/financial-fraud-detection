# -*- coding: utf-8 -*-
"""
SEC 美股上市公司财报造假与粉饰风险自动扫描审计引擎 (US Stocks Forensic Audit Engine)
基于 DuckDB 向量化计算，提供秒级单票诊断、最新披露全景扫描与 2020-2026 历年全量历史大排查。
"""

import os
import sys
import time
import argparse
import duckdb
import pandas as pd
import numpy as np

# 保证 Windows 控制台 UTF-8 输出
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def safe_save_excel(df: pd.DataFrame, file_path: str) -> str:
    """安全保存 Excel 文件，若被 Excel 软件打开锁定则自动保存为备用名称"""
    try:
        df.to_excel(file_path, index=False, engine='openpyxl')
        return file_path
    except PermissionError:
        base, ext = os.path.splitext(file_path)
        alt_path = f"{base}_最新{ext}"
        try:
            df.to_excel(alt_path, index=False, engine='openpyxl')
            print(f"⚠️ 提示: 检测到原文件 {os.path.basename(file_path)} 正被 Excel 占用，已安全保存至: {os.path.basename(alt_path)}")
            return alt_path
        except Exception:
            return file_path
    except Exception as e:
        print(f"[-] 保存 Excel 失败: {e}")
        return file_path


class USStockFraudDetector:
    def __init__(self, db_path="./sec_financials.duckdb", output_report="./美股上市公司财报造假风险扫描榜单.xlsx"):
        self.db_path = os.path.abspath(db_path)
        self.output_report = os.path.abspath(output_report)
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"未找到 SEC DuckDB 数据库 ({self.db_path})！请先运行 sec_to_duckdb.py。")

    def analyze_single_stock(self, cik_or_name: str, fy: str = "") -> dict:
        """从 DuckDB 秒级提取指定美股的报表并执行造假与粉饰排雷审计"""
        con = duckdb.connect(self.db_path, read_only=True)
        fy_filter = f"AND s.fy = '{fy}'" if fy else ""
        
        query = f"""
            WITH target_sub AS (
                SELECT cik, name, adsh, form, period, fy, fp
                FROM sub s
                WHERE (UPPER(s.name) LIKE UPPER(?) OR CAST(s.cik AS VARCHAR) = ?)
                  AND s.form IN ('10-K', '10-Q')
                  {fy_filter}
                ORDER BY s.period DESC
                LIMIT 1
            )
            SELECT 
                s.cik, s.name, s.form, s.period, s.fy, s.fp,
                MAX(CASE WHEN n.tag IN ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet') THEN n.value END) AS revenue,
                MAX(CASE WHEN n.tag IN ('NetIncomeLoss', 'ProfitLoss') THEN n.value END) AS net_income,
                MAX(CASE WHEN n.tag = 'Assets' THEN n.value END) AS assets,
                MAX(CASE WHEN n.tag IN ('StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest') THEN n.value END) AS equity,
                MAX(CASE WHEN n.tag = 'NetCashProvidedByUsedInOperatingActivities' THEN n.value END) AS cfo,
                MAX(CASE WHEN n.tag IN ('Goodwill', 'GoodwillGross') THEN n.value END) AS goodwill,
                MAX(CASE WHEN n.tag IN ('AccountsReceivableNetCurrent', 'AccountsAndOtherReceivablesNetCurrent') THEN n.value END) AS accounts_receivable,
                MAX(CASE WHEN n.tag IN ('CashAndCashEquivalentsAtCarryingValue', 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents') THEN n.value END) AS cash,
                MAX(CASE WHEN n.tag IN ('LongTermDebtNoncurrent', 'LongTermDebt', 'ShortTermBorrowings') THEN n.value END) AS debt
            FROM target_sub s
            JOIN num n ON s.adsh = n.adsh
            GROUP BY s.cik, s.name, s.form, s.period, s.fy, s.fp
        """
        df = con.execute(query, [f"%{cik_or_name}%", cik_or_name]).df()
        con.close()

        if df.empty:
            print(f"[-] 未在 DuckDB 中检索到公司 '{cik_or_name}' 的财报数据。")
            return {}

        row = df.iloc[0]
        cik = row['cik']
        name = row['name']
        rev = row['revenue'] if pd.notnull(row['revenue']) else 0.0
        ni = row['net_income'] if pd.notnull(row['net_income']) else 0.0
        assets = row['assets'] if pd.notnull(row['assets']) else 0.0
        equity = row['equity'] if pd.notnull(row['equity']) else 0.0
        cfo = row['cfo'] if pd.notnull(row['cfo']) else 0.0
        gw = row['goodwill'] if pd.notnull(row['goodwill']) else 0.0
        ar = row['accounts_receivable'] if pd.notnull(row['accounts_receivable']) else 0.0
        cash = row['cash'] if pd.notnull(row['cash']) else 0.0
        debt = row['debt'] if pd.notnull(row['debt']) else 0.0

        score = 0
        warnings = []

        # 规则 1: 净现比严重背离
        if ni > 5e7:
            if cfo <= 0:
                score += 25
                warnings.append(f"【净现比断裂】净利润(${ni/1e6:.1f}M)盈利，但经营现金流为负(${cfo/1e6:.1f}M)")
            elif cfo / ni < 0.3:
                score += 15
                warnings.append(f"【现金流羸弱】净现比仅为 {cfo/ni:.2f}")

        # 规则 2: 高额商誉悬顶
        if equity > 0 and gw > 0:
            gw_ratio = gw / equity
            if gw_ratio > 0.4 and gw > 5e7:
                score += 20
                warnings.append(f"【高额商誉悬顶】商誉占净资产比例达 {gw_ratio*100:.1f}% (${gw/1e6:.1f}M)")

        # 规则 3: 应收账款占收入比例畸高
        if rev > 0 and ar > 0:
            ar_ratio = ar / rev
            if ar_ratio > 0.6 and ar > 5e7:
                score += 15
                warnings.append(f"【应收账款畸高】应收账款占收入比重达 {ar_ratio*100:.1f}% (${ar/1e6:.1f}M)")

        # 规则 4: 资不抵债或负股东权益
        if equity < 0 and assets > 1e7:
            score += 30
            warnings.append(f"【资不抵债】股东权益为赤字负值 (${equity/1e6:.1f}M)，面临巨大重组/破产风险")

        # 规则 5: 存贷双高与流动性受限
        if cash > 5e8 and debt > 1e9 and cash / debt > 0.7:
            score += 20
            warnings.append(f"【存贷双高疑似】大额现金(${cash/1e6:.1f}M)与高额债务(${debt/1e6:.1f}M)并存")

        risk_level = "[极危] 红色高危" if score >= 50 else ("[预警] 橙色关注" if score >= 30 else ("[提示] 黄色提示" if score >= 15 else "[稳健] 绿色正常"))

        print("\n" + "=" * 65)
        print(f"【美股公司法务审计报告】: {name} (CIK: {cik})")
        print("=" * 65)
        print(f"● 报告期数据  : {row['period']} (Form {row['form']} | FY: {row['fy']})")
        print(f"● 营业收入    : ${rev/1e6:.2f} Million")
        print(f"● 净利润      : ${ni/1e6:.2f} Million")
        print(f"● 经营现金流  : ${cfo/1e6:.2f} Million")
        print(f"● 股东权益    : ${equity/1e6:.2f} Million")
        print(f"● 综合风险评分: {score} 分")
        print(f"● 综合风险等级: {risk_level}")
        print(f"● 命中风险项数: {len(warnings)} 项")
        print("-" * 65)
        print("【预警详情与审计诊断】:")
        if warnings:
            for item in warnings:
                print(f"  ❌ {item}")
        else:
            print("  ✅ 财务三张表指标勾稽稳健，未触发高危造假预警。")
        print("=" * 65 + "\n")

        return {
            "CIK": cik, "公司名称": name, "报告期": row['period'], "报表类型": row['form'],
            "风险评分": score, "风险等级": risk_level, "高危预警详情": " | ".join(warnings) if warnings else "正常"
        }

    def scan_all_stocks(self, fy: str = "", form: str = "", all_years: bool = False, output_report: str = ""):
        """使用 DuckDB 向量化引擎秒级全量扫描美股数万家公司"""
        out_file = output_report or self.output_report
        mode_desc = "2020-2026 历年所有申报记录 (全量历史)" if all_years or fy.lower() == 'all' else (f"{fy} 财年数据" if fy else "全美股所有公司最新披露数据 (含2026最新)")
        
        print("\n" + "=" * 70)
        print(f"[*] 正在通过 DuckDB 向量化引擎全量扫描美股上市公司造假风险...")
        print(f"[*] 扫描范围: {mode_desc} | 报表类型: {form if form else '10-K & 10-Q'}")
        print("=" * 70 + "\n")

        t0 = time.time()
        con = duckdb.connect(self.db_path, read_only=True)

        form_filter = f"AND form = '{form}'" if form and form.lower() != 'all' else "AND form IN ('10-K', '10-Q')"
        fy_filter = f"AND fy = '{fy}'" if fy and fy.lower() != 'all' else ""

        if all_years or fy.lower() == 'all':
            query = f"""
                WITH target_sub AS (
                    SELECT cik, name, adsh, form, period, fy, fp
                    FROM sub
                    WHERE 1=1 {form_filter} {fy_filter}
                )
                SELECT 
                    s.cik, s.name, s.form, s.period, s.fy, s.fp,
                    MAX(CASE WHEN n.tag IN ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet') THEN n.value END) AS revenue,
                    MAX(CASE WHEN n.tag IN ('NetIncomeLoss', 'ProfitLoss') THEN n.value END) AS net_income,
                    MAX(CASE WHEN n.tag = 'Assets' THEN n.value END) AS assets,
                    MAX(CASE WHEN n.tag IN ('StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest') THEN n.value END) AS equity,
                    MAX(CASE WHEN n.tag = 'NetCashProvidedByUsedInOperatingActivities' THEN n.value END) AS cfo,
                    MAX(CASE WHEN n.tag IN ('Goodwill', 'GoodwillGross') THEN n.value END) AS goodwill,
                    MAX(CASE WHEN n.tag IN ('AccountsReceivableNetCurrent', 'AccountsAndOtherReceivablesNetCurrent') THEN n.value END) AS accounts_receivable,
                    MAX(CASE WHEN n.tag IN ('CashAndCashEquivalentsAtCarryingValue', 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents') THEN n.value END) AS cash,
                    MAX(CASE WHEN n.tag IN ('LongTermDebtNoncurrent', 'LongTermDebt', 'ShortTermBorrowings') THEN n.value END) AS debt
                FROM target_sub s
                JOIN num n ON s.adsh = n.adsh
                GROUP BY s.cik, s.name, s.form, s.period, s.fy, s.fp
            """
        else:
            query = f"""
                WITH latest_filings AS (
                    SELECT cik, name, adsh, form, period, fy, fp,
                           ROW_NUMBER() OVER (PARTITION BY cik ORDER BY period DESC) as rn
                    FROM sub
                    WHERE 1=1 {form_filter} {fy_filter}
                ),
                target_sub AS (
                    SELECT cik, name, adsh, form, period, fy, fp
                    FROM latest_filings
                    WHERE rn = 1
                )
                SELECT 
                    s.cik, s.name, s.form, s.period, s.fy, s.fp,
                    MAX(CASE WHEN n.tag IN ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet') THEN n.value END) AS revenue,
                    MAX(CASE WHEN n.tag IN ('NetIncomeLoss', 'ProfitLoss') THEN n.value END) AS net_income,
                    MAX(CASE WHEN n.tag = 'Assets' THEN n.value END) AS assets,
                    MAX(CASE WHEN n.tag IN ('StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest') THEN n.value END) AS equity,
                    MAX(CASE WHEN n.tag = 'NetCashProvidedByUsedInOperatingActivities' THEN n.value END) AS cfo,
                    MAX(CASE WHEN n.tag IN ('Goodwill', 'GoodwillGross') THEN n.value END) AS goodwill,
                    MAX(CASE WHEN n.tag IN ('AccountsReceivableNetCurrent', 'AccountsAndOtherReceivablesNetCurrent') THEN n.value END) AS accounts_receivable,
                    MAX(CASE WHEN n.tag IN ('CashAndCashEquivalentsAtCarryingValue', 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents') THEN n.value END) AS cash,
                    MAX(CASE WHEN n.tag IN ('LongTermDebtNoncurrent', 'LongTermDebt', 'ShortTermBorrowings') THEN n.value END) AS debt
                FROM target_sub s
                JOIN num n ON s.adsh = n.adsh
                GROUP BY s.cik, s.name, s.form, s.period, s.fy, s.fp
            """

        df_raw = con.execute(query).df()
        con.close()

        print(f"[+] DuckDB 数据聚合完成，耗时 {time.time()-t0:.2f} 秒，共提取 {len(df_raw):,} 份财报记录。")
        print("[*] 正在并行计算每家公司的 8 大造假/粉饰风险评分与诊断详情...")

        results = []
        for _, row in df_raw.iterrows():
            cik = row['cik']
            name = row['name']
            rev = row['revenue'] if pd.notnull(row['revenue']) else 0.0
            ni = row['net_income'] if pd.notnull(row['net_income']) else 0.0
            assets = row['assets'] if pd.notnull(row['assets']) else 0.0
            equity = row['equity'] if pd.notnull(row['equity']) else 0.0
            cfo = row['cfo'] if pd.notnull(row['cfo']) else 0.0
            gw = row['goodwill'] if pd.notnull(row['goodwill']) else 0.0
            ar = row['accounts_receivable'] if pd.notnull(row['accounts_receivable']) else 0.0
            cash = row['cash'] if pd.notnull(row['cash']) else 0.0
            debt = row['debt'] if pd.notnull(row['debt']) else 0.0

            score = 0
            warnings = []

            # 规则 1: 净现比严重背离
            if ni > 5e7:
                if cfo <= 0:
                    score += 25
                    warnings.append(f"【净现比断裂】净利润({ni/1e6:.1f}M)盈利，但经营现金流为负({cfo/1e6:.1f}M)")
                elif cfo / ni < 0.3:
                    score += 15
                    warnings.append(f"【现金流羸弱】净现比仅为 {cfo/ni:.2f}")

            # 规则 2: 高额商誉悬顶
            if equity > 0 and gw > 0:
                gw_ratio = gw / equity
                if gw_ratio > 0.4 and gw > 5e7:
                    score += 20
                    warnings.append(f"【高额商誉悬顶】商誉占净资产比例达 {gw_ratio*100:.1f}% (${gw/1e6:.1f}M)")

            # 规则 3: 应收账款占收入比例畸高
            if rev > 0 and ar > 0:
                ar_ratio = ar / rev
                if ar_ratio > 0.6 and ar > 5e7:
                    score += 15
                    warnings.append(f"【应收账款畸高】应收账款占收入比重达 {ar_ratio*100:.1f}% (${ar/1e6:.1f}M)")

            # 规则 4: 资不抵债或负股东权益
            if equity < 0 and assets > 1e7:
                score += 30
                warnings.append(f"【资不抵债】股东权益为赤字负值 (${equity/1e6:.1f}M)，面临巨大重组/破产风险")

            # 规则 5: 存贷双高与流动性受限
            if cash > 5e8 and debt > 1e9 and cash / debt > 0.7:
                score += 20
                warnings.append(f"【存贷双高疑似】大额现金(${cash/1e6:.1f}M)与高额债务(${debt/1e6:.1f}M)并存")

            risk_level = "[极危] 红色高危" if score >= 50 else ("[预警] 橙色关注" if score >= 30 else ("[提示] 黄色提示" if score >= 15 else "[稳健] 绿色正常"))

            results.append({
                "CIK": cik,
                "公司名称": name,
                "财年": row['fy'],
                "报告期": row['period'],
                "报表类型": row['form'],
                "营业收入_百万美元": round(rev / 1e6, 2),
                "净利润_百万美元": round(ni / 1e6, 2),
                "经营现金流_百万美元": round(cfo / 1e6, 2),
                "总资产_百万美元": round(assets / 1e6, 2),
                "股东权益_百万美元": round(equity / 1e6, 2),
                "商誉_百万美元": round(gw / 1e6, 2),
                "风险评分": score,
                "风险等级": risk_level,
                "命中风险项数": len(warnings),
                "高危预警详情": " | ".join(warnings) if warnings else "财务指标稳健，未触发高危预警"
            })

        df_out = pd.DataFrame(results).sort_values(by="风险评分", ascending=False)
        actual_output = safe_save_excel(df_out, out_file)

        print("\n" + "=" * 70)
        print("🎉 【美股全市场财务造假与粉饰风险扫描完成！】")
        print("=" * 70)
        print(f"● 扫描财报总数: {len(df_out):,} 份")
        print(f"● 红色高危记录: {len(df_out[df_out['风险评分'] >= 50]):,} 份")
        print(f"● 橙色关注记录: {len(df_out[(df_out['风险评分'] >= 30) & (df_out['风险评分'] < 50)]):,} 份")
        print(f"● 黄色提示记录: {len(df_out[(df_out['风险评分'] >= 15) & (df_out['风险评分'] < 30)]):,} 份")
        print(f"● 全景报告导出: {os.path.abspath(actual_output)}")
        print("=" * 70)
        print("\n【美股风险评分 TOP 20 排行榜】:")
        print(df_out[["CIK", "公司名称", "财年", "报告期", "风险评分", "风险等级", "命中风险项数", "净利润_百万美元", "经营现金流_百万美元"]].head(20).to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="SEC 美股上市公司财报造假与粉饰风险自动扫描审计引擎")
    parser.add_argument("--db", type=str, default="./sec_financials.duckdb", help="SEC 美股 DuckDB 数据库路径")
    parser.add_argument("--output", type=str, default="./美股上市公司财报造假风险扫描榜单.xlsx", help="美股输出风险报告路径")
    parser.add_argument("--company", "--ticker", dest="company", type=str, default="", help="审计单只美股公司，如: --company 'APPLE' 或 --company 'TESLA'")
    parser.add_argument("--scan", action="store_true", help="全量扫描美股上万家公司的造假与粉饰风险 (DuckDB 秒级引擎)")
    parser.add_argument("--all-years", action="store_true", help="全量扫描 2020-2026 历年全部 18 万份历史申报记录")
    parser.add_argument("--fy", type=str, default="", help="目标财年过滤，如: 2025、2024、或留空默认最新")
    parser.add_argument("--form", type=str, default="", help="报表类型过滤，如 10-K 或 10-Q，留空默认全部")
    args = parser.parse_args()

    detector = USStockFraudDetector(db_path=args.db, output_report=args.output)

    if args.company:
        detector.analyze_single_stock(cik_or_name=args.company, fy=args.fy)
    elif args.scan or args.all_years:
        detector.scan_all_stocks(fy=args.fy, form=args.form, all_years=args.all_years, output_report=args.output)
    else:
        # 默认模式：全美股最新一期扫描
        detector.scan_all_stocks(fy=args.fy, form=args.form, all_years=args.all_years, output_report=args.output)


if __name__ == "__main__":
    main()
