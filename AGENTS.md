# Agent Instructions for wordnet_autotranslate-

## Preferred workflow skills
- Use `skills/translate-synset-serbian/SKILL.md` when users request English WordNet synset translation to Serbian.
- Prefer selector-based lookup (ENG30 ID, WordNet synset name, or lemma + POS) over ad-hoc prompt-only translation.
- When users ask Codex to translate directly, use the skill's pure agent workflows instead of requiring CLI commands.
- Support all three pure agent workflow options: `agent-baseline`, `agent-multiphase`, and `agent-conceptual`; use `agent-all` for side-by-side output.

## Operational guidance
- For reproducible runs, use `scripts/translate_synset_workflow.py`.
- Default repo-backed pipeline: `langgraph`; use `all` for side-by-side repo comparison output.
- Default direct Codex workflow: `agent-multiphase`; use `agent-all` for all three pure agent workflows.
- Use `--strict` for fail-fast automation; omit it for best-effort multi-pipeline reports.

## Safety
- Do not log secrets.
- Keep prompts and outputs in structured JSON where possible.
