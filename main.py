"""btc-cent-forecast-01 entry: 4-hour-ahead BTC price forecast.

Approach (mean reversion on the 24-hour return)
------------------------------------------------
The house baseline (persistence) guesses the price does not move. On the
practice cases that scores a mean absolute error of 44,521.58 cents.

Bitcoin's 4-hour returns show mean reversion against the past day's move:
over the practice recording (2026-11-07 to 2026-11-11, the Orca cbBTC/USDC
pool), the correlation between the past 24-hour log-return and the next
4-hour log-return is about -0.54, and between the past 4-hour return and
the next 4-hour return about -0.31. A big move in the past day tends to
partially reverse over the next 4 hours.

So the forecast shrinks the past day's move back toward the checkpoint
price instead of extrapolating it:

    forecast = last_price * exp(-0.2 * r24)

where r24 is the log-return over the 24 hours up to the checkpoint.
The coefficient 0.2 is a shrunk, round-number value: on the six practice
cases it scores 39,943 cents (10.3% below persistence) and on 18 hourly
rolling checkpoints over the same window 45,520 cents (10.6% below
persistence, winning 11 of 18). Finer values (0.15, 0.25) and adding a
4-hour term were both worse or within noise, so the single 0.2 term is
kept. No intercept is fitted: the practice window trends down, and a
fitted drift would not generalise to the final's unseen 48 hours.

Deterministic (no randomness, no clock, no network), standard library
only, and fast (a few milliseconds per case).

Input:  /input/<id>.in  (or $MAKEFUN_INPUT_DIR) — one case, JSON:
        {"schema","competition","case","at","horizon_minutes":240,
         "markets":[{"id","name","start","prices":[4320 closes]}]}
Output: /output/<id>.out (or $MAKEFUN_OUTPUT_DIR):
        {"forecasts":[{"case":"<id>","price":<number>}]}
"""

import json
import math
import os
from pathlib import Path

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

# Reversion strength on the past day's log-return (tuned on the practice
# recording; see the module docstring). 0 = persistence.
REVERT = 0.2
# The 24-hour lookback, in minutes.
LOOKBACK = 1440

MIN_PRICE = 0.00001
MAX_PRICE = 9_999_999.99999


def price5(x):
    """Keep x on the grid's 5 decimals and inside the scorer's bounds."""
    return round(min(MAX_PRICE, max(MIN_PRICE, x)) * 1e5) / 1e5


def forecast(prices):
    """One forecast from a list of minute closes (oldest first)."""
    if not prices:
        raise ValueError("no prices")
    logs = []
    for p in prices:
        if not isinstance(p, (int, float)) or not math.isfinite(p) or p <= 0:
            raise ValueError("non-finite or non-positive price")
        logs.append(math.log(p))
    last = logs[-1]
    ref = logs[max(0, len(logs) - LOOKBACK - 1)]
    r24 = last - ref
    return price5(math.exp(last - REVERT * r24))


def main():
    in_dir = Path(INPUT_DIR)
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = sorted(p for p in in_dir.iterdir()
                    if p.is_file() and p.name.endswith(".in"))
    for path in inputs:
        case_id = path.name[: -len(".in")]
        with open(path, "r", encoding="utf-8") as f:
            case = json.load(f)
        markets = case["markets"]
        if len(markets) != 1:
            raise ValueError(f"{path.name} does not hold exactly one market")
        price = forecast(markets[0]["prices"])
        out = {"forecasts": [{"case": case_id, "price": price}]}
        with open(out_dir / f"{case_id}.out", "w", encoding="utf-8") as f:
            f.write(json.dumps(out) + "\n")


if __name__ == "__main__":
    main()
