# POS-aware Serbian definition structure correction suggestions

## Context

The requested correction is to make Serbian WordNet output structurally agree with the source synset POS:

- Adjective literals should remain adjectival, and the Serbian gloss should usually begin with an adjectival relative pattern such as `koji ...`, `koja ...`, `koje ...`, or `koji se ...`.
  - Example: `prijatan; ljubazan`
  - Gloss pattern: `koji je dopadljiv; odgovarajuci`
- Verb literals should remain verbs, usually infinitives, and the Serbian gloss should describe an action/process with a verbal phrase.
  - Example: `nauciti; saznati; saznavati; studirati; uciti`
  - Gloss pattern: `sticati znanja ili vestine`
- Noun literals should remain nouns, usually nominative singular, and the Serbian gloss should usually start from a broader noun/hypernym plus narrowing details.
  - Example: `djak; ucenik`
  - Gloss pattern: `polaznik koji se upisao u neku obrazovnu instituciju`

This should be added as a lexicographic quality constraint, not as a mechanical rewrite rule. WordNet glosses sometimes need exceptions: relational adjectives, participles, proper noun synsets, mass nouns, plural-only nouns, support-verb constructions, and Serbian definitions that are more natural without the most common pattern.

## Main recommendation

Add a shared "POS-aware Serbian WordNet style" rule to prompt text and add a final validation/check stage that can flag or revise mismatches. Do not rely only on the initial definition prompt, because the best definition form depends on the selected Serbian literals and may need to avoid circularity after filtering.

The strongest implementation would have three layers:

1. Prompt guidance during definition drafting.
2. Prompt guidance during final definition/gloss review.
3. Optional deterministic lint after model output, with warnings rather than automatic hard failure.

## POS source

The expected grammatical category should be read from the resolved English synset payload, usually `synset["pos"]` or `synset.get("pos")`.

The source and target POS should normally match conceptually:

```text
n -> Serbian noun literals and noun-style gloss
v -> Serbian verb literals and verb/action-style gloss
a/s -> Serbian adjective literals and adjective-style gloss
r -> Serbian adverb literals and adverbial gloss
```

Repository nuance:

- Princeton/English WordNet uses `r` for adverbs.
- Serbian WordNet XML uses `b` for adverbs.
- The repo already normalizes this in `LanguageUtils.normalize_pos_for_english()` and `LanguageUtils.normalize_pos_for_serbian()`.

So the prompt/check logic should treat `r` and Serbian XML `b` as the same adverb category after normalization.

Important distinction:

- The English synset POS tells the pipeline what Serbian POS is expected.
- It does not prove that the generated Serbian literal has that POS.
- Filtering and validation should still check the produced Serbian literals and gloss shape.

## Suggested shared prompt block

The full block below is useful as a design reference, but it should not usually be pasted wholesale into every LLM call. In runtime prompts, generate only the POS-specific instruction relevant to the current synset. This saves tokens and avoids confusing the model with patterns for unrelated parts of speech.

Reference block:

```text
Serbian POS-aware WordNet style:
- Preserve the synset POS in both literals and gloss style.
- For nouns (`n`), prefer Serbian noun lemmas in nominative singular when possible. The gloss should usually start with a broader noun or class term, then add distinguishing details, e.g. "polaznik koji ...".
- For verbs (`v`), prefer Serbian infinitive lemmas. The gloss should be a verbal/action phrase, usually starting with an infinitive or verbal noun phrase that describes the process/action, e.g. "sticati znanja ...".
- For adjectives (`a`/`s`), prefer Serbian adjective lemmas. The gloss should usually be an adjectival relative clause, commonly starting with "koji/koja/koje" or "koji se ...", e.g. "koji je dopadljiv ...".
- For adverbs (`r`, Serbian XML `b`), prefer Serbian adverb lemmas. The gloss should define manner, degree, time, or circumstance, often with "na nacin koji ..." when natural.
- Treat these as strong style defaults, not absolute templates. If a different Serbian wording is more natural or needed for the exact WordNet sense, keep the natural wording and explain it in notes.
- Do not force a Serbian gloss to start with the selected literal itself; avoid circular definitions.
```

Recommended runtime approach:

