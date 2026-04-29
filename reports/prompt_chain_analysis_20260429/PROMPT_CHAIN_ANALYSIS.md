# Prompt Chain Analysis Report

Date: 2026-04-29  
Scope: repository prompt chains for Serbian WordNet translation: `baseline`, `langgraph`, and `conceptual`.  
Evidence reviewed: prompt source code plus first-five OpenAI result sets from `gpt-4o-mini` and `gpt-5.4-nano`.

## Executive summary

Yes, there are prompt-chain problems. The failures are not caused by one single bad prompt; they come from a combination of prompt design, missing deterministic quality gates, and one Windows logging/runtime weakness.

The core problem is that the prompts ask the models to generate or validate translations, but they do not enforce enough hard lexical constraints after generation. This allows:

- duplicate literals,
- wrong part-of-speech variants,
- descriptive phrases in synonym lists,
- overly broad representative literals,
- Croatian/Bosnian variants where Serbian standard is expected,
- taxonomy hallucinations,
- circular glosses,
- self-validation false positives.

The safest current interpretation is:

- `baseline` is useful as a simple candidate source, especially for transparent terms.
- `langgraph` is useful for exploration, but it over-generates and should not feed final literals without stricter filtering.
- `conceptual` has the best curator-facing structure, but its self-validation is not trustworthy enough for unattended import.

## Files reviewed

Prompt source:

- `src/wordnet_autotranslate/pipelines/translation_pipeline.py`
- `src/wordnet_autotranslate/pipelines/langgraph_translation_pipeline.py`
- `src/wordnet_autotranslate/pipelines/conceptual_langgraph_pipeline.py`

Result evidence:

- `reports/openai_first5_smoke_20260429/final_results/all_final_results.json`
- `reports/openai_first5_smoke_20260429/complete_logs/all_complete_logs.json`
- `reports/openai_gpt54nano_first5_smoke_20260429/final_results/all_final_results.json`
- `reports/openai_gpt54nano_first5_smoke_20260429/complete_logs/all_complete_logs.json`

## Observed result symptoms

| Symptom | Evidence | Likely cause |
|---|---|---|
| Duplicated literals | `expectorate.v.02` baseline produced repeated `ispljunuti` / `iskašljati` variants. | Baseline prompt asks for translated literals but does not require deduplication or canonical representative selection. |
| Wrong or weak taxonomy terms | `cirripedia.n.01` produced `bubice`, `jastučići`, `barnakl`, `barnakli`. | Prompts do not require external taxonomy verification; self-validation accepts unsupported terms. |
| False-ready validation | `gpt-4o-mini` conceptual marked `jastučići` for `Cirripedia` as ready. | Same-model validation plus validation prompt schema bias and no deterministic domain gate. |
| Over-generation | `gpt-5.4-nano` LangGraph generated 16 candidates for `expectorate`, 18+ for `even`, 16+ for `physical_entity`. | Expansion prompt invites broad synonym generation and iterative self-expansion. |
| Wrong POS variants retained | Verb synset `expectorate.v.02` retained noun forms such as `iskašljavanje`; abstract noun synset produced phrases like `fizičko postojanje`. | Filtering prompt permits derivational variants and lacks a hard POS constraint. |
| Context-bound function-word variants | `even.r.01` conceptual selected `čak i`, `čak ni`, `čak da` in `gpt-5.4-nano`. | No special prompt rule for particles/adverbs separating stable literals from constructional variants. |
| Croatian/Bosnian form leakage | `metatheria.n.01` conceptual used `sisavci` in `gpt-4o-mini`. | Serbian prompt rules say standard Serbian, but do not include known high-risk variants like `sisavci` vs `sisari`. |
| Circular glosses | `gpt-5.4-nano` conceptual for `expectorate` selected `iskašljati` and wrote a gloss starting with `iskašljati`. | Final gloss prompt says non-circular but does not explicitly ban selected Serbian literals and stems in the gloss. |
| Windows encoding failure risk | One `gpt-5.4-nano` LangGraph row failed with a `charmap` encoding error before rerun. | Debug `print()` of Unicode candidate lists can fail under Windows console encodings. This is runtime/logging, not translation quality. |

