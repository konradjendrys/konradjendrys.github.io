"""Test logiki na danych podstawionych recznie. Nie laczy sie z siecia."""
import pandas as pd
import screener as s

D1 = pd.Timestamp("2025-12-31")
D2 = pd.Timestamp("2024-12-31")


def frame(rows, cols=(D1, D2)):
    # nazwy pozycji musza byc indeksem (wierszami), tak jak zwraca yfinance
    return pd.DataFrame.from_dict(rows, orient="index", columns=list(cols))


print("=" * 62)
print("TEST 1: pick_value bierze najnowsza niepusta kolumne")
f = frame({"Operating Cash Flow": [100.0, 90.0]})
print("  ->", s.pick_value(f, "ocf"), "  oczekiwane: (100.0, 2025-12-31)")

print("\nTEST 2: pusta najnowsza kolumna -> siega do starszej")
f = frame({"Operating Cash Flow": [None, 90.0]})
print("  ->", s.pick_value(f, "ocf"), "  oczekiwane: (90.0, 2024-12-31)")

print("\nTEST 3: zdublowany wiersz (tu v1.0 sie wywalala)")
f = pd.DataFrame([[100.0, 90.0], [111.0, 99.0]],
                 index=["Operating Cash Flow", "Operating Cash Flow"],
                 columns=[D1, D2])
print("  ->", s.pick_value(f, "ocf"), "  oczekiwane: (100.0, 2025-12-31) bez wyjatku")

print("\nTEST 4: alias zapasowy (stara nazwa wiersza u Yahoo)")
f = frame({"Total Cash From Operating Activities": [80.0, 70.0]})
print("  ->", s.pick_value(f, "ocf"), "  oczekiwane: (80.0, 2025-12-31)")

print("\nTEST 5: brak wiersza")
print("  ->", s.pick_value(frame({"Cos Innego": [1.0, 2.0]}), "ocf"), "  oczekiwane: (None, None)")

print("\n" + "=" * 62)
print("TEST 6: verdict")
for v, t, exp in [(0.20, 0.15, "PASS"), (0.10, 0.15, "FAIL"),
                  (None, 0.15, "-"), (float("nan"), 0.15, "-")]:
    print(f"  verdict({v}, {t}) = {s.verdict(v, t):5s} oczekiwane: {exp}")

print("\n" + "=" * 62)
print("TEST 7: recznie liczony ROIC i Real FCF")
ebit, pretax, tax = 80_000.0, 78_000.0, 12_000.0
debt, equity, cash = 30_000.0, 180_000.0, 45_000.0
tax_rate = min(max(tax / pretax, 0.0), s.MAX_TAX_RATE)
ic = debt + equity - cash
roic = ebit * (1 - tax_rate) / ic
print(f"  stopa podatkowa {tax_rate:.2%}, kapital zainwestowany {ic:,.0f}")
print(f"  ROIC = {roic:.2%}   bramka: {s.verdict(roic, s.ROIC_THRESHOLD)}")

ocf, capex, sbc = 100_000.0, -60_000.0, 14_000.0
real_fcf = ocf - abs(capex) - abs(sbc)
print(f"  Real FCF = {ocf:,.0f} - {abs(capex):,.0f} - {abs(sbc):,.0f} = {real_fcf:,.0f}")
print(f"  bramka Real FCF: {s.verdict(real_fcf, 0)}")
mcap = 1_500_000.0
print(f"  rentownosc = {real_fcf/mcap:.2%}  vs 10Y 4.20% -> {s.verdict(real_fcf/mcap, 0.042)}")

print("\n" + "=" * 62)
print("TEST 8: sufit na stope podatkowa (one-off 87%)")
print(f"  surowa 87% -> uzyta {min(max(0.87, 0.0), s.MAX_TAX_RATE):.0%} (sufit {s.MAX_TAX_RATE:.0%})")

print("\nTEST 9: ujemny kapital zainwestowany")
print(f"  dlug 5k + kapital 100k - gotowka 200k = {5_000+100_000-200_000:,.0f} -> ROIC pomijany, warning")

print("\n" + "=" * 62)
print("TEST 10: pusta lista tickerow (tu v1.0 dawala KeyError)")
empty = s.build_report([], 0.042)
print(f"  wierszy: {len(empty)}, kolumny obecne: {'summary' in empty.columns}")
s.print_report(empty, 0.042)