```python
def serbian_pos_style_instruction(pos: str) -> str:
    normalized = LanguageUtils.normalize_pos_for_english(pos)
    if normalized == "n":
        return (
            "POS style: this is a noun synset. Use Serbian noun lemmas, usually "
            "nominative singular. The gloss should usually start with a broader "
            "noun/class term plus distinguishing details."
        )
    if normalized == "v":
        return (
            "POS style: this is a verb synset. Use Serbian infinitive verb lemmas. "
            "The gloss should be a verbal/action phrase that describes the process "
            "or action."
        )
    if normalized in {"a", "s"}:
        return (
            "POS style: this is an adjective synset. Use Serbian adjective lemmas. "
            "The gloss should usually be an adjectival relative clause, commonly "
            "starting with 'koji/koja/koje' or 'koji se' when natural."
        )
    if normalized == "r":
        return (
            "POS style: this is an adverb synset. Use Serbian adverb lemmas. "
            "The gloss should define manner, degree, time, or circumstance."
        )
    return (
        "POS style: preserve the synset part of speech in Serbian literals and "
        "make the gloss structurally compatible with that POS."
    )
```

For code prompts, keep ASCII if the file style is ASCII-only. The compact all-POS form may still be useful in documentation or system-level skill instructions:

```text
Serbian POS-aware WordNet style:
- For nouns (n), prefer noun lemmas and a gloss that starts with a broader noun/class term plus differentia.
- For verbs (v), prefer infinitive verb lemmas and a gloss that is a verbal/action phrase.
- For adjectives (a/s), prefer adjective lemmas and a gloss that usually starts with "koji/koja/koje" or "koji se".
- For adverbs (r; Serbian XML b), prefer adverb lemmas and a gloss that defines manner/degree/time/circumstance.
- These are strong defaults, not rigid templates; explain justified exceptions in notes.
- Avoid circularity: the gloss should not simply repeat the selected literal.
```

## Where to add it

### 1. `skills/translate-synset-serbian/SKILL.md`

Add the rule under "Serbian Drafting Rules" and mirror it in the pure agent workflow steps.

Why:

- This repo explicitly says direct Codex translation should use the skill's pure agent workflows.
- If the skill does not mention POS-aware gloss structure, pure `agent-baseline`, `agent-multiphase`, and `agent-conceptual` outputs can drift even if repo-backed pipelines are improved.
- The skill can contain the full POS reference because it is human/agent guidance, while individual generated prompts should include only the relevant POS-specific line.

Suggested additions:

- Under "Serbian Drafting Rules":
  - Add noun/verb/adjective/adverb gloss-shape defaults.
  - Add "style defaults, not rigid templates".
  - Add "record exceptions in notes".
- Under `Agent-Multiphase Steps`:
  - In `definition_translation`, require a POS-aware draft.
  - In `filtering`, reject candidates whose Serbian POS does not match the synset POS unless justified.
  - In `assemble_result`, validate literal POS and gloss shape together.
- Under `Agent-Conceptual Steps`:
  - In `concept_package`, include expected Serbian POS and gloss pattern.
  - In `final_gloss`, require POS-aware gloss form.
  - In `validation`, check "POS/gloss structure agreement".

### 2. `src/wordnet_autotranslate/pipelines/translation_pipeline.py`

Relevant pipeline: `BaselineTranslationPipeline`

Relevant prompt method: `_render_prompt`

Current issue:

- The baseline prompt receives lemmas and gloss but does not pass POS into `_call_llm` or `_render_prompt`.
- It asks for `definition_translation` and `translated_synonyms`, but does not tell the model to preserve POS or shape the Serbian gloss according to POS.

Suggested correction:

- Pass POS from `translate_synset()` into `_call_llm()` and `_render_prompt()`.
- Add `POS: {pos}` to the prompt.
- Add only the POS-specific style instruction generated from that POS, not the full all-POS block.

Why this matters:

- Baseline has no later review stage. If POS/gloss structure is not included in the single prompt, there is no place to recover it.
- Because baseline has only one prompt, it needs the relevant POS instruction, but adding all noun/verb/adjective/adverb rules would waste tokens and may distract the model.

Risk:

- Baseline is intentionally simple. Keep the instruction short so it remains an ablation baseline rather than turning into the full multi-stage workflow.

### 3. `src/wordnet_autotranslate/pipelines/langchain_base_pipeline.py`

Relevant pipeline: `LangChainBasePipeline`

Relevant prompt method: `_render_prompt`

Current state:

- It already includes `Part of speech: {pos}`.
- It does not specify what Serbian gloss structure should look like for each POS.

Suggested correction:

