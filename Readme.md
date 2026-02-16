# techWeekSL

A collection of demos, utilities, and implementation tests built during **Tech Week @SL**.

## Repository Structure

```
techWeekSL/
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

### Running Demos

Run individual demo modules:

```bash
python -m demos.simple
python -m common.string_reverser
```

## Modules

### common/
- `string_reverser.py` - String reversal utility

### shared/
- `utils.py` - Common utilities (e.g., flatten nested lists)

### demos/
- `simple.py` - Simple greeting demo

### specs/
- `test_all.py` - Comprehensive test suite

## Tech Stack

- **Language:** Python 3.12+
- **Testing:** pytest
- **Code Formatting:** black
- **Package Management:** pip / venv
