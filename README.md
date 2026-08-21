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
10Y UST: 4.70%  +  premia za ryzyko 4.5%  =  stopa wymagana 9.20%
Prog ROIC: 15%   |   sufit wzrostu: 12%
Oczekiwany zwrot = rentownosc Real FCF + wzrost przychodow.
Real FCF w mln USD, dane roczne z ostatniego sprawozdania.

ticker  roic real_fcf_musd fcf_yield growth exp_return spread_pp gate_roic gate_fcf gate_return        summary
     F -4.1%        11,957    21.43%   5.8%     27.25%   +18.1pp      FAIL     PASS        PASS            2/3
    NU     -         2,888     4.21%  52.9%     16.21%    +7.0pp         -     PASS        PASS 2/2 (bez ROIC)
    MA 96.2%        15,836     3.15%  13.8%     15.15%    +6.0pp      PASS     PASS        PASS            3/3
  META 23.1%        25,682     1.85%  19.9%     13.85%    +4.7pp      PASS     PASS        PASS            3/3
 GOOGL 29.9%        48,313     1.16%  12.5%     13.16%    +4.0pp      PASS     PASS        PASS            3/3
  AMZN     -       -11,772    -0.42%  11.7%     11.31%    +2.1pp         -     FAIL        PASS 1/2 (bez ROIC)
   NUE  8.4%          -321    -0.59%  -7.8%     -8.43%   -17.6pp      FAIL     FAIL        FAIL            0/3

Ostrzezenia:
  [NU] niekompletne dane do ROIC; wzrost 53% przyciety do 12%; spolka finansowa - ROIC nieporownywalny
  [MA] wzrost 14% przyciety do 12%
  [META] wzrost 20% przyciety do 12%
  [GOOGL] wzrost 13% przyciety do 12%
  [AMZN] niekompletne dane do ROIC
```

Przebieg z 21 sierpnia 2026 r.

## Kalibracja progów

Pierwsza wersja bramki trzeciej odrzucała wszystkie spółki, druga przepuszczała wszystkie. Ani jedna, ani druga nie niosła informacji.

Trzy parametry decydują o tym, gdzie leży próg, i każdy jest wyborem, nie faktem: premia za ryzyko akcji (`EQUITY_RISK_PREMIUM`, domyślnie 4,5%), sufit wzrostu (`GROWTH_CAP`, domyślnie 12%) oraz próg ROIC (15%). Podniesienie premii lub obniżenie sufitu zaostrza kryterium.

Sensowna kalibracja polega na sprawdzeniu, czy narzędzie odrzuca to, co powinno odrzucić — stąd spółki spoza portfela na domyślnej liście.

Pierwszy przebieg pełnej listy dał dwa wnioski. Nucor wypadł na wszystkich trzech bramkach, co jest zachowaniem oczekiwanym dla hutnictwa po szczycie cyklu. Ford natomiast ujawnił wadę samego narzędzia: wypadł na ROIC, ale rentowność przepływów na poziomie 21,4% wypchnęła go na szczyt rankingu. Ta liczba jest artefaktem — przepływy operacyjne Forda zawierają działalność kredytową Ford Credit, więc nie odzwierciedlają gotówki generowanej przez produkcję samochodów.

**Znane ograniczenie do poprawy w kolejnej wersji:** sortowanie po nadwyżce powinno obejmować wyłącznie spółki, które przeszły komplet bramek. W obecnej wersji kolejność wierszy może wprowadzać w błąd i trzeba czytać kolumnę podsumowania.

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
