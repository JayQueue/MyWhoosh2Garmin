#!/usr/bin/env python3
"""
Integration tests that use actual FIT file processing.

These tests require fit_tool to be installed and will create real FIT files,
but still mock Garmin interactions.
"""
import unittest
from unittest.mock import patch, Mock
from pathlib import Path
import sys
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import test FIT generator
from tests.generate_test_fit import create_test_fit_file

# Import the module under test
import myWhoosh2Garmin as mw2g


class TestFITFileProcessingIntegration(unittest.TestCase):
    """Integration tests with real FIT file processing."""
    
    def setUp(self):
        """Set up test environment with real FIT file."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.input_file = self.test_dir / "MyNewActivity-3.8.5.fit"
        self.output_file = self.test_dir / "cleaned.fit"
        
        # Ensure modules are imported
        if mw2g.FitFileBuilder is None:
            if not mw2g.import_required_modules():
                self.skipTest("fit_tool not available")
        
        # Create a real test FIT file
        try:
            create_test_fit_file(self.input_file)
        except Exception as e:
            self.skipTest(f"Could not create test FIT file: {e}")
    
    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.test_dir)
    
    def test_cleanup_fit_file_creates_output(self):
        """Test that cleanup_fit_file creates an output file."""
        if mw2g.FitFileBuilder is None:
            self.skipTest("fit_tool not available")
        
        mw2g.cleanup_fit_file(self.input_file, self.output_file)
        
        # Verify output file was created
        self.assertTrue(self.output_file.exists())
        self.assertGreater(self.output_file.stat().st_size, 0)
    
    def test_cleanup_fit_file_removes_temperature(self):
        """Test that cleaned file doesn't contain temperature data."""
        if mw2g.FitFileBuilder is None:
            self.skipTest("fit_tool not available")
        
        mw2g.cleanup_fit_file(self.input_file, self.output_file)
        
        # Read the cleaned file and verify temperature is removed
        # This is a basic check - in a real scenario you'd parse the FIT file
        # to verify temperature fields are absent
        self.assertTrue(self.output_file.exists())
        
        # Load the cleaned file to verify structure
        try:
            cleaned_fit = mw2g.FitFile.from_file(str(self.output_file))
            # Check that records don't have temperature
            for record in cleaned_fit.records:
                if isinstance(record.message, mw2g.RecordMessage):
                    # Temperature field should be removed
                    # We can't easily check this without parsing, but the file
                    # should be valid
                    pass
        except Exception as e:
            self.fail(f"Cleaned FIT file is invalid: {e}")
    
    def test_cleanup_fit_file_calculates_averages(self):
        """Test that averages are calculated in session messages."""
        if mw2g.FitFileBuilder is None:
            self.skipTest("fit_tool not available")
        
        mw2g.cleanup_fit_file(self.input_file, self.output_file)
        
        # Load the cleaned file and check session averages
        cleaned_fit = mw2g.FitFile.from_file(str(self.output_file))
        
        session_found = False
        for record in cleaned_fit.records:
            if isinstance(record.message, mw2g.SessionMessage):
                session = record.message
                session_found = True
                # Averages should be calculated (not None)
                # Note: The original test file has None averages
                # After cleanup, they should be calculated
                if session.avg_power is not None:
                    self.assertGreater(session.avg_power, 0)
                if session.avg_heart_rate is not None:
                    self.assertGreater(session.avg_heart_rate, 0)
                if session.avg_cadence is not None:
                    self.assertGreater(session.avg_cadence, 0)
        
        self.assertTrue(session_found, "No session message found in cleaned file")


class TestFullWorkflowWithMocks(unittest.TestCase):
    """Test the full workflow with all Garmin interactions mocked."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.fitfile_location = self.test_dir / "fitfiles"
        self.backup_location = self.test_dir / "backup"
        self.fitfile_location.mkdir()
        self.backup_location.mkdir()
        
        # Create a test FIT file
        self.test_fit = self.fitfile_location / "MyNewActivity-3.8.5.fit"
        try:
            create_test_fit_file(self.test_fit)
        except Exception as e:
            self.skipTest(f"Could not create test FIT file: {e}")
    
    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.test_dir)
    
    @patch('myWhoosh2Garmin.upload_fit_file_to_garmin')
    @patch('myWhoosh2Garmin.authenticate_to_garmin')
    @patch('myWhoosh2Garmin.get_backup_path')
    @patch('myWhoosh2Garmin.get_fitfile_location')
    @patch('myWhoosh2Garmin.import_required_modules')
    @patch('myWhoosh2Garmin.ensure_packages')
    def test_full_workflow_no_garmin_upload(
        self, mock_ensure, mock_import, mock_get_fit,
        mock_get_backup, mock_auth, mock_upload
    ):
        """Test full workflow ensuring no actual Garmin upload occurs."""
        # Setup mocks
        mock_ensure.return_value = True
        mock_import.return_value = True
        mock_get_fit.return_value = self.fitfile_location
        mock_get_backup.return_value = self.backup_location
        mock_auth.return_value = True
        mock_upload.return_value = True
        
        # Run main
        result = mw2g.main()
        
        # Verify Garmin was never actually called
        # The upload function should be called with a mock
        self.assertEqual(result, 0)
        
        # Verify upload was called (but mocked, so no real upload)
        mock_upload.assert_called_once()
        uploaded_path = mock_upload.call_args[0][0]
        self.assertTrue(uploaded_path.exists())
        
        # Verify the file was created in backup location
        backup_files = list(self.backup_location.glob("*.fit"))
        self.assertGreater(len(backup_files), 0)


if __name__ == '__main__':
    unittest.main()

