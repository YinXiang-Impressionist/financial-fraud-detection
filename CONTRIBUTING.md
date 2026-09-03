# Contributing to SEC Financial Lakehouse

Thank you for your interest in contributing! This project thrives on contributions from the quantitative finance, accounting, data engineering, and Python communities.

---

## 🚀 How to Contribute

### 1. Reporting Bugs & Asking Questions
* Check existing [GitHub Issues](https://github.com/YinXiang-Impressionist/financial-fraud-detection/issues) before submitting a new one.
* Use the **Bug Report** template to provide detailed environment info, error tracebacks, and reproducible ticker codes.

### 2. Suggesting New Forensic Rules or Statistical Models
We welcome suggestions for new econometric and forensic accounting rules (e.g., industry-specific metrics, new restatement predictors).
* Please open a **Feature Request** issue detailing the mathematical formula, economic intuition, and academic references.

### 3. Submitting Pull Requests (PRs)
1. **Fork the Repository** and create a feature branch (`git checkout -b feature/my-new-rule`).
2. **Set up the Development Environment**:
   ```bash
   pip install -r requirements.txt
   pip install -e ".[dev]"
   ```
3. **Ensure All Tests Pass**:
   ```bash
   python -m unittest discover tests
   python tests/test_forensic_engine.py
   python examples/case_study_fraud_showcase.py
   ```
4. **Adhere to Project Principles**:
   * **Deterministic Pure Math**: Models must remain 100% deterministic (no random hallucinations, no reliance on non-reproducible external APIs).
   * **High Performance**: Ensure vectorized implementations remain zero-copy and efficient.
   * **Code Quality**: Keep functions modular and maintain clean type annotations.
5. **Submit your PR** with a clear explanation of changes, test logs, and reference links.

---

## 📜 Code of Conduct

All contributors are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md) to maintain an open, welcoming, and harassment-free environment for everyone.
