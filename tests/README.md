# Unit Tests for MyWhoosh2Garmin

This directory contains comprehensive unit tests for the MyWhoosh2Garmin application.

## Running Tests

To run all tests:

```bash
python -m pytest tests/
```

Or using unittest:

```bash
python -m unittest discover tests
```

## Test Coverage

The tests cover:

1. **Core Functions**
   - `calculate_avg()` - Average calculation
   - `append_value()` - Value extraction from messages
   - `reset_values()` - Value list reset
   - `get_most_recent_fit_file()` - FIT file discovery
   - `generate_new_filename()` - Filename generation

2. **FIT File Processing**
   - `cleanup_fit_file()` - Temperature removal and average calculation
   - `cleanup_and_save_fit_file()` - Full file processing workflow

3. **Garmin Integration** (All Mocked)
   - `authenticate_to_garmin()` - Authentication flow
   - `upload_fit_file_to_garmin()` - File upload (mocked, no actual uploads)

4. **File System Operations**
   - `get_fitfile_location()` - Path discovery
   - `get_backup_path()` - Backup path management

5. **Main Function**
   - Complete workflow testing with all mocks

## Important Notes

- **All Garmin interactions are mocked** - No actual uploads occur during testing
- Test FIT files are generated programmatically
- Tests use temporary directories that are cleaned up automatically
- All external dependencies (garth, fit_tool) are mocked where appropriate

## Generating Test Data

To generate a test FIT file:

```bash
python tests/generate_test_fit.py
```

This creates a FIT file with:
- 360 record messages (30 minutes of data)
- Varying power (150-250W), heart rate (140-160 bpm), cadence (80-100 rpm)
- Temperature data (to test removal)
- Session message without averages (to test calculation)

