# Testing Guide for MyWhoosh2Garmin

This document explains how to run the unit tests for MyWhoosh2Garmin.

## Overview

The test suite includes:
- **Unit tests** with mocked dependencies
- **Integration tests** using real FIT file processing
- **Test FIT file generator** for creating sample data
- **Complete Garmin service mocking** - no actual uploads occur

## Quick Start

### Run All Tests

```bash
# Using the test runner (recommended)
python tests/run_tests.py

# Or using pytest directly
pytest tests/

# Or using unittest
python -m unittest discover tests
```

### Generate Test FIT File

```bash
python tests/generate_test_fit.py
```

This creates `tests/test_data/MyNewActivity-3.8.5.fit` with:
- 360 record messages (30 minutes of cycling data)
- Power values: 150-250W
- Heart rate: 140-160 bpm
- Cadence: 80-100 rpm
- Temperature data (to test removal)
- Session message without averages (to test calculation)

## Test Structure

```
tests/
├── __init__.py
├── test_myWhoosh2Garmin.py    # Main unit tests
├── test_integration.py          # Integration tests with real FIT files
├── generate_test_fit.py         # Test FIT file generator
├── run_tests.py                 # Test runner script
├── README.md                     # Test documentation
└── test_data/                    # Generated test FIT files
    └── MyNewActivity-3.8.5.fit
```

## Test Coverage

### Unit Tests (`test_myWhoosh2Garmin.py`)

1. **Core Functions**
   - `calculate_avg()` - Average calculation logic
   - `append_value()` - Value extraction from messages
   - `reset_values()` - List reset functionality
   - `get_most_recent_fit_file()` - FIT file discovery
   - `generate_new_filename()` - Filename generation with timestamps

2. **FIT File Processing**
   - `cleanup_fit_file()` - Temperature removal and average calculation
   - `cleanup_and_save_fit_file()` - Complete processing workflow

3. **Garmin Integration (All Mocked)**
   - `authenticate_to_garmin()` - Authentication flow
   - `get_credentials_for_garmin()` - Credential handling
   - `upload_fit_file_to_garmin()` - File upload (mocked)

4. **File System Operations**
   - `get_fitfile_location()` - Path discovery for different OS
   - `get_backup_path()` - Backup path management

5. **Main Function**
   - Complete workflow testing with all dependencies mocked

### Integration Tests (`test_integration.py`)

- Real FIT file creation and processing
- Verification of temperature removal
- Average calculation verification
- Full workflow with mocked Garmin service

## Garmin Service Mocking

**All Garmin interactions are mocked** to prevent actual uploads:

```python
@patch('myWhoosh2Garmin.garth')
@patch('myWhoosh2Garmin.upload_fit_file_to_garmin')
def test_upload(mock_upload, mock_garth):
    # Mock returns success without actual upload
    mock_upload.return_value = True
    # Test proceeds without network calls
```

The tests use `unittest.mock` to:
- Mock `garth` module and all its methods
- Mock `garth.client.upload()` to return success
- Prevent any actual network requests
- Verify function calls without side effects

## Running Specific Tests

### Run a Single Test Class

```bash
pytest tests/test_myWhoosh2Garmin.py::TestCalculateAvg
```

### Run a Single Test Method

```bash
pytest tests/test_myWhoosh2Garmin.py::TestCalculateAvg::test_calculate_avg_with_values
```

### Run with Coverage

```bash
pytest tests/ --cov=myWhoosh2Garmin --cov-report=html
```

## Requirements

Tests require:
- Python 3.7+
- `pytest` (optional, for better test output)
- `fit_tool` (for integration tests)
- `garth` (mocked, not actually used)

Install test dependencies:

```bash
pip install pytest pytest-cov
```

Or using pipenv:

```bash
pipenv install --dev
```

## Test Data

The test FIT file generator creates realistic cycling data:
- **Duration**: 30 minutes
- **Data points**: 360 records (one every 5 seconds)
- **Power**: Varies between 150-250W
- **Heart Rate**: Varies between 140-160 bpm
- **Cadence**: Varies between 80-100 rpm
- **Temperature**: Included (to test removal)

## Important Notes

1. **No Real Uploads**: All Garmin service calls are mocked. No actual uploads occur.

2. **Temporary Files**: Tests use `tempfile` for temporary directories that are automatically cleaned up.

3. **Module Imports**: Some tests may skip if `fit_tool` is not available, but core unit tests will still run.

4. **OS-Specific Tests**: Some tests mock OS-specific behavior (Windows vs POSIX).

## Troubleshooting

### Import Errors

If you see import errors, ensure you're running tests from the project root:

```bash
cd /path/to/MyWhoosh2Garmin
python tests/run_tests.py
```

### FIT File Generation Fails

If test FIT file generation fails, ensure `fit_tool` is installed:

```bash
pip install fit_tool
```

### Tests Skip with "fit_tool not available"

This is expected if `fit_tool` isn't installed. Core unit tests will still run, but integration tests will be skipped.

## Continuous Integration

The test suite is designed to run in CI/CD environments:
- No external dependencies required (Garmin is mocked)
- No network calls
- Deterministic results
- Fast execution

Example CI configuration:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pip install pytest fit_tool
    python tests/run_tests.py
```

