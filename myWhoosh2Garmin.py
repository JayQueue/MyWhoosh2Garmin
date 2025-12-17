#!/usr/bin/env python3
"""
Script name: myWhoosh2Garmin.py
Usage: "python3 myWhoosh2Garmin.py"
Description:    Checks for MyNewActivity-<myWhooshVersion>.fit
                Adds avg power and heartrate
                Removes temperature
                Creates backup for the file with a timestamp as a suffix
Credits:        Garth by matin - for authenticating and uploading with 
                Garmin Connect.
                https://github.com/matin/garth
                Fit_tool by mtucker - for parsing the fit file.
                https://bitbucket.org/stagescycling/python_fit_tool.git/src
                mw2gc by embeddedc - used as an example to fix the avg's. 
                https://github.com/embeddedc/mw2gc
"""
import os
import json
import subprocess
import sys
import logging
import re
from typing import List, Iterable, Optional, Tuple
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
from getpass import getpass
from pathlib import Path
import importlib.util


SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FILE_PATH = SCRIPT_DIR / "myWhoosh2Garmin.log"
JSON_FILE_PATH = SCRIPT_DIR / "backup_path.json"
INSTALLED_PACKAGES_FILE = SCRIPT_DIR / "installed_packages.json"
TOKENS_PATH = SCRIPT_DIR / '.garth'
FILE_DIALOG_TITLE = "MyWhoosh2Garmin"
# Fix for https://github.com/JayQueue/MyWhoosh2Garmin/issues/2
MYWHOOSH_PREFIX_WINDOWS = "MyWhooshTechnologyService."


