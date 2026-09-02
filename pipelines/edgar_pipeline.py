# -*- coding: utf-8 -*-
"""
EDGAR Advanced Forensic Data Pipeline (基于 edgar-tools)
提供全自动、纯 Python 代码、零 LLM 依赖的端到端 SEC 数据抽取与法务证据归集引擎：
1. 财务三张表高精度提取 (10-K / 10-Q 标准化 Balance Sheet, Income Statement, Cash Flow)
2. Form 8-K 重大舞弊与治理异动穿透 (Item 4.02 差错重述时效衰减、Item 4.01 突发换所、Item 5.02 CFO/高管离职)
3. Form 4 董监高与内部人交易追踪 (CEO/CFO/大股东套现减持检测)
4. Form 10-K Item 9A 内部控制重大缺陷检测 (Material Weakness) 与独立外部审计所核查
"""

import os
import sys
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

# 保证 Windows 控制台 UTF-8 输出
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from edgar import set_identity, Company


# 初始化 SEC 访问合规身份声明
SEC_IDENTITY = os.getenv("EDGAR_IDENTITY", "ForensicFraudResearchBot audit_research@quant.org")
set_identity(SEC_IDENTITY)


class EdgarPipeline:
    def __init__(self, identity: str = ""):
        if identity:
            set_identity(identity)

    @staticmethod
    def get_company(ticker_or_cik: str) -> Company:
        """根据股票代码或 CIK 获取 Company 对象"""
        clean_code = str(ticker_or_cik).strip().upper()
        return Company(clean_code)

    @staticmethod
    def fetch_financials_bundle(company: Company) -> Dict[str, Any]:
        """
        从 10-K / 10-Q 抽取标准财务三张表核心科目及历史差分数据
        """
        try:
            financials = company.get_financials()
        except Exception as e:
            # 若直接获取报错则降级为空
            financials = None

        data = {
            "cik": str(company.cik).zfill(10),
            "name": company.name,
            "tickers": company.tickers,
            "industry": company.industry,
            "sic": company.sic,
            "sales": 0.0,
            "cogs": 0.0,
            "operating_income": 0.0,
            "net_income": 0.0,
            "assets": 0.0,
            "current_assets": 0.0,
            "liabilities": 0.0,
            "current_liabilities": 0.0,
            "equity": 0.0,
            "cfo": 0.0,
            "capex": 0.0,
            "fcf": 0.0,
            "goodwill": 0.0,
            "ar": 0.0,
            "inv": 0.0,
            "cash": 0.0,
            "debt": 0.0,
            "ppe_net": 0.0,
            "cip": 0.0,
            "period": "",
            "form": "10-K"
        }

        if financials is None:
            return data

        # 提取当前期数据
        try:
            data["sales"] = float(financials.get_revenue() or 0.0)
        except Exception:
            pass
        try:
            data["net_income"] = float(financials.get_net_income() or 0.0)
        except Exception:
            pass
        try:
            data["operating_income"] = float(financials.get_operating_income() or 0.0)
        except Exception:
            pass
        try:
            data["cfo"] = float(financials.get_operating_cash_flow() or 0.0)
        except Exception:
            pass
        try:
            data["capex"] = float(financials.get_capital_expenditures() or 0.0)
        except Exception:
            pass
        try:
            data["fcf"] = float(financials.get_free_cash_flow() or 0.0)
        except Exception:
            pass
        try:
            data["assets"] = float(financials.get_total_assets() or 0.0)
        except Exception:
            pass
        try:
            data["current_assets"] = float(financials.get_current_assets() or 0.0)
        except Exception:
            pass
        try:
            data["liabilities"] = float(financials.get_total_liabilities() or 0.0)
        except Exception:
            pass
        try:
            data["current_liabilities"] = float(financials.get_current_liabilities() or 0.0)
        except Exception:
            pass
        try:
            data["equity"] = float(financials.get_stockholders_equity() or 0.0)
        except Exception:
            pass

        # 进一步从 facts / balance_sheet 补充细分资产 (商誉、现金、应收、存货、债务)
        try:
            facts = company.get_facts()
            if facts and hasattr(facts, 'get_facts_by_concept'):
                # 尝试提取商誉
                for gw_tag in ['Goodwill', 'GoodwillGross']:
                    f_gw = facts.get_facts_by_concept('us-gaap', gw_tag)
                    if f_gw is not None and not f_gw.empty:
                        data["goodwill"] = float(f_gw.sort_values('end', ascending=False).iloc[0]['val'] or 0.0)
                        break

                # 现金
                for cash_tag in ['CashAndCashEquivalentsAtCarryingValue', 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents']:
                    f_cash = facts.get_facts_by_concept('us-gaap', cash_tag)
                    if f_cash is not None and not f_cash.empty:
                        data["cash"] = float(f_cash.sort_values('end', ascending=False).iloc[0]['val'] or 0.0)
                        break

                # 应收
                for ar_tag in ['AccountsReceivableNetCurrent', 'AccountsAndOtherReceivablesNetCurrent']:
                    f_ar = facts.get_facts_by_concept('us-gaap', ar_tag)
                    if f_ar is not None and not f_ar.empty:
                        data["ar"] = float(f_ar.sort_values('end', ascending=False).iloc[0]['val'] or 0.0)
                        break

                # 债务
                for debt_tag in ['LongTermDebtNoncurrent', 'LongTermDebt', 'ShortTermBorrowings']:
                    f_debt = facts.get_facts_by_concept('us-gaap', debt_tag)
                    if f_debt is not None and not f_debt.empty:
                        data["debt"] = float(f_debt.sort_values('end', ascending=False).iloc[0]['val'] or 0.0)
                        break
        except Exception:
            pass

        return data

    @staticmethod
    def fetch_restatements_8k(company: Company) -> Dict[str, Any]:
        """
        穿透扫描 Form 8-K：
        1. Item 4.02: Non-Reliance on Previously Issued Financial Statements (财报重大差错与重述)
           -> 结合时效衰减机制 (1年内重大风险、1~3年历史观察、>3年历史已修正)
           -> 提供 target_is_restated_fraud 学术真实标签 (Ground Truth)
        2. Item 4.01: Changes in Registrant's Certifying Accountant (突发更换会计师事务所)
        3. Item 5.02: Departure of Directors or Principal Officers (CFO/财务总监/独董突发离职)
        """
        result = {
            "has_item_402_restatement": False,
            "recent_restatement_days": None,
            "restatement_time_tier": "无重述记录",
            "restatement_score_penalty": 0,
            "target_is_restated_fraud": False,  # 学术研究黄金 Ground Truth 标签
            "restatement_filings": [],
            "has_item_401_auditor_change": False,
            "auditor_change_filings": [],
            "has_item_502_officer_departure": False,
            "officer_departure_filings": []
        }

        try:
            filings_8k = company.get_filings(form="8-K")
            if filings_8k is None or len(filings_8k) == 0:
                return result

            now_dt = datetime.now()

            # 遍历检查 8-K
            # 最多检查最近 100 份 8-K
            max_check = min(100, len(filings_8k))
            for i in range(max_check):
                f = filings_8k[i]
                items_str = str(getattr(f, 'items', '') or '')
                f_date_str = str(getattr(f, 'filing_date', ''))

                # 1. 检查 Item 4.02 重大重述
                if "4.02" in items_str:
                    result["has_item_402_restatement"] = True
                    result["target_is_restated_fraud"] = True  # 确认为真实造假/重大差错样本
                    days_ago = None
                    try:
                        f_dt = datetime.strptime(f_date_str, "%Y-%m-%d")
                        days_ago = (now_dt - f_dt).days
                    except Exception:
                        days_ago = 999

                    result["restatement_filings"].append({
                        "filing_date": f_date_str,
                        "days_ago": days_ago,
                        "accession_no": getattr(f, 'accession_no', '')
                    })

                    if result["recent_restatement_days"] is None or (days_ago is not None and days_ago < result["recent_restatement_days"]):
                        result["recent_restatement_days"] = days_ago

                # 2. 检查 Item 4.01 审计师异动
                if "4.01" in items_str:
                    result["has_item_401_auditor_change"] = True
                    result["auditor_change_filings"].append({
                        "filing_date": f_date_str,
                        "accession_no": getattr(f, 'accession_no', '')
                    })

                # 3. 检查 Item 5.02 高管/CFO 离职
                if "5.02" in items_str:
                    result["has_item_502_officer_departure"] = True
                    result["officer_departure_filings"].append({
                        "filing_date": f_date_str,
                        "accession_no": getattr(f, 'accession_no', '')
                    })

            # 时效衰减机制判定:
            if result["recent_restatement_days"] is not None:
                days = result["recent_restatement_days"]
                if days <= 365:
                    result["restatement_time_tier"] = "近期重大重述 (1年内)"
                    result["restatement_score_penalty"] = 20  # 近期暴雷窗口，后续连环风险高
                elif days <= 1095:  # 1~3 年
                    result["restatement_time_tier"] = "历史观察期重述 (1~3年)"
                    result["restatement_score_penalty"] = 5   # 问题逐步整改中，轻微关注
                else:
                    result["restatement_time_tier"] = "远期已整改重述 (>3年前)"
                    result["restatement_score_penalty"] = 0   # 历史问题已妥善解决，不扣分

        except Exception as e:
            result["error"] = str(e)

        return result

    @staticmethod
    def fetch_insider_transactions_form4(company: Company) -> Dict[str, Any]:
        """
        穿透 Form 4：提取近 12 个月内部人（CEO/CFO/董事/大股东）的股票抛售套现动态
        检测高管大额减持套现 (Pump & Dump) 动机
        """
        result = {
            "has_insider_trading": False,
            "total_sell_shares": 0.0,
            "total_sell_value": 0.0,
            "total_buy_shares": 0.0,
            "total_buy_value": 0.0,
            "net_sell_value": 0.0,
            "heavy_insider_selling": False,
            "selling_officers": [],
            "form4_count": 0
        }

        try:
            filings_4 = company.get_filings(form="4")
            if filings_4 is None or len(filings_4) == 0:
                return result

            # 统计最近 20 份 Form 4
            check_n = min(20, len(filings_4))
            result["form4_count"] = check_n

            for i in range(check_n):
                f = filings_4[i]
                try:
                    obj = f.obj()
                    if obj is None:
                        continue
                    insider = str(getattr(obj, 'insider_name', ''))
                    position = str(getattr(obj, 'position', ''))

                    # 提取交易明细
                    activities = obj.get_transaction_activities()
                    for act in activities:
                        tx_type = str(getattr(act, 'transaction_type', '')).lower()
                        shares = float(getattr(act, 'shares', 0.0) or 0.0)
                        val = float(getattr(act, 'value', 0.0) or 0.0)

                        if 'sale' in tx_type or getattr(act, 'code', '') == 'S':
                            result["total_sell_shares"] += shares
                            result["total_sell_value"] += val
                            if insider and insider not in result["selling_officers"]:
                                result["selling_officers"].append(f"{insider} ({position})")
                        elif 'purchase' in tx_type or getattr(act, 'code', '') == 'P':
                            result["total_buy_shares"] += shares
                            result["total_buy_value"] += val
                except Exception:
                    continue

            result["net_sell_value"] = result["total_sell_value"] - result["total_buy_value"]
            result["has_insider_trading"] = bool(result["total_sell_shares"] > 0 or result["total_buy_shares"] > 0)
            
            # 若净抛售超过 1000 万美元，标记为高危高管减持
            if result["net_sell_value"] > 10_000_000:
                result["heavy_insider_selling"] = True

        except Exception as e:
            result["error"] = str(e)

        return result

    @staticmethod
    def fetch_internal_controls_10k(company: Company) -> Dict[str, Any]:
        """
        从最新 10-K 中抽取独立审计师事务所信息，并穿透 Item 9A 检索内部控制重大缺陷 (Material Weakness)
        """
        result = {
            "auditor_name": "未知",
            "pcaob_firm_id": "",
            "icfr_attestation": False,
            "has_material_weakness": False,
            "internal_control_status": "未披露或正常",
            "material_weakness_snippets": []
        }

        try:
            tenk = company.latest_tenk
            if tenk is None:
                return result

            # 1. 抽取审计师
            auditor = getattr(tenk, 'auditor', None)
            if auditor:
                result["auditor_name"] = str(auditor)

            # 2. 检查 Item 9A 内部控制缺陷
            item9a = tenk['Item 9A']
            if item9a:
                text = str(item9a)
                # 寻找关键词 "material weakness" / "ineffective"
                mw_pattern = re.compile(r"([^.\n]*?(?:material\s+weakness|ineffective|adverse\s+opinion)[^.\n]*?\.)", re.IGNORECASE)
                matches = mw_pattern.findall(text)
                
                # 过滤出实质性陈述（排除常见声明 "did not identify any material weaknesses"）
                valid_alerts = []
                for m in matches:
                    m_lower = m.lower()
                    if "no material weakness" in m_lower or "did not identify any material weakness" in m_lower:
                        continue
                    if "not effective" in m_lower or "identified a material weakness" in m_lower or "material weaknesses existed" in m_lower:
                        valid_alerts.append(m.strip())

                if valid_alerts:
                    result["has_material_weakness"] = True
                    result["internal_control_status"] = "存在实质性重大缺陷 (Material Weakness)"
                    result["material_weakness_snippets"] = valid_alerts[:3]
                else:
                    result["internal_control_status"] = "内部控制有效稳健 (Effective)"

        except Exception as e:
            result["error"] = str(e)

        return result

    @classmethod
    def fetch_two_period_financials(cls, company: Company) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """提取当期与上一期的连续两期年报数据，支持计算时序差分与修正琼斯模型"""
        curr = cls.fetch_financials_bundle(company)
        prev = None
        try:
            filings = company.get_filings(form="10-K")
            if filings and len(filings) >= 2:
                prev_obj = filings[1].obj()
                if prev_obj and hasattr(prev_obj, 'financials') and prev_obj.financials:
                    pf = prev_obj.financials
                    prev = {
                        "sales": float(pf.get_revenue() or 0.0),
                        "net_income": float(pf.get_net_income() or 0.0),
                        "operating_income": float(pf.get_operating_income() or 0.0),
                        "cfo": float(pf.get_operating_cash_flow() or 0.0),
                        "capex": float(pf.get_capital_expenditures() or 0.0),
                        "assets": float(pf.get_total_assets() or 0.0),
                        "current_assets": float(pf.get_current_assets() or 0.0),
                        "liabilities": float(pf.get_total_liabilities() or 0.0),
                        "current_liabilities": float(pf.get_current_liabilities() or 0.0),
                        "equity": float(pf.get_stockholders_equity() or 0.0)
                    }
        except Exception:
            pass
        return curr, prev

    def extract_full_forensic_profile(self, ticker_or_cik: str) -> Dict[str, Any]:
        """
        一站式端到端提取单家美股的立体法务档案 (包含当期与上期财务三张表、8-K、Form 4、Item 9A)
        纯 Python 确定性逻辑，零 LLM 耗时
        """
        company = self.get_company(ticker_or_cik)

        # 1. 连续两期财务三张表
        financials, prev_financials = self.fetch_two_period_financials(company)

        # 2. 8-K 重大重述与治理异动
        restatements = self.fetch_restatements_8k(company)

        # 3. Form 4 内部人抛售
        insiders = self.fetch_insider_transactions_form4(company)

        # 4. 10-K 审计师与内控缺陷
        controls = self.fetch_internal_controls_10k(company)

        # 合并构建完整的法务输入字典
        dossier = {**financials}
        dossier["prev_record"] = prev_financials
        dossier["restatement_info"] = restatements
        dossier["insider_info"] = insiders
        dossier["control_info"] = controls

        # 提取关键扁平指标供评分器调用
        dossier["has_item_402_restatement"] = restatements["has_item_402_restatement"]
        dossier["recent_restatement_days"] = restatements["recent_restatement_days"]
        dossier["restatement_score_penalty"] = restatements["restatement_score_penalty"]
        dossier["target_is_restated_fraud"] = restatements["target_is_restated_fraud"]
        
        dossier["accountant_changed_8k"] = restatements["has_item_401_auditor_change"]
        dossier["officer_departure_8k"] = restatements["has_item_502_officer_departure"]
        
        dossier["heavy_insider_selling"] = insiders["heavy_insider_selling"]
        dossier["insider_net_sell_val"] = insiders["net_sell_value"]
        
        dossier["has_material_weakness"] = controls["has_material_weakness"]
        dossier["auditor_name"] = controls["auditor_name"]

        return dossier
