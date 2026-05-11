# AI Representation Optimizer
**Kasparro Hackathon — Track 5**

A tool that scans a Shopify store and tells owners exactly what to fix so AI shopping agents can understand and recommend their products.

## What it does
- Reads store data (products, policies, pages)
- Checks for missing/weak content that AI agents rely on
- Simulates how an AI agent would actually describe your store
- Gives a ranked action plan with exact fixes
- Scores each product 1-10 for AI recommendation confidence

## How to run
```
pip install -r requirements.txt
streamlit run app.py
```
Opens at http://localhost:8501

## Files
| File | Purpose |
|------|---------|
| app.py | Streamlit UI — the full dashboard |
| store_data.py | Simulated Shopify store data (TheSkullStore) |
| analyzer.py | Rule-based checker for policies, descriptions, FAQ |
| ai_simulator.py | Groq/Llama AI simulates how agents see the store |
| config.py | All thresholds and scoring constants |
| .env | Your Groq API key goes here |

## No Shopify account needed
All store data comes from store_data.py — a realistic simulation of a real Shopify store with intentional flaws for demo purposes.
