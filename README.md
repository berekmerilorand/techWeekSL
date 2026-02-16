# techWeekSL

A collection of demos, utilities, and implementation tests built during **Tech Week @SL**.

## Repository Structure

```
techWeekSL/
├── .github/            # GitHub workflows for CI/CD
│   └── workflows/      # Automated testing and formatting checks
├── common/             # Common modules (e.g., string_reverser)
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
cd techWeekSL

# Create a virtual environment
python -m venv venv
source venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### Running Tests

Run all tests:

```bash
python -m pytest specs/test_all.py -v
```

### Code Formatting

Format code with black:

```bash
black . --exclude=venv
```

Check formatting without making changes:

```bash
black . --check --exclude=venv
```

### Running Functions

Run individual common functions:

```bash
python -m common.string_reverser
```

## Modules

### common/
- `string_reverser.py` - String reversal utility

### shared/
- `utils.py` - Common utilities (e.g., flatten nested lists)

### specs/
- `test_all.py` - Comprehensive test suite

### .github/workflows/
- `formatting.yml` - Automated code formatting checks with Black (Required)
- `tests.yml` - Automated test execution with pytest
- `claude.yml` - AI-powered code review using Claude (triggered by @claude mentions)

## CI/CD

The repository includes GitHub Actions workflows that automatically run on every pull request and push to master:

- **Code Formatting** - Ensures all code adheres to Black formatting standards
- **Tests** - Runs the full pytest test suite to catch regressions
- **Claude Code Review** - AI-powered code review (triggered by mentioning @claude in PR comments)

## Tech Stack

- **Language:** Python 3.12+
- **Testing:** pytest
- **Code Formatting:** black
- **Package Management:** pip / venv
