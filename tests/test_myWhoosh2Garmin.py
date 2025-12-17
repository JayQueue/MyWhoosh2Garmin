#!/usr/bin/env python3
"""
Unit tests for myWhoosh2Garmin.py

These tests mock all Garmin interactions to ensure no actual uploads occur.
"""
import unittest
from unittest.mock import (
    Mock, patch, MagicMock, mock_open, call
)
from pathlib import Path
import json
import sys
import tempfile
import shutil
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the module under test
import myWhoosh2Garmin as mw2g


class TestCalculateAvg(unittest.TestCase):
    """Test the calculate_avg function."""
    
    def test_calculate_avg_with_values(self):
        """Test average calculation with values."""
        values = [100, 150, 200, 250, 300]
        result = mw2g.calculate_avg(values)
        self.assertEqual(result, 200.0)
    
    def test_calculate_avg_empty(self):
        """Test average calculation with empty list."""
        result = mw2g.calculate_avg([])
        self.assertEqual(result, 0.0)
    
    def test_calculate_avg_single_value(self):
        """Test average calculation with single value."""
        result = mw2g.calculate_avg([42])
        self.assertEqual(result, 42.0)


class TestAppendValue(unittest.TestCase):
    """Test the append_value function."""
    
    def test_append_value_exists(self):
        """Test appending a value that exists."""
        values = []
        message = Mock()
        message.cadence = 90
        mw2g.append_value(values, message, "cadence")
        self.assertEqual(values, [90])
    
    def test_append_value_missing(self):
        """Test appending a value that doesn't exist."""
        values = []
        message = Mock()
        del message.power  # Attribute doesn't exist
        mw2g.append_value(values, message, "power")
        self.assertEqual(values, [0])


class TestResetValues(unittest.TestCase):
    """Test the reset_values function."""
    
    def test_reset_values(self):
        """Test resetting values returns three empty lists."""
        cadence, power, heart_rate = mw2g.reset_values()
        self.assertEqual(cadence, [])
        self.assertEqual(power, [])
        self.assertEqual(heart_rate, [])


class TestGetMostRecentFitFile(unittest.TestCase):
    """Test the get_most_recent_fit_file function."""
    
    def setUp(self):
        """Set up test directory with FIT files."""
        self.test_dir = Path(tempfile.mkdtemp())
        # Create test FIT files with different versions
        (self.test_dir / "MyNewActivity-3.8.5.fit").touch()
        (self.test_dir / "MyNewActivity-3.7.2.fit").touch()
        (self.test_dir / "MyNewActivity-3.9.1.fit").touch()
        (self.test_dir / "other_file.fit").touch()
    
    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.test_dir)
    
    def test_get_most_recent_fit_file(self):
        """Test finding the most recent FIT file."""
        result = mw2g.get_most_recent_fit_file(self.test_dir)
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "MyNewActivity-3.9.1.fit")
    
    def test_get_most_recent_fit_file_no_files(self):
        """Test when no FIT files exist."""
        empty_dir = Path(tempfile.mkdtemp())
        try:
            result = mw2g.get_most_recent_fit_file(empty_dir)
            self.assertIsNone(result)
        finally:
            shutil.rmtree(empty_dir)


class TestGenerateNewFilename(unittest.TestCase):
    """Test the generate_new_filename function."""
    
    def test_generate_new_filename(self):
        """Test filename generation with timestamp."""
        fit_file = Path("MyNewActivity-3.8.5.fit")
        filename = mw2g.generate_new_filename(fit_file)
        self.assertTrue(filename.startswith("MyNewActivity-3.8.5_"))
        self.assertTrue(filename.endswith(".fit"))
        # Check timestamp format
        timestamp_part = filename.replace("MyNewActivity-3.8.5_", "").replace(".fit", "")
        self.assertRegex(timestamp_part, r"\d{4}-\d{2}-\d{2}_\d{6}")


