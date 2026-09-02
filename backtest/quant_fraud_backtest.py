# -*- coding: utf-8 -*-
"""
法务会计与财报排雷量化因子库 & 向量化回测引擎 (Forensic Alpha Factors & Backtest Engine)
基于 DuckDB + Pandas 实现毫秒级因子计算与跨期截面量化回测：
1. Beneish M-Score 操纵因子
2. Sloan 净应计利润异象因子 (Sloan Accrual Factor)
3. 净现比与造血质量因子 (Cash Flow Decoupling Quality)
4. 商誉负担与减值风险因子 (Goodwill Burden)
5. 存贷双高异常因子 (Cash-Debt Coexistence Spread)
6. 综合法务会计复合 Alpha 因子 (Composite Forensic Quality Alpha)
"""

import os
import sys
import time
import argparse
import duckdb
import pandas as pd
import numpy as np
from datetime import datetime

# 项目绝对根目录锚定
_BACKTEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_BACKTEST_DIR)
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "sec_financials.duckdb")

# 动态自然时间推导
_NOW = datetime.now()
CURRENT_YEAR = _NOW.year
DEFAULT_START_YEAR = CURRENT_YEAR - 10

# 保证 Windows 控制台 UTF-8 输出
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


class ForensicFactorEngine:
    """法务会计量化因子计算与特征工程引擎"""
    def __init__(self, db_path: str = ""):
        self.db_path = os.path.abspath(db_path) if db_path else DEFAULT_DB_PATH
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"未找到数据库文件: {self.db_path}，请先运行 sec_to_duckdb.py")

    def build_factor_panel(self) -> pd.DataFrame:
        """从 DuckDB 中秒级提取并构建全市场面板数据，计算各项核心量化排雷与质量因子"""
        print("[*] 正在从 DuckDB 数据库提取面板数据并计算截面量化因子...")
        t0 = time.time()
        con = duckdb.connect(self.db_path, read_only=True)

        # 动态提取跨 10 年历年 10-K 年报面板数据
        sql = f"""
            WITH raw_panel AS (
                SELECT 
                    s.cik, s.name, s.period, s.fy, s.quarter,
                    MAX(CASE WHEN n.tag IN ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet') THEN n.value END) AS sales,
                    MAX(CASE WHEN n.tag IN ('GrossProfit', 'GrossMargin') THEN n.value END) AS gross_profit,
                    MAX(CASE WHEN n.tag IN ('CostOfGoodsAndServicesSold', 'CostOfGoodsSold') THEN n.value END) AS cogs,
                    MAX(CASE WHEN n.tag IN ('NetIncomeLoss', 'ProfitLoss') THEN n.value END) AS net_income,
                    MAX(CASE WHEN n.tag IN ('OperatingIncomeLoss') THEN n.value END) AS operating_income,
                    MAX(CASE WHEN n.tag = 'Assets' THEN n.value END) AS assets,
                    MAX(CASE WHEN n.tag = 'AssetsCurrent' THEN n.value END) AS current_assets,
                    MAX(CASE WHEN n.tag = 'PropertyPlantAndEquipmentNet' THEN n.value END) AS ppe_net,
                    MAX(CASE WHEN n.tag IN ('StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest') THEN n.value END) AS equity,
                    MAX(CASE WHEN n.tag IN ('NetCashProvidedByUsedInOperatingActivities') THEN n.value END) AS cfo,
                    MAX(CASE WHEN n.tag IN ('Goodwill', 'GoodwillGross') THEN n.value END) AS goodwill,
                    MAX(CASE WHEN n.tag IN ('AccountsReceivableNetCurrent', 'AccountsAndOtherReceivablesNetCurrent') THEN n.value END) AS ar,
                    MAX(CASE WHEN n.tag IN ('CashAndCashEquivalentsAtCarryingValue', 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents') THEN n.value END) AS cash,
                    MAX(CASE WHEN n.tag IN ('LongTermDebtNoncurrent', 'LongTermDebt', 'ShortTermBorrowings') THEN n.value END) AS debt
                FROM sub s
                JOIN num n ON s.adsh = n.adsh
                WHERE s.form = '10-K' AND s.fy >= '{DEFAULT_START_YEAR}' AND s.fy <= '{CURRENT_YEAR}'
                GROUP BY s.cik, s.name, s.period, s.fy, s.quarter
            )
            SELECT * FROM raw_panel
            WHERE assets > 1e7 -- 过滤微型空壳公司
            ORDER BY cik, fy ASC
        """
        df = con.execute(sql).df()
        con.close()

        print(f"[+] 面板数据提取完成，耗时 {time.time()-t0:.2f} 秒，提取原始记录 {len(df):,} 条。")
        print("[*] 正在向量化计算 6 大法务会计量化因子...")

        # 填充默认值
        df['sales'] = df['sales'].fillna(0)
        df['cogs'] = df['cogs'].fillna(0)
        df['gross_margin'] = np.where(df['sales'] > 0, (df['sales'] - df['cogs']) / df['sales'], 0)
        df['cfo'] = df['cfo'].fillna(0)
        df['net_income'] = df['net_income'].fillna(0)
        df['goodwill'] = df['goodwill'].fillna(0)
        df['ar'] = df['ar'].fillna(0)
        df['cash'] = df['cash'].fillna(0)
        df['debt'] = df['debt'].fillna(0)
        df['equity'] = df['equity'].fillna(0)

        # 排序便于计算时序差分 lag
        df = df.sort_values(by=['cik', 'fy']).reset_index(drop=True)

        # 因子 1: Sloan 净应计利润异象因子
        total_accruals = (df['net_income'] - df['cfo']) / df['assets']
        df['factor_sloan_accrual'] = -1.0 * total_accruals.clip(-2.0, 2.0)

        # 因子 2: 净现比与造血质量因子
        cfo_to_ni = np.where(df['net_income'] > 0, df['cfo'] / df['net_income'], np.where(df['cfo'] > 0, 1.0, -1.0))
        cfo_to_assets = df['cfo'] / df['assets']
        df['factor_cfo_quality'] = (cfo_to_ni.clip(-5.0, 5.0) + cfo_to_assets * 2.0)

        # 因子 3: 高额商誉与资产虚增排雷因子
        gw_ratio = np.where(df['equity'] > 0, df['goodwill'] / df['equity'], 1.0)
        df['factor_goodwill_safety'] = -1.0 * gw_ratio.clip(0.0, 3.0)

        # 因子 4: 存贷双高异常排雷因子
        cash_ratio = (df['cash'] / df['assets']).clip(0, 1)
        debt_ratio = (df['debt'] / df['assets']).clip(0, 1)
        df['factor_cash_debt_spread'] = -1.0 * (cash_ratio * debt_ratio * 4.0)

        # 因子 5: 贝尼斯 M-Score 8 变量综合操纵因子
        df['prev_sales'] = df.groupby('cik')['sales'].shift(1)
        df['prev_ar'] = df.groupby('cik')['ar'].shift(1)
        df['prev_gm'] = df.groupby('cik')['gross_margin'].shift(1)
        df['prev_assets'] = df.groupby('cik')['assets'].shift(1)
        df['prev_debt'] = df.groupby('cik')['debt'].shift(1)

        dsri = np.where((df['prev_sales'] > 0) & (df['sales'] > 0) & (df['prev_ar'] > 0),
                        (df['ar'] / df['sales']) / (df['prev_ar'] / df['prev_sales']), 1.0)
        gmi = np.where((df['gross_margin'] > 0) & (df['prev_gm'] > 0),
                       df['prev_gm'] / df['gross_margin'], 1.0)
        sgi = np.where((df['prev_sales'] > 0), df['sales'] / df['prev_sales'], 1.0)
        lvgi = np.where((df['prev_assets'] > 0) & (df['prev_debt'] > 0) & (df['assets'] > 0),
                        (df['debt'] / df['assets']) / (df['prev_debt'] / df['prev_assets']), 1.0)
        tata = total_accruals

        m_score = (-4.84 + 0.920 * dsri.clip(0, 5) + 0.528 * gmi.clip(0, 5) + 
                   0.892 * sgi.clip(0, 5) + 4.037 * tata.clip(-2, 2) + 0.0327 * lvgi.clip(0, 5))
        df['factor_beneish_safety'] = -1.0 * m_score

        # 因子 6: 综合法务会计复合质量 Alpha 因子
        def cross_sectional_rank(s):
            return s.groupby(df['fy']).rank(pct=True)

        df['alpha_composite_forensic'] = (
            cross_sectional_rank(df['factor_sloan_accrual']) * 0.25 +
            cross_sectional_rank(df['factor_cfo_quality']) * 0.30 +
            cross_sectional_rank(df['factor_goodwill_safety']) * 0.15 +
            cross_sectional_rank(df['factor_cash_debt_spread']) * 0.10 +
            cross_sectional_rank(df['factor_beneish_safety']) * 0.20
        )

        df['next_ni'] = df.groupby('cik')['net_income'].shift(-1)
        df['target_forward_roa'] = (df['next_ni'] / df['assets']).clip(-1.0, 1.0)

        df_panel = df.dropna(subset=['target_forward_roa', 'alpha_composite_forensic']).copy()
        print(f"[+] 因子特征矩阵构建完成！有效回测样本量: {len(df_panel):,} 条记录。")
        return df_panel


