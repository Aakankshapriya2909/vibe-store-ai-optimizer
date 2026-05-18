# Technical Document — AI Representation Optimizer
**Kasparro Hackathon — Track 5 (Advanced): AI Representation Optimizer**

---

## System Architecture

```
store_data.py          ← Data layer: simulated Shopify stores + live fetch support
      │
      ▼
analyzer.py            ← Deterministic engine: rule-based checks, zero AI calls
      │                   Policies · Product descriptions · FAQ · Contradictions
      │                   Intent-gap checks (new) — keyword match against store text
      ▼
ai_simulator.py        ← AI layer: all Groq/Llama calls isolated here
      │                   simulate_ai_perception()   — how AI sees the store
      │                   compare_to_intent()        — the gap analysis
      │                   get_product_confidence()   — concurrent per-product scores
      ▼
app.py                 ← Streamlit UI: gap hero, score, action plan, export
      │
config.py              ← All thresholds and scoring weights (single source of truth)
test_analyzer.py       ← pytest test suite: scoring, intent gaps, edge cases
```

---

## Key Implementation Decisions

### 1. AI / Deterministic Boundary

`analyzer.py` contains **zero AI calls**. Every check is a Python string/length operation against known thresholds from `config.py`.

**Why:** The score must be reproducible. If the score changed between runs due to LLM non-determinism, merchants couldn't trust it. The AI layer (`ai_simulator.py`) is only used for qualitative outputs — perception and gap text — where exact reproducibility is less critical.

**How it works:**
- `analyze_store()` returns a deterministic score + issue list
- `ai_simulator.py` functions are called separately in `app.py` after the score is shown
- Merchants see the score instantly; AI results load after (~10 seconds)

### 2. Intent-Gap Scoring

The most original technical feature. When a merchant enters a positioning statement, we:

1. Extract all store text into one lowercase string (`_build_full_store_text`)
2. For each known claim type (EMI, fast shipping, sustainability, etc.), check if the merchant's intent *triggers* the claim using word-boundary regex
3. If triggered, check if the store data *confirms* the claim anywhere
4. If triggered but not confirmed → raise issue + deduct from score

```python
# Word-boundary match prevents false positives
# e.g. "emi" inside "accessories" must NOT confirm EMI
pattern = r'\b' + re.escape(kw) + r'\b'
if re.search(pattern, text):
    return True
```

**Bug we caught and fixed:** Simple substring search (`"emi" in text`) matched "emi" inside "accessories" — silently suppressing the EMI gap for accessory stores. Fixed with `\b` word-boundary regex. This is documented in `DECISIONS.md` and covered by a regression test.

### 3. Concurrent Product Confidence Scoring

15 products × ~2 seconds per Groq call = ~30 seconds sequential.

**Solution:** `ThreadPoolExecutor` with max 5 workers.

```python
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(_score_one, p, i): i for i, p in enumerate(products)}
    for future in concurrent.futures.as_completed(futures):
        idx = futures[future]
        results[idx] = future.result()
```

**Why ThreadPoolExecutor and not asyncio:** Groq's Python client is not async-native. Threading gives ~4x speedup without rewriting the client layer. Max 5 workers stays within Groq's free-tier rate limits.

**Order preservation:** Thread completion is non-deterministic, so results are stored by index and reordered after all futures complete.

### 4. Groq Client — Single Instantiation

The Groq client is instantiated once at module level (not per API call):

```python
_client: Groq | None = None

def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client
```

**Why:** Instantiating the client on every retry call (the original bug) created unnecessary overhead. Module-level singleton instantiation is standard practice.

### 5. Retry Logic with Exponential Backoff

All Groq calls go through `_ask()` which retries on failure:

```python
def _ask(prompt, retries=2, timeout_secs=20):
    for attempt in range(retries + 1):
        try:
            response = _get_client().chat.completions.create(...)
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt < retries:
                time.sleep(2 ** attempt)  # 1s, 2s backoff
            else:
                return f"AI_UNAVAILABLE: {e}"
```

**Failure handling:** If a product score fails after retries, it returns `{"score": 5, "reason": "...", "failed": True}`. The UI shows a ⚠️ marker. The app never crashes on API errors.

---

## Data Flow

