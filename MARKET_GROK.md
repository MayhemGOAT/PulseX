# MarketGrok — Free Grok → Multi-Stock Predictions

Use **free Grok** (grok.com) as your research assistant. Paste its answer back — our local judge predicts direction for multiple stocks.

## How it works

```
You copy our prompt → paste into grok.com (FREE)
         ↓
Grok searches X, summarizes market buzz
         ↓
You save Grok's answer → data/my_briefing.txt
         ↓
MarketGrok parser extracts ticker scores + movers
         ↓
Local judge (60% Grok narrative + 40% price confirmation)
         ↓
UP / DOWN / FLAT for each stock + top picks
```

## Quick start

```bash
# 1. See available prompts
python3 market_grok.py prompts

# 2. Copy a prompt to Grok
python3 market_grok.py prompt market_pulse

# 3. Paste Grok's answer into a file, then analyze
python3 market_grok.py analyze data/sample_grok_paste.txt

# Or paste directly in terminal
python3 market_grok.py interactive
```

## Available Grok commands

| Command | Use when |
|---------|----------|
| `market_pulse` | Full daily briefing — 10 stocks + top movers |
| `buzzing_companies` | **Which companies everyone is talking about** on X |
| `portfolio_review` | **Analyze YOUR holdings** — HOLD/ADD/TRIM/SELL advice |
| `fed_macro` | Fed/rates focus — SPY, QQQ, TLT |
| `meme_movers` | What's buzzing on financial X |
| `single_stock` | Deep dive one ticker (`--ticker NVDA`) |

## Portfolio (for traders)

```bash
# Set your holdings
python3 market_grok.py portfolio add AAPL 10 185
python3 market_grok.py portfolio add NVDA 5 120
python3 market_grok.py portfolio set-cash 2500
python3 market_grok.py portfolio show

# Get Grok prompt tailored to YOUR portfolio
python3 market_grok.py prompt portfolio_review

# After pasting Grok's answer — get trade recommendations
python3 market_grok.py analyze data/my_briefing.txt
```

Edit `data/portfolio.json` directly, or use CLI commands above.

## Output example

```
Ticker   Dir    Conf    Grok    Tech      Price     Est%
NVDA     UP     85%    +0.70   +0.35   $875.00    +1.6%
TSLA     DOWN   62%    -0.20   -0.15   $245.00    -0.5%
SPY      UP     71%    +0.30   +0.22   $580.00    +0.8%
```

Plus: strongest bullish/bearish picks, price movers vs Grok buzz.

## Accuracy — honest expectations

| Claim | Reality |
|-------|---------|
| 100% directional accuracy | **Impossible** — markets are random short-term |
| 60%+ accuracy | **Possible sometimes** on high-conviction picks where Grok + price agree |
| Better than coin flip | **Achievable** when Grok gives explicit scores + technicals confirm |

Check your own accuracy:
```bash
python3 market_grok.py evaluate data/my_briefing.txt
```

**Tips to improve signal quality:**
- Use `market_pulse` prompt (structured format parses best)
- Only trust high-confidence picks where Grok score + technical bias agree (✓ in output)
- Run daily — track hit rate with `evaluate`

## No API keys needed

- Grok chat: **free** at grok.com
- MarketGrok judge: **free** (local Python)
- Price data: **free** (Yahoo Finance)
