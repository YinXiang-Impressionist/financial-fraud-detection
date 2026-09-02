# -*- coding: utf-8 -*-
"""
SEC Data Ingestion & Extraction Pipelines
包含:
1. EdgarPipeline: 基于 edgar-tools 的在线秒级多维财报穿透抽取
2. lakehouse: 基于 SEC DERA Bulk 数据的离线湖仓下载与构建包
"""

from .edgar_pipeline import EdgarPipeline

__all__ = ["EdgarPipeline"]
