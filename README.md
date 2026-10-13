# AIGlobe · AI Direction Globe

Czy AI idzie w stronę człowieka czy nieokiełznanej technologii?

- **Kula 1** – wektor na trzech osiach (K kontrola, U użycie, R rozkład korzyści) z ocenionych wydarzeń; okno 30 dni, proporcja (n₊ − n₋)/(n₊ + n₋).
- **Kula 2** – globus wydarzeń AI z wiadomości w 5 językach (EN, ZH, ES, RU, HI), kolor = kategoria.

Statyczna strona (`index.html`), dane w `data/`:

| plik | zawartość |
|---|---|
| `data/events.json` | lista wydarzeń: `id, date, lang, place, lat, lon, title, summary, cat, k, u, r, src, srcName, added` |
| `data/snapshots.json` | jedna migawka dziennie: `date, k30, u30, r30, k7, u7, r7, n30, n7` |
| `data/status.json` | `updated, events, languages, lastRun` |

Kategorie: `incydent`, `bezpieczenstwo`, `badania`, `agenci`, `regulacje`, `gospodarka`.
Osie: wartości −1 / 0 / +1; 0 = oś nie dotyczy wydarzenia.

Codzienne zadanie (Claude scheduled task) dopisuje nowe wydarzenia, przelicza migawkę i pushuje do `main`; Vercel publikuje automatycznie.

Zasady punktacji: patrz sekcja „Metoda” na stronie.
