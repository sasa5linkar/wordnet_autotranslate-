# GPT-5.5 low vs GPT-5.4-nano first-five comparison

## Run labels

- New run: provider `openai`, model `gpt-5.5`, reasoning `low`.
- Reference run: provider `openai`, model `gpt-5.4-nano`.
- Scope: first 5 rows from `Literali počinju sa ? u srpskom`.

## Aggregate literal-count comparison

| Pipeline | Nano literals | GPT-5.5 literals | Delta | Added by GPT-5.5 | Removed from Nano |
|---|---:|---:|---:|---:|---:|
| baseline | 12 | 13 | +1 | 4 | 3 |
| langgraph | 13 | 22 | +9 | 16 | 7 |
| conceptual | 7 | 13 | +6 | 7 | 1 |

## Main gains

- Function-word precision improved: even.r.01 no longer carries wrong/contextual variants like ipak and nipošto.
- Calque reduction improved: so_far.r.01 no longer suggests tako daleko.
- Script consistency improved: ultimately.r.01 LangGraph output is Serbian Latin instead of mixed Cyrillic/Latin.
- Recall improved strongly in LangGraph and conceptual outputs, especially expectorate.v.02 and musical_performance.n.01.
- Conceptual glosses are generally shorter and more WordNet-like, especially for expectorate.v.02.

## Main risks / curator notes

- 5.5 is broader; this is useful for review but can include trim candidates such as hraknuti/hrakati or muzički nastup.
- For so_far.r.01, Serbian adverbs are context-sensitive in negative clauses; curator should keep the stable literals and maybe note usage constraints.
- Baseline changes are smaller because baseline is intentionally simple.

## Row-by-row judgment

| Row | Synset | Gain with GPT-5.5 low | Review risk |
|---:|---|---|---|
| 2 | ENG30-00006238-v / expectorate.v.02 | Better lexical precision for expectorating: removes broad spit-only variants from LangGraph, adds useful medical/colloquial Serbian candidates, and conceptual output becomes concise while preserving the secretion-from-lungs sense. | LangGraph is now broader and includes colloquial hraknuti/hrakati plus medical ekspektorisati; good for review, but curator may trim register-specific items. |
| 3 | ENG30-00017445-r / even.r.01 | Clear gain: keeps the stable adverb čak and drops Nano wrong/context-bound LangGraph variants ipak and nipošto. | No major risk; this is cleaner and easier to approve. |
| 4 | ENG30-00027918-r / so_far.r.01 | Clearer Serbian adverb set: removes Nano calque tako daleko, adds dosad/do sada/još/zasad, and conceptual recall improves from one literal to three. | LangGraph gloss is a little terse/awkward; final curator choice should separate negative-statement use of još from general dosad/zasad. |
| 5 | ENG30-00047903-r / ultimately.r.01 | Improved script consistency and lexical coverage: 5.5 keeps Serbian Latin throughout and gives a richer but still focused set of adverbs. | Some variants overlap stylistically; curator can reduce redundancy. |
| 6 | ENG30-00100253-n / musical_performance.n.01 | Large recall gain for musical performance: 5.5 adds muzičko izvođenje, izvođenje muzike, muziciranje, muzička interpretacija, and muzički nastup instead of one or two literals. | muzički nastup may be slightly broader/event-like; should be reviewed, but breadth is useful for annotation. |

## Detailed literal deltas

### 2 - ENG30-00006238-v / expectorate.v.02

- **baseline**
  - Nano: iskašljati; ispljunuti
  - GPT-5.5 low: iskašljati; ispljunuti
  - Added: (none)
  - Removed: (none)
- **langgraph**
  - Nano: iskašljati; ispljunuti; iskašljavati; ispljuvati
  - GPT-5.5 low: iskašljati; iskašljavati; ekspektorisati; odhraknuti; odhrakivati; hraknuti; hrakati
  - Added: ekspektorisati; odhraknuti; odhrakivati; hraknuti; hrakati
  - Removed: ispljunuti; ispljuvati
- **conceptual**
  - Nano: iskašljati
  - GPT-5.5 low: iskašljati; iskašljavati; ekspektorisati
  - Added: iskašljavati; ekspektorisati
  - Removed: (none)

### 3 - ENG30-00017445-r / even.r.01

- **baseline**
  - Nano: čak
  - GPT-5.5 low: čak
  - Added: (none)
  - Removed: (none)
- **langgraph**
  - Nano: čak; ipak; nipošto
  - GPT-5.5 low: čak
  - Added: (none)
  - Removed: ipak; nipošto
- **conceptual**
  - Nano: čak
  - GPT-5.5 low: čak
  - Added: (none)
  - Removed: (none)

### 4 - ENG30-00027918-r / so_far.r.01

- **baseline**
  - Nano: do sada; tako daleko; još
  - GPT-5.5 low: dosad; do sada; još uvek; još
  - Added: dosad; još uvek
  - Removed: tako daleko
- **langgraph**
  - Nano: dosad; dotad
  - GPT-5.5 low: dosad; još; zasad
  - Added: još; zasad
  - Removed: dotad
- **conceptual**
  - Nano: još
  - GPT-5.5 low: dosad; još; zasad
  - Added: dosad; zasad
  - Removed: (none)

### 5 - ENG30-00047903-r / ultimately.r.01

- **baseline**
  - Nano: konačno; najzad; na kraju; naposletku; najzad, napokon
  - GPT-5.5 low: naposletku; konačno; na kraju; najzad; napokon
  - Added: napokon
  - Removed: najzad, napokon
- **langgraph**
  - Nano: konačno; најзад; најпосле
  - GPT-5.5 low: naposletku; konačno; najzad; napokon; najposle
  - Added: naposletku; najzad; napokon; najposle
  - Removed: најзад; најпосле
- **conceptual**
  - Nano: konačno; naposletku
  - GPT-5.5 low: konačno; napokon; najzad
  - Added: napokon; najzad
  - Removed: naposletku

### 6 - ENG30-00100253-n / musical_performance.n.01

- **baseline**
  - Nano: muzička izvedba
  - GPT-5.5 low: muzičko izvođenje
  - Added: muzičko izvođenje
  - Removed: muzička izvedba
- **langgraph**
  - Nano: muzička izvedba
  - GPT-5.5 low: muzičko izvođenje; muzička izvedba; muzički nastup; izvođenje muzike; muziciranje; muzička interpretacija
  - Added: muzičko izvođenje; muzički nastup; izvođenje muzike; muziciranje; muzička interpretacija
  - Removed: (none)
- **conceptual**
  - Nano: muzičko izvođenje; izvođenje muzike
  - GPT-5.5 low: muzičko izvođenje; izvođenje muzike; muziciranje
  - Added: muziciranje
  - Removed: (none)
