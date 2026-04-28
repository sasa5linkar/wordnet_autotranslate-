# Workflow evaluation: first 25 synsets

## Why the first report was too thin

`REPORT.md` showed only each workflow's representative `translation`. That made it useful as a quick run summary, but not useful enough for evaluating translation quality because it hid each workflow's full `translated_synonyms` list. The full lists were present in `results.json`; this report exposes and compares them.

## Evaluation basis

- Source: `results.json`
- Rows: first 25 NLTK WordNet synsets sorted by `synset.name()`
- Workflows compared: `agent-baseline`, `agent-multiphase`, `agent-conceptual`
- Ollama/backend use: none
- Criteria: literal coverage, sense fidelity, natural Serbian, POS fit, gloss quality, curator risk

## Aggregate literal coverage

| Workflow | Total literals | Avg literals / synset | Single-literal rows | Confidence profile |
|---|---:|---:|---:|---|
| `agent-baseline` | 33 | 1.32 | 18/25 | 8 high, 17 medium |
| `agent-multiphase` | 56 | 2.24 | 0/25 | 21 high, 4 medium |
| `agent-conceptual` | 35 | 1.40 | 18/25 | 21 high, 4 medium |

## Full literal comparison

| # | Synset | Baseline literals | Multiphase literals | Conceptual literals |
|---:|---|---|---|---|
| 1 | `'hood.n.01` | kraj | kvart; kraj; komsiluk | kraj; kvart |
| 2 | `.22_caliber.a.01` | kalibra .22; .22-kalibarski | kalibra .22; kalibra 0,22 inca | kalibra .22 |
| 3 | `.38_caliber.a.01` | kalibra .38; .38-kalibarski | kalibra .38; kalibra 0,38 inca | kalibra .38 |
| 4 | `.45_caliber.a.01` | kalibra .45; .45-kalibarski | kalibra .45; kalibra 0,45 inca | kalibra .45 |
| 5 | `1530s.n.01` | 1530-e | tridesete godine 16. veka; 1530-e | tridesete godine 16. veka |
| 6 | `15_may_organization.n.01` | Organizacija 15. maj | Organizacija 15. maj; 15. maj | Organizacija 15. maj |
| 7 | `1750s.n.01` | 1750-e | pedesete godine 18. veka; 1750-e | pedesete godine 18. veka |
| 8 | `1760s.n.01` | 1760-e | sezdesete godine 18. veka; 1760-e | sezdesete godine 18. veka |
| 9 | `1770s.n.01` | 1770-e | sedamdesete godine 18. veka; 1770-e | sedamdesete godine 18. veka |
| 10 | `1780s.n.01` | 1780-e | osamdesete godine 18. veka; 1780-e | osamdesete godine 18. veka |
| 11 | `1790s.n.01` | 1790-e | devedesete godine 18. veka; 1790-e | devedesete godine 18. veka |
| 12 | `18-karat_gold.n.01` | 18-karatno zlato | osamnaestokaratno zlato; 18-karatno zlato | osamnaestokaratno zlato; 18-karatno zlato |
| 13 | `1820s.n.01` | 1820-e | dvadesete godine 19. veka; 1820-e | dvadesete godine 19. veka |
| 14 | `1830s.n.01` | 1830-e | tridesete godine 19. veka; 1830-e | tridesete godine 19. veka |
| 15 | `1840s.n.01` | 1840-e | cetrdesete godine 19. veka; 1840-e | cetrdesete godine 19. veka |
| 16 | `1850s.n.01` | 1850-e | pedesete godine 19. veka; 1850-e | pedesete godine 19. veka |
| 17 | `1860s.n.01` | 1860-e | sezdesete godine 19. veka; 1860-e | sezdesete godine 19. veka |
| 18 | `1870s.n.01` | 1870-e | sedamdesete godine 19. veka; 1870-e | sedamdesete godine 19. veka |
| 19 | `1900s.n.01` | 1900-e | prva decenija 20. veka; godine 1900-1909 | prva decenija 20. veka |
| 20 | `22-karat_gold.n.01` | 22-karatno zlato | dvadesetdvokaratno zlato; 22-karatno zlato | dvadesetdvokaratno zlato; 22-karatno zlato |
| 21 | `24-karat_gold.n.01` | 24-karatno zlato; cisto zlato | dvadesetcetvorokaratno zlato; 24-karatno zlato; cisto zlato | cisto zlato; dvadesetcetvorokaratno zlato; 24-karatno zlato |
| 22 | `24/7.n.01` | 24/7 | neprekidan rad; 24/7; stalna dostupnost | stalna dostupnost; neprekidan rad; 24/7 |
| 23 | `401-k_plan.n.01` | 401(k) plan; 401(k) | 401(k) penzioni plan; 401(k) plan stednje za penziju; 401(k) | 401(k) plan stednje za penziju; 401(k) penzioni plan |
| 24 | `9/11.n.01` | 11. septembar; 9/11; 9-11 | 11. septembar; 9/11; napadi 11. septembra | 11. septembar; napadi 11. septembra; 9/11 |
| 25 | `a'man.n.01` | Aman; A'man | Aman; A'man; izraelska vojna obavestajna sluzba | Aman |

