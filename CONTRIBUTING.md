# Contributing

Small bug fixes, clearer examples, and tests for API edge cases are welcome.
For larger changes, open an issue describing the use case first.

```sh
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
uv run --locked python examples/offline_report.py
uv build
```

Tests must run without Google credentials. Use synthetic data and fake API
sessions, and include a regression test for behavior changes. Keep report access
read-only and require explicit property selection in MCP tools.

Do not include credentials, real property IDs, or private Analytics exports in
issues, fixtures, or pull requests. For bugs, include the Python and package
versions, a minimal command with placeholder IDs, and the error message.

This project is licensed under the [MIT License](LICENSE).
