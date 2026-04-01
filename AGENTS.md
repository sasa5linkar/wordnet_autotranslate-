# Agent Instructions for wordnet_autotranslate-

## Preferred workflow skills
- Use `skills/translate-synset-serbian/SKILL.md` when users request English WordNet synset translation to Serbian.
- Prefer selector-based lookup (`--english-id`, `--synset-name`, or `--lemma` + `--pos`) over ad-hoc prompt-only translation.

## Operational guidance
- For reproducible runs, use `scripts/translate_synset_workflow.py`.
- Default pipeline: `langgraph`; use `all` for side-by-side comparison output.
- Use `--strict` for fail-fast automation; omit it for best-effort multi-pipeline reports.

## Safety
- Do not log secrets.
- Keep prompts and outputs in structured JSON where possible.
