# Agent Developer Onboarding: PyMan

Welcome! This document provides information on directories, development setup, validation workflows, and code guidelines for AI agents or developers working on PyMan.

---

## 📂 Codebase Directory Map

- `/home/huberto/work/pyman/` (Root workspace directory)
  - `GEMINI.md`: Project memory, architecture description, and known bugs.
  - `AGENTS.md`: This onboarding documentation.
  - `pyman/` (Main project repository)
    - `pyman/` (Package source code)
      - `__init__.py`: Package initialization & versioning.
      - `pyman.py`: CLI argparse entry point (`main()`).
      - `core_logic.py`: Execution engine (merges configs, hooks, request runner).
      - `request_parser.py`: YAML parser.
      - `pyman_helpers.py`: Injected utility helpers (`pm` object).
      - `log_reporter.py`: Parsers log files and builds HTML reports.
      - `postman_importer.py`: Importer for Postman JSON collections.
      - `bruno_importer.py`: Importer for Bruno folder structures.
    - `examples/`
      - `pyman_collection/`: Complete test suite executing multiple requests on `httpbin.org`.
      - `bruno_collection/`: Test Bruno collection directory.
    - `setup.py` & `pyproject.toml`: Package descriptors.
    - `requirements.txt`: Package dependencies (`requests`, `PyYAML`, `Faker`).
    - `venv/`: Local virtual environment.
  - `DOCs/`
    - Presentations (`.pdf`, `.odp`, `.pptx`) and draft files related to PyMan documentation and LinkedIn posts.

---

## ⚙️ Development Environment Setup

To begin working on the codebase, execute:

```bash
# 1. Access the codebase root directory
cd pyman

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Make an editable installation (optional)
pip install -e .
```

---

## 🧪 Testing & Execution

PyMan uses its `examples/pyman_collection` as an integration test suite. Use it to check functionality:

```bash
# Execute collection using python module format
python -m pyman.pyman run examples/pyman_collection

# Execute collection using pyman command directly (if installed in venv)
pyman run examples/pyman_collection
```

### Verification Checklist:
- Logs are created under `examples/pyman_collection/logs/run_*.log`.
- JSON reports are created under `examples/pyman_collection/logs/report_*.json`.
- HTML reports are created under `examples/pyman_collection/reports/report_*.html`.
- Exit code should be `0` if all requests run successfully (no script failures or bad assert statuses).

---

## 📝 Code Guidelines

1. **Python Version Compatibility**: Maintain support for Python `3.7+`.
2. **Logging**:
   - Console logs should be simple and structured using ANSI colors via the `ColorFormatter` inside `core_logic.py`.
   - File logs must capture everything (`DEBUG` level) with timestamps.
3. **Helper Additions**:
   - Any new helper methods injected into script contexts must be added to the `PyManHelpers` class in `pyman/pyman_helpers.py`.
4. **Environment Variables**:
   - Remember that `environment_vars` is serialized back to `.environment-variables` automatically on script termination if modified. Make sure any transient/internal variables are prefixed with an underscore (`_`) so they are ignored by `write_environment_file()`.
5. **No Placeholders**: Avoid committing placeholder templates. Ensure examples remain fully executable (targeting reliable endpoints like `httpbin.org`).
