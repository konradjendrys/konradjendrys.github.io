# Quality Screener

Skrypt przepuszcza listę spółek przez trzy bramki jakości, których używam przy przeglądzie portfela. Nie służy do wyceny ani do podejmowania decyzji — służy do odsiania spółek, którym w ogóle nie warto poświęcać czasu.

## Co robi

Dla każdej spółki z listy pobiera roczne sprawozdania z Yahoo Finance i sprawdza trzy warunki:

**1. ROIC powyżej 15%**
Zwrot z zainwestowanego kapitału liczony jako NOPAT podzielony przez kapitał zainwestowany, gdzie kapitał zainwestowany to dług plus kapitał własny minus gotówka. Odpowiada na pytanie, czy biznes zarabia więcej, niż kosztuje go kapitał.

**2. Real FCF powyżej zera**
Przepływy operacyjne minus nakłady inwestycyjne minus wynagrodzenia w akcjach. Odjęcie SBC jest tu celowe: to realny koszt dla akcjonariusza, choć nie wypływa z rachunku bankowego. Spółka płacąca akcjami zamiast gotówką rozwadnia udział właścicieli, a klasyczny FCF tego nie pokazuje.

**3. Oczekiwana stopa zwrotu wyższa niż stopa wymagana**
Oczekiwany zwrot to rentowność Real FCF powiększona o wzrost, a stopa wymagana to rentowność dziesięcioletnich obligacji USA powiększona o premię za ryzyko akcji.

Konstrukcja wynika z przekształcenia modelu Gordona. Skoro cena to przepływ podzielony przez różnicę stopy wymaganej i wzrostu, to po przekształceniu oczekiwany zwrot równa się rentowności przepływów plus ich wzrost.

Pierwsza wersja skryptu zestawiała samą rentowność Real FCF z rentownością obligacji. Pierwszy przebieg pokazał, że to porównanie jest nierówne: obligacja płaci stały kupon, a przepływy spółki rosną. Przy rentowności 10Y na poziomie 4,7% bramka odrzucała wszystkie pięć spółek z portfela, łącznie z Mastercardem przy ROIC 96%. Żeby Meta ją przeszła, musiałaby stanieć o około 60%. Bramka, która odrzuca każdego, nie niesie informacji — tak samo jak bramka, która przepuszcza każdego.

Wynik to tabela z wartościami wskaźników, oceną każdej bramki i podsumowaniem w formie „ile z ilu". Mianownik to liczba bramek, które udało się policzyć — jeśli w sprawozdaniu zabrakło pozycji potrzebnej do ROIC, spółka dostaje wynik `2/2 (bez ROIC)` zamiast `brak danych`. Brak jednej liczby nie powinien unieważniać dwóch pozostałych. Spółki są posortowane według nadwyżki oczekiwanego zwrotu ponad stopę wymaganą, wyrażonej w punktach procentowych — ta liczba jest użyteczniejsza od samego PASS/FAIL, bo pozwala uszeregować spółki, które bramkę przeszły.

## Jak uruchomić

```bash
pip install yfinance pandas
python screener.py
```

Listę spółek zmienia się w stałej `TICKERS` na początku pliku, progi w stałych poniżej.

Domyślna lista zawiera spółki z mojego portfela oraz dwie spoza niego — Forda i Nucora. Są tam celowo: narzędzie, które przepuszcza wyłącznie to, co się już posiada, niczego nie weryfikuje. Motoryzacja i hutnictwo to biznesy kapitałochłonne i cykliczne, więc powinny wypaść inaczej niż spółki technologiczne — a jeśli nie wypadają, znaczy to, że progi są źle dobrane.

## Przykładowy wynik

```
10Y UST (^TNX): 4.20%  +  premia za ryzyko 4.5%  =  stopa wymagana 8.70%
Prog ROIC: 15%   |   sufit wzrostu: 12%
Oczekiwany zwrot = rentownosc Real FCF + wzrost przychodow (model Gordona).
Real FCF w mln USD, dane roczne z ostatniego dostepnego sprawozdania.

ticker  roic real_fcf_musd fcf_yield growth exp_return spread_pp gate_roic gate_fcf gate_return        summary
   AAA 25.0%        30,000     5.50%  18.0%     17.50%    +8.8pp      PASS     PASS        PASS            3/3
   BBB     -        18,400     2.10%  14.0%     14.10%    +5.4pp         -     PASS        PASS  2/2 (bez ROIC)
   CCC  8.0%        -1,200    -0.40%   3.0%      2.60%    -6.1pp      FAIL     FAIL        FAIL            0/3

Ostrzezenia:
  [BBB] niekompletne dane do ROIC
```

## Kalibracja progów

Pierwsza wersja bramki trzeciej odrzucała wszystkie spółki, druga przepuszczała wszystkie. Ani jedna, ani druga nie niosła informacji.

Trzy parametry decydują o tym, gdzie leży próg, i każdy jest wyborem, nie faktem: premia za ryzyko akcji (`EQUITY_RISK_PREMIUM`, domyślnie 4,5%), sufit wzrostu (`GROWTH_CAP`, domyślnie 12%) oraz próg ROIC (15%). Podniesienie premii lub obniżenie sufitu zaostrza kryterium.

