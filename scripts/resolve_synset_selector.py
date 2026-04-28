#!/usr/bin/env python3
"""Resolve a synset selector into a canonical JSON payload for native-agent workflows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from wordnet_autotranslate.workflows.synset_translation_workflow import (
    resolve_wordnet_synset,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve an ILI, ENG30 id, synset name, or lemma+POS into a canonical synset payload."
    )
    parser.add_argument("--ili", help="ILI selector (e.g., i35545)")
    parser.add_argument("--english-id", help="ENG30 ID (e.g., ENG30-00001740-n)")
    parser.add_argument("--synset-name", help="WordNet synset name (e.g., entity.n.01)")
    parser.add_argument("--lemma", help="English lemma (requires --pos)")
    parser.add_argument("--pos", help="POS tag: n|v|a|r (Serbian b is accepted)")
    parser.add_argument("--sense-index", type=int, default=1, help="1-based sense index for lemma lookup")
    parser.add_argument(
        "--with-relations",
        action="store_true",
        help="Attach WordNet relation/domain fields useful for conceptual native-agent translation.",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON output path. When omitted, the payload is printed to stdout.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.lemma and not args.pos:
        parser.error("--lemma requires --pos")

    try:
        payload = resolve_wordnet_synset(
            ili=args.ili,
            english_id=args.english_id,
            synset_name=args.synset_name,
            lemma=args.lemma,
            pos=args.pos,
            sense_index=args.sense_index,
            include_relations=args.with_relations,
        )
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
