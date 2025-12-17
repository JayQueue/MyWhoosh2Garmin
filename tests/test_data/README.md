# Test Data Directory

This directory contains test FIT files for unit testing.

To generate a test FIT file, run:

```bash
python tests/generate_test_fit.py
```

This will create `MyNewActivity-3.8.5.fit` with sample data including:
- Record messages with power, heart rate, cadence, and temperature
- Session message without averages (to test calculation)
- Lap message

The test file is designed to verify:
- Temperature removal
- Average calculation for power, heart rate, and cadence
- File processing and cleanup

