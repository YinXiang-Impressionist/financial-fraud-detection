# -*- coding: utf-8 -*-
"""
Financial Tag Mapping & Standardization
多市场会计准则财务科目映射与归一化工具 (支持 SEC US-GAAP / A股 / 港股 / 通用字段)
"""

from typing import Dict, Any
import pandas as pd

# A股中文科目映射表
CN_ASHAR_FIELD_MAP = {
    "营业收入": "sales",
    "营业总收入": "sales",
    "营业成本": "cogs",
    "营业利润": "operating_income",
    "净利润": "net_income",
    "归属于母公司所有者的净利润": "net_income",
    "扣除非经常性损益后的净利润": "operating_income",
    "经营活动产生的现金流量净额": "cfo",
    "投资活动产生的现金流量净额": "cfi",
    "筹资活动产生的现金流量净额": "cff",
    "资产总计": "assets",
    "流动资产合计": "current_assets",
    "负债合计": "liabilities",
    "流动负债合计": "current_liabilities",
    "所有者权益合计": "equity",
    "归属于母公司所有者权益合计": "equity",
    "货币资金": "cash",
    "应收账款": "ar",
    "存货": "inv",
    "商誉": "goodwill",
    "固定资产": "ppe_net",
    "在建工程": "cip",
    "其他应收款": "other_receivables",
    "预付款项": "prepayments",
    "有息负债": "debt",
    "短期借款": "short_debt",
    "长期借款": "long_debt",
    "少数股东权益": "minority_equity",
    "少数股东损益": "minority_profit",
    "研发费用": "total_rd",
    "开发支出": "capitalized_rd",
    "购建固定资产、无形资产和其他长期资产支付的现金": "capex",
    "分配股利、利润或偿付利息支付的现金": "dividends",
    "支付的其他与筹资活动有关的现金": "repurchases",
    "第四季度净利润": "q4_net_income",
    "前三季度净利润": "q1_to_q3_net_income"
}

# SEC US-GAAP 常见标签映射表
SEC_TAG_MAP = {
    # 营业收入
    "Revenues": "sales",
    "RevenueFromContractWithCustomerExcludingAssessedTax": "sales",
    "SalesRevenueNet": "sales",
    # 营业成本
    "CostOfGoodsAndServicesSold": "cogs",
    "CostOfGoodsSold": "cogs",
    # 营业利润
    "OperatingIncomeLoss": "operating_income",
    # 净利润
    "NetIncomeLoss": "net_income",
    "ProfitLoss": "net_income",
    # 资产与负债
    "Assets": "assets",
    "AssetsCurrent": "current_assets",
    "Liabilities": "liabilities",
    "LiabilitiesCurrent": "current_liabilities",
    "StockholdersEquity": "equity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": "equity",
    # 现金流
    "NetCashProvidedByUsedInOperatingActivities": "cfo",
    "NetCashProvidedByUsedInInvestingActivities": "cfi",
    "NetCashProvidedByUsedInFinancingActivities": "cff",
    "PaymentsToAcquirePropertyPlantAndEquipment": "capex",
    # 细分资产
    "Goodwill": "goodwill",
    "GoodwillGross": "goodwill",
    "AccountsReceivableNetCurrent": "ar",
    "AccountsAndOtherReceivablesNetCurrent": "ar",
    "InventoryNet": "inv",
    "PropertyPlantAndEquipmentNet": "ppe_net",
    "ConstructionInProgress": "cip",
    "CashAndCashEquivalentsAtCarryingValue": "cash",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents": "cash",
    # 负债科目
    "LongTermDebtNoncurrent": "debt",
    "LongTermDebt": "debt",
    "ShortTermBorrowings": "short_debt",
    # 权益与分配
    "MinorityInterest": "minority_equity",
    "PaymentsOfDividends": "dividends",
    "PaymentsOfDividendsCommonStock": "dividends",
    "PaymentsForRepurchaseOfCommonStock": "repurchases"
}


def normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    将包含中文或 US-GAAP 原始名称的 DataFrame 字段标准化为内部英文标准键
    """
    rename_dict = {}
    for col in df.columns:
        clean_col = str(col).strip()
        if clean_col in CN_ASHAR_FIELD_MAP:
            rename_dict[col] = CN_ASHAR_FIELD_MAP[clean_col]
        elif clean_col in SEC_TAG_MAP:
            rename_dict[col] = SEC_TAG_MAP[clean_col]
    return df.rename(columns=rename_dict)


def normalize_record_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    将单条报表字典映射为内部标准键
    """
    out = {}
    for k, v in d.items():
        clean_k = str(k).strip()
        mapped_key = CN_ASHAR_FIELD_MAP.get(clean_k, SEC_TAG_MAP.get(clean_k, clean_k.lower()))
        out[mapped_key] = v
    return out