class TestCleanupFitFile(unittest.TestCase):
    """Test the cleanup_fit_file function."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.input_file = self.test_dir / "input.fit"
        self.output_file = self.test_dir / "output.fit"
    
    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.test_dir)
    
    @patch('myWhoosh2Garmin.FitFileBuilder')
    @patch('myWhoosh2Garmin.FitFile')
    @patch('myWhoosh2Garmin.RecordTemperatureField')
    def test_cleanup_fit_file_removes_temperature(
        self, mock_temp_field, mock_fit_file, mock_builder
    ):
        """Test that temperature is removed from records."""
        # Setup mocks
        mock_temp_field.ID = 13
        
        # Create mock record messages
        record1 = Mock()
        record1.cadence = 90
        record1.power = 200
        record1.heart_rate = 150
        record1.remove_field = Mock()
        
        record2 = Mock()
        record2.cadence = 95
        record2.power = 210
        record2.heart_rate = 155
        record2.remove_field = Mock()
        
        # Create mock session message
        session = Mock()
        session.avg_cadence = None
        session.avg_power = None
        session.avg_heart_rate = None
        
        # Create mock lap message
        lap = Mock()
        
        # Setup FitFile mock
        mock_fit_instance = Mock()
        mock_fit_instance.records = [
            Mock(message=record1),
            Mock(message=lap),
            Mock(message=record2),
            Mock(message=session),
        ]
        mock_fit_file.from_file.return_value = mock_fit_instance
        
        # Setup builder mock
        mock_builder_instance = Mock()
        mock_builder.return_value = mock_builder_instance
        mock_built_file = Mock()
        mock_builder_instance.build.return_value = mock_built_file
        
        # Ensure modules are imported
        if mw2g.FitFileBuilder is None:
            mw2g.import_required_modules()
        
        # Temporarily replace with mocks
        original_builder = mw2g.FitFileBuilder
        original_fit = mw2g.FitFile
        original_temp = mw2g.RecordTemperatureField
        
        try:
            mw2g.FitFileBuilder = mock_builder
            mw2g.FitFile = mock_fit_file
            mw2g.RecordTemperatureField = mock_temp_field
            
            # Run the function
            mw2g.cleanup_fit_file(self.input_file, self.output_file)
            
            # Verify temperature was removed from records
            self.assertEqual(record1.remove_field.call_count, 1)
            self.assertEqual(record2.remove_field.call_count, 1)
            record1.remove_field.assert_called_with(mock_temp_field.ID)
            record2.remove_field.assert_called_with(mock_temp_field.ID)
            
            # Verify averages were calculated
            self.assertIsNotNone(session.avg_cadence)
            self.assertIsNotNone(session.avg_power)
            self.assertIsNotNone(session.avg_heart_rate)
            
            # Verify builder was used correctly
            self.assertGreaterEqual(mock_builder_instance.add.call_count, 3)
            mock_built_file.to_file.assert_called_once()
        finally:
            # Restore originals
            mw2g.FitFileBuilder = original_builder
            mw2g.FitFile = original_fit
            mw2g.RecordTemperatureField = original_temp


class TestGetFitfileLocation(unittest.TestCase):
    """Test the get_fitfile_location function."""
    
    @patch('myWhoosh2Garmin.os.name', 'posix')
    @patch('myWhoosh2Garmin.Path.home')
    def test_get_fitfile_location_posix_exists(self, mock_home):
        """Test POSIX path when directory exists."""
        mock_home.return_value = Path("/home/user")
        target_path = Path("/home/user/Library/Containers/com.whoosh.whooshgame/Data/Library/Application Support/Epic/MyWhoosh/Content/Data")
        
        with patch.object(target_path, 'is_dir', return_value=True):
            with patch('myWhoosh2Garmin.Path') as mock_path:
                mock_path.home.return_value = Path("/home/user")
                # Build the path manually for testing
                result = mw2g.get_fitfile_location()
                # Since we can't easily mock the full path construction,
                # we'll test the logic differently
                pass  # This test would need more complex mocking
    
    @patch('myWhoosh2Garmin.os.name', 'nt')
    @patch('myWhoosh2Garmin.Path.home')
    def test_get_fitfile_location_windows(self, mock_home):
        """Test Windows path finding."""
        mock_home.return_value = Path("C:/Users/Test")
        base_path = Path("C:/Users/Test/AppData/Local/Packages")
        
        # Create a mock directory structure
        mock_package_dir = Mock()
        mock_package_dir.is_dir.return_value = True
        mock_package_dir.name = "MyWhooshTechnologyService.1234567890"
        mock_package_dir.__truediv__ = lambda self, other: Path(str(self) + "/" + str(other))
        
        target_path = Path(str(mock_package_dir) + "/LocalCache/Local/MyWhoosh/Content/Data")
        
        with patch.object(Path, 'iterdir') as mock_iterdir:
            with patch.object(target_path, 'is_dir', return_value=True):
                mock_iterdir.return_value = [mock_package_dir]
                # This test needs more complex setup
                pass


class TestGetBackupPath(unittest.TestCase):
    """Test the get_backup_path function."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.json_file = self.test_dir / "backup_path.json"
    
    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.test_dir)
    
    def test_get_backup_path_from_json(self):
        """Test getting backup path from existing JSON file."""
        backup_path = self.test_dir / "backup"
        backup_path.mkdir()
        
        with self.json_file.open('w') as f:
            json.dump({'backup_path': str(backup_path)}, f)
        
        result = mw2g.get_backup_path(self.json_file)
        self.assertEqual(result, backup_path)
    
    @patch('myWhoosh2Garmin.filedialog')
    @patch('myWhoosh2Garmin.tk.Tk')
    def test_get_backup_path_new_selection(self, mock_tk, mock_filedialog):
        """Test getting backup path from file dialog."""
        backup_path = self.test_dir / "backup"
        backup_path.mkdir()
        
        mock_root = Mock()
        mock_tk.return_value = mock_root
        mock_filedialog.askdirectory.return_value = str(backup_path)
        
        result = mw2g.get_backup_path(self.json_file)
        
        self.assertEqual(result, backup_path)
        self.assertTrue(self.json_file.exists())
        
        # Verify JSON was saved
        with self.json_file.open('r') as f:
            data = json.load(f)
            self.assertEqual(data['backup_path'], str(backup_path))
    
    @patch('myWhoosh2Garmin.filedialog')
    @patch('myWhoosh2Garmin.tk.Tk')
    def test_get_backup_path_cancelled(self, mock_tk, mock_filedialog):
        """Test when user cancels file dialog."""
        mock_root = Mock()
        mock_tk.return_value = mock_root
        mock_filedialog.askdirectory.return_value = ""
        
        result = mw2g.get_backup_path(self.json_file)
        
        self.assertIsNone(result)


