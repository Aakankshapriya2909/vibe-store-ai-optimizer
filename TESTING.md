# Testing Guide

## Running Tests
python -m pytest test_analyzer.py -v

## Test Coverage

| Test | What it checks |
|---|---|
| test_score_perfect_store | A fully complete store scores 100 |
| test_missing_return_policy | Missing return policy deducts correct points |
| test_missing_shipping_policy | Missing shipping policy deducts correct points |
| test_short_description | Products with short descriptions are flagged |
| test_intent_gap_detected | Unverifiable claims reduce score |
| test_intent_gap_not_false_positive | Present claims don't trigger gap |
| test_word_boundary_regression | "emi" inside "accessories" not matched |
| test_action_plan_sort_order | Action plan sorted by impact descending |

## Design Philosophy
analyzer.py has zero AI calls — the score is fully deterministic
and reproducible without a Groq API key. This makes the test suite
fast, reliable, and runnable in CI without secrets.