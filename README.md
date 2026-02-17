# techWeekSL

A collection of demos, utilities, and implementation tests built during **Tech Week @SL**.

## Repository Structure

```
techWeekSL/
├── .github/            # GitHub workflows for CI/CD
│   └── workflows/      # Automated testing and formatting checks
├── common/             # Common modules (e.g., string_reverser)
├── demos/              # Demo projects
├── shared/             # Shared utilities and helper modules
├── specs/              # Test specifications
├── requirements.txt    # Project dependencies
└── conftest.py         # PyCharm sample script
```

## Getting Started

### Prerequisites

- Python 3.12+
- pip

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd techWeekSL

# Create a virtual environment
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt
```

### Running Tests

Run all tests:

```bash
python -m pytest specs/test_all.py -v
```

Run specific tests:

```bash
# Run a specific test function
python -m pytest specs/test_all.py::test_add -v

# Run tests with coverage
python -m pytest specs/test_all.py --cov=common -v
```

**Note:** Some tests in `test_all.py` are intentionally written with bugs for PR review testing purposes. You may see failing tests - this is expected.

### Code Formatting

Format code with black:

```bash
black . --exclude=venv
```

Check formatting without making changes:

```bash
black . --check --exclude=venv
```

### Running Demos

Run individual demo modules:

```bash
python -m demos.simple
python -m common.string_reverser
```

## Modules

### common/
- `string_reverser.py` - String reversal utility
- `methods.py` - Mathematical utility functions:
  - `add()` - Addition of two integers
  - `divide()` - Division of two floats
  - `calculate_average()` - Calculate average of a list of numbers
  - `is_even()` - Check if a number is even
  - `reverse_string()` - String reversal function

### shared/
- `utils.py` - Common utilities (e.g., flatten nested lists)

### demos/
- `simple.py` - Simple greeting demo

### specs/
- `test_all.py` - Test suite with intentional bugs for PR review practice

### .github/workflows/
- `formatting.yml` - Automated code formatting checks with Black (Required)
- `tests.yml` - Automated test execution with pytest

## CI/CD

The repository includes GitHub Actions workflows that automatically run on every pull request and push to master:

- **Code Formatting** - Ensures all code adheres to Black formatting standards
- **Tests** - Runs the full pytest test suite to catch regressions

## Tech Stack

- **Language:** Python 3.12+
- **Testing:** pytest
- **Code Formatting:** black
- **Package Management:** pip / venv

## Contributing

When contributing to this repository:

1. Create a new branch for your feature/fix
2. Write tests for your changes in the `specs/` directory
3. Ensure code is formatted with Black: `black . --exclude=venv`
4. Run tests to verify: `python -m pytest specs/test_all.py -v`
5. Create a pull request with a clear description of changes
6. Wait for CI/CD checks to pass (formatting and tests)

### Adding New Modules

- Add source code to `common/` or `demos/`
- Add corresponding tests to `specs/`
- Update this README with module documentation
- Ensure all functions have type hints

### PR Review Testing

This repository contains intentionally buggy tests in `test_all.py` to practice PR review skills. When reviewing PRs, check for:
- Incorrect assertions
- Missing edge cases
- Logic errors
- Code quality issues

## License

This project is for educational purposes as part of Tech Week @SL.
