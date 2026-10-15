# AIGlobe · AI Direction Globe

Czy AI idzie w stronę człowieka czy nieokiełznanej technologii?

- **Kula 1** – wektor na trzech osiach (K kontrola, U użycie, R rozkład korzyści) z ocenionych wydarzeń; okno 30 dni, proporcja (n₊ − n₋)/(n₊ + n₋).
- **Suwaki pod kulą 1** – G geopolityka (konfrontacja ↔ współpraca, ten sam wzór) i T tempo (przyspieszenie ↔ hamowanie, (n₊ − n₋)/n wszystkich zdarzeń w oknie).
- **Kula 2** – globus wydarzeń AI z wiadomości w 8 językach (EN, ZH, JA, KO, RU, ES, HI, AR), rama G20 + punkty krytyczne AI (TW, NL, IL, AE), kolor = kategoria.
- **Zakładka Markets** (`#markets`) – reżim rynku risk-on / risk-off z 6 wskaźników, globus G20 (ETF-y krajowe vs średnia 200-dniowa), ledger tematów z regułą wyjścia na złamaniu trendu względem S&P 500. Informacja, nie rekomendacja.

Statyczna strona (`index.html`), dane w `data/`:

| plik | zawartość |
|---|---|
| `data/events.json` | lista wydarzeń: `id, date, lang, place, lat, lon, title, summary, cat, k, u, r, g, t, src, srcName, added` |
| `data/archive.json` | compact rows `[date,k,u,r,g,t,lang,retro,region]` of every scored event, never pruned; feeds the 180d / 360d / 5y windows |
| `data/market/series.json` | wskaźniki rynku dzień po dniu od 2021-10: surowe wartości, wynik −1..+1 (percentyl w kroczącym oknie 5 lat), osie F/G/L, kompozyt, reżim, zmiany reżimu, SPY, migawka krajów G20 |
| `data/market/themes.json` | transakcje tematów: IN w dniu, gdy event był oczywisty, OUT na złamaniu trendu względem S&P 500 (zamknięcie następnego dnia), wynik obok S&P 500 z tych samych dni |
| `data/market/scanner.json` | skaner fal: 43 fundusze (sektory, tematy, surowce), stan dziś (new / in / exit / watch / out), transakcje z 5 lat i ich statystyka |
| `data/market/why.json` | ręczne etykiety przyczyn fal: `{ETF: {in, why, src, srcName}}`; pokazywane tylko, gdy `in` zgadza się z bieżącą transakcją |
| `data/snapshots.json` | jedna migawka dziennie: `date, k30, u30, r30, g30, t30, k7, u7, r7, g7, t7, n30, n7` |
| `data/status.json` | `updated, events, languages, lastRun` |

Kategorie: `incydent`, `bezpieczenstwo`, `badania`, `agenci`, `regulacje`, `gospodarka`.
Osie i suwaki: wartości −1 / 0 / +1; 0 = nie dotyczy. −1 zawsze po stronie technologii, +1 po stronie człowieka.

Cotygodniowe zadanie (Claude scheduled task, środa 07:07 London) dopisuje nowe wydarzenia do `events.json` (okno 180 dni) i `archive.json` (bez limitu), przelicza migawkę i pushuje do `main`; Vercel publikuje automatycznie.

Zasady punktacji i neutralności: `RUBRIC.md` (reguła lustra, G tylko dla państw, limit 40% na język).
Retro: `data/retro/YYYY-MM.json` (pełne rekordy do audytu), archiwum przebudowuje `python3 scripts/build_archive.py`.

Rynki: `scripts/fetch_market.py` uruchamia GitHub Action `market` (dni robocze 22:17 UTC, po zamknięciu USA, lub ręcznie z zakładki Actions). Źródła: FRED (VIXCLS, BAA10Y, T10Y2Y, RMFSL) i Yahoo Finance (ETF-y krajowe G20, miedź, złoto, ETF-y tematów). Wskaźnik, którego źródło przestało się aktualizować, jest pomijany, nie przeciągany. Daty tematów w `THEMES` to ocena człowieka, do edycji.
