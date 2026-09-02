# -*- coding: utf-8 -*-
"""
SEC 美股财务数据 DuckDB 秒级查询工具 (CLI & Python API)
"""

import os
import sys
import argparse
import duckdb
import pandas as pd

# 保证 Windows 控制台 UTF-8 输出
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


class SecQueryEngine:
    def __init__(self, db_path="./sec_financials.duckdb"):
        self.db_path = os.path.abspath(db_path)
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"未找到 DuckDB 数据库 ({self.db_path})！请先运行 sec_to_duckdb.py。")
        self.con = duckdb.connect(self.db_path, read_only=True)

    def search_company(self, keyword: str) -> pd.DataFrame:
        """根据公司名称或 CIK 模糊搜索美股公司"""
        query = """
            SELECT DISTINCT cik, name, sic, countryba, cityba
            FROM sub
            WHERE UPPER(name) LIKE UPPER(?) OR CAST(cik AS VARCHAR) = ?
            ORDER BY name
            LIMIT 20
        """
        return self.con.execute(query, [f"%{keyword}%", keyword]).df()

    def get_company_filings(self, cik_or_name: str, form: str = "10-K") -> pd.DataFrame:
        """查询指定公司的历年财报列表"""
        query = f"""
            SELECT cik, name, form, period, fy, fp, filed, quarter, adsh
            FROM sub
            WHERE (UPPER(name) LIKE UPPER(?) OR CAST(cik AS VARCHAR) = ?)
              {"AND form = '" + form + "'" if form else ""}
            ORDER BY period DESC
            LIMIT 30
        """
        return self.con.execute(query, [f"%{cik_or_name}%", cik_or_name]).df()

    def get_three_statement_metrics(self, cik_or_name: str, fy: str = "") -> pd.DataFrame:
        """提取指定公司的核心三张表指标（营收、净利润、总资产、经营现金流等）"""
        fy_filter = f"AND s.fy = '{fy}'" if fy else ""
        query = f"""
            WITH target_sub AS (
                SELECT cik, name, adsh, form, period, fy, fp
                FROM sub s
                WHERE (UPPER(s.name) LIKE UPPER(?) OR CAST(s.cik AS VARCHAR) = ?)
                  AND s.form IN ('10-K', '10-Q')
                  {fy_filter}
            )
            SELECT 
                s.cik, s.name, s.form, s.period, s.fy, s.fp,
                MAX(CASE WHEN n.tag IN ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet') THEN n.value END) AS revenue,
                MAX(CASE WHEN n.tag IN ('NetIncomeLoss', 'ProfitLoss') THEN n.value END) AS net_income,
                MAX(CASE WHEN n.tag = 'Assets' THEN n.value END) AS total_assets,
                MAX(CASE WHEN n.tag IN ('StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest') THEN n.value END) AS total_equity,
                MAX(CASE WHEN n.tag = 'NetCashProvidedByUsedInOperatingActivities' THEN n.value END) AS operating_cash_flow,
                MAX(CASE WHEN n.tag IN ('Goodwill', 'GoodwillGross') THEN n.value END) AS goodwill
            FROM target_sub s
            JOIN num n ON s.adsh = n.adsh
            GROUP BY s.cik, s.name, s.form, s.period, s.fy, s.fp
            ORDER BY s.period DESC
            LIMIT 20
        """
        return self.con.execute(query, [f"%{cik_or_name}%", cik_or_name]).df()

    def execute_sql(self, sql_str: str) -> pd.DataFrame:
        """执行任意自定义 DuckDB SQL 查询"""
        return self.con.execute(sql_str).df()


def main():
    parser = argparse.ArgumentParser(description="SEC 美股财务数据 DuckDB 查询工具")
    parser.add_argument("--search", type=str, default="", help="搜索公司名称或 CIK，如: --search 'NVIDIA'")
    parser.add_argument("--company", type=str, default="", help="查询指定公司的核心财务三张表指标，如: --company 'APPLE'")
    parser.add_argument("--fy", type=str, default="", help="指定财年过滤，如: --fy 2025")
    parser.add_argument("--filings", type=str, default="", help="查询公司的财报申报记录，如: --filings 'TESLA'")
    parser.add_argument("--sql", type=str, default="", help="执行自定义 SQL 查询")
    parser.add_argument("--export", type=str, default="", help="导出查询结果为 Excel 文件路径")
    parser.add_argument("--db", type=str, default="./sec_financials.duckdb", help="DuckDB 数据库路径")
    args = parser.parse_args()

    engine = SecQueryEngine(db_path=args.db)
    df_res = None

    if args.search:
        print(f"\n[*] 正在搜索公司: '{args.search}'...")
        df_res = engine.search_company(args.search)
    elif args.company:
        print(f"\n[*] 正在查询公司财务指标: '{args.company}'...")
        df_res = engine.get_three_statement_metrics(args.company, fy=args.fy)
    elif args.filings:
        print(f"\n[*] 正在查询公司申报记录: '{args.filings}'...")
        df_res = engine.get_company_filings(args.filings)
    elif args.sql:
        print(f"\n[*] 正在执行自定义 SQL:\n{args.sql}\n")
        df_res = engine.execute_sql(args.sql)
    else:
        print("[*] 默认查询示例: NVIDIA 历史财务三张表核心指标:")
        df_res = engine.get_three_statement_metrics("NVIDIA")

    if df_res is not None:
        print("=" * 80)
        print(df_res.to_string(index=False))
        print("=" * 80)

        if args.export:
            df_res.to_excel(args.export, index=False, engine='openpyxl')
            print(f"[+] 结果已导出至 Excel: {args.export}")


if __name__ == "__main__":
    main()
