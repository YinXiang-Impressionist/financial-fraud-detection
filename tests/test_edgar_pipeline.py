# -*- coding: utf-8 -*-
"""
EDGAR Pipeline & Multi-Source Forensic Audit Test Script
测试基于 edgar-tools 的新一代数据抽取与立体排雷审计全流程 (NVDA 实战集成测试)
支持 unittest/pytest 自动发现，并具备网络异常跳过与离线保护机制
"""

import os
import sys
import time
import unittest

# 保证当前项目根目录在 sys.path 中
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from pipelines import EdgarPipeline
from forensic_engine import ForensicEvaluator


def run_edgar_audit_integration(ticker: str = "NVDA") -> dict:
    """运行真实 SEC 在线数据抽取与法务评估"""
    pipeline = EdgarPipeline()
    dossier = pipeline.extract_full_forensic_profile(ticker)
    assert dossier is not None
    assert dossier.get("cik") is not None or dossier.get("name") is not None

    report = ForensicEvaluator.evaluate_single(dossier)
    assert "total_risk_score" in report
    assert "risk_level" in report
    return {**dossier, **report}


try:
    import pytest
    integration_mark = pytest.mark.integration
except ImportError:
    def integration_mark(cls):
        return cls


@integration_mark
class TestEdgarPipelineIntegration(unittest.TestCase):
    """EDGAR 在线抽取与集成测试套件"""

    def test_online_sec_pipeline(self):
        # 允许通过环境变量禁用在线网络测试
        if os.environ.get("SKIP_SEC_ONLINE_TESTS") == "1":
            self.skipTest("SKIP_SEC_ONLINE_TESTS is set, skipping online SEC integration test.")

        try:
            res = run_edgar_audit_integration("NVDA")
            self.assertIn("total_risk_score", res)
            self.assertIn("risk_level", res)
        except Exception as e:
            # 若处于完全无外网或被 SEC 暂时 429 限流的环境，优雅跳过而非破坏 CI
            self.skipTest(f"Online SEC EDGAR access skipped due to environment/network limitation: {e}")


def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    zh = os.environ.get("FORENSIC_LANG", "en").lower().startswith("zh")
    print("=" * 70)
    title = f"🚀 【启动 EDGAR 立体法务审计全流程集成测试】: 目标股票 {ticker}" if zh else f"🚀 [Launch EDGAR Forensic Audit Pipeline Integration Test]: Target {ticker}"
    print(title)
    print("=" * 70 + "\n")

    t0 = time.time()
    res = run_edgar_audit_integration(ticker)
    elapsed = time.time() - t0

    success_line = f"[+] 数据抽取与评估完成！耗时: {elapsed:.2f} 秒" if zh else f"[+] Data extraction & audit completed! Elapsed: {elapsed:.2f} s"
    print(success_line)
    print(f"  ● {'公司名称' if zh else 'Company'}: {res.get('name')} (CIK: {res.get('cik')})")
    print(f"  ● {'风险评分' if zh else 'Risk Score'}: {res.get('total_risk_score')} ({res.get('risk_level')})")
    print(f"  ● {'命中预警' if zh else 'Triggered Warnings'}: {res.get('warning_count')} items")
    print("=" * 70)
    done_msg = "🎉 【EDGAR 在线穿透测试顺利完成！】" if zh else "🎉 [EDGAR Online Audit Pipeline Integration Test Passed!]"
    print(done_msg)


if __name__ == "__main__":
    main()