## Per-row quality observations

| Rows | Pattern | Strongest workflow | Main issue |
|---|---|---|---|
| 1 | Slang neighborhood sense | `agent-multiphase` for coverage; `agent-conceptual` for cleaner filtering | `komsiluk` can mean people/neighbors, not only the place. |
| 2-4 | Caliber adjectives | `agent-multiphase` | Baseline adds `.xx-kalibarski`, which is understandable but less natural than `kalibra .xx`. Conceptual is clean but under-expanded. |
| 5, 7-11, 13-18 | Decades | `agent-multiphase` | Baseline numeric forms are too bare for Serbian. Conceptual gives the best natural form but omits useful numeric alternates. |
| 6 | Proper organization name | No clear winner | Multiphase adds `15. maj`, but that may be too abbreviated. Conceptual gloss is smoother but softens the source label `teroristicka`. |
| 12, 20-21 | Karat gold | `agent-multiphase` | Multiphase best preserves numeric and spelled forms. Conceptual chooses the most natural representative for `24-karat_gold` (`cisto zlato`). |
| 19 | `1900s` decade | `agent-multiphase` and `agent-conceptual` | Baseline `1900-e` is ambiguous; explicit `prva decenija 20. veka` is safer. |
| 22 | `24/7` uptime noun | `agent-multiphase` for candidate pool; `agent-conceptual` for final literal | Baseline preserves the label but does not expose enough concept-level Serbian alternatives. |
| 23 | US `401(k)` plan | `agent-multiphase` | All outputs need cultural/legal curation. Baseline is safest for preserving the term; multiphase gives the best Serbian explanation candidates. |
| 24 | `9/11` day/event | All acceptable, with curation | `napadi 11. septembra` is useful, but the source synset is the day, so the date should remain primary. |
| 25 | Israeli intelligence proper name | Baseline safest; conceptual cleanest | Multiphase descriptive literal is too broad as a synonym. Transliteration of `Aman` should be checked by curator. |

## Workflow strengths and weaknesses

### `agent-baseline`

Strengths:
- Conservative and easy to inspect.
- Usually preserves proper names and source literals without over-inventing.
- Good as a control workflow or minimum viable output.

Weaknesses:
- Too sparse for evaluation: 18 of 25 rows have only one literal.
- Often keeps compact numeric/borrowed forms where Serbian needs a natural phrase, especially decade synsets.
- Less useful for synonym discovery and curator choice because it rarely proposes alternates.

Best use:
- Regression/control baseline and quick sanity check, not final candidate generation.

### `agent-multiphase`

Strengths:
- Best candidate coverage: 56 literals total and no single-literal rows.
- Strongest for evaluation because it exposes alternatives: natural phrase plus numeric/proper-name variants.
- Usually catches sense risks and rejects overly broad candidates in notes.

Weaknesses:
- Can include borderline candidates that require curator filtering, such as `komsiluk`, `15. maj`, or `izraelska vojna obavestajna sluzba`.
- Sometimes favors candidate breadth over final-entry cleanliness.
- Needs a downstream selection step if the target format expects only tight synset literals.

Best use:
- Primary candidate-generation workflow for human evaluation.

### `agent-conceptual`

Strengths:
- Best gloss discipline and sense framing.
- Often chooses the most natural representative literal, for example `cisto zlato` and `stalna dostupnost`.
- Better than baseline at avoiding ambiguous literal-only renderings such as `1900-e`.

Weaknesses:
- Too sparse for evaluating synonym sets: 18 of 25 rows have only one literal.
- Sometimes omits useful alternates that should be available to curators.
- Can smooth or generalize source definitions, which is useful for readability but risky when the source label matters.

Best use:
- Final-entry gloss and representative literal selection after candidates are generated.

## Overall conclusion

For these 25 synsets, `agent-multiphase` is the strongest workflow for evaluation because it gives the richest candidate lists and keeps useful alternatives visible. `agent-conceptual` is strongest for final gloss quality and representative-literal choice, but it is not enough by itself for synonym-set evaluation. `agent-baseline` is useful as a conservative control, but it under-generates literals and should not be treated as the main evaluation output.

Recommended evaluation workflow:

1. Use `agent-multiphase` to generate the candidate pool.
2. Use `agent-conceptual` to judge representative literal and gloss.
3. Keep `agent-baseline` as a control column.
4. Have the curator mark each candidate as `accept`, `reject`, or `maybe`, especially for proper names, culture-specific financial terms, and event/day distinctions.