- Add the POS-specific style instruction after `Part of speech: {pos}` or before the JSON schema.
- Add a note that synonyms must be target-language lemmas matching the POS.

Why:

- This is another single-prompt path. It needs both literal POS constraints and definition structure constraints in one place.

### 4. `src/wordnet_autotranslate/pipelines/langgraph_translation_pipeline.py`

Relevant pipeline: `LangGraphTranslationPipeline`

This is the main repo-backed `langgraph` pipeline. It is the best place for a robust correction because it has separate stages for sense analysis, definition translation, literal generation, filtering, and definition quality review.

#### `_render_sense_prompt`

Suggested addition:

- Ask the model to identify "expected Serbian literal POS" and "expected Serbian gloss pattern" in the sense analysis.
- Optionally add fields to the returned JSON:

```json
{
  "expected_literal_pos_sr": "noun|verb|adjective|adverb|other",
  "expected_gloss_shape_sr": "noun class + differentia | verbal phrase | koji/koja/koje clause | manner/degree phrase"
}
```

Why:

- This lets later stages reason from an explicit style target, not just from the raw POS tag.

Implementation caution:

- Adding fields to `SenseAnalysisSchema` is backward compatible if optional, but tests with dummy payloads may need no change if defaults are used.

#### `_render_definition_prompt`

Suggested addition:

- Pass the source POS into this prompt.
- Add only the POS-aware Serbian gloss style rule for the current synset POS.
- Ask the model to return an optional note when it intentionally deviates from the default pattern.

Why:

- This is where the translated definition is first drafted.

Important caveat:

- Do not require every adjective definition to begin exactly with `koji`. Serbian adjective glosses can naturally be `koji se odnosi na ...`, `svojstven ...`, `bez ...`, etc.
- Use "usually/prefer" language rather than "must always".

#### `_render_initial_translation_prompt`

Suggested addition:

- Add "Each Serbian translation must preserve source POS: nouns as nouns, verbs as infinitives, adjectives as adjectives, adverbs as adverbs."
- For verbs, explicitly prefer infinitive and allow aspectual pairs if they represent the same synset sense.
- In the actual prompt, prefer a generated POS-specific sentence, e.g. only the verb instruction for verb synsets.

Why:

- If initial literal candidates are wrong POS, expansion and filtering often amplify the mistake.

#### `_render_expansion_prompt`

Suggested addition:

- Add POS preservation to expansion rules.
- For verbs, allow perfective/imperfective variants only if they remain the same core action.
- For adjectives, reject noun paraphrases unless no lexical adjective exists and mark them as descriptive rather than synonyms.
- Runtime prompt should include only the applicable branch for the synset POS.

Why:

- Expansion is the stage most likely to introduce cross-POS paraphrases.

#### `_render_filtering_prompt`

Suggested addition:

- Add a specific filter criterion: remove candidates whose Serbian grammatical category does not match the synset POS, unless the candidate is a conventional lexical equivalent and the exception is explained.
- Add removed reason examples: `wrong_pos`, `descriptive_phrase`, `too_generic_hypernym`, `wrong_gloss_shape`.
- Include the expected POS label derived from the synset, for example `Expected Serbian POS: verb; preferred literal form: infinitive`.

Why:

- Filtering is the right place to remove candidate literals that are semantically close but lexically the wrong kind of item.

#### `_render_definition_quality_prompt`

This is the most important prompt to update.

Current tasks:

- Circularity
- Grammar and agreement
- Style and fluency
- Corrected version if needed

Suggested addition:

- Pass source POS into `_review_definition_quality()` and `_render_definition_quality_prompt()`.
- Add a new task before or after grammar:

```text
POS/gloss structure - Check whether the definition's grammatical shape agrees with the synset POS:
- noun: broader noun/class term plus differentia
- verb: verbal/action phrase, usually infinitive-led
- adjective: adjectival relative clause, usually "koji/koja/koje..." where natural
- adverb: manner/degree/time/circumstance definition
If the gloss shape conflicts with the POS, revise it while preserving meaning and avoiding circularity.
```

- In implementation, render only the one relevant checklist item for the current POS, not all four bullets.
- Extend `DefinitionQualityIssue.type` to include something like `pos_structure`.

Why:

- Final definition quality has access to filtered synonyms, so it can detect cases such as adjective literals with a noun-like gloss or verb literals with a noun phrase.

Risk:

- This is a schema change. Existing tests that assert allowed issue types may need updating.

