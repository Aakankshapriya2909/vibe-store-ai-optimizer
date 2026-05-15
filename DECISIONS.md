# Decision Log — AI Representation Optimizer

## Decision 1: AI/Deterministic Boundary
**Options considered:**
- (a) All AI — send everything to Groq, let LLM judge
- (b) All rules — pure Python string checks
- (c) Hybrid — rules for scoring, AI for perception

**Chosen:** Hybrid (c)

**Rationale:** Rules give reproducible, testable scores.
AI gives qualitative perception that rules can't capture.
Mixing them in one layer would make scores non-deterministic.

**Tradeoff:** Rules can't judge description *quality*, only length.
A 200-word description full of filler scores the same as a 
200-word detailed spec. Accepted this tradeoff for v1.

---

## Decision 2: Intent-vs-Reality Gap Scoring
**Problem:** Merchants write positioning statements claiming features
(EMI, eco-friendly, fast shipping) that their store data doesn't confirm.
AI agents can't verify these claims → merchant gets misrepresented.

**Options considered:**
- (a) Show gap only in AI analysis text (no score impact)
- (b) Deduct from score when claim is unverifiable

**Chosen:** (b) — deduct from score

**Rationale:** If it doesn't affect the score, merchants ignore it.
Score impact creates urgency to fix the real data gap.

**Tradeoff:** Merchant might genuinely offer EMI but forgot to
add it to their store copy. Score penalises a real capability.
Accepted — the fix (add it to store copy) is exactly what's needed.

---

## Decision 3: Word-Boundary Keyword Matching
**Bug discovered:** "emi" matched inside "accessories" via substring search.
Store was falsely confirmed as having EMI support.

**Fix:** Replaced `keyword in text` with `\bkeyword\b` regex.

**Why this matters:** False positives silently drop issues from the
score. A merchant with "accessories" in their store name would never
see the EMI gap flagged, even if they claim EMI in their intent.

---

## Decision 4: Concurrent Product Scoring
**Problem:** 15 products × ~2s per Groq call = ~30s sequential.

**Options considered:**
- (a) Sequential calls
- (b) ThreadPoolExecutor (concurrent)
- (c) Async (asyncio)

**Chosen:** ThreadPoolExecutor (b)

**Rationale:** Groq client is not async-native. Threading gives
~4x speedup (30s → 8-10s) without rewriting the client layer.
Max 5 workers to stay within Groq free-tier rate limits.

**Tradeoff:** Thread order is non-deterministic — product order
is explicitly restored after completion via index mapping.