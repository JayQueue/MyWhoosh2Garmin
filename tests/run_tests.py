#!/usr/bin/env python3
"""
Test runner script for MyWhoosh2Garmin tests.

This script:
1. Generates a test FIT file if it doesn't exist
2. Runs all unit tests
3. Ensures no Garmin uploads occur (all mocked)
"""
import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def generate_test_fit_file():
    """Generate test FIT file if it doesn't exist."""
    test_data_dir = Path(__file__).parent / "test_data"
    test_data_dir.mkdir(exist_ok=True)
    test_fit_file = test_data_dir / "MyNewActivity-3.8.5.fit"
    
    if not test_fit_file.exists():
        print("Generating test FIT file...")
        try:
            from tests.generate_test_fit import create_test_fit_file
            create_test_fit_file(test_fit_file)
            print(f"✓ Test FIT file created: {test_fit_file}")
        except ImportError as e:
            print(f"⚠ Warning: Could not generate test FIT file: {e}")
            print("  Tests that require FIT files will be skipped.")
    else:
        print(f"✓ Test FIT file already exists: {test_fit_file}")

def run_tests():
    """Run all unit tests."""
    print("\n" + "="*60)
    print("Running Unit Tests")
    print("="*60 + "\n")
    
    # Try pytest first, fall back to unittest
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v"],
            cwd=Path(__file__).parent.parent
        )
        return result.returncode
    except FileNotFoundError:
        print("pytest not found, using unittest instead...")
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "tests", "-v"],
            cwd=Path(__file__).parent.parent
        )
        return result.returncode

if __name__ == "__main__":
    print("MyWhoosh2Garmin Test Suite")
    print("="*60)
    print("\n⚠ IMPORTANT: All Garmin interactions are mocked.")
    print("  No actual uploads will occur during testing.\n")
    
    generate_test_fit_file()
    exit_code = run_tests()
    
    print("\n" + "="*60)
    if exit_code == 0:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed.")
    print("="*60)
    
    sys.exit(exit_code)