def setup_logging() -> logging.Logger:
    """Configure and return a logger instance."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    # Avoid adding multiple handlers if logger already configured
    if not logger.handlers:
        file_handler = logging.FileHandler(LOG_FILE_PATH)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


logger = setup_logging()


def load_installed_packages() -> set[str]:
    """Load the set of installed packages from a JSON file."""
    if INSTALLED_PACKAGES_FILE.exists():
        try:
            with INSTALLED_PACKAGES_FILE.open("r") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error loading installed packages: {e}")
            return set()
    return set()


def save_installed_packages(installed_packages: set[str]) -> None:
    """Save the set of installed packages to a JSON file."""
    try:
        with INSTALLED_PACKAGES_FILE.open("w") as f:
            json.dump(list(installed_packages), f)
    except IOError as e:
        logger.error(f"Error saving installed packages: {e}")


def get_pip_command() -> Optional[List[str]]:
    """Return the pip command if pip is available."""
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return [sys.executable, "-m", "pip"]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def install_package(package: str) -> bool:
    """Install the specified package using pip.
    
    Returns:
        True if installation succeeded, False otherwise.
    """
    pip_command = get_pip_command()
    if pip_command:
        try:
            logger.info(f"Installing missing package: {package}.")
            subprocess.check_call(
                pip_command + ["install", package],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error installing {package}: {e}.")
            return False
    else:
        logger.debug("pip is not available. Unable to install packages.")
        return False


def ensure_packages() -> bool:
    """Ensure all required packages are installed and tracked.
    
    Returns:
        True if all packages are available, False otherwise.
    """
    required_packages = ["garth", "fit_tool"]
    installed_packages = load_installed_packages()
    all_available = True

    for package in required_packages:
        if package in installed_packages:
            logger.debug(f"Package {package} is already tracked as installed.")
            continue

        if not importlib.util.find_spec(package):
            logger.info(f"Package {package} not found. Attempting to install...")
            if not install_package(package):
                all_available = False
                continue

        try:
            __import__(package)
            logger.info(f"Successfully imported {package}.")
            installed_packages.add(package)
        except ModuleNotFoundError:
            logger.error(f"Failed to import {package} even after installation.")
            all_available = False

    save_installed_packages(installed_packages)
    return all_available


# Imports - will be loaded after ensure_packages()
garth = None
GarthException = None
GarthHTTPError = None
FitFile = None
FitFileBuilder = None
FileCreatorMessage = None
RecordMessage = None
RecordTemperatureField = None
SessionMessage = None
LapMessage = None


def import_required_modules() -> bool:
    """Import required modules after ensuring packages are installed.
    
    Returns:
        True if all imports succeeded, False otherwise.
    """
    global garth, GarthException, GarthHTTPError, FitFile, FitFileBuilder
    global FileCreatorMessage, RecordMessage, RecordTemperatureField
    global SessionMessage, LapMessage
    
    try:
        import garth
        from garth.exc import GarthException, GarthHTTPError
        from fit_tool.fit_file import FitFile
        from fit_tool.fit_file_builder import FitFileBuilder
        from fit_tool.profile.messages.file_creator_message import (
            FileCreatorMessage
        )
        from fit_tool.profile.messages.record_message import (
            RecordMessage,
            RecordTemperatureField
        )
        from fit_tool.profile.messages.session_message import SessionMessage
        from fit_tool.profile.messages.lap_message import LapMessage
        return True
    except ImportError as e:
        logger.error(f"Error importing modules: {e}")
        return False 


def get_fitfile_location() -> Optional[Path]:
    """
    Get the location of the FIT file directory based on the operating system.

    Returns:
        Path: The path to the FIT file directory, or None if not found.

    Raises:
        RuntimeError: If the operating system is unsupported.
    """
    if os.name == "posix":  # macOS and Linux
        target_path = (
           Path.home()
           / "Library"
           / "Containers"
           / "com.whoosh.whooshgame"
           / "Data"
           / "Library"
           / "Application Support"
           / "Epic"
           / "MyWhoosh"
           / "Content"
           / "Data"
        )
        if target_path.is_dir():
            return target_path
        else:
            logger.error(f"Target path {target_path} does not exist. "
                         "Check your MyWhoosh installation.")
            return None
    elif os.name == "nt":  # Windows
        try:
            base_path = Path.home() / "AppData" / "Local" / "Packages"
            target_path = None
            
            for directory in base_path.iterdir():
                if (directory.is_dir() and 
                        directory.name.startswith(MYWHOOSH_PREFIX_WINDOWS)):
                    candidate_path = (
                        directory
                        / "LocalCache"
                        / "Local"
                        / "MyWhoosh"
                        / "Content"
                        / "Data"
                    )
                    if candidate_path.is_dir():
                        target_path = candidate_path
                        break
            
            if target_path:
                return target_path
            else:
                logger.error(f"No valid MyWhoosh directory found in {base_path}")
                return None
        except PermissionError as e:
            logger.error(f"Permission denied: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    else:
        logger.error("Unsupported OS")
        return None


def get_backup_path(json_file: Path = JSON_FILE_PATH) -> Optional[Path]:
    """
    This function checks if a backup path already exists in a JSON file.
    If it does, it returns the stored path. If the file does not exist, 
    it prompts the user to select a directory via a file dialog, saves 
    the selected path to the JSON file, and returns it.

    Args:
        json_file: Path to the JSON file containing the backup path.

    Returns:
        Path: The selected backup path, or None if no path was selected.
    """
    if json_file.exists():
        try:
            with json_file.open('r') as f:
                data = json.load(f)
                backup_path = data.get('backup_path')
            if backup_path and Path(backup_path).is_dir():
                logger.info(f"Using backup path from JSON: {backup_path}.")
                return Path(backup_path)
            else:
                logger.error("Invalid backup path stored in JSON.")
                return None
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading backup path from JSON: {e}")
            return None
    else:
        root = tk.Tk()
        root.withdraw() 
        backup_path = filedialog.askdirectory(
            title=f"Select {FILE_DIALOG_TITLE} Directory"
        )
        if not backup_path:
            logger.info("No directory selected, exiting.")
            return None
        try:
            with json_file.open('w') as f:
                json.dump({'backup_path': backup_path}, f)
            logger.info(f"Backup path saved to {json_file}.")
            return Path(backup_path)
        except IOError as e:
            logger.error(f"Error saving backup path: {e}")
            return None

def get_credentials_for_garmin() -> bool:
    """
    Prompt the user for Garmin credentials and authenticate using Garth.

    Returns:
        True if authentication succeeded, False otherwise.
    """
    username = input("Username: ")
    password = getpass("Password: ")
    logger.info("Authenticating...")
    try:
        garth.login(username, password)
        garth.save(TOKENS_PATH)
        print()
        logger.info("Successfully authenticated!")
        return True
    except GarthHTTPError:
        logger.info("Wrong credentials. Please check username and password.")
        return False


def authenticate_to_garmin() -> bool:
    """
    Authenticate the user to Garmin by checking for existing tokens and 
    resuming the session, or prompting for credentials if no session 
    exists or the session is expired.

    Returns:
        True if authentication succeeded, False otherwise.
    """
    try:
        if TOKENS_PATH.exists():
            garth.resume(TOKENS_PATH)
            try:
                logger.info(f"Authenticated as: {garth.client.username}")
                return True
            except GarthException:
                logger.info("Session expired. Re-authenticating...")
                return get_credentials_for_garmin()
        else:
            logger.info("No existing session. Please log in.")
            return get_credentials_for_garmin()
    except GarthException as e:
        logger.info(f"Authentication error: {e}")
        return False


def calculate_avg(values: Iterable[float]) -> float:
    """
    Calculate the average of a list of values, returning 0 if the list is empty.

    Args:
        values: The iterable of values to average.

    Returns:
        The average value or 0.0 if the list is empty.
    """
    values_list = list(values)
    return sum(values_list) / len(values_list) if values_list else 0.0


def append_value(values: List[int], message: object, field_name: str) -> None:
    """
    Appends a value to the 'values' list based on a field from 'message'.

    Args:
        values (List[int]): The list to append the value to.
        message (object): The object that holds the field value.
        field_name (str): The name of the field to retrieve from the message.

    Returns:
        None
    """
    value=getattr(message, field_name, None)
    values.append(value if value else 0)


def reset_values() -> Tuple[List[int], List[int], List[int]]:
    """
    Resets and returns three empty lists for cadence, power 
    and heart rate values.

    Returns:
        A tuple containing three empty lists 
        (cadence, power, and heart rate).
    """
    return [], [], []


def cleanup_fit_file(fit_file_path: Path, new_file_path: Path) -> None:
    """
    Clean up the FIT file by processing and removing unnecessary fields.
    Also, calculate average values for cadence, power, and heart rate.

    Args:
        fit_file_path: The path to the input FIT file.
        new_file_path: The path to save the processed FIT file.

    Raises:
        IOError: If the file cannot be read or written.
        ValueError: If the FIT file is invalid.
    """
    builder = FitFileBuilder()
    fit_file = FitFile.from_file(str(fit_file_path))
    cadence_values, power_values, heart_rate_values = reset_values()

    for record in fit_file.records:
        message = record.message
        if isinstance(message, LapMessage):
            continue
        if isinstance(message, RecordMessage):
            message.remove_field(RecordTemperatureField.ID)
            append_value(cadence_values, message, "cadence")
            append_value(power_values, message, "power")
            append_value(heart_rate_values, message, "heart_rate")
        if isinstance(message, SessionMessage):
            if not message.avg_cadence:
                message.avg_cadence = int(calculate_avg(cadence_values))
            if not message.avg_power:
                message.avg_power = int(calculate_avg(power_values))
            if not message.avg_heart_rate:
                message.avg_heart_rate = int(calculate_avg(heart_rate_values))
            cadence_values, power_values, heart_rate_values = reset_values()
        builder.add(message)
    builder.build().to_file(str(new_file_path))
    logger.info(f"Cleaned-up file saved as {new_file_path}")


def get_most_recent_fit_file(fitfile_location: Path) -> Optional[Path]:
    """
    Returns the most recent .fit file based on versioning in the filename.
    
    Args:
        fitfile_location: Directory to search for FIT files.
        
    Returns:
        Path to the most recent FIT file, or None if none found.
    """
    fit_files = list(fitfile_location.glob("MyNewActivity-*.fit"))
    if not fit_files:
        return None
    
    def extract_version(file_path: Path) -> Tuple[int, ...]:
        """Extract version numbers from filename for sorting."""
        version_str = file_path.stem.split('-')[-1]
        numbers = re.findall(r'(\d+)', version_str)
        return tuple(map(int, numbers)) if numbers else (0,)
    
    fit_files = sorted(fit_files, key=extract_version, reverse=True)
    return fit_files[0]


def generate_new_filename(fit_file: Path) -> str:
    """Generates a new filename with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return f"{fit_file.stem}_{timestamp}.fit"


