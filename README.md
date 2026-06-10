# 📈 PulseX — AI Council Market Predictor

**Predict markets from leader X sentiment — plus a free Grok copy-paste workflow for daily trade ideas.**

No paid API keys required for the daily workflow. Runs 100% locally (tested on macOS and Linux).

---

## 🤔 What does this do?

Every day, people on X (Twitter) talk about stocks — CEOs, the Fed, influencers, traders.

**PulseX helps you:**

1. 📋 Copy a smart question → paste it into **free Grok** at [grok.com](https://grok.com)
2. 🧠 Grok searches X and tells you what the market is buzzing about
3. 📥 You paste Grok's answer back into this tool
4. 🎯 A local judge reads it + checks live prices → gives you **UP / DOWN / HOLD / TRIM / SELL** signals

Under the hood, PulseX also runs an **AI Council** — six specialist members that score leader tweets, technicals, macro events, and risk, then vote on market direction.

Think of it as: **Grok = your eyes on X** | **PulseX = your brain for trading decisions**

---

## ⚡ Quick start (5 minutes)

### Step 1 — Install (one time only)

Open Terminal and run:

```bash
git clone https://github.com/MayhemGOAT/PulseX.git
cd PulseX
pip install -r requirements.txt
export PULSEX_FAST=1
```

### Step 2 — Try the demo (no Grok needed)

```bash
python3 market_grok.py analyze data/sample_grok_paste.txt
```

You'll see stock predictions instantly. This proves everything works.

### Step 3 — Your first real run

```bash
# See all available prompts
python3 market_grok.py prompts

# Copy the "market pulse" prompt
python3 market_grok.py prompt market_pulse
```

Copy everything it prints → go to **[grok.com](https://grok.com)** → paste → wait for the answer.

Save Grok's reply to a file (e.g. `grok_answer.txt`), then:

```bash
python3 market_grok.py analyze grok_answer.txt
```

**Done.** You now have predictions for 10+ stocks.

---

## 📅 Daily trader routine

```text
☀️ Morning
   │
   ├─ 1️⃣  python3 market_grok.py portfolio show     ← check your holdings
   │
   ├─ 2️⃣  python3 market_grok.py prompt portfolio_review
   │       → copy → paste into grok.com
   │
   ├─ 3️⃣  Save Grok's answer → grok_answer.txt
   │
   └─ 4️⃣  python3 market_grok.py analyze grok_answer.txt
           → get trade recommendations
```

Takes about **5–10 minutes** once you're used to it.

---

## 💼 Set up your portfolio (important for traders)

Tell the tool what you own so it gives **personal** advice.

```bash
# Add your stocks (TICKER  SHARES  AVG_BUY_PRICE)
python3 market_grok.py portfolio add AAPL 10 185
python3 market_grok.py portfolio add NVDA 5 120
python3 market_grok.py portfolio add TSLA 8 250
python3 market_grok.py portfolio set-cash 2500

# Check it looks right
python3 market_grok.py portfolio show
```

Or edit `data/portfolio.json` directly in any text editor.

Now when you run `prompt portfolio_review`, Grok sees **your exact holdings** and gives tailored advice.

---

## 📝 Grok prompts — which one to use?

| Prompt                   | When to use                                     | Command                             |
| ------------------------ | ----------------------------------------------- | ----------------------------------- |
| 📊 **Market Pulse**      | Daily morning briefing — 10 big stocks + movers | `prompt market_pulse`               |
| 🔥 **Buzzing Companies** | "What's everyone talking about on X?"           | `prompt buzzing_companies`          |
| 💼 **Portfolio Review**  | Trade advice for **your** holdings              | `prompt portfolio_review`           |
| 🏦 **Fed & Macro**       | Interest rates, inflation, Fed news             | `prompt fed_macro`                  |
| 🚀 **Meme Movers**       | Trending / viral stocks on X                    | `prompt meme_movers`                |
| 🔍 **Single Stock**      | Deep dive on one ticker                         | `prompt single_stock --ticker NVDA` |

**New trader?** Start with `portfolio_review` if you have holdings, or `market_pulse` if you don't.

---

## 📖 How to read the output

After `analyze`, you'll see something like this:

```text
Ticker   Dir    Conf    Grok    Tech      Price     Est%
NVDA     UP     81%    +0.70   -0.20   $208.64    +0.5%
TSLA     DOWN   46%    -0.20   +0.04   $408.95    -0.2%
```

| Column     | Meaning                          | What to look for                        |
| ---------- | -------------------------------- | --------------------------------------- |
| **Ticker** | Stock symbol                     | —                                       |
| **Dir**    | Predicted direction              | 🟢 UP · 🔴 DOWN · ⚪ FLAT                  |
| **Conf**   | How confident the judge is       | Higher = stronger signal (70%+ is good) |
| **Grok**   | Sentiment from Grok's X research | +1 = very bullish, -1 = very bearish    |
| **Tech**   | What the price chart says        | Confirms or conflicts with Grok         |
| **Price**  | Current live price               | —                                       |
| **Est%**   | Rough expected move              | Small numbers are normal for 1 day      |

### Trade recommendations (if you set up a portfolio)

| Icon         | Action     | Meaning                                    |
| ------------ | ---------- | ------------------------------------------ |
| 🔴 **SELL**  | Get out    | Strong bearish signal                      |
| 🟠 **TRIM**  | Sell some  | Take partial profits or reduce risk        |
| 🟢 **ADD**   | Buy more   | Bullish + good entry point                 |
| ⚪ **HOLD**  | Do nothing | No clear edge — wait                       |
| 👀 **WATCH** | New idea   | Buzzing on X but not in your portfolio yet |

**Golden rule:** Only act when **Conf is 55%+** AND Grok + Tech **agree** (both positive or both negative).

---

## 🛠️ All commands cheat sheet

### Daily workflow (start here)

Copy-paste Grok → local judge → trade signals:

```bash
python3 market_grok.py prompts              # 📋 list all Grok prompts
python3 market_grok.py prompt market_pulse  # 📋 copy a prompt for Grok
python3 market_grok.py analyze FILE.txt     # 🎯 run predictions
python3 market_grok.py interactive          # 📥 paste Grok's answer in terminal
python3 market_grok.py evaluate FILE.txt    # 📊 check if past picks were right

python3 market_grok.py portfolio show              # 💼 view holdings
python3 market_grok.py portfolio add AAPL 10 185   # ➕ add stock
python3 market_grok.py portfolio remove AAPL       # ➖ remove stock
python3 market_grok.py portfolio set-cash 5000     # 💵 set cash balance
```

### PulseX pipeline (AI Council + backtesting)

Full ML pipeline with AI Council deliberation:

```bash
python3 cli.py import-tweets data/sample_tweets.csv   # one-time setup
python3 cli.py run                                      # full analysis + charts
python3 cli.py council                                  # AI council vote only
python3 cli.py backtest                                 # strategy comparison
```

Most beginners can start with the **daily workflow** above. Use the full PulseX pipeline when you want council votes, backtests, and HTML reports.

---

## 🗂️ Project files you'll touch

| File                         | What it's for                            |
| ---------------------------- | ---------------------------------------- |
| `grok_answer.txt`            | Save Grok's reply here (you create this) |
| `data/portfolio.json`        | Your stock holdings                      |
| `data/sample_grok_paste.txt` | Demo file — try `analyze` on this first  |
| `data/sample_tweets.csv`     | Sample tweet data for PulseX             |

---

## ❓ FAQ for first-time traders

**Do I need to pay for anything?**
No. Grok.com is free. This tool is free. Stock prices come from Yahoo Finance (free).

**Do I need an API key?**
No for the copy-paste workflow. Optional keys only if you want full automation later.

**Will this make me rich?**
No tool guarantees profits. Markets are unpredictable. Use this for **research**, not as your only reason to trade.

**How accurate is it?**
Honest answer: sometimes better than a coin flip (~50%), sometimes not. Track your own results with `evaluate`. Never trust 100% accuracy claims from any tool.

**What stocks does it cover?**
Any US ticker Grok mentions — SPY, AAPL, NVDA, TSLA, etc. Default watchlist: SPY, QQQ, AAPL, MSFT, NVDA, TSLA, AMZN, META, GOOGL, AMD.

**Grok gave a messy answer — will it still work?**
Best results when Grok follows the structured format in the prompts. Use `market_pulse` or `portfolio_review` for the cleanest output.

**I already have a Grok answer saved (`grok_answer.txt`)**
```bash
python3 market_grok.py analyze grok_answer.txt
```

---

## ⚠️ Disclaimer

This is **research and education software** — not financial advice.

- Past performance does not guarantee future results
- Always do your own research before trading
- Never invest money you can't afford to lose
- The author is not a licensed financial advisor

---

## 🏗️ How it works under the hood (optional reading)

### Daily workflow

```text
You  →  Grok (free, searches X live)
         ↓
      Paste answer
         ↓
   PulseX parser     →  extracts ticker scores + themes
         ↓
   Local judge       →  60% Grok narrative + 40% price chart
         ↓
   Portfolio advisor →  HOLD / TRIM / SELL / WATCH per your holdings
         ↓
   Terminal report   →  easy-to-read table + trade ideas
```

### AI Council pipeline

```text
Leader tweets  →  sentiment + impact scoring
         ↓
   AI Council (6 members)  →  weighted deliberation
         ↓
   ML model + backtest  →  compare vs buy-and-hold
         ↓
   HTML report + charts
```

---

## 🆘 Something broken?

```bash
# Make sure you're in the project folder
cd PulseX

# Re-install dependencies
pip install -r requirements.txt

# Run tests
PULSEX_FAST=1 pytest tests/ -q
```

All tests should pass. If not, check your Python version (3.10+ recommended).

---

**Happy trading — stay curious, stay cautious.** 📊🚀
