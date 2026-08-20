"""
Quality Screener v1.2

Trzy bramki, przez ktore przepuszczam spolki przed dokladniejsza analiza:
    1. ROIC > 15%
    2. Real FCF = OCF - CapEx - SBC > 0
    3. Oczekiwany zwrot (FCF yield + wzrost) > stopa wymagana (10Y UST + premia)

Bramka 3 to przeksztalcony model Gordona: P = CF / (r - g), czyli r = CF/P + g.
Pierwsza wersja porownywala sama rentownosc Real FCF z rentownoscia obligacji
i odrzucala wszystko - obligacja placi staly kupon, przeplywy spolki rosna.

Dane z Yahoo Finance. Sa wtorne, wiec przy kazdej pozycji wazacej na decyzji
i tak trzeba otworzyc 10-K. To narzedzie do odsiewania, nie do rozstrzygania.
"""

import pandas as pd
import yfinance as yf

TICKERS = ["META", "GOOGL", "MA", "AMZN", "NU", "F", "NUE"]

ROIC_THRESHOLD = 0.15
EQUITY_RISK_PREMIUM = 0.045
GROWTH_CAP = 0.12
MAX_TAX_RATE = 0.50
FALLBACK_BOND_YIELD = 0.042

FINANCIAL_SECTORS = {"Financial Services", "Financials"}
# Yahoo wrzuca sieci platnicze do sektora finansowego, ale one nie biora
# ryzyka kredytowego ani nie maja bilansu bankowego - ROIC ma dla nich sens.
NOT_REALLY_FINANCIALS = {"MA", "V"}

# Nazwy wierszy zmieniaja sie miedzy wersjami yfinance. Pierwszy trafiony wygrywa.
ROW_ALIASES = {
    "ocf": ["Operating Cash Flow", "Total Cash From Operating Activities"],
    "capex": ["Capital Expenditure", "Capital Expenditures"],
    "sbc": ["Stock Based Compensation"],
    "ebit": ["EBIT", "Operating Income"],
    "pretax_income": ["Pretax Income", "Income Before Tax"],
    "tax": ["Tax Provision", "Income Tax Expense"],
    "revenue": ["Total Revenue", "Operating Revenue"],
    "total_debt": ["Total Debt"],
    "long_term_debt": ["Long Term Debt", "Long Term Debt And Capital Lease Obligation"],
    "current_debt": ["Current Debt", "Current Debt And Capital Lease Obligation"],
    "equity": ["Stockholders Equity", "Total Stockholder Equity"],
    "cash": [
        "Cash And Cash Equivalents",
        "Cash And Cash Equivalents At Carrying Value",
        "Cash Cash Equivalents And Short Term Investments",
    ],
}

GATE_LABELS = {"gate_roic": "ROIC", "gate_fcf": "Real FCF", "gate_return": "zwrot"}

COLUMNS = ["ticker", "roic", "real_fcf_musd", "fcf_yield", "growth",
           "exp_return", "spread_pp", "gate_roic", "gate_fcf", "gate_return", "summary"]


def pick_value(frame, field):
    """Najnowsza niepusta wartosc pozycji plus data okresu, z ktorego pochodzi."""
    if frame is None or getattr(frame, "empty", True):
        return None, None

    for row_name in ROW_ALIASES[field]:
        if row_name not in frame.index:
            continue

        selected = frame.loc[row_name]
        # Zdublowany label daje DataFrame zamiast Series i float() sie wywala.
        if isinstance(selected, pd.DataFrame):
            selected = selected.iloc[0]

        series = selected.dropna()
        if not series.empty:
            return float(series.iloc[0]), series.index[0]

    return None, None


def pick_total_debt(balance):
    value, period = pick_value(balance, "total_debt")
    if value is not None:
        return value, period, ""

    long_term, p1 = pick_value(balance, "long_term_debt")
    current, p2 = pick_value(balance, "current_debt")
    if long_term is None and current is None:
        return None, None, ""

    return (long_term or 0.0) + (current or 0.0), (p1 or p2), "dlug ze skladowych; "


