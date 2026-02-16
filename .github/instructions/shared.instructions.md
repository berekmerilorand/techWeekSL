# Copilot Code Review Instructions

## General Guidelines
- Review code for correctness, readability, and maintainability
- Flag any security concerns, even in demo/experimental code
- Check for proper error handling and edge cases
- Verify that functions have clear, descriptive names and docstrings
- Ensure code follows PEP 8 style conventions for Python

## Testing
- Check that new functionality has corresponding tests
- Flag missing test coverage for edge cases
- Verify assertions are meaningful and not just checking for truthiness
- Ensure test names clearly describe what they test

## Project Structure
- This is a demo/experimentation repo — keep suggestions practical, not over-engineered
- Verify imports resolve correctly given the project's package structure
- Check that `__init__.py` files exist where needed
- Flag any hardcoded values that should be configurable

## Python Specific
- Prefer type hints on function signatures
- Flag mutable default arguments (e.g., `def foo(items=[])`)
- Check for proper use of context managers for file/resource handling
- Flag bare `except:` clauses — prefer specific exception types
- Suggest f-strings over `.format()` or `%` formatting where appropriate

## PR Hygiene
- Flag PRs with no description — a short summary should always be included
- Check that commit messages are descriptive
- Flag unrelated changes bundled into a single PR