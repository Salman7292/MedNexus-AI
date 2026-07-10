# Contributing Guide

Thank you for your interest in contributing to MedNexus AI! We welcome contributions to enhance medical reasoning accuracy, add new specialist agents, or optimize the RAG indexing pipeline.

---

## Code Style & Conventions

To keep the project maintainable, please adhere to the following rules:

### Python Conventions
*   **Docstrings**: All new functions, routes, and tool definitions must contain docstrings. Follow [Google style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) so `mkdocstrings` can render the manual properly.
*   **Logic files**: Define all agent graphs in a separate `<specialist>_logic.py` module. Keep database persistence variables isolated inside the module:
    ```python
    DB_NAME = "specialist_name.db"
    ```
*   **Tool Definitions**: Use LangChain's `@tool` decorator. Write descriptive docstrings detailing arguments and return types — the LLM reads these descriptions to decide which tool to call.

### HTML/JS Templates
*   Create new templates inside `templates/` extending `base.html`.
*   Keep frontend script actions modular inside `static/js/<specialty>.js`.
*   Maintain clean, mobile-first designs utilizing Tailwind styling variables.

---

## Development Workflow

1.  **Fork the Repository**: Clone your fork locally.
2.  **Create a Branch**: Create a feature branch (e.g. `feature/add-neurologist-agent`).
3.  **Run Tests**: Run the Python import and tool tests before committing:
    ```bash
    python -c "from dermatologist_logic import dermatologist_app; print('Imports OK')"
    ```
4.  **Add Documentation**: If you add a new tool or configuration key, update the files in `docs/` and verify that the docs build locally via `mkdocs build`.
5.  **Submit a Pull Request**: Detail your changes and submit a PR to the main repository.
