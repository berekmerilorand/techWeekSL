# PR Review Guidelines

This document provides guidelines for automated PR reviews using Claude.

## What to Review

### Critical Issues (Always Comment)
- **Bugs and Logic Errors**: Incorrect logic, off-by-one errors, wrong operators
- **Security Issues**: SQL injection, XSS vulnerabilities, unsafe deserialization
- **Missing Error Handling**: Unhandled exceptions, missing edge cases
- **Breaking Changes**: API changes that break existing functionality
- **Test Coverage**: Missing tests for new functionality or bug fixes

### Important Issues (Comment if Significant)
- **Performance Problems**: O(n²) algorithms where O(n) is possible, unnecessary loops
- **Resource Leaks**: Unclosed files, connections, or database cursors
- **Type Safety**: Missing or incorrect type hints in Python
- **Edge Cases**: Division by zero, empty lists, null/None values

### Code Quality (Comment if Egregious)
- **Duplicate Code**: Large blocks of repeated logic
- **Overly Complex Code**: Functions doing too many things, deep nesting
- **Misleading Names**: Variables or functions with confusing names

## What NOT to Review

- **Formatting**: Black handles this automatically
- **Import Order**: Not critical unless it causes issues
- **Minor Style**: Personal preferences about code style
- **Positive Feedback**: Keep reviews focused on improvements only
- **Code Not Changed**: Only review code modified in the PR

## Project-Specific Guidelines

### Python Code
- All functions must have type hints
- Use pytest for all tests
- Follow PEP 8 (enforced by Black)
- Document complex logic with comments

### Testing
- Tests should be in the `specs/` directory
- Test file names must start with `test_`
- Each function should have corresponding tests
- Test for edge cases: empty inputs, null values, division by zero, etc.

## Review Tone
- Be direct and clear about issues
- Focus on **what** is wrong and **why** it matters
- Suggest **how** to fix it when appropriate
- Avoid praise or positive feedback (keep reviews actionable)
- Be pragmatic: only comment on things that truly matter