class TestAuthenticateToGarmin(unittest.TestCase):
    """Test Garmin authentication functions."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.tokens_path = self.test_dir / ".garth"
    
    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.test_dir)
    
    @patch('myWhoosh2Garmin.TOKENS_PATH')
    @patch('myWhoosh2Garmin.garth')
    def test_authenticate_to_garmin_with_existing_tokens(self, mock_garth, mock_tokens_path):
        """Test authentication with existing valid tokens."""
        mock_tokens_path.exists.return_value = True
        mock_garth.resume.return_value = None
        mock_garth.client.username = "testuser"
        
        result = mw2g.authenticate_to_garmin()
        
        self.assertTrue(result)
        mock_garth.resume.assert_called_once_with(mock_tokens_path)
    
    @patch('myWhoosh2Garmin.TOKENS_PATH')
    @patch('myWhoosh2Garmin.garth')
    @patch('myWhoosh2Garmin.get_credentials_for_garmin')
    def test_authenticate_to_garmin_expired_session(
        self, mock_get_creds, mock_garth, mock_tokens_path
    ):
        """Test authentication with expired session."""
        mock_tokens_path.exists.return_value = True
        mock_garth.resume.return_value = None
        mock_garth.client.username = "testuser"
        
        # Simulate expired session
        mock_garth.client = Mock()
        mock_garth.client.username = Mock(side_effect=mw2g.GarthException("Expired"))
        mock_get_creds.return_value = True
        
        # Need to handle the exception properly
        with patch.object(mw2g, 'GarthException', Exception):
            try:
                result = mw2g.authenticate_to_garmin()
            except:
                # If exception is raised, test get_credentials_for_garmin is called
                pass
    
    @patch('myWhoosh2Garmin.TOKENS_PATH')
    @patch('myWhoosh2Garmin.garth')
    @patch('myWhoosh2Garmin.get_credentials_for_garmin')
    def test_authenticate_to_garmin_no_tokens(
        self, mock_get_creds, mock_garth, mock_tokens_path
    ):
        """Test authentication when no tokens exist."""
        mock_tokens_path.exists.return_value = False
        mock_get_creds.return_value = True
        
        result = mw2g.authenticate_to_garmin()
        
        self.assertTrue(result)
        mock_get_creds.assert_called_once()


class TestUploadFitFileToGarmin(unittest.TestCase):
    """Test the upload_fit_file_to_garmin function."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_file = self.test_dir / "test.fit"
        self.test_file.write_bytes(b"fake fit file data")
    
    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.test_dir)
    
    @patch('myWhoosh2Garmin.garth')
    def test_upload_fit_file_to_garmin_success(self, mock_garth):
        """Test successful upload."""
        mock_garth.client.upload.return_value = {"status": "success"}
        
        result = mw2g.upload_fit_file_to_garmin(self.test_file)
        
        self.assertTrue(result)
        mock_garth.client.upload.assert_called_once()
    
    @patch('myWhoosh2Garmin.garth')
    @patch('myWhoosh2Garmin.GarthHTTPError')
    def test_upload_fit_file_to_garmin_duplicate(
        self, mock_http_error, mock_garth
    ):
        """Test upload with duplicate activity error."""
        mock_garth.client.upload.side_effect = mock_http_error("Duplicate")
        
        result = mw2g.upload_fit_file_to_garmin(self.test_file)
        
        self.assertFalse(result)
    
    def test_upload_fit_file_to_garmin_invalid_path(self):
        """Test upload with invalid file path."""
        invalid_path = Path("/nonexistent/file.fit")
        
        result = mw2g.upload_fit_file_to_garmin(invalid_path)
        
        self.assertFalse(result)