def revenue_cagr(income):
    """
    Wzrost licze z przychodow, nie z Real FCF. FCF potrafi zmienic sie o kilkadziesiat
    procent przy jednym cyklu inwestycyjnym i zaburzylby bramke. Cena tego uproszczenia:
    zakladam stabilne marze.
    """
    if income is None or getattr(income, "empty", True):
        return None, "brak rachunku wynikow"

    for row_name in ROW_ALIASES["revenue"]:
        if row_name not in income.index:
            continue

        selected = income.loc[row_name]
        if isinstance(selected, pd.DataFrame):
            selected = selected.iloc[0]

        series = selected.dropna()
        if len(series) < 2:
            continue

        newest, oldest = float(series.iloc[0]), float(series.iloc[-1])
        if oldest <= 0 or newest <= 0:
            return None, "przychod niedodatni"
        return (newest / oldest) ** (1 / (len(series) - 1)) - 1, ""

    return None, "brak pozycji przychodu"


def get_bond_yield():
    try:
        close = yf.Ticker("^TNX").history(period="5d")["Close"].dropna()
        raw = float(close.iloc[-1])
        if raw > 20:          # ^TNX bywa kwotowany jako 47.0 zamiast 4.70
            raw /= 10
        return raw / 100
    except Exception:
        return FALLBACK_BOND_YIELD


def screen_ticker(ticker):
    """Liczy wskazniki dla jednej spolki. Bledy trafiaja do 'warning', nie do wyjatku."""
    row = {"ticker": ticker, "sector": None, "roic": None, "real_fcf_musd": None,
           "fcf_yield": None, "growth": None, "exp_return": None, "spread_pp": None,
           "period": None, "warning": ""}

    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        cash_flow, income, balance = stock.cashflow, stock.income_stmt, stock.balance_sheet
    except Exception as error:
        row["warning"] = f"pobieranie danych nieudane ({type(error).__name__})"
        return row

    row["sector"] = info.get("sector")
    periods = []

    def take(frame, field):
        value, period = pick_value(frame, field)
        if period is not None:
            periods.append(period)
        return value

    ebit = take(income, "ebit")
    pretax_income = take(income, "pretax_income")
    tax = take(income, "tax")
    equity = take(balance, "equity")
    cash, _ = pick_value(balance, "cash")

    total_debt, debt_period, debt_note = pick_total_debt(balance)
    if debt_period is not None:
        periods.append(debt_period)
    row["warning"] += debt_note

    if cash is None:
        cash = 0.0
        row["warning"] += "brak gotowki, przyjeto 0 (ROIC zanizony); "

    if None not in (ebit, pretax_income, tax, total_debt, equity) and pretax_income != 0:
        # Sufit na stope podatkowa, bo zdarzenia jednorazowe potrafia dac 87%.
        tax_rate = min(max(tax / pretax_income, 0.0), MAX_TAX_RATE)
        invested_capital = total_debt + equity - cash
        if invested_capital > 0:
            row["roic"] = ebit * (1 - tax_rate) / invested_capital
        else:
            row["warning"] += "ujemny kapital zainwestowany; "
    else:
        row["warning"] += "niekompletne dane do ROIC; "

    ocf = take(cash_flow, "ocf")
    capex = take(cash_flow, "capex")
    sbc = take(cash_flow, "sbc")

    if sbc is None:
        sbc = 0.0
        row["warning"] += "brak SBC, przyjeto 0 (Real FCF zawyzony); "

    if ocf is not None and capex is not None:
        real_fcf = ocf - abs(capex) - abs(sbc)     # CapEx u Yahoo ujemny, SBC dodatni
        row["real_fcf_musd"] = real_fcf / 1e6

        market_cap = info.get("marketCap")
        if not market_cap:
            row["warning"] += "brak kapitalizacji; "
        else:
            row["fcf_yield"] = real_fcf / market_cap
            growth, note = revenue_cagr(income)
            if growth is None:
                row["warning"] += note + "; "
            else:
                row["growth"] = growth
                if growth > GROWTH_CAP:
                    row["warning"] += f"wzrost {growth:.0%} przyciety do {GROWTH_CAP:.0%}; "
                row["exp_return"] = row["fcf_yield"] + min(growth, GROWTH_CAP)
    else:
        row["warning"] += "niekompletne dane do Real FCF; "

    # Bez tego mozna policzyc OCF z 2025 minus CapEx z 2024 i nie zauwazyc,
    # bo wynik wyglada sensownie.
    if periods:
        row["period"] = max(periods).date().isoformat()
        if len(set(periods)) > 1:
            span = sorted({p.date().isoformat() for p in periods})
            row["warning"] += f"dane z roznych okresow ({', '.join(span)}); "

    if row["sector"] in FINANCIAL_SECTORS and ticker.upper() not in NOT_REALLY_FINANCIALS:
        row["warning"] += "spolka finansowa - ROIC nieporownywalny; "

    return row


