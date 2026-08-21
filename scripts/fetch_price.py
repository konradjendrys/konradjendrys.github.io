"""
Pobiera ostatnie zamkniecie MA i zapisuje do data/ma.json.
Uruchamiany raz dziennie przez GitHub Actions - strona czyta gotowy plik,
bo GitHub Pages serwuje wylacznie statyczna zawartosc.
"""

import json
import pathlib
from datetime import datetime, timezone

import yfinance as yf

TICKER = "MA"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "ma.json"


def main():
    history = yf.Ticker(TICKER).history(period="5d")["Close"].dropna()
    if history.empty:
        raise SystemExit("brak notowan - nie nadpisuje poprzedniej wartosci")

    payload = {
        "ticker": TICKER,
        "price": round(float(history.iloc[-1]), 2),
        "close_date": history.index[-1].date().isoformat(),
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"{payload['price']} USD, zamkniecie {payload['close_date']}")


if __name__ == "__main__":
    main()