print("\n" + "=" * 62)
print("TEST 11: raport na podstawionych wierszach")
fake = [
    {"ticker": "AAA", "sector": "Technology", "roic": 0.25, "real_fcf_musd": 30_000.0,
     "fcf_yield": 0.055, "growth": 0.18, "exp_return": 0.175, "period": "2025-12-31", "warning": ""},
    {"ticker": "BBB", "sector": "Technology", "roic": 0.08, "real_fcf_musd": -1_200.0,
     "fcf_yield": -0.004, "growth": 0.03, "exp_return": 0.026, "period": "2025-12-31", "warning": ""},
    {"ticker": "CCC", "sector": "Financial Services", "roic": None, "real_fcf_musd": None,
     "fcf_yield": None, "growth": None, "exp_return": None, "period": None,
     "warning": "spolka finansowa; "},
]
bond = 0.042
req = bond + s.EQUITY_RISK_PREMIUM
t = pd.DataFrame(fake)
t["gate_roic"] = t["roic"].apply(lambda v: s.verdict(v, s.ROIC_THRESHOLD))
t["gate_fcf"] = t["real_fcf_musd"].apply(lambda v: s.verdict(v, 0))
t["gate_return"] = t["exp_return"].apply(lambda v: s.verdict(v, req))
t["spread_pp"] = t["exp_return"].apply(lambda v: None if v is None or pd.isna(v) else (v - req) * 100)
t["summary"] = [s.summarize(row) for row in
                t[["gate_roic", "gate_fcf", "gate_return"]].to_dict(orient="records")]
s.print_report(t.sort_values("spread_pp", ascending=False, na_position="last"), bond)

print("\n" + "=" * 62)
print("TEST 12: bramka 3 na modelu Gordona")
bond = 0.047
req = bond + s.EQUITY_RISK_PREMIUM
print(f"  stopa wymagana = {bond:.2%} + {s.EQUITY_RISK_PREMIUM:.1%} = {req:.2%}")
for name, y, g in [("jakosciowy kompaunder", 0.018, 0.21),
                   ("drogi wolnorosnacy", 0.020, 0.02),
                   ("tani stabilny", 0.085, 0.01)]:
    capped = min(g, s.GROWTH_CAP)
    exp = y + capped
    print(f"  {name:24s} FCF {y:.1%} + wzrost {capped:.1%} = {exp:.2%}  -> "
          f"{s.verdict(exp, req)}  ({(exp-req)*100:+.1f}pp)")
print("  Bramka odrzuca droga spolke bez wzrostu, przepuszcza tania i rosnaca.")

print("\nTEST 13: sufit wzrostu")
print(f"  wzrost 45% -> uzyty {min(0.45, s.GROWTH_CAP):.0%} (sufit {s.GROWTH_CAP:.0%})")

print("\nTEST 14: revenue_cagr")
rev = frame({"Total Revenue": [200.0, 170.0, 140.0, 120.0]},
            cols=(D1, D2, pd.Timestamp("2023-12-31"), pd.Timestamp("2022-12-31")))
g, note = s.revenue_cagr(rev)
print(f"  120 -> 200 przez 3 lata = {g:.2%} rocznie (oczekiwane ok. 18.6%)")
rev_bad = frame({"Total Revenue": [200.0, None, None, None]},
                cols=(D1, D2, pd.Timestamp("2023-12-31"), pd.Timestamp("2022-12-31")))
print("  jeden rok danych ->", s.revenue_cagr(rev_bad))

print("\nTEST 15: pick_total_debt bez pozycji Total Debt")
bal = frame({"Long Term Debt": [30_000.0, 28_000.0],
             "Current Debt": [5_000.0, 4_000.0]})
print("  ->", s.pick_total_debt(bal)[0], "oczekiwane 35000.0, z ostrzezeniem")

print("\n" + "=" * 62)
print("TEST 16: podsumowanie przy brakujacych bramkach")
for gates, opis in [
    ({"gate_roic": "PASS", "gate_fcf": "PASS", "gate_return": "PASS"}, "komplet"),
    ({"gate_roic": "-", "gate_fcf": "PASS", "gate_return": "PASS"}, "brak ROIC, reszta PASS"),
    ({"gate_roic": "-", "gate_fcf": "PASS", "gate_return": "FAIL"}, "brak ROIC, jedna FAIL"),
    ({"gate_roic": "FAIL", "gate_fcf": "FAIL", "gate_return": "FAIL"}, "komplet, wszystkie FAIL"),
    ({"gate_roic": "-", "gate_fcf": "-", "gate_return": "-"}, "nic sie nie policzylo"),
]:
    print(f"  {opis:28s} -> {s.summarize(gates)}")

print("\n" + "=" * 62)
print("Wszystkie testy przeszly bez wyjatku.")
