# AIGlobe War tab: scoring rubric

Single source of truth for every scorer of `data/war/events.json`. All event text on the site is in English.
The tab measures **signals of war risk**, not guilt. It answers: are the main powers moving toward war or away
from it, in what they say and in what they do?

## 0. Neutrality rules (apply before anything else)

1. **Mirror rule.** Before saving a score, swap the actor for another bloc. If the score would change, it is wrong.
   A mobilisation, a strike, a threat or a ceasefire offer gets the same score whoever makes it.
2. **Score the signal, not the side.** -1 means "this raises the chance of a wider war", +1 means "this lowers it".
   A defensive step can still be -1 (a government telling citizens to prepare for war raises the perceived risk,
   whichever government says it). No actor is the default aggressor or the default peacemaker.
3. **Attribute every claim.** Statements and one-sided accusations are written as claims: "Kremlin says…",
   "NATO says…", "Xinhua reports…", "IRNA says…". Never state an accusation as fact unless both sides or an
   independent body confirm it.
4. **States and blocs only.** Score governments, militaries, heads of state, ministers, official spokespeople and
   bloc bodies (EU, NATO, Arab League, GCC, SCO). Not commentators, think tanks or opposition politicians.
5. **No loaded words.** Neutral verbs: strikes, deploys, warns, threatens, proposes, agrees. No "regime",
   "terrorist state", "aggressor", "puppet" unless quoted and attributed.
6. **Source balance.** For every actor use its own state or major domestic media AND at least one outside source.
   Languages: en, ru, uk, zh, ar, fa, fr, de, ja, hi. Caps per run: no language above 40% of events,
   no actor above 40%, whenever other actors have significant events. Significance first: report a gap rather
   than fill it with minor items. Encyclopedias and timelines (Wikipedia) are an index for finding events, not
   the source to cite: cite press, wire services or official pages, and keep Wikipedia below 40% of any batch.

## 1. Fields

| field | values | meaning |
|---|---|---|
| `actor` | `us`, `eu`, `ru`, `cn`, `il`, `ir`, `arab`, `tr`, `ua`, `tw`, `kp`, `kr`, `jp`, `in`, `pk`, `other` | the state or bloc that acted or spoke. `eu` = EU institutions, EU member states, UK, European NATO members and NATO itself. `arab` = Arab states, the Arab League and the GCC (Saudi Arabia, UAE, Qatar, Egypt, Yemen's government, Jordan, Iraq, Syria, Lebanon). `il` Israel, `ir` Iran, `tr` Türkiye, `ua` Ukraine, `tw` Taiwan, `kp` North Korea, `kr` South Korea, `jp` Japan, `in` India, `pk` Pakistan. `other` = everyone else (name the state in the title) |
| `kind` | `word`, `deed` | `word` = statement, threat, warning, offer, doctrine text. `deed` = something done: strike, mobilisation, deployment, exercise near a border, arms delivery, sanctions, blockade, ceasefire, talks held, prisoner exchange, troop withdrawal, treaty signed |
| `score` | -1, 0, +1 | -1 toward war, +1 away from war, 0 unclear |
| `front` | `ukraine`, `taiwan`, `korea`, `middle-east`, `south-asia`, `americas`, `other` | the flashpoint |

## 2. Scoring guide

| | -1 toward war | +1 away from war |
|---|---|---|
| word | threats, ultimatums, nuclear signalling, "prepare for war" warnings to the public, claims of imminent attack, refusal of talks | offers of talks or ceasefire, guarantees of non-attack, calls for restraint, acceptance of mediation |
| deed | strikes, incursions, mobilisation, large deployments or exercises near a rival, new long-range arms deliveries, blockades, cutting hotlines, new sanctions aimed at a rival | ceasefires, talks actually held, prisoner exchanges, troop pull-backs, arms-control steps, hotlines restored, sanctions lifted |

Routine events (scheduled exercises far from rivals, budget votes without new posture) are 0 or skipped.
One event = one actor. If two actors act (a strike and a retaliation), record two events.

**Standing deeds.** War does not stop being war between announcements. While a state keeps up an ongoing
military operation, blockade, occupation or campaign of strikes, record at least one dated deed for it in every
month it continues (a new strike, an extension, a confirmed continuation), so a party to an ongoing war cannot
look peaceful just because its latest news was a talk or an offer.

**Both directions for every actor.** Search each actor explicitly for escalation AND de-escalation in the window.
A window in which a party to an active war shows only peace signals means the search missed something: look again.

## 3. Aggregation (computed by the page)

- Per actor and kind over a window: `(n_plus - n_minus) / (n_plus + n_minus)`, shown as the share of signals away from war.
- Say-do gap per actor: words score minus deeds score.
- Global risk: all events, deeds counted twice and words once, because what is done moves risk more than what is said.

## 4. Event record

```json
{"id": "YYYY-MM-DD-short-slug", "date": "YYYY-MM-DD", "actor": "ru", "kind": "word", "score": 1,
 "front": "ukraine", "lang": "ru", "place": "City, Country", "lat": 0.0, "lon": 0.0,
 "title": "specific, attributed, max 160 chars", "summary": "one factual sentence",
 "src": "https://…", "srcName": "…", "added": "ISO-8601 UTC"}
```

`lang` is the language of the cited page. `place` is where the act happened or where the actor is based.

## 5. Files

- `data/war/events.json`: all records, never pruned. Backfilled history carries `"retro": true`.
- `scripts/merge_war.py`: validates batches and merges them (`--write`). Never hand-edit the data file.
