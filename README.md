# AIGlobe · AI Direction Globe

Czy AI idzie w stronę człowieka czy nieokiełznanej technologii?

- **Kula 1** – wektor na trzech osiach (K kontrola, U użycie, R rozkład korzyści) z ocenionych wydarzeń; okno 30 dni, proporcja (n₊ − n₋)/(n₊ + n₋).
- **Suwaki pod kulą 1** – G geopolityka (konfrontacja ↔ współpraca, ten sam wzór) i T tempo (przyspieszenie ↔ hamowanie, (n₊ − n₋)/n wszystkich zdarzeń w oknie).
- **Kula 2** – globus wydarzeń AI z wiadomości w 5 językach (EN, ZH, ES, RU, HI), kolor = kategoria.

Statyczna strona (`index.html`), dane w `data/`:

| plik | zawartość |
|---|---|
| `data/events.json` | lista wydarzeń: `id, date, lang, place, lat, lon, title, summary, cat, k, u, r, g, t, src, srcName, added` |
| `data/archive.json` | compact rows `[date,k,u,r,g,t]` of every scored event, never pruned; feeds the 180d / 360d / 5y windows |
| `data/snapshots.json` | jedna migawka dziennie: `date, k30, u30, r30, g30, t30, k7, u7, r7, g7, t7, n30, n7` |
| `data/status.json` | `updated, events, languages, lastRun` |

Kategorie: `incydent`, `bezpieczenstwo`, `badania`, `agenci`, `regulacje`, `gospodarka`.
Osie i suwaki: wartości −1 / 0 / +1; 0 = nie dotyczy. −1 zawsze po stronie technologii, +1 po stronie człowieka.

Cotygodniowe zadanie (Claude scheduled task, środa 07:07 London) dopisuje nowe wydarzenia do `events.json` (okno 180 dni) i `archive.json` (bez limitu), przelicza migawkę i pushuje do `main`; Vercel publikuje automatycznie.

Zasady punktacji i neutralności: `RUBRIC.md` (reguła lustra, G tylko dla państw, limit 40% na język).
Retro: `data/retro/YYYY-MM.json` (pełne rekordy do audytu), archiwum przebudowuje `python3 scripts/build_archive.py`.