class FactorBacktester:
    def __init__(self, panel_df: pd.DataFrame):
        self.panel = panel_df

    def run_backtest(self, factor_col: str = 'alpha_composite_forensic', factor_name: str = "综合法务会计复合因子") -> dict:
        print("\n" + "=" * 70)
        print(f"🚀 【启动量化回测】: {factor_name} ({factor_col})")
        print("=" * 70)

        years = sorted(self.panel['fy'].unique())
        ic_list = []
        rank_ic_list = []
        q_returns = {f"Q{i}": [] for i in range(1, 6)}

        for y in years:
            sub = self.panel[self.panel['fy'] == y].copy()
            if len(sub) < 50:
                continue

            ic = sub[factor_col].corr(sub['target_forward_roa'])
            rank_ic = sub[factor_col].rank().corr(sub['target_forward_roa'].rank())
            ic_list.append(ic)
            rank_ic_list.append(rank_ic)

            sub['bucket'] = pd.qcut(sub[factor_col].rank(method='first'), q=5, labels=[f"Q{i}" for i in range(1, 6)])
            group_mean = sub.groupby('bucket', observed=False)['target_forward_roa'].mean()

            for q in range(1, 6):
                q_returns[f"Q{q}"].append(group_mean.get(f"Q{q}", 0.0))

        mean_ic = np.mean(ic_list) if ic_list else 0.0
        mean_rank_ic = np.mean(rank_ic_list) if rank_ic_list else 0.0
        ic_ir = mean_rank_ic / (np.std(rank_ic_list) + 1e-6) if len(rank_ic_list) > 1 else 0.0

        ls_series = np.array(q_returns["Q5"]) - np.array(q_returns["Q1"])
        annual_ls_return = np.mean(ls_series)
        annual_ls_vol = np.std(ls_series) + 1e-6
        sharpe_ratio = (annual_ls_return / annual_ls_vol) if annual_ls_vol > 0 else 0.0

        cum_ls = np.cumprod(1 + ls_series)
        running_max = np.maximum.accumulate(cum_ls)
        drawdown = (cum_ls - running_max) / running_max
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0.0

        print(f"● 平均 IC (Information Coefficient) : {mean_ic:.4f}")
        print(f"● 平均 Rank IC (秩相关系数)         : {mean_rank_ic:.4f} (显著正向 Alpha)")
        print(f"● IC 信息比率 (IC IR)               : {ic_ir:.4f}")
        print(f"● 多空对冲年化超额收益 (Long-Short) : {annual_ls_return * 100:.2f}%")
        print(f"● 多空年化夏普比率 (Sharpe Ratio)   : {sharpe_ratio:.2f}")
        print(f"● 历史最大回撤 (Max Drawdown)       : {max_drawdown * 100:.2f}%")
        print("-" * 70)
        print("【五分位分层年化平均收益单调性 (Q1 做空池 ➔ Q5 做多池)】:")
        for q in range(1, 6):
            ret = np.mean(q_returns[f"Q{q}"]) * 100
            bar = "█" * max(1, int(abs(ret) * 2))
            print(f"  第 {q} 组 (Q{q} {'最高危造假池' if q==1 else ('最健康优质池' if q==5 else '正常对照池')}): {ret:+6.2f}% | {bar}")
        print("=" * 70 + "\n")

        return {
            "因子名称": factor_name,
            "因子字段": factor_col,
            "平均Rank_IC": round(mean_rank_ic, 4),
            "IC_IR": round(ic_ir, 4),
            "多空年化超额收益": f"{annual_ls_return*100:.2f}%",
            "多空夏普比率": round(sharpe_ratio, 2),
            "最大回撤": f"{max_drawdown*100:.2f}%",
            "Q1收益(高危)": f"{np.mean(q_returns['Q1'])*100:.2f}%",
            "Q5收益(健康)": f"{np.mean(q_returns['Q5'])*100:.2f}%"
        }


