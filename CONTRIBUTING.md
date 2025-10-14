# Contributing to PolyTerm

Thank you for your interest in contributing to PolyTerm! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/polyterm.git`
3. Create a virtual environment: `python -m venv venv`
4. Activate it: `source venv/bin/activate` (Unix) or `venv\Scripts\activate` (Windows)
5. Install dependencies: `pip install -e ".[dev]"`

## Development Workflow

1. Create a new branch: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Run tests: `pytest`
4. Run linter: `flake8 polyterm tests`
5. Commit your changes: `git commit -m "Add your feature"`
6. Push to your fork: `git push origin feature/your-feature-name`
7. Create a Pull Request

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write docstrings for all public functions and classes
- Keep functions focused and small
- Add tests for new features

## Testing

- Write unit tests for all new functionality
- Ensure all tests pass before submitting PR
- Aim for >80% code coverage
- Use pytest fixtures for test setup
- Mock external API calls in tests

## Pull Request Process

1. Update README.md with details of changes if needed
2. Update the requirements.txt if you add dependencies
3. Ensure all tests pass and code follows style guidelines
4. Request review from maintainers
5. Address any feedback from reviewers

## Bug Reports

When filing a bug report, please include:

- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- PolyTerm version
- Python version
- Operating system

## Feature Requests

We welcome feature requests! Please include:

- Clear description of the feature
- Use case and benefits
- Any implementation ideas you have

## Questions?

Feel free to open an issue for any questions about contributing.

Thank you for contributing to PolyTerm!

