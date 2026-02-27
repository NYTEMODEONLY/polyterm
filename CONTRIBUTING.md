# Contributing to PolyTerm

Thank you for your interest in contributing to PolyTerm! This document provides guidelines for contributing to the project.

## 🚀 Quick Start

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/yourusername/polyterm.git`
3. **Setup** development environment:
   ```bash
   cd polyterm
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   ```
4. **Create** a feature branch: `git checkout -b feature/your-feature-name`

## 🔄 Development Workflow

1. **Make** your changes
2. **Test** your changes:
   ```bash
   pytest                    # Run all tests
   pytest tests/test_live_data/ -v  # Test live data
   pytest tests/test_tui/ -v        # Test TUI
   flake8 polyterm tests     # Check code style
   ```
3. **Commit** your changes: `git commit -m "Add your feature"`
4. **Push** to your fork: `git push origin feature/your-feature-name`
5. **Create** a Pull Request

## 📝 Code Style

- Follow **PEP 8** guidelines
- Use **type hints** where appropriate
- Write **docstrings** for all public functions and classes
- Keep functions **focused and small**
- Add **tests** for new features

## 🧪 Testing

- Write **unit tests** for all new functionality
- Ensure **all tests pass** before submitting PR
- Aim for **>80% code coverage**
- Use **pytest fixtures** for test setup
- **Mock external API calls** in tests

### Test Categories
- **Live Data Tests**: `tests/test_live_data/`
- **TUI Tests**: `tests/test_tui/`
- **API Tests**: `tests/test_api/`
- **Core Tests**: `tests/test_core/`
- **CLI Tests**: `tests/test_cli/`

## CI Checks

Every pull request and push to `main` runs the following automated checks via GitHub Actions (`.github/workflows/ci.yml`):

| Check | What it does |
|-------|-------------|
| **Syntax check** | Parses all `.py` files with `ast.parse` to catch syntax errors (zero dependencies) |
| **Import smoke test** | Verifies top-level package imports (CLI, TUI, API, Core, DB) |
| **Test suite** | Runs `pytest` against Python 3.10 and 3.11 (excludes live-data and flaky TUI integration tests) |

**Design tradeoffs:**
- Uses stdlib `ast.parse` instead of `flake8`/`ruff` to avoid adding dev dependencies. A linter can be added later.
- Tests run on Python 3.10 and 3.11 to balance coverage vs CI runtime (~20s per matrix entry).
- `tests/test_live_data/` is excluded because it hits real APIs and is non-deterministic.
- `tests/test_tui/test_integration.py` is excluded due to pre-existing stdin capture issues in CI.

To run the same checks locally:
```bash
# Syntax check
python -c "import ast, os, sys; [ast.parse(open(os.path.join(r,f)).read()) for r,_,fs in os.walk('polyterm') for f in fs if f.endswith('.py')]"

# Tests (matching CI)
pytest tests/ --ignore=tests/test_live_data --ignore=tests/test_tui/test_integration.py -q
```

## 📋 Pull Request Process

1. **Update** README.md with details of changes if needed
2. **Update** requirements.txt if you add dependencies
3. **Ensure** all tests pass and code follows style guidelines
4. **Request** review from maintainers
5. **Address** any feedback from reviewers

## 🐛 Bug Reports

When filing a bug report, please include:

- **Clear description** of the issue
- **Steps to reproduce**
- **Expected vs actual behavior**
- **PolyTerm version**: `polyterm --version`
- **Python version**: `python --version`
- **Operating system**

## 💡 Feature Requests

We welcome feature requests! Please include:

- **Clear description** of the feature
- **Use case and benefits**
- **Any implementation ideas** you have

## 🔧 Development Setup

### Prerequisites
- Python 3.8+
- pip
- git

### Optional Tools
- **pipx**: For testing package installation
- **tox**: For testing multiple Python versions
- **pre-commit**: For code quality hooks

### Environment Variables
```bash
export POLYMARKET_API_KEY="your-key"  # Optional
export POLYTERM_CONFIG_PATH="/custom/path"  # Optional
```

## 📚 Documentation

- **README.md**: Main documentation
- **TUI_GUIDE.md**: Terminal User Interface guide
- **API_SETUP.md**: API configuration guide
- **Code comments**: Inline documentation

## 🎯 Areas for Contribution

### High Priority
- **API Integration**: New data sources
- **TUI Enhancements**: Additional screens/features
- **Performance**: Optimization improvements
- **Testing**: More test coverage

### Medium Priority
- **Documentation**: Improvements and examples
- **Error Handling**: Better error messages
- **Configuration**: More customization options

### Low Priority
- **Themes**: Additional color schemes
- **Export Formats**: More output formats
- **Analytics**: Advanced market analysis

## ❓ Questions?

Feel free to open an issue for any questions about contributing.

**Thank you for contributing to PolyTerm!** 🎉