def cleanup_and_save_fit_file(
    fitfile_location: Path, 
    backup_location: Path
) -> Optional[Path]:
    """
    Clean up the most recent .fit file in a directory and save it 
    with a timestamped filename.

    Args:
        fitfile_location: The directory containing the .fit files.
        backup_location: The directory to save the cleaned file.

    Returns:
        Path to the newly saved and cleaned .fit file, 
        or None if no .fit file is found or if the path is invalid.
    """
    if not fitfile_location or not fitfile_location.is_dir():
        logger.error(f"The specified path is not a directory: {fitfile_location}.")
        return None

    logger.debug(f"Checking for .fit files in directory: {fitfile_location}.")
    fit_file = get_most_recent_fit_file(fitfile_location)

    if not fit_file:
        logger.info("No .fit files found.")
        return None

    logger.debug(f"Found the most recent .fit file: {fit_file.name}.")
    new_filename = generate_new_filename(fit_file)

    if not backup_location or not backup_location.exists():
        logger.error(f"{backup_location} does not exist. Did you delete it?")
        return None

    new_file_path = backup_location / new_filename
    logger.info(f"Cleaning up {new_file_path}.")

    try:
        cleanup_fit_file(fit_file, new_file_path)  
        logger.info(f"Successfully cleaned {fit_file.name} "
                    f"and saved it as {new_file_path.name}.")
        return new_file_path
    except Exception as e:
        logger.error(f"Failed to process {fit_file.name}: {e}.")
        return None