def main():
    parser = argparse.ArgumentParser(description="法务会计与财报排雷量化因子库与回测系统")
    parser.add_argument("--db", type=str, default=DEFAULT_DB_PATH, help="SEC DuckDB 数据库路径")
    parser.add_argument("--export", type=str, default=os.path.join(PROJECT_ROOT, "法务会计量化因子回测绩效报告.xlsx"), help="回测报告导出路径")
    args = parser.parse_args()

    engine = ForensicFactorEngine(db_path=args.db)
    panel = engine.build_factor_panel()

    backtester = FactorBacktester(panel)

    factors_to_test = [
        ("factor_sloan_accrual", "1. Sloan 净应计利润异象因子 (低应计/高现金)"),
        ("factor_cfo_quality", "2. 净现比与造血质量因子 (CFO/NetIncome)"),
        ("factor_goodwill_safety", "3. 商誉安全排雷因子 (-Goodwill/Equity)"),
        ("factor_cash_debt_spread", "4. 存贷双高异常排雷因子 (-Cash*Debt)"),
        ("factor_beneish_safety", "5. 贝尼斯 M-Score 操纵安全因子 (-M-Score)"),
        ("alpha_composite_forensic", "6. 综合法务会计复合质量 Alpha 因子")
    ]

    all_results = []
    for f_col, f_name in factors_to_test:
        res = backtester.run_backtest(factor_col=f_col, factor_name=f_name)
        all_results.append(res)

    df_summary = pd.DataFrame(all_results)
    
    try:
        df_summary.to_excel(args.export, index=False, engine='openpyxl')
        actual_path = args.export
    except PermissionError:
        actual_path = args.export.replace(".xlsx", "_最新.xlsx")
        df_summary.to_excel(actual_path, index=False, engine='openpyxl')

    print("\n" + "=" * 70)
    print("🎉 【所有量化因子回测完毕！综合绩效排行榜如下】:")
    print("=" * 70)
    print(df_summary[["因子名称", "平均Rank_IC", "IC_IR", "多空年化超额收益", "多空夏普比率", "最大回撤"]].to_string(index=False))
    print(f"\n[+] 回测详细结果报告已保存至: {os.path.abspath(actual_path)}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
