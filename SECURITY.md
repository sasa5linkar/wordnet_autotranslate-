# Security Policy

## Supported Versions

This repository is currently pre-1.0 (`0.1.x`). Security fixes are applied to
the latest commit on the default branch.

## Reporting a Vulnerability

Please report vulnerabilities privately to the maintainers by opening a
**private security advisory** on GitHub (preferred). If that is unavailable,
open an issue with minimal details and ask maintainers for a private channel.

When reporting, include:
- Affected files/components.
- Reproduction steps and expected impact.
- Suggested mitigation (if known).

## Secrets and Sensitive Data

- Never commit `.env` files, API keys, or tokens.
- Do not include prompts/responses containing secrets in shared logs.
- Rotate any secret immediately if exposure is suspected.

## Secure Development Notes

- Translation pipeline calls to external/local LLMs should use bounded retries
  and explicit timeouts.
- Keep dependency versions pinned/minimum-bounded and run dependency audits
  regularly.
- CI includes secret scanning and dependency auditing workflows.
- Secret scanning uses `.gitleaks.toml` to ignore generated/non-sensitive
  fixture directories while still enforcing leaks in source and config files.