```
Merchant enters positioning statement
         │
         ▼
get_store_data(demo_key)          ← store_data.py
         │
         ├──► analyze_store(data, merchant_intent)   ← analyzer.py
         │         │
         │         ├── check_policies()              ← string length checks
         │         ├── check_products()              ← desc length + alt text
         │         ├── check_faq()                   ← page title + ? count
         │         ├── check_contradictions()        ← fast-claim vs policy
         │         └── check_intent_gaps()           ← keyword match (new)
         │                   ↓
         │           score + issues list (deterministic)
         │
         └──► simulate_ai_perception(data)           ← ai_simulator.py (Groq)
              compare_to_intent(perception, intent)  ← ai_simulator.py (Groq)
              get_product_confidence(products)        ← ai_simulator.py (Groq, concurrent)
                          ↓
                  perception text + gap text + product scores
```

---

## Failure Handling

| Failure | Behaviour |
|---|---|
| `GROQ_API_KEY` missing | `ValueError` with clear message on first AI call |
| Groq API timeout | Retry 2x with backoff, then return `AI_UNAVAILABLE` string |
| Product score API error | Return fallback score 5/10 marked as `failed=True` |
| Store data key not found | Falls back to first demo store |
| `merchant_intent` empty | Intent checks skipped, `intent_checked=False` in report |

The UI handles all `AI_UNAVAILABLE` and `GAP_UNAVAILABLE` strings with warning banners. The app never crashes mid-analysis.

---

## Known Limitations

| Limitation | Root cause | Future fix |
|---|---|---|
| Description quality check is length-only | Rules can't judge prose quality | Replace with AI scoring for description quality |
| Intent gap uses keyword matching | Won't catch paraphrased claims | NLP similarity matching |
| Simulated store data only | No live Shopify API in demo | Add OAuth flow for live store auth |
| Score deductions are additive | Can go below 0 without floor | Already floored at 0 in code |
| Groq free tier rate limits | Max 5 concurrent workers | Switch to paid tier for production |

---

## Test Coverage

Run with: `python -m pytest test_analyzer.py -v`

| Test | What it covers |
|---|---|
| `test_perfect_store_scores_100` | Full store with all data = 100/100 |
| `test_missing_refund_deducts_20` | Refund policy gap = −20 pts |
| `test_missing_shipping_deducts_15` | Shipping policy gap = −15 pts |
| `test_score_never_goes_below_zero` | Score floor at 0 |
| `test_short_product_desc_deducts_5` | Short description = −5 pts |
| `test_emi_intent_gap_detected_when_missing` | EMI claimed, not in store = flagged |
| `test_emi_confirmed_in_store_no_deduction` | EMI in FAQ = no deduction |
| `test_no_intent_no_intent_issues` | Empty intent = no intent checks |
| `test_sustainability_intent_gap` | Eco claim without store data = flagged |
| `test_emi_not_matched_inside_accessories` | Word boundary regression test |
| `test_no_false_positive_on_accessories_store` | Accessory store EMI regression |
| `test_fast_shipping_claim_without_policy_flagged` | Contradiction detection |
| `test_high_severity_issues_come_first` | Sort order validation |

---

## How to Run

```bash
pip install -r requirements.txt

# Add Groq API key (free at console.groq.com)
echo "GROQ_API_KEY=your_key_here" > .env

# Run the app
streamlit run app.py

# Run tests
python -m pytest test_analyzer.py -v
```

Opens at `http://localhost:8501`

---

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI — gap hero, score, action plan, product scores, export |
| `store_data.py` | Demo stores + live Shopify fetch support |
| `analyzer.py` | Deterministic checker: policies, descriptions, FAQ, contradictions, intent gaps |
| `ai_simulator.py` | Groq/Llama: AI perception, gap analysis, concurrent product confidence |
| `config.py` | All thresholds and scoring constants with documented rationale |
| `test_analyzer.py` | pytest test suite — 13 tests covering scoring and edge cases |
| `DECISIONS.md` | Running log of every build decision and tradeoff |
| `.env` | API keys (not committed to git) |


---

## Failure Handling

### Groq API Timeout
If a Groq call times out, the UI shows a warning and falls back to
the deterministic score only. The AI perception section is skipped
rather than crashing the app.

### Rate Limit Hits
ThreadPoolExecutor is capped at 5 workers. If Groq returns a 429,
the affected product shows "scoring unavailable" inline — other
products complete normally.

### Missing Store Fields
analyzer.py treats missing fields as empty strings, not errors.
Every check has a null-safe path — the scorer never throws on
incomplete store data.

---

## Testing Strategy

13 pytest tests in test_analyzer.py cover:
- Scoring: correct deductions for each issue type
- Intent gap: keyword present vs absent vs false positive
- Word boundary: "emi" inside "accessories" regression test
- Sort order: action plan sorted by impact descending