# Contributing

Please keep changes small and tied to a reproducible workflow problem. Do not add tools merely
to increase the catalog. Use API/CLI-first examples that run without company access.

1. Create a Python 3.11+ virtual environment and install `python -m pip install -e '.[dev]'`.
2. Read AGENTS.md. Keep upstream imports in compat/ and preserve attribution.
3. Add regression tests for success, failure and authorization boundaries.
4. Run the tests, Ruff, deterministic demo and release check documented in README.
5. Explain which behavior is inherited versus implemented here, and report unverified claims.

Never submit personal paths, private domains/IPs, real accounts, service credentials, cookies,
production logs, or proprietary business code. Do not copy another repository's history.
User-facing changes should update English and Chinese README summaries.

Release packaging: run `python -m build` followed by `python scripts/prepare_release.py`.
The latter removes build-machine ownership metadata from the sdist and emits SHA256SUMS.