## Chain 1: Baseline prompt

### Current behavior

The baseline prompt asks the model to translate only the provided English gloss and literals and return:

- `definition_translation`
- `translated_synonyms`
- optional `notes`

### What is wrong

1. **No deduplication instruction**  
   The prompt asks for translated literals in source-lemma order. If several English lemmas map to the same Serbian verb, duplicates are expected.

2. **No POS, lexname, examples, or relation context in prompt**  
   The baseline chain ignores information already available in the enriched work items. For ambiguous or taxonomic entries, gloss + literals alone are often insufficient.

3. **No uncertainty/confidence field**  
   The model has no structured way to say “no safe Serbian lexicalized equivalent found.” This encourages plausible but unsafe translations.

4. **No Serbian domain/style traps**  
   It does not explicitly warn about high-risk Serbian variants such as `sisavci` vs `sisari`, `podklasa` vs `potklasa`, or Latin taxonomy retention.

5. **No final-literal constraints**  
   It does not say whether descriptive phrases, multiword constructions, or transliterated Latin names are allowed as literals.

### Prompt-level fix

Baseline should require:

- deduplicated literals,
- maximum 1-3 canonical Serbian literals,
- same POS as source,
- no descriptive phrases unless no lexicalized term exists,
- explicit `confidence`, `uncertainty_notes`, and `needs_domain_check`,
- `null` or empty literal list when no safe literal exists.

## Chain 2: LangGraph generate/filter prompt chain

### Current stages

1. sense analysis
2. definition translation
3. initial lemma translation
4. synonym expansion
5. synonym filtering
6. definition quality review
7. result assembly

### What is wrong

1. **Expansion is too permissive**  
   The expansion prompt says to generate new synonyms that express the concept, but it does not cap count tightly or forbid derivational POS drift. This caused large lists for `expectorate`, `even`, and `physical_entity`.

2. **Filtering contradicts itself**  
   The filtering prompt says to remove overly generic or shifted expressions, but it also says to keep aspectual or derivational variants and normal lexical polysemy. That makes the filter too permissive.

3. **No hard POS invariant**  
   A verb synset should not retain a noun such as `iskašljavanje` as a literal unless explicitly converting to a noun synset. A noun synset should not select a phrase like `fizičko postojanje` as the representative literal for `physical_entity.n.01`.

4. **Representative literal is just first filtered item**  
   The code picks the first filtered synonym as `translation`. If filtering order is poor, the representative becomes poor (`baš`, `fizičko postojanje`, `cirripedia`).

5. **Definition quality does not validate the literal set**  
   The final quality stage checks the Serbian definition but not whether final literals are valid synonyms with correct POS/domain/register.

6. **Prompt formatting has a small indentation defect**  
   The target-language rules are inserted with excessive indentation in the filtering and definition-quality prompts. This is not the main cause of bad outputs, but it makes the prompt less clean.

7. **Iterative expansion amplifies earlier mistakes**  
   Once a bad candidate enters the expansion list, later iterations can create variants around it. This happened with function-word variants and broad abstract terms.

### Prompt-level fix

LangGraph should be changed from “generate many and filter loosely” to “generate few and filter strictly”:

- cap expansion to 5-8 candidates,
- forbid wrong POS and derivational category drift,
- reject descriptive phrases by default,
- separate `candidate_literals` from `candidate_explanatory_phrases`,
- rank candidates and choose representative by score, not list order,
- add a final literal-set validator after definition quality,
- make definition-quality review also check selected literal compatibility.

## Chain 3: Conceptual prompt chain

### Current stages

1. concept package
2. expanded English definition
3. expanded Serbian definition
4. literal candidates
5. literal selection
6. final gloss
7. validation
8. assembly

### What is good

This is the best chain design for curator-facing output. It separates concept understanding, candidate generation, selection, gloss writing, and validation. It also gives rejected literals and validation issues, which are useful for review.

### What is wrong

1. **Self-validation is unreliable**  
   The same model that generated a bad taxonomy literal can also validate it. This is why `jastučići` for `Cirripedia` was marked ready by `gpt-4o-mini`.

