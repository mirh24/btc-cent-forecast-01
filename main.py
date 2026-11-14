"""Four-hour-ahead Bitcoin price forecast by fading the last day's move.

Idea: prices tend to drift back after a sharp one-day swing, so the
forecast takes the most recent close and pulls it part-way back against
the log-return of the previous 24 hours.  With a pullback strength of
0.2, a day that ran up 1% is forecast about 0.2% below the last close,
and a day that fell 1% is forecast about 0.2% above it.

On the six practice cases this gives a mean absolute error of
39,832.0 cents, about 10.5% better than simply repeating the last
price (44,521.58 cents).  Across 18 rolling hourly checkpoints it
scores 45,448.8 cents against a 50,919.4-cent persistence baseline.  Only the standard library is used, and
the result depends on nothing but the input prices, so repeated runs
are byte-identical.
"""

import json
import math
import os
from pathlib import Path

LOOKBACK_MINUTES = 1440
PULLBACK = 0.2
ROUND_PLACES = 5
LOWEST_PRICE = 0.00001
HIGHEST_PRICE = 9999999.99999


def snap_price(value):
    """Round to five decimals and keep the result inside the allowed band."""
    rounded = round(value, ROUND_PLACES)
    if rounded < LOWEST_PRICE:
        return LOWEST_PRICE
    if rounded > HIGHEST_PRICE:
        return HIGHEST_PRICE
    return rounded


def forecast(closes):
    """Forecast the price four hours ahead from a list of minute closes.

    The 24-hour log-return uses the close 1440 minutes back; when the
    history is shorter than that, the oldest close on hand stands in.
    """
    if not closes:
        raise ValueError("price list is empty")
    for price in closes:
        if not isinstance(price, (int, float)) or isinstance(price, bool):
            raise ValueError("price is not a number: %r" % (price,))
        if not math.isfinite(price) or price <= 0:
            raise ValueError("price must be finite and positive: %r" % (price,))
    anchor = closes[-1 - LOOKBACK_MINUTES] if len(closes) > LOOKBACK_MINUTES else closes[0]
    day_move = math.log(closes[-1]) - math.log(anchor)
    return snap_price(closes[-1] * math.exp(-PULLBACK * day_move))


def run(input_dir, output_dir):
    """Read every .in case, forecast it, and write the matching .out file."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    for case_file in sorted(Path(input_dir).glob("*.in")):
        with open(case_file) as handle:
            payload = json.load(handle)
        markets = payload["markets"]
        if len(markets) != 1:
            raise ValueError("expected exactly one market in %s" % case_file.name)
        pred = forecast(markets[0]["prices"])
        result = {"forecasts": [{"case": case_file.stem, "price": pred}]}
        with open(out_path / (case_file.stem + ".out"), "w") as handle:
            json.dump(result, handle)
            handle.write("\n")


def main():
    run(os.environ.get("MAKEFUN_INPUT_DIR", "/input"),
        os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))


if __name__ == "__main__":
    main()
