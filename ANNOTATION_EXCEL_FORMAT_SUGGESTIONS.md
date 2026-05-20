# Annotation Excel format suggestions for Serbian WordNet synset evaluation

## Purpose

This document proposes a two-sheet Excel workbook format for manual evaluation of Serbian WordNet synset candidates. It is a documentation/design proposal only; it does not define or implement code changes.

The format is based on:

- Google Doc questionnaire: `UPITNIK ZA EVALUACIJU SINSETA (GLOSA I LITERALI)`
- Existing human-readable workbook shape: `reports/human_readable_excel_no_ollama_100_2026-05-08/agent_all_100_results_human_readable.xlsx`
- Free online WordNet inspection reference: [Open English WordNet](https://en-word.net/), using synset links such as `https://en-word.net/id/oewn-08641944-n`

The main design choice is a **wide-row annotation table**: one row represents one English synset plus one Serbian candidate/version to judge. All judging fields are columns in that same row.

This avoids asking annotators to compare all pipeline outputs in one row. If the current workbook has multiple Serbian outputs for the same English synset, such as `baseline`, `multiphase`, and `conceptual`, each output should become a separate annotation row.

## Workbook structure

The workbook should contain exactly two sheets:

1. `Instructions`
2. `Annotations`

### Sheet 1: `Instructions`

This sheet should explain the annotation task in plain Serbian or Serbian/English mixed documentation, depending on the annotator group. It should include:

- Goal: evaluate the quality of translated or expanded Serbian synsets, with focus on meaning precision, Serbian gloss clarity, POS-compatible gloss structure, literal adequacy, and usefulness for NLP tasks such as word sense disambiguation.
- Script/literal rule: Serbian answers and proposed literals should use Latin script unless the dataset explicitly requires otherwise.
- Literal separator rule: when multiple literals are entered in one cell, separate them with `;`.
- Rating scale:
  - `1` - uopste ne zadovoljava
  - `2` - delimicno ne zadovoljava
  - `3` - neutralno / delimicno zadovoljava
  - `4` - uglavnom zadovoljava
  - `5` - u potpunosti zadovoljava
- Link usage rule: use `wordnet_link` for close inspection of the English WordNet synset, but judge the Serbian candidate shown in the row.
- POS/gloss structure examples:
  - Adjective: `prijatan; ljubazan` with gloss shape such as `koji je dopadljiv; odgovarajuci`.
  - Verb: `nauciti; saznati; saznavati; studirati; uciti` with gloss shape such as `sticati znanja ili vestine`.
  - Noun: `djak; ucenik` with gloss shape such as `polaznik koji se upisao u neku obrazovnu instituciju`.
  - Adverb: use an adverbial gloss shape describing manner, degree, time, or circumstance, for example `na nacin koji ...` when natural.

### Sheet 2: `Annotations`

This sheet is the main human annotation table.

Rules:

- One row equals one candidate to judge.
- Repeat the English context on every row so filtering, sorting, or exporting does not detach a candidate from its source synset.
- Use `candidate_source` to identify which Serbian candidate/version is being judged.
- Keep `english_id` as plain text for sorting, filtering, scripts, and traceability.
- Keep `wordnet_link` as a separate inspection column rather than embedding a hyperlink into `english_id`.
- Leave annotator fields blank in the generated template, except `review_status`, which may default to `pending`.

## Transforming the existing one-sheet workbook

The current human-readable workbook has one `results` sheet with columns shaped like:

```text
id
english_literals
english_definition
baseline_serbian_literals
baseline_serbian_definition
multiphase_serbian_literals
multiphase_serbian_definition
conceptual_serbian_literals
conceptual_serbian_definition
```

To convert this into the proposed annotation workbook:

1. Create the `Instructions` sheet from the guidance above.
2. Create the `Annotations` sheet with the exact column order listed below.
3. For each source row in `results`, create one annotation row per available Serbian candidate:
   - `baseline` from `baseline_serbian_literals` and `baseline_serbian_definition`
   - `multiphase` from `multiphase_serbian_literals` and `multiphase_serbian_definition`
   - `conceptual` from `conceptual_serbian_literals` and `conceptual_serbian_definition`
4. Copy source context into each generated row:
   - `id` -> `english_id`
   - `english_literals` -> `english_literals`
   - `english_definition` -> `english_gloss`
5. Fill candidate columns:
   - pipeline name -> `candidate_source`
   - pipeline Serbian literals -> `serbian_literals`
   - pipeline Serbian definition -> `serbian_gloss`
6. Generate `wordnet_link` from `english_id` using the link rule below.
7. Set `review_status` to `pending`.
8. Leave human judgment columns blank until annotators fill them.

## `Annotations` column order

Use this exact column order:

```text
row_id
annotator_name
annotation_date
english_id
wordnet_link
synset_name
pos
candidate_source
english_literals
english_gloss
serbian_literals
serbian_gloss
gloss_naturalness_1_5
gloss_meaning_adequacy_1_5
gloss_distinguishes_sense_1_5
gloss_pos_structure_1_5
gloss_non_circularity_1_5
gloss_correction_needed
proposed_serbian_gloss
literals_fit_sense_1_5
extra_literals_present
extra_literals
missing_literals_present
missing_literals
literal_coverage_1_5
general_comment
annotator_confidence_1_5
review_status
```

## Column definitions

| Column | Meaning |
| --- | --- |
| `row_id` | Stable row identifier for the annotation row, e.g. `ENG30-08641944-n__baseline`. |
| `annotator_name` | Name, initials, or agreed annotator ID. |
| `annotation_date` | Date of annotation, preferably `YYYY-MM-DD`. |
| `english_id` | Plain ENG30 synset ID, e.g. `ENG30-08641944-n`. |
| `wordnet_link` | Separate clickable or plain URL for online inspection. |
| `synset_name` | Optional WordNet synset name if available, e.g. `neighborhood.n.01`. |
| `pos` | Source POS from WordNet, e.g. `n`, `v`, `a`, `s`, `r`. Serbian XML adverb `b` should be treated as `r` for English WordNet inspection. |
| `candidate_source` | Source of the Serbian candidate, e.g. `baseline`, `multiphase`, `conceptual`, `human`, `imported`. |
| `english_literals` | English source literals, separated with `;` when multiple. |
| `english_gloss` | English WordNet gloss/definition. |
| `serbian_literals` | Serbian candidate literals to judge, separated with `;` when multiple. |
| `serbian_gloss` | Serbian candidate gloss to judge. |
| `gloss_naturalness_1_5` | Is the Serbian gloss grammatically and stylistically natural? |
| `gloss_meaning_adequacy_1_5` | Does the gloss adequately express the synset meaning? |
| `gloss_distinguishes_sense_1_5` | Is the gloss clear enough to distinguish this meaning from related senses? |
| `gloss_pos_structure_1_5` | Is the gloss structure compatible with the POS? |
| `gloss_non_circularity_1_5` | Is the gloss lexicographic, non-circular, and not needlessly repeating the lemma? |
| `gloss_correction_needed` | Whether the Serbian gloss needs correction. |
| `proposed_serbian_gloss` | Annotator's corrected gloss if correction is needed. |
| `literals_fit_sense_1_5` | Do all listed Serbian literals fit the synset meaning? |
| `extra_literals_present` | Whether some listed Serbian literals are extra/wrong for this sense. |
| `extra_literals` | Extra literals, separated with `;` when multiple. |
| `missing_literals_present` | Whether important Serbian literals are missing. |
| `missing_literals` | Missing literals, separated with `;` when multiple. |
| `literal_coverage_1_5` | How well the Serbian literal set covers the synset meaning. |
| `general_comment` | Optional free-text note. |
| `annotator_confidence_1_5` | Annotator confidence in their judgment. |
| `review_status` | Workflow status for the row. |

## Allowed values

Rating fields must use integers from `1` to `5`:

```text
gloss_naturalness_1_5
gloss_meaning_adequacy_1_5
gloss_distinguishes_sense_1_5
gloss_pos_structure_1_5
gloss_non_circularity_1_5
literals_fit_sense_1_5
literal_coverage_1_5
annotator_confidence_1_5
```

Controlled text fields:

| Column | Allowed values |
| --- | --- |
| `gloss_correction_needed` | `no`, `minor`, `major` |
| `extra_literals_present` | `yes`, `no` |
| `missing_literals_present` | `yes`, `no` |
| `review_status` | `pending`, `complete`, `needs_second_review` |

## WordNet link rule

Generate `wordnet_link` from `english_id` by removing the `ENG30-` prefix and adding the `oewn-` prefix used by Open English WordNet URLs.

Example:

```text
english_id: ENG30-08641944-n
wordnet_link: https://en-word.net/id/oewn-08641944-n
```

Implementation rule:

```text
wordnet_link = "https://en-word.net/id/oewn-" + english_id.replace("ENG30-", "")
```

Keep both columns:

- `english_id` stays plain text for sorting, filtering, scripts, and traceability.
- `wordnet_link` is used only for online inspection.

## Example rows

The example below shows the intended shape. It is illustrative, not a gold annotation set.

| row_id | annotator_name | annotation_date | english_id | wordnet_link | synset_name | pos | candidate_source | english_literals | english_gloss | serbian_literals | serbian_gloss | gloss_naturalness_1_5 | gloss_meaning_adequacy_1_5 | gloss_distinguishes_sense_1_5 | gloss_pos_structure_1_5 | gloss_non_circularity_1_5 | gloss_correction_needed | proposed_serbian_gloss | literals_fit_sense_1_5 | extra_literals_present | extra_literals | missing_literals_present | missing_literals | literal_coverage_1_5 | general_comment | annotator_confidence_1_5 | review_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ENG30-09827683-n__baseline |  |  | ENG30-09827683-n | https://en-word.net/id/oewn-09827683-n | student.n.01 | n | baseline | student; pupil | a learner who is enrolled in an educational institution | djak; ucenik | polaznik koji se upisao u neku obrazovnu instituciju |  |  |  |  |  |  |  |  |  |  |  |  |  |  | pending |
| ENG30-00597915-v__multiphase |  |  | ENG30-00597915-v | https://en-word.net/id/oewn-00597915-v | learn.v.01 | v | multiphase | learn; study | gain knowledge or skills | nauciti; saznati; saznavati; studirati; uciti | sticati znanja ili vestine |  |  |  |  |  |  |  |  |  |  |  |  |  |  | pending |
| ENG30-01801029-a__conceptual |  |  | ENG30-01801029-a | https://en-word.net/id/oewn-01801029-a | pleasant.a.01 | a | conceptual | pleasant | affording pleasure; being in harmony with your taste or likings | prijatan; ljubazan | koji je dopadljiv; odgovarajuci |  |  |  |  |  |  |  |  |  |  |  |  |  |  | pending |

## Acceptance checklist

This proposed format satisfies the intended annotation workflow if:

- The workbook has exactly two sheets: `Instructions` and `Annotations`.
- The `Annotations` sheet uses the exact column names and order listed above.
- The format preserves all questionnaire judging items:
  - Serbian gloss naturalness
  - meaning adequacy
  - sense distinction
  - POS-compatible gloss structure
  - non-circularity
  - whether gloss correction is needed
  - proposed corrected gloss
  - literal fit
  - extra literals
  - missing literals
  - literal coverage
  - general comment
  - annotator confidence
- Existing one-row, multi-pipeline result workbooks can be flattened into one row per Serbian candidate/version.
- `wordnet_link` is a separate column from `english_id`.
- Human annotators can judge each candidate independently without comparing all pipeline outputs in one cell or one row.

