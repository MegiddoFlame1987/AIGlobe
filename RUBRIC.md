# AIGlobe scoring rubric

Single source of truth for every scorer: the weekly news task and the retro backfill.
All event text on the site is in English.

## 0. Neutrality rules (apply before anything else)

1. **Mirror rule.** Before saving a score, swap the actor for another country or bloc
   (USA, EU, China, Russia, India, Gulf states, anyone). If the score would change, the score is wrong.
   The same act gets the same score whoever does it.
2. **Score the act, not the actor.** Nationality never adds or removes a point.
   No country or bloc is the default good side or the default bad side.
3. **Attribute claims.** If only one party says something happened, the title says so
   ("OpenAI says…", "Xinhua reports…", "Russian ministry claims…"). Do not state a one-sided accusation as fact.
4. **State vs. individual.** An act by a company or an individual is not a state act. G applies to
   states, state agencies and state-directed actors only, plus cross-border acts that exist because of a
   state measure (e.g. smuggling around an export control).
5. **No loaded words.** Use neutral verbs (restricts, blocks, accuses, releases). No "regime", "rogue",
   "aggressive", "leading democracy" and similar framing unless quoted and attributed.
6. **Source balance.** The sampling frame is the **G20** (19 states + EU + African Union) plus four
   **AI chokepoints** outside it: Taiwan, Netherlands, Israel, UAE (chips, lithography, compute capital).
   Not the G7: that is one bloc. Search in **eight languages**: EN, ZH, JA, KO, RU, ES, HI, AR.
   Two caps per run: no single **language** above 40% of events, and no single **actor country** above 40%,
   whenever other languages or countries have significant events. Significance comes first: if a country
   has no significant events, report the gap instead of filling it with minor ones.
   Prefer the original-language source over an English rewrite of it.

## 1. Measures

Each event gets five scores from {-1, 0, +1}. 0 means "does not apply".
-1 always points to the technology side, +1 to the human side.

| | Measure | -1 | +1 |
|---|---|---|---|
| K | Control: do people still understand and steer the systems? | agents acting out of scope, sandbox escapes, deception or test/production divergence in evals, unexpected capabilities, safety teams or commitments dismantled, guardrails removed | interpretability, published evals, external audits, kill switches, safety standards and requirements, rollout halted after a problem, oversight regulation |
| U | Use: what people do with AI | cyberattacks, fraud, deepfakes, data theft, bio/chem uplift, autonomous weapons, surveillance, disinformation | defence, vulnerability patching, fraud detection, results in medicine, science, education, energy |
| R | Reward distribution: who benefits | concentration of capital and power (megarounds, acquisitions, trillion-dollar valuations), layoffs without a safety net, access only for the rich or the state, political capture of the topic | open access (free models, open weights, open standards), public funding of science, benefits in health and education beyond rich countries, citizen participation |
| G | Geopolitics: the field the race runs in (states only, see rule 0.4) | export controls, chip smuggling, acquisitions or investments blocked on national-security grounds, military AI, state propaganda or deepfakes, state-linked cyber operations, self-sufficiency measures explicitly framed against a named rival | treaties, UN resolutions, joint safety institutes, dialogue between rival states or blocs, shared standards across blocs |
| T | Pace: how hard the race is pushing | frontier model releases, new chip generations or supercomputers, deals and rounds of USD 1bn+, data-centre build-outs, large compute pledges, releases without safeguards | pauses, withheld or withdrawn releases, cancelled investments, IPOs or data centres, refusal to deploy agents over risk, slowdown after public backlash |

Ordinary industrial policy with no named rival is G 0. Research without a capability jump is T 0.

## 2. Aggregation (computed by code, not by the scorer)

- K, U, R, G over a window: `(n_plus - n_minus) / (n_plus + n_minus)`, 0 if both are 0.
- T over a window: `(n_plus - n_minus) / n_all_events_in_window` (acceleration news dominates, so a plain ratio would saturate).

## 3. Event record

```json
{"id": "YYYY-MM-DD-short-slug", "date": "YYYY-MM-DD", "lang": "en|zh|ja|ko|ru|es|hi|ar",
 "place": "City, Country", "lat": 0.0, "lon": 0.0,
 "title": "specific, attributed, max 160 chars", "summary": "one factual sentence",
 "cat": "incident|safety|research|agents|policy|economy",
 "k": 0, "u": 0, "r": 0, "g": 0, "t": 0,
 "src": "https://…", "srcName": "…", "added": "ISO-8601 UTC"}
```

`lang` is the language of the source used. `place` is the main actor's base or where the event happened;
skip events with no place. Categories: incident (breach, escape, misuse, failure), safety (actions and
statements for safety), research (science, benchmarks, breakthroughs), agents (models, products, agents),
policy (law, government, standards, polls, geopolitics), economy (money, rounds, jobs, chips, data centres).

## 4. Files

- `data/events.json`: full records, last 180 days (globe and list).
- `data/archive.json`: compact rows `[date, k, u, r, g, t, lang, retro, region]`, never pruned (all windows).
  `retro` is 1 for backfilled history, 0 for live weekly runs. `region` is derived from `place` by
  `scripts/build_archive.py`: us, cn, eu, g20 (other G20 incl. African Union), choke (TW, NL, IL, AE), other.
  Always rebuild the archive with that script; never hand-edit it.
- `data/retro/YYYY-MM.json`: full records of backfilled months, kept for audit.
- `data/snapshots.json`, `data/status.json`: run metadata.
