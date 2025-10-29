# Python Coding Standards

This document defines the coding standards for the **Synthetic Newsroom (AI Pressroom)** project. All code contributions must adhere to these guidelines to ensure consistency, readability, and maintainability.

## Table of Contents

1. [Core Principles](#core-principles)
2. [Code Style - PEP 8](#code-style---pep-8)
3. [Naming Conventions](#naming-conventions)
4. [Code Layout](#code-layout)
5. [Imports](#imports)
6. [Comments and Documentation](#comments-and-documentation)
7. [Type Hints](#type-hints)
8. [Error Handling](#error-handling)
9. [Testing](#testing)
10. [Project-Specific Guidelines](#project-specific-guidelines)
11. [Tools and Enforcement](#tools-and-enforcement)

---

## Core Principles

> **"Code is read much more often than it is written."** - PEP 8

- **Readability counts**: Write code that others (and your future self) can understand
- **Consistency is key**: Follow existing patterns in the codebase
- **Explicit is better than implicit**: Avoid clever tricks; prefer clear, straightforward code
- **Simple is better than complex**: Choose simplicity over unnecessary abstraction

---

## Code Style - PEP 8

This project follows [PEP 8](https://peps.python.org/pep-0008/), the official Python style guide.

### Indentation

- Use **4 spaces** per indentation level
- Never use tabs
- Configure your editor to insert spaces when pressing Tab

```python
# Good
def my_function():
    if condition:
        do_something()
    return result

# Bad
def my_function():
  if condition:  # 2 spaces
      do_something()  # inconsistent
```

### Line Length

- **Maximum 79 characters** for code
- **Maximum 72 characters** for docstrings and comments
- Break long lines using parentheses, brackets, or backslashes

```python
# Good
result = some_function_with_long_name(
    first_argument,
    second_argument,
    third_argument
)

# Good
total = (first_very_long_variable_name
         + second_very_long_variable_name
         + third_very_long_variable_name)
```

### Line Breaks with Operators

- Break **before** binary operators, not after

```python
# Good
income = (gross_wages
          + taxable_interest
          + dividends
          - qualified_dividends)

# Bad
income = (gross_wages +
          taxable_interest +
          dividends -
          qualified_dividends)
```

---

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| **Modules** | lowercase with underscores | `debate_orchestrator.py` |
| **Packages** | lowercase, no underscores preferred | `agents`, `audio` |
| **Classes** | CapWords (PascalCase) | `DebateOrchestrator`, `TTSProvider` |
| **Functions** | lowercase with underscores | `generate_debate()`, `create_episode()` |
| **Variables** | lowercase with underscores | `episode_id`, `audio_path` |
| **Constants** | UPPERCASE with underscores | `MAX_ARTICLES`, `DEFAULT_TIMEOUT` |
| **Private members** | single leading underscore | `_internal_method()`, `_cache` |
| **"Magic" methods** | double underscores | `__init__()`, `__str__()` |

### Specific Naming Guidelines

- Use descriptive names that reveal intent:
  ```python
  # Good
  episode_duration_seconds = 300

  # Bad
  d = 300  # what is d?
  ```

- Avoid single-letter names except for:
  - Loop counters: `i`, `j`, `k`
  - Coordinates: `x`, `y`, `z`
  - Generic exceptions: `e`
  - File handles: `f`

- For boolean variables, use `is_`, `has_`, `can_` prefixes:
  ```python
  is_valid = True
  has_audio = False
  can_retry = True
  ```

---

## Code Layout

### Blank Lines

- **Two blank lines** before top-level function and class definitions
- **One blank line** between method definitions inside classes
- Use blank lines sparingly within functions to indicate logical sections

```python
"""Module docstring."""
import os


class MyClass:
    """Class docstring."""

    def __init__(self):
        """Constructor."""
        self.value = 0

    def method_one(self):
        """First method."""
        pass


def standalone_function():
    """Function docstring."""
    pass
```

### Whitespace

**Avoid extraneous whitespace:**

```python
# Good
spam(ham[1], {eggs: 2})
if x == 4:
    print(x, y)

# Bad
spam( ham[ 1 ], { eggs: 2 } )
if x == 4 :
    print( x , y )
```

**Use whitespace around operators:**

```python
# Good
x = y + z
result = function(arg1, arg2)

# Bad
x=y+z
result=function(arg1,arg2)
```

**Exception for keyword arguments:**

```python
# Good
def function(default=None):
    pass

# Good (with type hints)
def function(default: Optional[str] = None):
    pass
```

---

## Imports

### Import Order

Group imports in this order, separated by blank lines:

1. Standard library imports
2. Third-party library imports
3. Local application imports

```python
# Standard library
import os
import sys
from pathlib import Path
from typing import List, Optional

# Third-party
import requests
from pydantic import BaseModel

# Local
from src.shared.settings import get_settings
from src.agents.debate_orchestrator import DebateOrchestrator
```

### Import Guidelines

- Use **absolute imports** by default
- Import one module per line
- Avoid wildcard imports (`from module import *`)
- Use `from module import name` for frequently used items

```python
# Good
import os
import sys
from pathlib import Path

# Bad
import os, sys
from pathlib import *
```

### Import Sorting

Use `isort` to automatically sort imports:

```bash
make format  # Runs isort and black
```

---

## Comments and Documentation

### Docstrings

**All public modules, classes, functions, and methods must have docstrings.**

Use Google-style docstrings:

```python
def synthesize_speech(
    text: str,
    speaker: str,
    output_path: Path
) -> Path:
    """Synthesize speech from text using configured TTS provider.

    Args:
        text: The text to convert to speech
        speaker: Name of the speaker (must exist in voice config)
        output_path: Path where audio file will be saved

    Returns:
        Path to the generated audio file

    Raises:
        ValueError: If speaker is not configured
        TTSError: If synthesis fails

    Example:
        >>> path = synthesize_speech(
        ...     "Hello world",
        ...     "chatgpt",
        ...     Path("output.wav")
        ... )
    """
    pass
```

### Inline Comments

- Use sparingly and only when necessary
- Place on separate line above code being explained
- Keep comments up-to-date with code changes

```python
# Good
# Normalize loudness to broadcast standard (-16 LUFS)
normalized_audio = normalize_loudness(audio, target_lufs=-16)

# Bad
x = x + 1  # Increment x (obvious, don't comment)
```

### TODO Comments

Use this format for TODO items:

```python
# TODO(username): Description of what needs to be done
# TODO: Implement S3 multipart upload for large files
```

---

## Type Hints

**Use type hints for all function signatures and class attributes.**

```python
from typing import List, Optional, Dict, Any
from pathlib import Path

def process_articles(
    articles: List[Dict[str, Any]],
    max_count: Optional[int] = None
) -> List[str]:
    """Process articles and return summaries."""
    summaries: List[str] = []
    # Implementation
    return summaries
```

### Type Hint Guidelines

- Use built-in types for Python 3.9+ when possible: `list[str]` instead of `List[str]`
- Use `Optional[T]` for values that can be `None`
- Use `Union[T1, T2]` for multiple possible types
- Use `Any` sparingly; prefer specific types
- For complex types, consider using `TypedDict` or Pydantic models

```python
# Python 3.9+ style
def process(items: list[str]) -> dict[str, int]:
    pass

# Use Pydantic for complex data structures
from pydantic import BaseModel

class ArticleData(BaseModel):
    title: str
    url: str
    content: Optional[str] = None
```

### Type Checking

Run `mypy` to verify type correctness:

```bash
make lint  # Runs flake8 and mypy
```

---

## Error Handling

### Exception Handling

- Catch **specific exceptions**, not bare `except:`
- Use `finally` for cleanup code
- Don't use exceptions for flow control

```python
# Good
try:
    result = risky_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise
except FileNotFoundError:
    logger.warning("File not found, using default")
    result = default_value

# Bad
try:
    result = risky_operation()
except:  # Too broad
    pass  # Silently swallowing errors
```

### Custom Exceptions

Define custom exceptions for domain-specific errors:

```python
class TTSError(Exception):
    """Base exception for TTS-related errors."""
    pass

class SpeakerNotFoundError(TTSError):
    """Raised when speaker configuration is not found."""
    pass
```

### Logging

Use the `logging` module, not `print()`:

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed diagnostic information")
logger.info("General informational message")
logger.warning("Warning message")
logger.error("Error message")
logger.exception("Error with traceback")
```

---

## Testing

### Test Structure

- Place tests in `tests/` directory mirroring `src/` structure
- Name test files `test_*.py`
- Name test functions `test_*`

```python
# tests/test_audio/test_mix.py
import pytest
from src.audio.mix import AudioMixer

def test_audio_mixer_initialization():
    """Test that AudioMixer initializes correctly."""
    mixer = AudioMixer()
    assert mixer is not None

@pytest.mark.slow
def test_audio_mixing_integration():
    """Integration test for full audio mixing pipeline."""
    # Test implementation
    pass
```

### Test Guidelines

- Each test should test one thing
- Use descriptive test names that explain what is being tested
- Use pytest fixtures for setup/teardown
- Mark slow tests with `@pytest.mark.slow`
- Mark integration tests with `@pytest.mark.integration`

### Running Tests

```bash
make test           # Run all tests with coverage
pytest tests/ -v    # Verbose output
pytest tests/ -k test_audio  # Run specific tests
```

---

## Project-Specific Guidelines

### Settings and Configuration

- Use `get_settings()` singleton to access configuration
- Never hardcode API keys or credentials
- Store secrets in `.env` file (never commit to git)

```python
from src.shared.settings import get_settings

settings = get_settings()
api_key = settings.openai_api_key  # From .env
max_articles = settings.sources[0].max_articles  # From settings.yaml
```

### Path Handling

- Use `pathlib.Path` instead of string paths
- Use `Path.resolve()` for absolute paths
- Use `/` operator for path joining

```python
from pathlib import Path

# Good
work_dir = Path("data/work")
episode_dir = work_dir / f"episode_{date}"
audio_file = episode_dir / "audio.mp3"

# Bad
episode_dir = f"data/work/episode_{date}"
audio_file = episode_dir + "/audio.mp3"
```

### Async/Await (Future)

When adding async functionality:

- Use `async def` for asynchronous functions
- Use `await` for awaitable calls
- Use `asyncio.gather()` for concurrent operations
- Add type hints: `async def func() -> Coroutine[Any, Any, ReturnType]`

### Resource Management

Always use context managers for resources:

```python
# Good
with open(file_path, 'r') as f:
    content = f.read()

# Good (for custom resources)
class ResourceManager:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
```

---

## Tools and Enforcement

### Code Formatting

**Black** - Automatic code formatter:

```bash
make format  # Auto-format all Python files
```

Configuration in `pyproject.toml`:
```toml
[tool.black]
line-length = 79
target-version = ['py39']
```

### Import Sorting

**isort** - Automatic import sorter:

```bash
make format  # Also runs isort
```

### Linting

**flake8** - Style checker:

```bash
make lint
```

Common flake8 codes:
- `E` prefix: PEP 8 errors
- `F` prefix: PyFlakes errors (undefined names, imports)
- `W` prefix: PEP 8 warnings

### Type Checking

**mypy** - Static type checker:

```bash
make lint  # Includes mypy
```

### Pre-commit Hooks

Consider setting up pre-commit hooks:

```bash
# .git/hooks/pre-commit
#!/bin/bash
make lint
make test
```

### Continuous Integration

GitHub Actions automatically runs:
- Code formatting check (black, isort)
- Linting (flake8, mypy)
- Tests (pytest with coverage)

Ensure all checks pass before merging pull requests.

---

## Summary Checklist

Before committing code, ensure:

- [ ] Code follows PEP 8 (run `make lint`)
- [ ] Code is formatted with Black (run `make format`)
- [ ] Imports are sorted with isort (run `make format`)
- [ ] All functions have type hints
- [ ] All public functions/classes have docstrings
- [ ] Tests are written and passing (run `make test`)
- [ ] No hardcoded secrets or credentials
- [ ] Logging is used instead of print statements
- [ ] Error handling is appropriate and specific

---

## References

- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [PEP 257 - Docstring Conventions](https://peps.python.org/pep-0257/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Real Python - PEP 8 Tutorial](https://realpython.com/python-pep8/)
- [Black Code Style](https://black.readthedocs.io/en/stable/the_black_code_style/)

---

## Questions or Suggestions?

If you have questions about these coding standards or suggestions for improvements, please open an issue or submit a pull request.