def verdict(value, threshold):
    if value is None or pd.isna(value):
        return "-"
    return "PASS" if value > threshold else "FAIL"


def summarize(gates):
    """
    Liczy tylko bramki, ktore dalo sie policzyc. Brak jednej pozycji w sprawozdaniu
    nie powinien unieważniać dwoch pozostalych - traci sie wtedy informacje,
    ktora juz sie ma.
    """
    available = {name: result for name, result in gates.items() if result != "-"}
    if not available:
        return "brak danych"

    passed = sum(1 for result in available.values() if result == "PASS")
    summary = f"{passed}/{len(available)}"

    missing = [GATE_LABELS[name] for name in gates if gates[name] == "-"]
    if missing:
        summary += f" (bez {', '.join(missing)})"
    return summary


def build_report(tickers, bond_yield):
    if not tickers:
        return pd.DataFrame(columns=COLUMNS + ["sector", "period", "warning"])

    required_return = bond_yield + EQUITY_RISK_PREMIUM
    table = pd.DataFrame([screen_ticker(t) for t in tickers])

    table["gate_roic"] = table["roic"].apply(lambda v: verdict(v, ROIC_THRESHOLD))
    table["gate_fcf"] = table["real_fcf_musd"].apply(lambda v: verdict(v, 0))
    table["gate_return"] = table["exp_return"].apply(lambda v: verdict(v, required_return))

    # Nadwyzka ponad stope wymagana jest uzyteczniejsza od PASS/FAIL,
    # bo pozwala uszeregowac spolki, ktore bramke przeszly.
    table["spread_pp"] = table["exp_return"].apply(
        lambda v: None if v is None or pd.isna(v) else (v - required_return) * 100
    )

    table["summary"] = [
        summarize(gates) for gates in
        table[list(GATE_LABELS)].to_dict(orient="records")
    ]
    return table.sort_values("spread_pp", ascending=False, na_position="last")


def print_report(table, bond_yield):
    required_return = bond_yield + EQUITY_RISK_PREMIUM
    print(f"10Y UST: {bond_yield:.2%}  +  premia za ryzyko {EQUITY_RISK_PREMIUM:.1%}"
          f"  =  stopa wymagana {required_return:.2%}")
    print(f"Prog ROIC: {ROIC_THRESHOLD:.0%}   |   sufit wzrostu: {GROWTH_CAP:.0%}")
    print("Oczekiwany zwrot = rentownosc Real FCF + wzrost przychodow.")
    print("Real FCF w mln USD, dane roczne z ostatniego sprawozdania.\n")

    if table.empty:
        print("Brak spolek do przeskanowania.")
        return

    pct = lambda v, d=1: "-" if pd.isna(v) else f"{v:.{d}%}"
    display = table[COLUMNS].copy()
    display["roic"] = table["roic"].map(pct)
    display["real_fcf_musd"] = table["real_fcf_musd"].map(lambda v: "-" if pd.isna(v) else f"{v:,.0f}")
    display["fcf_yield"] = table["fcf_yield"].map(lambda v: pct(v, 2))
    display["growth"] = table["growth"].map(pct)
    display["exp_return"] = table["exp_return"].map(lambda v: pct(v, 2))
    display["spread_pp"] = table["spread_pp"].map(lambda v: "-" if pd.isna(v) else f"{v:+.1f}pp")
    print(display.to_string(index=False))

    flagged = table[table["warning"] != ""]
    if not flagged.empty:
        print("\nOstrzezenia:")
        for _, r in flagged.iterrows():
            print(f"  [{r['ticker']}] {r['warning'].rstrip('; ')}")


if __name__ == "__main__":
    yield_10y = get_bond_yield()
    print_report(build_report(TICKERS, yield_10y), yield_10y)
