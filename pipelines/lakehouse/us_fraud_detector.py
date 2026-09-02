# -*- coding: utf-8 -*-
"""
SEC 美股上市公司财报造假与粉饰风险自动扫描审计引擎 (US Stocks Forensic Audit Engine)
全面整合 forensic_engine 法务会计规则库与 Beneish M-Score / Altman Z-Score / Sloan 净应计模型。
支持秒级单票深度诊断与全美股数十万申报记录全量向量化极速扫描。
"""

import os
import sys
import time
import re
import argparse
from datetime import datetime
import duckdb
import pandas as pd
import numpy as np

# 保证 Windows 控制台 UTF-8 输出
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from forensic_engine import ForensicEvaluator


def generate_report_filename(prefix: str = "美股上市公司财报排雷榜单", fy: str = "", all_years: bool = False, company: str = "", actual_min_y: str = "", actual_max_y: str = "") -> str:
    """根据扫描目标、年份区间与当前时间自动生成语义化文件命名"""
    now_str = datetime.now().strftime("%Y%m%d_%H%M")
    if company:
        safe_c = re.sub(r'[^\w]+', '_', company).strip('_')
        return f"美股法务排雷报告_{safe_c}_{now_str}.xlsx"
    if actual_min_y and actual_max_y:
        if actual_min_y == actual_max_y:
            return f"{prefix}_{actual_min_y}年全景_{now_str}.xlsx"
        else:
            return f"{prefix}_{actual_min_y}-{actual_max_y}历年全景_{now_str}.xlsx"
    elif all_years or (fy and fy.lower() == 'all'):
        return f"{prefix}_2016-2026历年全景_10年完整数据_{now_str}.xlsx"
    elif fy:
        return f"{prefix}_{fy}财年_{now_str}.xlsx"
    else:
        return f"{prefix}_全市场最新财年_{now_str}.xlsx"


def safe_save_excel(data, file_path: str) -> str:
    """安全保存 Excel 文件（支持单 DataFrame 或多 Sheet 字典），若被 Excel 软件打开锁定则自动保存为备用名称"""
    base, ext = os.path.splitext(file_path)
    for attempt_path in [file_path, f"{base}_最新{ext}"]:
        try:
            if isinstance(data, dict):
                with pd.ExcelWriter(attempt_path, engine='openpyxl') as writer:
                    for sheet_name, df_sheet in data.items():
                        df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                data.to_excel(attempt_path, index=False, engine='openpyxl')

            if attempt_path != file_path:
                print(f"⚠️ 提示: 检测到原文件 {os.path.basename(file_path)} 正被 Excel 占用，已安全保存至: {os.path.basename(attempt_path)}")
            return attempt_path
        except PermissionError:
            continue
        except Exception as e:
            print(f"[-] 保存 Excel 失败: {e}")
            return file_path
    return file_path