Sensowna kalibracja polega na sprawdzeniu, czy narzędzie odrzuca to, co powinno odrzucić — stąd spółki spoza portfela na domyślnej liście.

## Ograniczenia, o których trzeba wiedzieć

To jest najważniejsza sekcja tego pliku.

**Dane są wtórne.** Yahoo Finance agreguje sprawozdania, ale robi to automatycznie i bywa, że pozycje są przypisane inaczej niż w oryginale. Przy każdej spółce, która realnie waży na decyzji, i tak trzeba otworzyć 10-K. Skaner zawęża listę, nie rozstrzyga.

**ROIC nie ma sensu dla spółek finansowych.** Dla banków i ubezpieczycieli dług jest surowcem, a nie finansowaniem, więc kapitał zainwestowany liczony w ten sposób nic nie znaczy. Skrypt takie spółki oznacza ostrzeżeniem, ale ich nie odrzuca — decyzja należy do czytającego.

**Klasyfikacja sektorowa Yahoo bywa myląca.** Mastercard i Visa figurują jako Financial Services, ale nie są pośrednikami kredytowymi — sieci płatnicze nie biorą ryzyka kredytowego i nie mają bilansu bankowego, więc ROIC ma dla nich pełny sens. Te dwa tickery są wyłączone z ostrzeżenia w stałej `NOT_REALLY_FINANCIALS`.

**Wzrost liczony jest z przychodów, nie z Real FCF.** Real FCF potrafi zmienić się o dziesiątki procent przy jednym cyklu inwestycyjnym, co zaburzyłoby całą bramkę. Podstawienie przychodu zakłada, że marże pozostają stabilne — założenie wygodne, ale nie zawsze prawdziwe.

**Wzrost historyczny nie jest prognozą.** Skrypt ekstrapoluje średni wzrost z ostatnich lat, co przy spółkach po silnym cyklu zawyża oczekiwania. Stąd sufit na poziomie 12% — nie po to, żeby był trafny, tylko żeby ograniczyć szkodę z ekstrapolacji. Spółki, którym wzrost przycięto, dostają ostrzeżenie.

**Premia za ryzyko jest arbitralna.** Przyjęte 4,5% to wartość zbliżona do historycznej premii dla rynku amerykańskiego, ale nie jest to liczba obiektywna. Zmiana tego parametru przesuwa wyniki wszystkich spółek naraz.

**Spółki z gotówką netto przewyższającą dług** dają ujemny kapitał zainwestowany. Wtedy ROIC jest pomijany zamiast pokazywać liczbę bez sensu.

**Efektywna stopa podatkowa bywa zaburzona.** Jednorazowe zdarzenia potrafią wypchnąć ją do kilkudziesięciu procent, co zaniżyłoby NOPAT. Skrypt przycina ją do 50%.

**Nazwy pozycji u Yahoo zmieniają się między wersjami biblioteki.** Stąd listy aliasów dla każdej pozycji — jeśli kolejna wersja wprowadzi nową nazwę, trzeba ją dopisać.

**Kontrola spójności okresów.** Yahoo potrafi mieć wypełniony rachunek przepływów za 2025 r., ale bilans tylko za 2024 r. Bez sprawdzenia można policzyć OCF z jednego roku minus CapEx z drugiego i nie zauważyć, bo wynik wygląda sensownie. Skrypt zbiera daty wszystkich użytych pozycji i ostrzega, gdy pochodzą z różnych lat.

**Brakujące pozycje są zastępowane zerem, ale z ostrzeżeniem.** Brak SBC zawyża Real FCF, brak gotówki zaniża ROIC. Ostrzeżenie mówi, w którą stronę wynik jest przesunięty.

## Struktura kodu

| Funkcja | Odpowiada za |
|---|---|
| `pick_value` | wyciągnięcie pozycji ze sprawozdania wraz z datą okresu |
| `pick_total_debt` | dług całkowity, a przy jego braku suma pozycji składowych |
| `revenue_cagr` | średni roczny wzrost przychodów z dostępnej historii |
| `get_bond_yield` | rentowność 10Y UST z ^TNX, z wartością zapasową przy braku połączenia |
| `screen_ticker` | policzenie trzech wskaźników dla jednej spółki |
| `verdict` | ocena PASS / FAIL / brak danych |
| `summarize` | podsumowanie liczone tylko z bramek, które dało się policzyć |
| `build_report` | złożenie tabeli zbiorczej |
| `print_report` | formatowanie wyniku i lista ostrzeżeń |

Żadna funkcja nie rzuca wyjątkiem przy niekompletnych danych — problemy trafiają do kolumny ostrzeżeń, więc jedna wadliwa spółka nie przerywa całego przeglądu.

## Testy

Plik `test_logic.py` sprawdza logikę na danych podstawionych ręcznie, bez łączenia się z siecią: wybór najnowszego okresu, obsługę zdublowanych wierszy, aliasy nazw, sufit podatkowy, pustą listę spółek i formatowanie raportu.

```bash
python test_logic.py
```
