# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

toto GOAL3 Predictor is a machine learning system for predicting team goal distributions in Japanese sports lottery (toto GOAL3). It combines Wyscout soccer statistics with ensemble ML models (Poisson Regression + XGBoost) to identify value betting opportunities by comparing model predictions against public voting rates.

## Development Commands

```bash
# Install dependencies (use dev for development)
pip install -e ".[dev]"

# Run all tests with coverage
pytest

# Run specific test file
pytest tests/unit/services/test_data_loader.py

# Run tests matching pattern
pytest -k "test_calculate_features"

# Linting and formatting
ruff check .
ruff format .

# Type checking
mypy src/toto_predictor
```

## CLI Commands

```bash
toto-predictor import --dir data/wyscout/2025 --season 2025  # Import Wyscout data
toto-predictor train --seasons 2025 --cv 5                    # Train ML models
toto-predictor predict --round 1607                           # Generate predictions
toto-predictor scrape --round 1607                            # Scrape voting rates
toto-predictor strategy --round 1607                          # Calculate value scores
toto-predictor pipeline --round 1607                          # Run full pipeline
```

## Architecture

**Layered Architecture** with strict dependency rules:

```
cli/       → Entry point (Typer + Rich)
    ↓
services/  → Business logic (DataLoader, FeatureEngine, ModelEnsemble, VoteScraper, StrategyEngine)
    ↓
db/        → Persistence (SQLite + repositories)
    ↓
models/    → Pure data structures (dataclasses, no dependencies)
```

**Dependency Rules**:
- `cli/` → `services/` → `db/` → `models/` (allowed)
- Reverse direction or circular imports (forbidden)
- `models/` has no external dependencies

## Key Directories

- `src/toto_predictor/` - Main source code
- `tests/unit/`, `tests/integration/` - Test suites with fixtures in `tests/conftest.py`
- `data/wyscout/` - Source Excel files by year
- `data/processed/` - SQLite database
- `data/predictions/`, `data/votes/` - JSON output files
- `models/` - Trained ML model artifacts
- `reports/` - Generated Markdown reports

## Code Conventions

- **Language**: Comments and docstrings in Japanese
- **Line length**: 100 characters max
- **Type hints**: Required on all functions
- **Docstring format**: Google style with Args/Returns/Raises
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE_CASE for constants
- **Boolean variables**: Use is_/has_/should_ prefix

## Data Flow

```
Wyscout Excel → DataLoader → SQLite → FeatureEngine (rolling windows)
    → ModelEnsemble (Poisson + XGBoost) → Predictions
    → VoteScraper (totoONE) → StrategyEngine → Recommendations + Report
```

## Testing Patterns

- **Naming**: `test_[subject]_[condition]_[expected_result]`
- **Fixtures**: Centralized in `tests/conftest.py` (temp_db, sample_match, mock_trained_model, etc.)
- **Mocking**: External dependencies (APIs, files) mocked; business logic tested directly
- **Coverage target**: 80%

## Exception Hierarchy

```python
TotoPredictorError
├── DataError (DataNotFoundError, DataFormatError, DatabaseError)
├── ModelError (ModelNotTrainedError, PredictionError)
├── ScrapingError (NetworkError, ParseError)
└── ValidationError
```

## Git Workflow

- **Branches**: `main` (production), `develop` (baseline), `feature/`, `fix/`, `refactor/`
- **Commits**: `<type>(<scope>): <subject>` (types: feat, fix, docs, style, refactor, test, chore)