class USStockFraudDetector:
    def __init__(self, db_path="./sec_financials.duckdb", output_report="./美股上市公司财报造假风险扫描榜单.xlsx"):
        self.db_path = os.path.abspath(db_path)
        self.output_report = os.path.abspath(output_report)

    def _ensure_db(self):
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"未找到 SEC DuckDB 数据库 ({self.db_path})！请先运行 sec_to_duckdb.py 构建湖仓。")

    def analyze_single_stock(self, cik_or_name: str, fy: str = "") -> dict:
        """从 DuckDB 秒级提取指定美股的报表并执行深度法务排雷审计"""
        self._ensure_db()
        con = duckdb.connect(self.db_path, read_only=True)
        fy_filter = f"AND s.fy = '{fy}'" if fy else ""
        
        # 提取最近 2 期报表以支持时序比率与 Beneish 计算
        query = f"""
            WITH target_subs AS (
                SELECT cik, name, adsh, form, period, fy, fp
                FROM sub s
                WHERE (UPPER(s.name) LIKE UPPER(?) OR CAST(s.cik AS VARCHAR) = ?)
                  AND s.form IN ('10-K', '10-Q')
                  {fy_filter}
                ORDER BY s.period DESC
                LIMIT 2
            )
            SELECT 
                s.cik, s.name, s.form, s.period, s.fy, s.fp,
                MAX(CASE WHEN n.tag IN ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet') THEN n.value END) AS sales,
                MAX(CASE WHEN n.tag IN ('CostOfGoodsAndServicesSold', 'CostOfGoodsSold') THEN n.value END) AS cogs,
                MAX(CASE WHEN n.tag IN ('OperatingIncomeLoss') THEN n.value END) AS operating_income,
                MAX(CASE WHEN n.tag IN ('NetIncomeLoss', 'ProfitLoss') THEN n.value END) AS net_income,
                MAX(CASE WHEN n.tag = 'Assets' THEN n.value END) AS assets,
                MAX(CASE WHEN n.tag = 'AssetsCurrent' THEN n.value END) AS current_assets,
                MAX(CASE WHEN n.tag = 'Liabilities' THEN n.value END) AS liabilities,
                MAX(CASE WHEN n.tag = 'LiabilitiesCurrent' THEN n.value END) AS current_liabilities,
                MAX(CASE WHEN n.tag IN ('StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest') THEN n.value END) AS equity,
                MAX(CASE WHEN n.tag = 'NetCashProvidedByUsedInOperatingActivities' THEN n.value END) AS cfo,
                MAX(CASE WHEN n.tag = 'NetCashProvidedByUsedInInvestingActivities' THEN n.value END) AS cfi,
                MAX(CASE WHEN n.tag = 'NetCashProvidedByUsedInFinancingActivities' THEN n.value END) AS cff,
                MAX(CASE WHEN n.tag IN ('Goodwill', 'GoodwillGross') THEN n.value END) AS goodwill,
                MAX(CASE WHEN n.tag IN ('AccountsReceivableNetCurrent', 'AccountsAndOtherReceivablesNetCurrent') THEN n.value END) AS ar,
                MAX(CASE WHEN n.tag IN ('InventoryNet') THEN n.value END) AS inv,
                MAX(CASE WHEN n.tag IN ('PropertyPlantAndEquipmentNet') THEN n.value END) AS ppe_net,
                MAX(CASE WHEN n.tag IN ('ConstructionInProgress') THEN n.value END) AS cip,
                MAX(CASE WHEN n.tag IN ('CashAndCashEquivalentsAtCarryingValue', 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents') THEN n.value END) AS cash,
                MAX(CASE WHEN n.tag IN ('LongTermDebtNoncurrent', 'LongTermDebt', 'ShortTermBorrowings') THEN n.value END) AS debt
            FROM target_subs s
            JOIN num n ON s.adsh = n.adsh
            GROUP BY s.cik, s.name, s.form, s.period, s.fy, s.fp
            ORDER BY s.period DESC
        """
        df = con.execute(query, [f"%{cik_or_name}%", cik_or_name]).df()
        con.close()

        if df.empty:
            print(f"[-] 未在 DuckDB 中检索到公司 '{cik_or_name}' 的财报数据。")
            return {}

        curr_record = df.iloc[0].to_dict()
        prev_record = df.iloc[1].to_dict() if len(df) > 1 else None

        # 执行法务排雷引擎深度评估
        report = ForensicEvaluator.evaluate_single(curr_record, prev_record=prev_record)

        cik = curr_record['cik']
        name = curr_record['name']
        rev = curr_record.get('sales') or 0.0
        ni = curr_record.get('net_income') or 0.0
        cfo = curr_record.get('cfo') or 0.0
        assets = curr_record.get('assets') or 0.0
        equity = curr_record.get('equity') or 0.0
        gw = curr_record.get('goodwill') or 0.0

        print("\n" + "=" * 70)
        print(f"🏛️ 【美股法务会计审计与排雷诊断报告】: {name} (CIK: {cik})")
        print("=" * 70)
        print(f"● 报告期数据  : {curr_record.get('period')} (Form {curr_record.get('form')} | FY: {curr_record.get('fy')})")
        print(f"● 营业收入    : ${rev/1e6:,.2f} Million")
        print(f"● 净利润      : ${ni/1e6:,.2f} Million")
        print(f"● 经营现金流  : ${cfo/1e6:,.2f} Million")
        print(f"● 股东总权益  : ${equity/1e6:,.2f} Million")
        print(f"● 账面商誉    : ${gw/1e6:,.2f} Million")
        print("-" * 70)
        print(f"● 综合风险评分: {report['total_risk_score']} 分 (0~100, 越高风险越大)")
        print(f"● 综合风险等级: {report['risk_level']}")
        print(f"● 命中排雷项数: {report['warning_count']} 项")
        print(f"● Altman Z分值: {report.get('altman_z')} ({report.get('altman_zone')})")
        print(f"● Sloan净应计 : {report.get('sloan_accrual')} ({'高应计水分' if report.get('sloan_accrual', 0) > 0.1 else '现金含量充足'})")
        if report.get('beneish_m_score') is not None:
            print(f"● Beneish M分 : {report.get('beneish_m_score')} ({'高危操纵嫌疑' if report.get('beneish_is_manipulator') else '未见系统性操纵'})")
        print("-" * 70)
        print("【预警明细与法务诊断】:")
        if report['warnings']:
            for item in report['warnings']:
                print(f"  ❌ {item}")
        else:
            print("  ✅ 财务三张表勾稽稳健，各项法务指标均处于正常安全区间。")
        print("=" * 70 + "\n")

        return report

    def scan_all_stocks(self, fy: str = "", form: str = "", all_years: bool = False, output_report: str = ""):
        """使用 DuckDB + ForensicEvaluator 向量化引擎秒级全量扫描美股数万家公司"""
        self._ensure_db()
        out_file = output_report or self.output_report
        mode_desc = "2016-2026 历年所有申报记录 (跨10年完整历史数据)" if all_years or fy.lower() == 'all' else (f"{fy} 财年数据" if fy else "全美股所有公司最新披露数据")
        
        print("\n" + "=" * 70)
        print(f"[*] 启动 DuckDB + ForensicEvaluator 极速向量化扫描引擎...")
        print(f"[*] 扫描范围: {mode_desc} | 报表类型: {form if form else '10-K & 10-Q'}")
        print("=" * 70 + "\n")

        t0 = time.time()
        con = duckdb.connect(self.db_path, read_only=True)

        form_filter = f"AND s.form = '{form}'" if form and form.lower() != 'all' else "AND s.form IN ('10-K', '10-Q')"
        
        if fy and fy.lower() != 'all':
            fy_filter = f"AND s.fy = '{fy}'"
        elif all_years:
            # 跨 10 年完整数据全景排查：严格限定 2016-2026，坚决过滤 2004 等历史迟交补报噪点
            fy_filter = "AND try_cast(substr(cast(s.period as varchar), 1, 4) as int) >= 2016"
        else:
            # 最新财年扫描模式：只扫描最近 3 年有真实披露的活跃上市公司，坚决过滤历史退市僵尸公司
            fy_filter = "AND try_cast(substr(cast(s.period as varchar), 1, 4) as int) >= 2022"

        if all_years or (fy and fy.lower() == 'all'):
            query = f"""
                WITH target_sub AS (
                    SELECT cik, name, adsh, form, period, fy, fp
                    FROM sub s
                    WHERE 1=1 {form_filter} {fy_filter}
                )
                SELECT 
                    s.cik, s.name, s.form, s.period, s.fy, s.fp,
                    MAX(CASE WHEN n.tag IN ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet') THEN n.value END) AS sales,
                    MAX(CASE WHEN n.tag IN ('CostOfGoodsAndServicesSold', 'CostOfGoodsSold') THEN n.value END) AS cogs,
                    MAX(CASE WHEN n.tag IN ('OperatingIncomeLoss') THEN n.value END) AS operating_income,
                    MAX(CASE WHEN n.tag IN ('NetIncomeLoss', 'ProfitLoss') THEN n.value END) AS net_income,
                    MAX(CASE WHEN n.tag = 'Assets' THEN n.value END) AS assets,
                    MAX(CASE WHEN n.tag = 'AssetsCurrent' THEN n.value END) AS current_assets,
                    MAX(CASE WHEN n.tag = 'Liabilities' THEN n.value END) AS liabilities,
                    MAX(CASE WHEN n.tag = 'LiabilitiesCurrent' THEN n.value END) AS current_liabilities,
                    MAX(CASE WHEN n.tag IN ('StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest') THEN n.value END) AS equity,
                    MAX(CASE WHEN n.tag = 'NetCashProvidedByUsedInOperatingActivities' THEN n.value END) AS cfo,
                    MAX(CASE WHEN n.tag = 'NetCashProvidedByUsedInInvestingActivities' THEN n.value END) AS cfi,
                    MAX(CASE WHEN n.tag = 'NetCashProvidedByUsedInFinancingActivities' THEN n.value END) AS cff,
                    MAX(CASE WHEN n.tag IN ('Goodwill', 'GoodwillGross') THEN n.value END) AS goodwill,
                    MAX(CASE WHEN n.tag IN ('AccountsReceivableNetCurrent', 'AccountsAndOtherReceivablesNetCurrent') THEN n.value END) AS ar,
                    MAX(CASE WHEN n.tag IN ('InventoryNet') THEN n.value END) AS inv,
                    MAX(CASE WHEN n.tag IN ('PropertyPlantAndEquipmentNet') THEN n.value END) AS ppe_net,
                    MAX(CASE WHEN n.tag IN ('ConstructionInProgress') THEN n.value END) AS cip,
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
                    FROM sub s
                    WHERE 1=1 {form_filter} {fy_filter}
                ),
                target_sub AS (
                    SELECT cik, name, adsh, form, period, fy, fp
                    FROM latest_filings
                    WHERE rn = 1
                )
                SELECT 
                    s.cik, s.name, s.form, s.period, s.fy, s.fp,
                    MAX(CASE WHEN n.tag IN ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet') THEN n.value END) AS sales,
                    MAX(CASE WHEN n.tag IN ('CostOfGoodsAndServicesSold', 'CostOfGoodsSold') THEN n.value END) AS cogs,
                    MAX(CASE WHEN n.tag IN ('OperatingIncomeLoss') THEN n.value END) AS operating_income,
                    MAX(CASE WHEN n.tag IN ('NetIncomeLoss', 'ProfitLoss') THEN n.value END) AS net_income,
                    MAX(CASE WHEN n.tag = 'Assets' THEN n.value END) AS assets,
                    MAX(CASE WHEN n.tag = 'AssetsCurrent' THEN n.value END) AS current_assets,
                    MAX(CASE WHEN n.tag = 'Liabilities' THEN n.value END) AS liabilities,
                    MAX(CASE WHEN n.tag = 'LiabilitiesCurrent' THEN n.value END) AS current_liabilities,
                    MAX(CASE WHEN n.tag IN ('StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest') THEN n.value END) AS equity,
                    MAX(CASE WHEN n.tag = 'NetCashProvidedByUsedInOperatingActivities' THEN n.value END) AS cfo,
                    MAX(CASE WHEN n.tag = 'NetCashProvidedByUsedInInvestingActivities' THEN n.value END) AS cfi,
                    MAX(CASE WHEN n.tag = 'NetCashProvidedByUsedInFinancingActivities' THEN n.value END) AS cff,
                    MAX(CASE WHEN n.tag IN ('Goodwill', 'GoodwillGross') THEN n.value END) AS goodwill,
                    MAX(CASE WHEN n.tag IN ('AccountsReceivableNetCurrent', 'AccountsAndOtherReceivablesNetCurrent') THEN n.value END) AS ar,
                    MAX(CASE WHEN n.tag IN ('InventoryNet') THEN n.value END) AS inv,
                    MAX(CASE WHEN n.tag IN ('PropertyPlantAndEquipmentNet') THEN n.value END) AS ppe_net,
                    MAX(CASE WHEN n.tag IN ('ConstructionInProgress') THEN n.value END) AS cip,
                    MAX(CASE WHEN n.tag IN ('CashAndCashEquivalentsAtCarryingValue', 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents') THEN n.value END) AS cash,
                    MAX(CASE WHEN n.tag IN ('LongTermDebtNoncurrent', 'LongTermDebt', 'ShortTermBorrowings') THEN n.value END) AS debt
                FROM target_sub s
                JOIN num n ON s.adsh = n.adsh
                GROUP BY s.cik, s.name, s.form, s.period, s.fy, s.fp
            """

        df_raw = con.execute(query).df()
        con.close()

        print(f"[+] DuckDB 湖仓聚合完成，耗时 {time.time()-t0:.2f} 秒，提取 {len(df_raw):,} 份财报记录。")
        print("[*] 正在执行全量向量化法务排雷算法与多模型预测...")

        t_eval = time.time()
        df_scored = ForensicEvaluator.evaluate_dataframe(df_raw, entity_col='cik', time_col='period')
        print(f"[+] 向量化评估完毕，耗时 {time.time()-t_eval:.2f} 秒！")

        # 计算实际覆盖的年份区间 (按主体年份统计，过滤个别迟交补报噪点)
        periods_str = df_scored['period'].astype(str).str[:4]
        valid_years = periods_str.value_counts()
        mainstream_years = valid_years[valid_years >= 50].index.sort_values()
        if not mainstream_years.empty:
            actual_min_y = str(mainstream_years[0])
            actual_max_y = str(mainstream_years[-1])
        else:
            actual_min_y = "2016"
            actual_max_y = "2026"

        # 动态智能命名报告文件 (若未指定自定义路径或为默认路径)
        if not output_report or "美股上市公司财报造假风险扫描榜单.xlsx" in output_report:
            out_file = generate_report_filename(
                prefix="美股上市公司排雷榜单",
                fy=fy,
                all_years=all_years,
                actual_min_y=actual_min_y,
                actual_max_y=actual_max_y
            )
        else:
            out_file = output_report

        # 整理导出列 (包含清晰直白的排雷诊断结论与具体成因 Notes)
        df_out = df_scored[[
            'cik', 'name', 'fy', 'period', 'form',
            'total_risk_score', 'risk_level', 'diagnostic_summary', 'risk_reasons_notes', 'hit_risk_count',
            'altman_z_score', 'altman_zone', 'sloan_accrual',
            'beneish_m_score', 'beneish_is_manipulator',
            'sales', 'net_income', 'cfo', 'assets', 'equity', 'goodwill'
        ]].copy()

        df_out['营业收入_百万美元'] = (df_out['sales'].fillna(0) / 1e6).round(2)
        df_out['净利润_百万美元'] = (df_out['net_income'].fillna(0) / 1e6).round(2)
        df_out['经营现金流_百万美元'] = (df_out['cfo'].fillna(0) / 1e6).round(2)
        df_out['总资产_百万美元'] = (df_out['assets'].fillna(0) / 1e6).round(2)
        df_out['股东权益_百万美元'] = (df_out['equity'].fillna(0) / 1e6).round(2)
        df_out['商誉_百万美元'] = (df_out['goodwill'].fillna(0) / 1e6).round(2)
        df_out = df_out.drop(columns=['sales', 'net_income', 'cfo', 'assets', 'equity', 'goodwill'])

        # -------------------------------------------------------------
        # 核心架构：以【公司 (Company/CIK)】为核心主键排列，输出清晰诊断 Notes
        # -------------------------------------------------------------
        # 1. 构建【公司排雷总榜 (Company Summary)】：每家公司独占一行
        df_latest_by_company = df_out.sort_values(by='period', ascending=False).groupby('cik', as_index=False).first()

        # 计算公司级跨期画像：历史最高风险、审计总期数
        agg_stats = df_out.groupby('cik').agg(
            历史最高风险评分=('total_risk_score', 'max'),
            纳入审计财报期数=('period', 'count')
        ).reset_index()

        df_company_summary = pd.merge(df_latest_by_company, agg_stats, on='cik', how='left')

        # 排序：优先按当前最新综合风险分倒序，相同时看历史最高风险
        df_company_summary = df_company_summary.sort_values(
            by=['total_risk_score', '历史最高风险评分'],
            ascending=[False, False]
        )

        df_company_summary = df_company_summary.rename(columns={
            'cik': 'CIK',
            'name': '公司名称',
            'period': '最新申报期',
            'fy': '最新财年',
            'form': '最新报表类型',
            'total_risk_score': '当前综合风险评分',
            'risk_level': '当前风险等级',
            'diagnostic_summary': '排雷诊断结论',
            'risk_reasons_notes': '具体风险成因与排雷证据说明(Notes)',
            'hit_risk_count': '当前预警项数',
            'altman_z_score': '最新Altman_Z',
            'altman_zone': '最新Z分区间',
            'sloan_accrual': '最新Sloan净应计',
            'beneish_m_score': '最新Beneish_M',
            'beneish_is_manipulator': '最新疑似操纵'
        })

        # 2. 构建【公司历年穿透明细 (Filings Timeline by Company)】：
        # 同一家公司的历年 10-K/10-Q 连续紧挨排列，时间倒序追踪财务异化轨迹
        df_out['公司最高风险分'] = df_out.groupby('cik')['total_risk_score'].transform('max')
        df_filings_by_company = df_out.sort_values(
            by=['公司最高风险分', 'cik', 'period'],
            ascending=[False, True, False]
        ).drop(columns=['公司最高风险分'])

        df_filings_by_company = df_filings_by_company.rename(columns={
            'cik': 'CIK',
            'name': '公司名称',
            'period': '财报报告期',
            'fy': '财年',
            'form': '申报类型',
            'total_risk_score': '当期风险评分',
            'risk_level': '当期风险等级',
            'diagnostic_summary': '排雷诊断结论',
            'risk_reasons_notes': '当期具体风险成因与排雷证据说明(Notes)',
            'hit_risk_count': '当期预警项数',
            'altman_z_score': 'Altman_Z分值',
            'altman_zone': 'Z分区间',
            'sloan_accrual': 'Sloan净应计',
            'beneish_m_score': 'Beneish_M分值',
            'beneish_is_manipulator': '疑似报表操纵'
        })

        # 3. 构建【高危操纵关注专区 (High Risk Watchlist)】
        df_red_flags = df_company_summary[df_company_summary['当前综合风险评分'] >= 50].copy()

        # 根据是否为多年度历年模式自适应调整 Sheet 顺序
        is_multi_year = all_years or (fy and fy.lower() == 'all') or (actual_min_y != actual_max_y)
        if is_multi_year:
            # 历年大排查模式下，首工作表优先展示同一家公司的跨年度历年穿透明细
            sheets_data = {
                f"公司历年穿透明细({actual_min_y}-{actual_max_y})": df_filings_by_company,
                "美股上市公司排雷总榜": df_company_summary,
                "高危操纵关注名单": df_red_flags
            }
        else:
            sheets_data = {
                "美股上市公司排雷总榜": df_company_summary,
                "公司历年报表穿透明细": df_filings_by_company,
                "高危操纵关注名单": df_red_flags
            }

        actual_output = safe_save_excel(sheets_data, out_file)

        print("\n" + "=" * 70)
        print("🎉 【美股全市场财务造假与粉饰风险扫描完成！】")
        print("=" * 70)
        print(f"● 实际覆盖区间: {actual_min_y} 年 ~ {actual_max_y} 年 (共 {len(df_filings_by_company):,} 份财报)")
        print(f"● 扫描覆盖公司: {len(df_company_summary):,} 家上市公司 (以公司为核心排列)")
        print(f"● 红色高危公司: {len(df_company_summary[df_company_summary['当前综合风险评分'] >= 50]):,} 家")
        print(f"● 橙色关注公司: {len(df_company_summary[(df_company_summary['当前综合风险评分'] >= 30) & (df_company_summary['当前综合风险评分'] < 50)]):,} 家")
        print(f"● 黄色提示公司: {len(df_company_summary[(df_company_summary['当前综合风险评分'] >= 15) & (df_company_summary['当前综合风险评分'] < 30)]):,} 家")
        print(f"● 绿色安全公司: {len(df_company_summary[df_company_summary['当前综合风险评分'] < 15]):,} 家")
        print(f"● 报告智能命名: {os.path.basename(actual_output)}")
        print(f"● 全景报告导出: {os.path.abspath(actual_output)}")
        print("  - 表格特性: 包含【排雷诊断结论】与分条【具体风险成因与证据说明(Notes)】")
        print(f"  - Sheet 1: {'公司历年穿透明细 (跨年度连续排列)' if is_multi_year else '美股上市公司排雷总榜 (每家公司独立一行)'}")
        print("=" * 70)
        print("\n【美股风险评分 TOP 20 公司排行榜】:")
        print(df_company_summary[["CIK", "公司名称", "最新申报期", "当前综合风险评分", "当前风险等级", "排雷诊断结论"]].head(20).to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="SEC 美股上市公司财报造假与粉饰风险自动扫描审计引擎")
    parser.add_argument("--db", type=str, default="./sec_financials.duckdb", help="SEC 美股 DuckDB 数据库路径")
    parser.add_argument("--output", type=str, default="./美股上市公司财报造假风险扫描榜单.xlsx", help="美股输出风险报告路径")
    parser.add_argument("--company", "--ticker", dest="company", type=str, default="", help="审计单只美股公司，如: --company 'APPLE' 或 --company 'TESLA'")
    parser.add_argument("--scan", action="store_true", help="全量扫描美股上万家公司的造假与粉饰风险 (DuckDB 秒级引擎)")
    parser.add_argument("--all-years", action="store_true", help="全量扫描 2016-2026 历年跨 10 年全部历史申报记录")
    parser.add_argument("--fy", type=str, default="", help="目标财年过滤，如: 2025、2024、或留空默认最新")
    parser.add_argument("--form", type=str, default="", help="报表类型过滤，如 10-K 或 10-Q，留空默认全部")
    args = parser.parse_args()

    detector = USStockFraudDetector(db_path=args.db, output_report=args.output)

    if args.company:
        detector.analyze_single_stock(cik_or_name=args.company, fy=args.fy)
    elif args.scan or args.all_years:
        detector.scan_all_stocks(fy=args.fy, form=args.form, all_years=args.all_years, output_report=args.output)
    else:
        detector.scan_all_stocks(fy=args.fy, form=args.form, all_years=args.all_years, output_report=args.output)


if __name__ == "__main__":
    main()