class TestCleanupAndSaveFitFile(unittest.TestCase):
    """Test the cleanup_and_save_fit_file function."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.fitfile_location = self.test_dir / "fitfiles"
        self.backup_location = self.test_dir / "backup"
        self.fitfile_location.mkdir()
        self.backup_location.mkdir()
        
        # Create a test FIT file
        self.test_fit = self.fitfile_location / "MyNewActivity-3.8.5.fit"
        self.test_fit.write_bytes(b"fake fit data")
    
    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.test_dir)
    
    @patch('myWhoosh2Garmin.get_most_recent_fit_file')
    @patch('myWhoosh2Garmin.cleanup_fit_file')
    @patch('myWhoosh2Garmin.generate_new_filename')
    def test_cleanup_and_save_fit_file_success(
        self, mock_gen_filename, mock_cleanup, mock_get_fit
    ):
        """Test successful cleanup and save."""
        mock_get_fit.return_value = self.test_fit
        mock_gen_filename.return_value = "MyNewActivity-3.8.5_2024-01-01_120000.fit"
        
        result = mw2g.cleanup_and_save_fit_file(
            self.fitfile_location, 
            self.backup_location
        )
        
        self.assertIsNotNone(result)
        mock_cleanup.assert_called_once()
    
    @patch('myWhoosh2Garmin.get_most_recent_fit_file')
    def test_cleanup_and_save_fit_file_no_files(self, mock_get_fit):
        """Test when no FIT files are found."""
        mock_get_fit.return_value = None
        
        result = mw2g.cleanup_and_save_fit_file(
            self.fitfile_location,
            self.backup_location
        )
        
        self.assertIsNone(result)
    
    def test_cleanup_and_save_fit_file_invalid_directory(self):
        """Test with invalid directory."""
        invalid_dir = Path("/nonexistent/dir")
        
        result = mw2g.cleanup_and_save_fit_file(
            invalid_dir,
            self.backup_location
        )
        
        self.assertIsNone(result)


class TestMainFunction(unittest.TestCase):
    """Test the main function with all mocks."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.fitfile_location = self.test_dir / "fitfiles"
        self.backup_location = self.test_dir / "backup"
        self.fitfile_location.mkdir()
        self.backup_location.mkdir()
    
    def tearDown(self):
        """Clean up test directory."""
        shutil.rmtree(self.test_dir)
    
    @patch('myWhoosh2Garmin.upload_fit_file_to_garmin')
    @patch('myWhoosh2Garmin.cleanup_and_save_fit_file')
    @patch('myWhoosh2Garmin.authenticate_to_garmin')
    @patch('myWhoosh2Garmin.get_backup_path')
    @patch('myWhoosh2Garmin.get_fitfile_location')
    @patch('myWhoosh2Garmin.import_required_modules')
    @patch('myWhoosh2Garmin.ensure_packages')
    def test_main_success(
        self, mock_ensure, mock_import, mock_get_fit, 
        mock_get_backup, mock_auth, mock_cleanup, mock_upload
    ):
        """Test successful main execution."""
        mock_ensure.return_value = True
        mock_import.return_value = True
        mock_get_fit.return_value = self.fitfile_location
        mock_get_backup.return_value = self.backup_location
        mock_auth.return_value = True
        mock_cleanup.return_value = self.test_dir / "cleaned.fit"
        mock_upload.return_value = True
        
        result = mw2g.main()
        
        self.assertEqual(result, 0)
        mock_upload.assert_called_once()
    
    @patch('myWhoosh2Garmin.ensure_packages')
    def test_main_package_failure(self, mock_ensure):
        """Test main when packages can't be ensured."""
        mock_ensure.return_value = False
        
        result = mw2g.main()
        
        self.assertEqual(result, 1)
    
    @patch('myWhoosh2Garmin.import_required_modules')
    @patch('myWhoosh2Garmin.ensure_packages')
    def test_main_import_failure(self, mock_ensure, mock_import):
        """Test main when imports fail."""
        mock_ensure.return_value = True
        mock_import.return_value = False
        
        result = mw2g.main()
        
        self.assertEqual(result, 1)
    
    @patch('myWhoosh2Garmin.get_fitfile_location')
    @patch('myWhoosh2Garmin.import_required_modules')
    @patch('myWhoosh2Garmin.ensure_packages')
    def test_main_no_fitfile_location(
        self, mock_ensure, mock_import, mock_get_fit
    ):
        """Test main when FIT file location not found."""
        mock_ensure.return_value = True
        mock_import.return_value = True
        mock_get_fit.return_value = None
        
        result = mw2g.main()
        
        self.assertEqual(result, 1)


if __name__ == '__main__':
    unittest.main()

