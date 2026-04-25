# Safe agent-mode report: 100 synsets

## Run configuration
- Base URL: `http://localhost:11434`
- Backend reachable: **False**
- Model setting: `gpt-oss:120b`

## Workflow policy
- Baseline workflow is executed for all synsets.
- LangGraph and Conceptual workflows are checked but skipped in safe mode
  when backend is unavailable (to avoid repeated hard connection failures).

## Outcome summary
- Synsets processed: **100**
- Baseline successful outputs: **100**
- LangGraph skipped: **100**
- Conceptual skipped: **100**
- Elapsed: **24.131s**

Detailed records are available in `results.json`.