### 5. `src/wordnet_autotranslate/pipelines/conceptual_langgraph_pipeline.py`

Relevant pipeline: `ConceptualLangGraphTranslationPipeline`

This pipeline should receive the strongest conceptual version of the rule because it already separates concept packaging, expanded Serbian definition, candidate generation, final gloss, and validation.

#### `_extract_concept`

Suggested addition:

- Add a derived field to the concept package such as:

```json
{
  "serbian_pos_style": {
    "literal_form": "infinitive verbs | nominative singular nouns | adjective lemmas | adverb lemmas",
    "gloss_shape": "verbal phrase | noun hypernym + differentia | koji/koja/koje clause | adverbial manner phrase"
  }
}
```

Why:

- Conceptual prompts use the concept package everywhere. Adding the rule once there makes it available to every later stage.

#### `_render_expanded_definition_sr_prompt`

Suggested addition:

- Ask for an expanded Serbian semantic definition that respects POS style but does not yet force final gloss brevity.
- For verbs, the expanded definition should still be action/process-oriented.
- For nouns, it should identify the broader class term.

Why:

- The expanded Serbian definition drives literal extraction. If it is noun-like for a verb, the literal candidates may drift.

#### `_render_literal_candidates_prompt`

Suggested addition:

- Add candidate POS assessment:

```json
{
  "literal": "candidate",
  "candidate_pos_sr": "noun|verb|adjective|adverb|phrase",
  "pos_match": true
}
```

Why:

- It makes wrong-POS candidates visible and easier to reject later.

Schema impact:

- `LiteralCandidatesOutputSchema` would need optional fields if strict validation is desired.

#### `_render_literal_selection_prompt`

Suggested addition:

- Reject wrong-POS candidates unless there is a documented Serbian lexicalization exception.
- Keep descriptive phrases only when no lexicalized literal exists, and mark them as not ideal for final synset literals.

Why:

- This prevents the final literal set from mixing definitions/paraphrases with actual lemmas.

#### `_render_final_gloss_prompt`

Suggested addition:

- Add POS-specific final gloss defaults:
  - noun: `opstiji pojam + odredbe`
  - verb: `glagolska fraza`
  - adjective: `koji/koja/koje ...`
  - adverb: `na nacin/stepen/vreme ...`

Why:

- This is the final place where the Serbian gloss is written in the conceptual pipeline.

#### `_render_validation_prompt`

Suggested addition:

- Add `POS/gloss structure agreement` to the checklist.
- Add issue code examples:
  - `literal_wrong_pos`
  - `noun_gloss_missing_hypernym`
  - `verb_gloss_not_verbal`
  - `adjective_gloss_not_relative_or_adjectival`
  - `adverb_gloss_not_adverbial`

Why:

- This gives curation reports actionable failure reasons instead of a vague style warning.

### 6. `src/wordnet_autotranslate/workflows/synset_translation_workflow.py`

Relevant function: `run_translation_workflow`

No direct prompt change is needed here. It selects and runs pipelines.

Possible improvement:

- If a deterministic lint helper is added, this workflow could attach a `pos_definition_structure_check` object to each pipeline result.

Why:

- This would make side-by-side `all` output easier to compare.
- It would also let automation use `--strict` later if desired.

Recommended behavior:

- Start as warnings only. Do not fail `strict` mode until the rule has been validated on a larger sample.

### 7. `scripts/translate_synset_workflow.py`

No prompt change is needed.

Possible future CLI addition:

- `--check-pos-style`
- `--pos-style-strict`

Why:

- This keeps style checking explicit for batch QA without changing default behavior too aggressively.

## Optional deterministic lint helper

A useful helper could live in a small module such as `src/wordnet_autotranslate/utils/serbian_style_checks.py`.

Suggested function:

```python
def check_serbian_pos_definition_structure(
    *,
    pos: str,
    literals: list[str],
    definition: str,
) -> dict:
    ...
```

Suggested output:

```json
{
  "status": "ok|warning|error",
  "issues": [
    {
      "code": "verb_gloss_not_verbal",
      "message": "Verb synset gloss should normally be an action/process phrase.",
      "severity": "warning"
    }
  ],
  "suggested_revision_prompt_hint": "Rewrite as a Serbian verbal phrase..."
}
```

Possible lightweight heuristics:

- Adjective gloss:
  - OK if it starts with `koji`, `koja`, `koje`, `koji se`, `koja se`, `koje se`, or a short adjectival construction known to be acceptable.
  - Warning if it starts with a noun-like `osoba`, `stvar`, `pojam`, `radnja`, unless justified.
