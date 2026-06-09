# PulseX

**AI Council-powered market predictor** using leader X/Twitter sentiment, technical indicators, and multi-agent deliberation.

Built on lessons from [FinPulse](https://github.com/MayhemGOAT/quant-backtester): honest evaluation, regularized models, no inflated backtest claims.

## Concept

Track posts from market-moving voices → score with FinBERT + keyword impact → **5-agent AI Council deliberates** → ML model forecasts → backtest → HTML report.

```
Leader X posts
    ↓
FinBERT + keyword impact scoring
    ↓
┌─────────────────────────────────────────┐
│           AI Council (5 agents)         │
│  Sentiment │ Technical │ Macro │ Risk   │
│            │           │       │ Event  │
└─────────────────────────────────────────┘
    ↓ weighted vote
Direction signal + confidence
    ↓
Random Forest (regularized) + backtest
    ↓
Charts + HTML report
```

## AI Council

| Agent | Role |
|-------|------|
| **Sentiment Analyst** | Leader tweet FinBERT scores, bullish/bearish counts |
| **Technical Analyst** | RSI, MACD, SMA ratios, momentum |
| **Macro Strategist** | Fed/political/macro leader posts weighted higher |
| **Risk Manager** | Volatility regime — dampens confidence in high-risk periods |
| **Event Detector** | Tier-1 leader posts (Powell, Musk, POTUS) → event boost |

Council produces: `STRONG_BUY | BUY | NEUTRAL | SELL | STRONG_SELL` with per-member reasoning.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env          # optional: X_BEARER_TOKEN

# Fast mode (no FinBERT download — uses keyword scoring)
export PULSEX_FAST=1

# Import sample tweets and run full pipeline
python3 cli.py import-tweets data/sample_tweets.csv
python3 cli.py run
```

## CLI commands

```bash
python3 cli.py run              # Full pipeline + HTML report
python3 cli.py council          # AI Council deliberation only
python3 cli.py backtest           # Strategy comparison
python3 cli.py events             # Detect tier-1 market events
python3 cli.py walkforward        # Walk-forward validation
python3 cli.py import-tweets FILE # Import tweet CSV
python3 cli.py fetch              # Fetch live tweets (needs X API)
python3 cli.py --ticker TSLA run  # Target specific ticker
```

## X API setup

1. [developer.x.com](https://developer.x.com) → create app → Bearer Token
2. Add to `.env`: `X_BEARER_TOKEN=...`

Without API: import tweets via CSV (`handle`, `text`, `created_at` columns).

## Project structure

```
pulse_x.py              # Main pipeline
cli.py                  # Command-line interface
council/                # AI Council (5 specialist agents)
  base.py               # CouncilContext, MemberOpinion, CouncilVerdict
  members.py            # Sentiment, Technical, Macro, Risk, Event agents
  orchestrator.py       # Weighted voting + consensus
impact_scorer.py        # Keyword + FinBERT hybrid impact scoring
event_detector.py       # Tier-1 leader event detection
backtester.py           # Long/flat strategy backtesting
features.py             # Technical indicators
tweet_fetcher.py        # X API v2 + cache + CSV import
tweet_sentiment.py      # FinBERT scoring + daily aggregation
visualizer.py           # All charts
report.py               # HTML report generator
config.yaml             # Project configuration
leaders.py              # Leader watchlist
data/
  sample_tweets.csv     # 90 demo tweets (Jan–Jun 2024)
  leaders_config.json   # Editable leader config
tests/                  # Unit tests
images/                 # Generated charts
reports/                # HTML reports
```

## Evaluation

Four A/B models on chronological test split:

| Model | Features |
|-------|----------|
| `technical_only` | Price indicators only |
| `leader_sentiment_only` | Tweet sentiment only |
| `combined` | Both |
| `ai_council_features` | Sentiment + key technicals |

**Directional accuracy below 50% = worse than a coin flip.** Reported plainly.

Backtest compares: ML model vs AI Council vs buy-and-hold vs event-only.

## Configuration

Edit `config.yaml`:

```yaml
ticker: SPY
council:
  member_weights:
    Event Detector: 1.2
    Macro Strategist: 1.1
```

Edit leaders via `data/leaders_config.json` or `leaders.py`.

## Tests

```bash
PULSEX_FAST=1 pytest tests/ -v
```

## Limitations

- Historical tweet data is scarce without paid X API or archives
- Correlation ≠ causation — bullish tweets don't guarantee rallies
- Daily direction for liquid ETFs ≈ 50% baseline (EMH)
- Research tooling only — not financial advice

## Next steps

1. **Historical tweet archive** — Finnhub, academic datasets, or paid providers
2. **LLM impact scoring** — GPT/Claude to classify market-moving vs noise
3. **Intraday alignment** — match tweet timestamps to 1-min bars
4. **Live alerts** — webhook when Tier-1 leader posts
5. **Multi-asset** — cross-sectional model per leader→ticker mapping
