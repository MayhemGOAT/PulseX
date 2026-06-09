"""Generate HTML report from PulseX run."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from backtester import BacktestResult


def generate_html_report(
    prediction: dict,
    council_result: dict,
    ablation: list,
    backtest: dict[str, BacktestResult] | None,
    output_dir: str = "reports",
) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(output_dir) / f"pulsex_report_{timestamp}.html"

    council_members_html = ""
    for m in council_result.get("members", []):
        color = "#2ecc71" if m["direction"] > 0 else "#e74c3c" if m["direction"] < 0 else "#95a5a6"
        council_members_html += f"""
        <div class="member">
          <strong style="color:{color}">{m['name']}</strong>
          <span>Direction: {m['direction']:+.3f} | Confidence: {m['confidence']:.0%}</span>
          <p>{m['reasoning']}</p>
        </div>"""

    ablation_rows = ""
    for r in ablation:
        acc_class = "good" if r.directional_accuracy >= 0.5 else "bad"
        ablation_rows += f"""
        <tr>
          <td>{r.name}</td>
          <td>{r.mae:.4f}</td>
          <td class="{acc_class}">{r.directional_accuracy:.1%}</td>
          <td>{r.n_samples}</td>
        </tr>"""

    backtest_rows = ""
    if backtest:
        for name, bt in backtest.items():
            backtest_rows += f"""
            <tr>
              <td>{name}</td>
              <td>{bt.total_return:.2%}</td>
              <td>{bt.sharpe:.2f}</td>
              <td>{bt.max_drawdown:.2%}</td>
              <td>{bt.win_rate:.1%}</td>
              <td>{bt.n_trades}</td>
            </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>PulseX Report — {prediction.get('ticker', 'SPY')}</title>
  <style>
    body {{ font-family: -apple-system, sans-serif; max-width: 960px; margin: 40px auto; padding: 0 20px; color: #222; }}
    h1 {{ border-bottom: 2px solid #3498db; padding-bottom: 8px; }}
    h2 {{ color: #2c3e50; margin-top: 32px; }}
    .verdict {{ background: #ecf0f1; padding: 16px; border-radius: 8px; font-size: 1.2em; }}
    .member {{ border-left: 3px solid #3498db; padding: 8px 12px; margin: 8px 0; background: #fafafa; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #3498db; color: white; }}
    .good {{ color: #27ae60; font-weight: bold; }}
    .bad {{ color: #e74c3c; font-weight: bold; }}
    img {{ max-width: 100%; margin: 12px 0; border: 1px solid #eee; border-radius: 4px; }}
    .disclaimer {{ color: #7f8c8d; font-size: 0.85em; margin-top: 40px; }}
  </style>
</head>
<body>
  <h1>PulseX — AI Council Market Report</h1>
  <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>

  <h2>Next-Day Prediction</h2>
  <div class="verdict">
    <strong>{prediction.get('ticker')}</strong> on {prediction.get('date')}<br>
    Price: ${prediction.get('current_price')} → ${prediction.get('predicted_price')}
    ({prediction.get('predicted_return_pct'):+.2f}%, {prediction.get('direction')})
  </div>

  <h2>AI Council Verdict</h2>
  <div class="verdict">
    <strong>{council_result.get('council_label')}</strong>
    — Direction {council_result.get('council_direction', 0):+.3f},
    Confidence {council_result.get('council_confidence', 0):.0%},
    Consensus {council_result.get('consensus_strength', 0):.0%}
  </div>
  {council_members_html}

  <h2>Charts</h2>
  <img src="../images/council_verdict.png" alt="Council Verdict">
  <img src="../images/sentiment_overlay.png" alt="Sentiment Overlay">
  <img src="../images/ablation_results.png" alt="Ablation Results">
  <img src="../images/backtest_equity.png" alt="Backtest Equity">
  <img src="../images/event_timeline.png" alt="Event Timeline">

  <h2>A/B Model Comparison</h2>
  <table>
    <tr><th>Model</th><th>MAE</th><th>Dir Accuracy</th><th>N</th></tr>
    {ablation_rows}
  </table>

  <h2>Backtest Results</h2>
  <table>
    <tr><th>Strategy</th><th>Return</th><th>Sharpe</th><th>Max DD</th><th>Win Rate</th><th>Trades</th></tr>
    {backtest_rows}
  </table>

  <p class="disclaimer">
    Research tooling only — not financial advice. Past performance does not guarantee future results.
  </p>
</body>
</html>"""

    path.write_text(html)
    return str(path)