def upload_fit_file_to_garmin(new_file_path: Path) -> bool:
    """
    Upload a .fit file to Garmin using the Garth client.

    Args:
        new_file_path: The path to the .fit file to upload.

    Returns:
        True if upload succeeded, False otherwise.
    """
    if not new_file_path or not new_file_path.exists():
        logger.error(f"Invalid file path: {new_file_path}.")
        return False
    
    try:
        with new_file_path.open("rb") as f:
            uploaded = garth.client.upload(f)
            logger.debug(f"Upload response: {uploaded}")
            logger.info("Successfully uploaded to Garmin Connect.")
            return True
    except GarthHTTPError as e:
        logger.info("Duplicate activity found on Garmin Connect.")
        return False
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return False


def main() -> int:
    """
    Main function to authenticate to Garmin, clean and save the FIT file, 
    and upload it to Garmin.

    Returns:
        Exit code: 0 for success, 1 for failure.
    """
    # Ensure required packages are installed
    if not ensure_packages():
        logger.error("Failed to ensure required packages are installed.")
        return 1
    
    # Import required modules
    if not import_required_modules():
        logger.error("Failed to import required modules.")
        return 1
    
    # Get FIT file location
    fitfile_location = get_fitfile_location()
    if not fitfile_location:
        logger.error("Could not locate MyWhoosh FIT file directory.")
        return 1
    
    # Get backup location
    backup_location = get_backup_path()
    if not backup_location:
        logger.error("Could not get backup location.")
        return 1
    
    # Authenticate to Garmin
    if not authenticate_to_garmin():
        logger.error("Failed to authenticate to Garmin.")
        return 1
    
    # Clean and save FIT file
    new_file_path = cleanup_and_save_fit_file(fitfile_location, backup_location)
    if not new_file_path:
        logger.error("Failed to process FIT file.")
        return 1
    
    # Upload to Garmin
    upload_fit_file_to_garmin(new_file_path)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
