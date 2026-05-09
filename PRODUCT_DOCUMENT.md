# Product Document — Nova AI Optimizer

## Project Name
Nova AI Optimizer — AI Representation 
Optimizer for Vibe Store

## Problem We Are Solving
Most small Shopify store owners don't know 
that their product descriptions are badly 
written for AI assistants.

When a customer asks an AI:
"Find me a floral dress for a wedding 
under ₹1500 in size M"

The AI visits the store and finds:
"Blue Dress — ₹1299 — Beautiful dress!"

The AI thinks:
- Is it floral? Don't know
- Is it for weddings? Don't know
- Is size M available? Don't know
→ AI skips this store → Sale lost ❌

## Our Solution
Nova AI Optimizer scans the store and:
- Finds all missing or vague information
- Gives an AI Readiness Score (0-10)
- Shows exactly what to fix
- Shows before vs after examples
- Gives a priority action plan

## Target User
Small Shopify clothing store owner with 
no technical knowledge who wants more 
sales through AI-powered shopping.

## Core User Journey
1. Store owner opens Nova AI Optimizer
2. Tool scans their Vibe Store data
3. Sees AI Readiness Score → 5.5/10
4. Sees list of problems found
5. Reads exact fixes for each problem
6. Fixes their store descriptions
7. AI now recommends their store better
8. More customers buy → Sales increase ✅

## What We Check
- Product name clarity
- Description length and detail
- Fabric information present or not
- Size guide present or not
- Occasion/use case mentioned or not
- Return policy clarity
- Shipping policy clarity
- Payment methods clarity
- Price clarity

## What We Decided NOT To Build
- Real Shopify API integration 
  (too complex for hackathon timeline)
- Multi-language support
- Automatic fixing of descriptions
  (we show fixes, owner applies them)
- Mobile app version

## Key Product Decisions

### Why Track 5 over other tracks?
Most teams will build chatbots (Track 4).
Track 5 solves a deeper problem — 
store data quality — which affects ALL 
AI commerce interactions, not just one.

### Why a score system?
Store owners need a simple number to 
understand how AI-ready their store is.
A score (0-10) is instantly understandable
and motivating to improve.

### Why before/after examples?
Showing the difference between bad and 
good descriptions makes the problem 
real and the solution obvious.

## Tradeoffs
- Used hardcoded store data instead of 
  live Shopify API — faster to build,
  reliable for demo
- Rule-based analysis instead of pure AI —
  more predictable and explainable results
- Focus on clothing store only —
  deeper solution for one category
  rather than shallow solution for all

## Success Metrics
- AI Readiness Score improves from 
  5.5/10 to 9/10 after fixes
- All critical issues resolved
- Before/after comparison shows 
  clear improvement in AI responses

## Team
| Name | Role |
|------|------|
| Aakanksha Priya | Backend + Technical Doc |
| Astha Pradhan | Frontend UI + Product Doc |