2. **Validation prompt is biased toward passing**  
   The requested JSON example uses `validation_passed: true` and `final_synset_ready: true`. For safety, validation prompts should bias toward failure unless all checks clearly pass.

3. **Final gloss prompt does not explicitly ban selected Serbian literals**  
   It says non-circular, but it should explicitly say: do not use selected literals, inflected forms, or close derivations in the final gloss.

4. **Taxonomy needs external verification**  
   The concept package includes domain/relation data, but the prompt still lets the model invent or assert Serbian biological terms. For taxonomy (`noun.animal`, Latin class/subclass names), the model should prefer Latin retention or mark domain check unless a known Serbian term is verified.

5. **Relation literals are weakly populated**  
   Relation entries include synset names and glosses, but the related literal arrays are often empty. This deprives the model of useful lexical anchors from hypernyms, meronyms, and holonyms.

6. **No special function-word policy**  
   For `even.r.01`, constructional variants like `čak i`, `čak ni`, and `čak da` should be notes/examples, not all accepted as synset literals.

### Prompt-level fix

Conceptual should keep its structure but add:

- validation default: fail unless proven safe,
- explicit selected-literal/stem blocklist in final gloss,
- taxonomy-specific no-invention rule,
- separate external/deterministic validator,
- function-word rules for particles/adverbs,
- stronger Serbian standard rules and high-risk variant list.

## Highest-priority deterministic gates

Prompts alone will not solve this. Add deterministic checks before any final import:

1. `duplicate_literal` — any repeated literal in a pipeline output.
2. `literal_in_gloss` — selected literal or stem appears in final gloss.
3. `wrong_pos_risk` — verb synset has noun candidates; adverb synset has clausal constructions; noun synset has event/state phrases.
4. `descriptive_phrase_literal` — literal contains typical objects or explanatory phrases.
5. `serbian_variant_risk` — terms like `sisavci`, `podklasa`, mixed Cyrillic/Latin, or nonstandard morphology.
6. `taxonomy_domain_check` — lexname `noun.animal` plus Latin taxonomy/source gloss too short requires manual/domain verification.
7. `broad_literal_risk` — abstract broad words such as `stvar`, `objekat`, `postojanje` selected for more specific synsets.
8. `model_disagreement` — models disagree on the representative literal or readiness.
9. `self_validation_only` — final readiness comes only from the same model that generated the output.
10. `windows_log_encoding_risk` — avoid direct Unicode debug prints in worker paths.

## Recommended prompt edits by priority

### Priority 1

- Add “same POS only” to every literal generation and filtering stage.
- Add “final gloss must not contain selected literals or close derivations.”
- Change validation examples from `true` to neutral placeholders or explicit default-false wording.
- Add taxonomy rule: “do not invent Serbian common names; if uncertain, retain Latin term and set `needs_domain_check=true`.”
- Add final schema fields: `confidence`, `quality_flags`, `needs_human_review`, `needs_domain_check`.

### Priority 2

- Reduce LangGraph expansion iterations or candidate caps.
- Add candidate scoring and choose representative by score.
- Add Serbian high-risk variant list (`sisavci` -> prefer `sisari`; `podklasa` -> prefer `potklasa`; avoid mixed Cyrillic/Latin).
- Add special prompt branch for function words, particles, and adverbs.

### Priority 3

- Improve relation payload literals by extracting readable lemmas from relation names.
- Split final outputs into `accepted_literals`, `candidate_literals`, and `notes_examples`.
- Use `gpt-5.4-nano` or another stricter model as a second-pass validator, not as the only generator.

## Batch-readiness conclusion

The prompts are good enough for pilot generation and comparison, but not good enough for unattended full-batch import.

The next safe engineering step is not to run more rows immediately. The next step should be to add deterministic quality gates and adjust the prompt rules above, then rerun a 10-20 row pilot and compare failure rates.

## Short answer

Yes: the prompt chains have real weaknesses. The biggest issue is not JSON formatting or model access; it is that the prompts ask the model to self-police lexicographic quality without enough hard constraints. Add deterministic gates plus stricter POS, circularity, taxonomy, Serbian-standard, and function-word rules before starting a large batch.