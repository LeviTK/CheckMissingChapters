# Sigil Plugin Development Guidelines

## Build & Test
- **Environment**: Python 3.4+ embedded in Sigil.
- **Run**: Zip the contents of the `src` folder (`.zip`) and install via Sigil > Plugins > Manage Plugins.
  - *Note: Do not zip the `src` folder itself, zip the files inside it.*
- **Test**: Manual verification only. No automated test suite exists.
- **Debug**: Use `print()` statements; output appears in Sigil's Plugin Runner window.

## Code Style
- **Formatting**: Use 4 spaces for indentation.
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants.
- **Imports**: Standard library first, followed by third-party (e.g., Qt), then local imports (`pyqt_import`).
- **Typing**: Dynamic typing; type hints are not used.
- **Error Handling**: Use `try...except` blocks generously to prevent crashing the host application.
- **UI**: Always import Qt classes from `pyqt_import` to ensure cross-version compatibility.
- **Structure**: The entry point must be `run(bk)`; source code resides in `src/`. Logic generally resides in `src/plugin.py`.