- Verb gloss:
  - OK if it starts with a Serbian infinitive-like ending (`-ti`, `-ci`) or a verbal noun/process phrase where natural.
  - Warning if it starts with a static noun class such as `osoba`, `predmet`, `mesto`.
- Noun gloss:
  - OK if it starts with a noun phrase or broad class term.
  - Warning if it starts with `koji je` and no head noun, because that is often adjective-style.
- Adverb gloss:
  - OK if it starts with `na nacin`, `u meri`, `u vreme`, `tako da`, or another adverbial explanation.

Important caution:

- Serbian morphology is rich. Regex checks should be conservative and warning-oriented. They should not replace model validation or human curation.

## Schema suggestions

### `DefinitionQualityIssue`

Current type literals:

```python
Literal["circular", "grammar", "style"]
```

Suggested:

```python
Literal["circular", "grammar", "style", "pos_structure"]
```

Why:

- POS/gloss mismatch is not only grammar and not only style. It is a lexicographic structural issue.

### `DefinitionQualitySchema`

Suggested optional field:

```python
pos_structure_status: Optional[Literal["ok", "warning", "needs_revision"]] = None
```

Why:

- This allows dashboards/reports to surface this check without parsing free-text notes.

### Conceptual schemas

If candidate-level POS is added:

- Add optional `candidate_pos_sr`.
- Add optional `pos_match`.
- Add optional `pos_note`.

Keep these optional at first to avoid breaking existing responses and tests.

## Test suggestions

Add focused tests with mocked LLMs rather than live model calls.

### Baseline/single-prompt tests

- Assert that `_render_prompt()` includes source POS and POS-aware Serbian style guidance.
- For `translation_pipeline.py`, this requires changing `_render_prompt` to accept POS.

### LangGraph prompt tests

- For adjective synset:
  - Input POS `a`.
  - Assert definition prompt includes `koji/koja/koje`.
  - Assert definition quality prompt receives POS and checks adjective gloss shape.
- For verb synset:
  - Assert initial translation prompt says infinitive.
  - Assert definition quality prompt checks verbal/action phrase.
- For noun synset:
  - Assert final quality prompt checks broader noun/class term plus differentia.

### Conceptual pipeline tests

- Assert concept package includes POS style metadata.
- Assert final gloss prompt includes POS-specific instructions.
- Assert validation prompt includes POS/gloss agreement checklist.

### Lint tests, if helper is added

- `pos=a`, gloss `koji je dopadljiv` -> OK
- `pos=v`, gloss `sticati znanja ili vestine` -> OK
- `pos=n`, gloss `polaznik koji se upisao...` -> OK
- `pos=a`, gloss `osoba koja je ljubazna` -> warning, because it defines a noun-like class rather than an adjective
- `pos=v`, gloss `proces sticanja znanja` -> warning or acceptable depending on policy; decide before enforcing

## Rollout plan

1. Add prompt-only guidance first, especially in:
   - `skills/translate-synset-serbian/SKILL.md`
   - `BaselineTranslationPipeline._render_prompt`
   - `LangChainBasePipeline._render_prompt`
   - `LangGraphTranslationPipeline._render_definition_prompt`
   - `LangGraphTranslationPipeline._render_definition_quality_prompt`
   - `ConceptualLangGraphTranslationPipeline._render_final_gloss_prompt`
   - `ConceptualLangGraphTranslationPipeline._render_validation_prompt`
2. Add optional schema fields and tests.
3. Run a small curated sample across noun, verb, adjective, and adverb synsets.
4. Only after reviewing false positives, add deterministic lint warnings.
5. Consider strict failures only for batch QA after enough empirical validation.

## Why not add a simple hard rule immediately?

A hard "definition must start with X" rule would improve some obvious cases but create new errors:

- Adjective definitions can be natural without exactly starting with `koji`.
- Verb definitions sometimes use verbal nouns or support constructions in Serbian dictionaries.
- Noun definitions may start with a domain/class phrase that is not a single hypernym word.
- WordNet satellite adjectives (`s`) and relational adjectives can require special handling.
- Circularity can conflict with POS shape. A formally correct `koji je X` definition is still bad if it repeats the selected literal.

The better correction is therefore: use POS style as a strong default, validate it late, keep exceptions visible in notes, and make deterministic checks conservative.
