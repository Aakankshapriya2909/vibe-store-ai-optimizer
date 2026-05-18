# Changelog

## [1.0.0] - 2026-05-20
### Added
- AI readiness score (0-100) with per-issue deductions
- Gap analysis comparing AI perception vs merchant intent
- Ranked action plan with fix templates
- Per-product confidence scoring via Groq/Llama
- Downloadable .txt report
- 13 pytest tests covering all core logic

## [0.3.0] - 2026-05-15
### Added
- Concurrent product scoring with ThreadPoolExecutor
- Word-boundary fix for keyword matching (EMI regression)
- Intent-vs-reality gap scoring with score deductions

## [0.2.0] - 2026-05-11
### Added
- Deterministic scoring engine in analyzer.py
- AI perception layer isolated in ai_simulator.py
- Config-driven thresholds in config.py

## [0.1.0] - 2026-05-09
### Added
- Initial project structure
- Simulated Shopify store data
- Basic Streamlit UI skeleton