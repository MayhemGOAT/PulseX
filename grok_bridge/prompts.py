"""Copy-paste commands for free Grok (grok.com or X app)."""

from __future__ import annotations

PROMPTS = {
    "market_pulse": {
        "title": "Market Pulse — Full Briefing",
        "description": "Broad read on what financial X is discussing today",
        "text": """You are a financial markets analyst with real-time X/Twitter access.

Analyze what market-moving voices (Fed officials, CEOs, politicians, macro influencers) are saying on X in the last 24-48 hours about US stocks.

For EACH of these tickers, give a directional score from -1 (very bearish) to +1 (very bullish):
SPY, QQQ, AAPL, MSFT, NVDA, TSLA, AMZN, META, GOOGL, AMD

Also list the TOP 5 highest-momentum stocks people are buzzing about (any ticker).

Format your answer EXACTLY like this:

=== MARKET MOOD ===
Overall: [bullish/bearish/neutral] (score: -1 to +1)
Key themes: [list 3-5 themes]

=== TICKER SCORES ===
SPY: [score] — [one line reason]
QQQ: [score] — [one line reason]
AAPL: [score] — [one line reason]
(... each ticker)

=== TOP MOVERS ON X ===
1. $TICKER — [bullish/bearish] — [why people are talking]
2. ...

=== TIER-1 VOICES ===
[List any posts from Powell, Musk, Trump/POTUS, Fed, major CEOs and their market impact]

=== RISKS ===
[Top 3 risks mentioned on X today]""",
    },
    "fed_macro": {
        "title": "Fed & Macro Focus",
        "description": "Rates, inflation, Fed speakers — affects SPY/QQQ/TLT",
        "text": """Search X for what Fed officials, macro economists, and financial journalists are saying about interest rates and inflation in the last 48 hours.

Score market impact:
SPY: -1 to +1
QQQ: -1 to +1
TLT: -1 to +1

List the 3 most market-moving Fed/macro posts you see.
End with: OVERALL DIRECTION: [UP/DOWN/FLAT] for next 1-3 trading days.""",
    },
    "meme_movers": {
        "title": "Highest Movers & Buzz",
        "description": "What's trending on financial X right now",
        "text": """What stocks are getting the most attention on financial X/Twitter right now?

List TOP 10 tickers by buzz/volume of discussion (not just price move).
For each: $TICKER, sentiment (-1 to +1), main reason people are posting.

Separate into:
🟢 BULLISH BUZZ (likely to go UP)
🔴 BEARISH BUZZ (likely to go DOWN)

Which 3 stocks have the strongest directional consensus?""",
    },
    "buzzing_companies": {
        "title": "Companies Everyone Is Talking About",
        "description": "Discover hot companies, sectors, and why X is obsessed with them",
        "text": """Search financial X/Twitter right now and tell me which COMPANIES and STOCKS people won't stop talking about.

Focus on:
- Earnings surprises, product launches, CEO drama, regulatory news
- Sectors getting the most posts (AI, crypto, biotech, energy, etc.)
- Small/mid caps suddenly trending (not just Mag 7)

Format EXACTLY like this:

=== HOT SECTORS ===
1. [Sector] — [why it's trending]
2. ...

=== COMPANIES EVERYONE IS TALKING ABOUT ===
Rank the TOP 15 by X buzz volume (not just price move):
1. $TICKER — [Company name] — sentiment: [score -1 to +1] — [why people are posting]
2. ...

=== SURPRISE DEBUTS ===
[Stocks that weren't talked about last week but are exploding on X today]

=== CONSENSUS PICKS ===
Most agreed-upon bullish: $TICKER, $TICKER, $TICKER
Most agreed-upon bearish: $TICKER, $TICKER, $TICKER

=== NOTABLE POSTS ===
[3-5 specific viral posts driving the conversation, with account names]

=== RISKS ===
[What could kill the buzz / reverse sentiment quickly]""",
    },
    "portfolio_review": {
        "title": "Portfolio Review — Trade My Holdings",
        "description": "Grok analyzes YOUR specific holdings + what's being said on X",
        "text": """You are my personal trading analyst with real-time X access.

MY CURRENT PORTFOLIO:
{portfolio_block}

For EACH holding above, search X for what people are saying in the last 48 hours.

Format EXACTLY like this:

=== PORTFOLIO MOOD ===
Overall portfolio risk: [low/medium/high]
Biggest threat today: [one line]

=== HOLDING REVIEWS ===
TICKER: [score -1 to +1] — [HOLD / ADD / TRIM / SELL] — [one line X sentiment reason]
(repeat for every holding)

=== HOLDINGS AT RISK ===
[List holdings with bearish X buzz or negative catalysts]

=== ADD OPPORTUNITIES ===
[Should I add to any current holdings? Why?]

=== NEW IDEAS (not in my portfolio) ===
[3 stocks buzzing on X that fit my portfolio style — ticker, score, reason]

=== TRADE PLAN ===
Today: [specific actions — e.g. trim TSLA 20%, hold NVDA, watch SMCI]
This week: [medium-term positioning advice]""",
    },
    "single_stock": {
        "title": "Deep Dive — One Stock",
        "description": "Replace TICKER before pasting to Grok",
        "text": """Analyze everything being said on X about $TICKER in the last 48 hours.

1. Overall sentiment score (-1 bearish to +1 bullish)
2. Key bullish arguments (top 3)
3. Key bearish arguments (top 3)
4. Notable posts from influential accounts
5. PREDICTION: Will $TICKER go UP or DOWN tomorrow? Confidence 0-100%
6. One-line trade thesis""",
    },
}


def list_prompts() -> str:
    lines = ["Available Grok commands (copy → paste into grok.com):\n"]
    for key, p in PROMPTS.items():
        lines.append(f"  [{key}] {p['title']}")
        lines.append(f"          {p['description']}\n")
    lines.append("Run: python3 market_grok.py prompt <name>")
    lines.append("     python3 market_grok.py prompt market_pulse")
    return "\n".join(lines)


def _format_portfolio_block(holdings: list[dict]) -> str:
    if not holdings:
        return "(No holdings — add with: python3 market_grok.py portfolio add TICKER SHARES [AVG_COST])"
    lines = []
    for h in holdings:
        t = h["ticker"].upper()
        sh = h["shares"]
        cost = h.get("avg_cost")
        if cost is not None:
            lines.append(f"- {t}: {sh} shares @ ${cost:.2f} avg cost")
        else:
            lines.append(f"- {t}: {sh} shares")
    return "\n".join(lines)


def get_prompt(
    name: str,
    ticker: str | None = None,
    portfolio_holdings: list[dict] | None = None,
) -> str:
    if name not in PROMPTS:
        raise KeyError(f"Unknown prompt '{name}'. Choose: {', '.join(PROMPTS)}")
    text = PROMPTS[name]["text"]
    if ticker:
        text = text.replace("$TICKER", f"${ticker.upper()}").replace("TICKER", ticker.upper())
    if "{portfolio_block}" in text:
        block = _format_portfolio_block(portfolio_holdings or [])
        text = text.replace("{portfolio_block}", block)
    return text
